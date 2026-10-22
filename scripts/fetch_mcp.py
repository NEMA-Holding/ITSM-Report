"""Pull ticket and change lists from the Nema helpdesk through the Zoho MCP server.
Replaces fetch_sdp.py: GitHub no longer holds a Zoho API key, only the MCP server address.
The MCP server exposes only the tools enabled in the Zoho MCP console (no attachment tool),
so nothing else can be fetched with it. Runs inside GitHub Actions; no Claude needed.

Environment (GitHub secrets):
  ZOHO_MCP_URL    the MCP server URL from the Zoho MCP console (it contains the server key)
  ZOHO_MCP_TOKEN  optional: a bearer token, if the server is set up to require one
  SDP_PORTAL      optional: portal name, default "nemahelpdesk"

usage: python3 fetch_mcp.py OUT_DIR
Writes OUT_DIR/req/pageNNN.json and OUT_DIR/chg/pageNNN.json in the same shape build_reports.py reads.
"""
import json, os, sys, time, urllib.request

out = sys.argv[1] if len(sys.argv) > 1 else "pages"
for d in ("req", "chg"):
    os.makedirs(os.path.join(out, d), exist_ok=True)

URL = os.environ["ZOHO_MCP_URL"].strip()
PORTAL = os.environ.get("SDP_PORTAL", "nemahelpdesk")
HEAD = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
if os.environ.get("ZOHO_MCP_TOKEN"):
    HEAD["Authorization"] = "Bearer " + os.environ["ZOHO_MCP_TOKEN"]
SDP_HEADERS = {"Accept": "application/vnd.manageengine.sdp.v3+json", "Content-Type": "application/x-www-form-urlencoded"}
FIELDS = ["display_id", "subject", "status", "group", "created_time", "request_type", "due_by_time",
          "technician", "requester", "customer", "is_overdue", "is_first_response_overdue",
          "completed_time", "is_fcr"]
CHANGE_FIELDS = ["display_id", "title", "created_time", "status", "change_owner", "customer", "group", "change_type",
                 "stage", "approval_status", "risk", "priority", "category", "subcategory", "completed_time"]
_id = [0]


def rpc(method, params=None, notify=False):
    """One JSON-RPC call over MCP streamable HTTP; handles JSON or event-stream replies."""
    body = {"jsonrpc": "2.0", "method": method}
    if params is not None: body["params"] = params
    if not notify:
        _id[0] += 1; body["id"] = _id[0]
    for attempt in range(4):
        try:
            req = urllib.request.Request(URL, data=json.dumps(body).encode(), headers=HEAD, method="POST")
            with urllib.request.urlopen(req, timeout=120) as r:
                sid = r.headers.get("Mcp-Session-Id")
                if sid: HEAD["Mcp-Session-Id"] = sid
                raw = r.read().decode("utf8", "replace")
                ctype = r.headers.get("Content-Type", "")
            break
        except Exception:
            if attempt == 3: raise
            time.sleep(5 * (attempt + 1))
    if notify: return None
    if "text/event-stream" in ctype:
        msgs = [json.loads(l[5:]) for l in raw.splitlines() if l.startswith("data:") and l[5:].strip()]
        msg = next((m for m in msgs if m.get("id") == body["id"]), msgs[-1] if msgs else {})
    else:
        msg = json.loads(raw) if raw.strip() else {}
    if "error" in msg: raise RuntimeError("%s failed: %s" % (method, msg["error"]))
    return msg.get("result", {})


def tool(name, args):
    res = rpc("tools/call", {"name": name, "arguments": args})
    if res.get("isError"): raise RuntimeError("tool %s error: %s" % (name, json.dumps(res)[:400]))
    text = "".join(c.get("text", "") for c in res.get("content", []) if c.get("type") == "text")
    data = json.loads(text) if text else res.get("structuredContent", {})
    return data.get("data", data)                     # same shape as the helpdesk API reply


def pull(tname, key, folder, list_info, page_args):
    start, page = 1, 1
    while True:
        li = dict({"row_count": 100, "start_index": start, "get_total_count": True,
                   "sort_field": "created_time", "sort_order": "asc"}, **list_info)
        d = tool(tname, page_args(li))
        json.dump(d, open(os.path.join(out, folder, "page%03d.json" % page), "w"))
        info, n = d.get("list_info", {}), len(d.get(key, []))
        print(tname, "page", page, "rows", n, "total", info.get("total_count"))
        if not info.get("has_more_rows") or n == 0: return
        start += 100; page += 1


rpc("initialize", {"protocolVersion": "2025-03-26", "capabilities": {},
                   "clientInfo": {"name": "itsm-report", "version": "1.0"}})
rpc("notifications/initialized", notify=True)
names = [t["name"] for t in rpc("tools/list").get("tools", [])]
find = lambda suffix: next((n for n in names if n.endswith(suffix)), None)
T_REQ, T_CHG = find("getListRequest"), find("getListOfChanges")
if not T_REQ: sys.exit("MCP server has no getListRequest tool; available: %s" % names)
print("tools enabled on the MCP server:", len(names), "| using:", T_REQ, T_CHG)

with_query = lambda li: {"path_variables": {"portal": PORTAL}, "headers": SDP_HEADERS,
                         "query_params": {"input_data": json.dumps({"list_info": li})}}
pull(T_REQ, "requests", "req", {"fields_required": FIELDS}, with_query)

if T_CHG:
    try:
        pull(T_CHG, "changes", "chg", {"fields_required": CHANGE_FIELDS}, with_query)
    except RuntimeError as e:                       # tool set up without paging options
        print("change list paging not accepted (%s); fetching the default page only" % str(e)[:120])
        d = tool(T_CHG, {"path_variables": {"portal": PORTAL}})
        json.dump(d, open(os.path.join(out, "chg", "page001.json"), "w"))
        if d.get("list_info", {}).get("has_more_rows"):
            print("WARNING: only the first %d changes were returned; enable paging (query_params) on the "
                  "change list tool in the Zoho MCP console" % len(d.get("changes", [])))
else:
    print("MCP server has no change list tool; ERP change requests will be empty")
