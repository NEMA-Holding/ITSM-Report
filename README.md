# ITSM Reports

Publishes the four ITSM reports at https://itsmreport.adu.ac.ae so anyone with the link sees live data, without a Claude account.

| Address | Report |
|---|---|
| itsmreport.adu.ac.ae | Landing page with links to all reports |
| /executive | Executive Report (all tickets) |
| /erp | ERP Report, with ERP change requests |
| /app-support | Application Report (L2 Application: Abu Dhabi University, Liwa University, Knowledge Group) |
| /adu | Abu Dhabi University Report |
| /liwa | Liwa University Report |
| /knowledge-group | Knowledge Group Report |
| /arclight | ArcLight Services Report |
| /salesforce | Salesforce Report (SalesForce Team, SalesForce External, L1 Support- SalesForce; all affiliates incl. SalesForce Notification) |
| /network | Network Report (L2 Network, all affiliates) |
| /system | System Report (L2 System, all affiliates) |
| /lms | LMS Report (L2 LMS, all affiliates) |

## How it works
Every 5 minutes GitHub reads all tickets and changes from the Nema helpdesk (ServiceDesk Plus) with its own read-only API key, splits them per report, and republishes the site. If the pull is incomplete nothing is published, so the totals always tally.

## Contents
| Item | Purpose |
|---|---|
| `site/index.html` | Landing page |
| `site/<report>/index.html` | Each report page (same design as in Claude) |
| `site/<report>/data/snap.js` | Each report's tickets, rebuilt every 5 minutes |
| `site/erp/data/chg.js` | ERP change requests, rebuilt every 5 minutes |
| `site/CNAME` | Site address: itsmreport.adu.ac.ae |
| `scripts/fetch_sdp.py` | Reads all tickets and changes from the helpdesk API |
| `scripts/build_reports.py` | Splits tickets per report; `REPORTS` at the top sets which tickets each report shows |
| `.github/workflows/refresh.yml` | Runs every 5 minutes (and on every change) and publishes the site |

## Setup
1. **Zoho API key** — api-console.zoho.com, read-only technician account → Add Client → Self Client.
   Generate Code with scope `SDPOnDemand.requests.READ,SDPOnDemand.changes.READ`, duration 10 minutes, then within 10 minutes run:
   `curl -X POST "https://accounts.zoho.com/oauth/v2/token" -d "code=CODE&client_id=ID&client_secret=SECRET&grant_type=authorization_code"`
   and keep the `refresh_token`.
2. **Repository** — create `itsm-report` on GitHub and upload this folder, including the hidden `.github` folder.
3. **Secrets** — Settings → Secrets and variables → Actions:
   `ZOHO_CLIENT_ID`, `ZOHO_CLIENT_SECRET`, `ZOHO_REFRESH_TOKEN`,
   `ZOHO_ACCOUNTS_URL` (e.g. `https://accounts.zoho.com`),
   `SDP_BASE_URL` (helpdesk address up to `/app/nemahelpdesk`).
4. **Pages** — Settings → Pages → Source: GitHub Actions.
5. **First run** — Actions → Refresh ITSM Reports → Run workflow.
6. **Domain** — DNS: `CNAME itsmreport → <github-account>.github.io`; then Settings → Pages → Custom domain `itsmreport.adu.ac.ae` → Enforce HTTPS.
7. **Check** — each report's total must match the helpdesk and tally with its breakdowns.

## Access
Anyone with the link can open the site, and the detailed reports show requester names. For staff-only access, put Entra ID SSO or Cloudflare Access in front of the domain.
