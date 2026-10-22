"""Build the data files for every report from one pull of the Nema helpdesk.
usage: python3 build_reports.py PAGES_DIR SITE_DIR

To add a report or change which tickets a report shows, edit REPORTS below.
Stops without writing anything if fewer tickets arrived than the helpdesk total,
so a partial pull never goes live.

Ticket subjects, requester names and change titles are NOT written to the public data files.
They go into data/detail.json, encrypted with AES-256-GCM under a key derived from the
REPORT_PASSWORD secret (PBKDF2-SHA256). The report pages decrypt it in the browser after
"Log in". Without REPORT_PASSWORD no detail file is written, so the details stay unpublished.
"""
import base64, glob, json, os, sys, time

pages_dir, site = sys.argv[1], sys.argv[2]

name = lambda o: (o.get("name") or "") if isinstance(o, dict) else ""
val = lambda o: o.get("value") if isinstance(o, dict) else o

# Affiliates shown in the Application report
APP_AFFILIATES = {"Abu Dhabi University", "Liwa University", "Knowledge Group"}

# Groups shown in the Salesforce report (each affiliate has its own copy of these groups)
SALESFORCE_GROUPS = {"SalesForce Team", "SalesForce External", "L1 Support- SalesForce"}

# Which tickets each report shows: (folder, filter on group and customer name, row format)
REPORTS = [
    ("erp",         lambda g, c: g.lower().startswith("erp"),                          "detail"),
    ("adu",         lambda g, c: c == "Abu Dhabi University" and g != "",              "detail"),  # tickets with no group are left out
    ("liwa",        lambda g, c: c == "Liwa University",                               "detail"),
    ("knowledge-group", lambda g, c: c == "Knowledge Group",                           "detail"),
    ("arclight",    lambda g, c: c == "ArcLight Services",                             "detail"),
    ("app-support", lambda g, c: g == "L2 Application" and c in APP_AFFILIATES,        "detail"),
    ("salesforce",  lambda g, c: g in SALESFORCE_GROUPS or c == "SalesForce Notification", "detail"),
    ("network",     lambda g, c: g == "L2 Network",                                    "detail"),
    ("system",      lambda g, c: g == "L2 System",                                     "detail"),
    ("lms",         lambda g, c: g == "L2 LMS",                                        "detail"),
    ("executive",   lambda g, c: True,                                                 "summary"),
]


def detail(q):
    return [str(val(q["display_id"])), q.get("subject") or "", int(q["created_time"]["value"]), name(q.get("status")),
            name(q.get("technician")) or "Unassigned", name(q.get("group")), name(q.get("customer")),
            name(q.get("requester")), name(q.get("request_type")) or "Incident", val(q.get("due_by_time")),
            1 if q.get("is_overdue") else 0, 1 if q.get("is_first_response_overdue") else 0]


def summary(q):
    done = val(q.get("completed_time"))
    return [str(val(q["display_id"])), int(q["created_time"]["value"]), name(q.get("status")), name(q.get("group")),
            name(q.get("customer")), name(q.get("request_type")) or "Incident", 1 if q.get("is_overdue") else 0,
            name(q.get("technician")) or "Unassigned", int(done) if done else None, 1 if q.get("is_fcr") else 0]


def change(c):
    cat, sub = name(c.get("category")), name(c.get("subcategory"))
    return [str(val(c["display_id"])), c.get("title") or "", int(c["created_time"]["value"]), name(c.get("status")),
            name(c.get("change_owner")) or "Unassigned", name(c.get("customer")), name(c.get("group")),
            name(c.get("change_type")), name(c.get("stage")), name(c.get("approval_status")),
            name(c.get("risk")), name(c.get("priority")), cat + (" / " + sub if sub else ""),
            val(c.get("completed_time"))]


def read(folder, key):
    rows, total = {}, None
    for f in sorted(glob.glob(os.path.join(pages_dir, folder, "*.json"))):
        d = json.load(open(f)); d = d.get("data", d)
        total = d.get("list_info", {}).get("total_count", total)
        for q in d.get(key, []):
            rows[q["id"]] = q
    return list(rows.values()), total


tickets, total = read("req", "requests")
if not tickets or total is None or len(tickets) < int(total):
    sys.exit("incomplete pull: %d of %s tickets, nothing published" % (len(tickets), total))
changes, _ = read("chg", "changes")

asof = int(time.time() * 1000)
dump = lambda v: json.dumps(v, ensure_ascii=False, separators=(",", ":"))
PASSWORD = os.environ.get("REPORT_PASSWORD", "")
ITERATIONS = 600000

if PASSWORD:
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
else:
    print("REPORT_PASSWORD not set: ticket details are not published")


def write_detail(folder, secret):
    path = os.path.join(site, folder, "data", "detail.json")
    if not PASSWORD:
        if os.path.exists(path): os.remove(path)
        return
    salt, iv = os.urandom(16), os.urandom(12)
    key = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=ITERATIONS).derive(PASSWORD.encode("utf8"))
    ct = AESGCM(key).encrypt(iv, dump(secret).encode("utf8"), None)
    b64 = lambda b: base64.b64encode(b).decode("ascii")
    json.dump({"v": 1, "kdf": "PBKDF2-SHA256", "iter": ITERATIONS, "salt": b64(salt), "iv": b64(iv), "ct": b64(ct)}, open(path, "w"))


# ERP change requests: categories starting with "ERP"
erp_chg = sorted((change(c) for c in changes if name(c.get("category")).upper().startswith("ERP")), key=lambda r: int(r[0]))

for folder, keep, fmt in REPORTS:
    rows = [(detail if fmt == "detail" else summary)(q) for q in tickets
            if keep(name(q.get("group")), name(q.get("customer")))]
    path = os.path.join(site, folder, "data", "snap.js")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if fmt == "detail":
        secret = {"t": {r[0]: [r[1], r[7]] for r in rows}}
        for r in rows: r[1], r[7] = "", ""                       # subject and requester only in the encrypted file
        if folder == "erp":
            secret["c"] = {r[0]: r[1] for r in erp_chg}
            public_chg = [[r[0], ""] + r[2:] for r in erp_chg]     # change title only in the encrypted file
            open(os.path.join(site, "erp", "data", "chg.js"), "w", encoding="utf8").write("window.CHG=%s;\n" % dump(public_chg))
        write_detail(folder, secret)
    open(path, "w", encoding="utf8").write("window.SNAP_ASOF=%d;\nwindow.SNAP=%s;\n" % (asof, dump(rows)))
    print(folder, len(rows), "tickets")

print("erp", len(erp_chg), "changes;", len(tickets), "tickets in total")
