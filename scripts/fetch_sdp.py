"""Pull all requests and changes from the Nema helpdesk (ServiceDesk Plus Cloud) for the ITSM reports.
Runs inside GitHub Actions; no Claude needed.

Environment variables (GitHub repository secrets):
  ZOHO_CLIENT_ID, ZOHO_CLIENT_SECRET, ZOHO_REFRESH_TOKEN
  ZOHO_ACCOUNTS_URL  e.g. https://accounts.zoho.com  (match your data centre: .eu / .in / .com.au ...)
  SDP_BASE_URL       portal address up to the portal name, e.g. https://sdpondemand.manageengine.com/app/nemahelpdesk

usage: python3 fetch_sdp.py OUT_DIR
Writes OUT_DIR/req/pageNNN.json (all requests) and OUT_DIR/chg/pageNNN.json (all changes).
"""
import json, os, sys, time, urllib.parse, urllib.request

out = sys.argv[1] if len(sys.argv) > 1 else "pages"
for d in ("req", "chg"):
    os.makedirs(os.path.join(out, d), exist_ok=True)

FIELDS = ["display_id", "subject", "status", "group", "created_time", "request_type", "due_by_time",
          "technician", "requester", "customer", "is_overdue", "is_first_response_overdue",
          "completed_time", "is_fcr"]


def token():
    data = urllib.parse.urlencode({
        "refresh_token": os.environ["ZOHO_REFRESH_TOKEN"],
        "client_id": os.environ["ZOHO_CLIENT_ID"],
        "client_secret": os.environ["ZOHO_CLIENT_SECRET"],
        "grant_type": "refresh_token",
    }).encode()
    url = os.environ["ZOHO_ACCOUNTS_URL"].rstrip("/") + "/oauth/v2/token"
    with urllib.request.urlopen(urllib.request.Request(url, data=data, method="POST"), timeout=60) as r:
        t = json.load(r)
    if "access_token" not in t:
        sys.exit("token error: %s" % t)
    return t["access_token"]


HEADERS = {"Authorization": "Zoho-oauthtoken " + token(),
           "Accept": "application/vnd.manageengine.sdp.v3+json"}
BASE = os.environ["SDP_BASE_URL"].rstrip("/") + "/api/v3/"


def get(module, list_info):
    url = BASE + module + "?input_data=" + urllib.parse.quote(json.dumps({"list_info": list_info}))
    for attempt in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=60) as r:
                return json.load(r)
        except Exception:
            if attempt == 3:
                raise
            time.sleep(5 * (attempt + 1))


def pull(module, key, folder, extra):
    start, page = 1, 1
    while True:
        d = get(module, dict({"row_count": 100, "start_index": start, "get_total_count": True,
                              "sort_field": "created_time", "sort_order": "asc"}, **extra))
        json.dump(d, open(os.path.join(out, folder, "page%03d.json" % page), "w"))
        li, n = d.get("list_info", {}), len(d.get(key, []))
        print(module, "page", page, "rows", n, "total", li.get("total_count"))
        if not li.get("has_more_rows") or n == 0:
            return
        start += 100
        page += 1


pull("requests", "requests", "req", {"fields_required": FIELDS})
CHANGE_FIELDS = ["display_id", "title", "created_time", "status", "change_owner", "customer", "group", "change_type",
                 "stage", "approval_status", "risk", "priority", "category", "subcategory", "completed_time"]
pull("changes", "changes", "chg", {"fields_required": CHANGE_FIELDS})   # no descriptions or plans
