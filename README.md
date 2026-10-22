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
Every 10 minutes GitHub reads the ticket and change lists from the Nema helpdesk (ServiceDesk Plus) through the Zoho MCP server, splits them per report, and republishes the site. If the pull is incomplete nothing is published, so the totals always tally.

The MCP server has only two tools enabled (getListRequest, getListOfChanges), so attachments, resolutions, notes and conversations cannot be fetched. GitHub holds no Zoho API key, only the MCP server address.

Ticket subjects, requester names and change titles are encrypted (AES-256-GCM, key from the REPORT_PASSWORD secret) and shown only after Log in.

## Contents
| Item | Purpose |
|---|---|
| `site/index.html` | Landing page |
| `site/<report>/index.html` | Each report page |
| `site/<report>/data/` | Built on every run, never stored in the repository |
| `site/lib/` | Download PDF and Log in code, and the PDF libraries (MIT) |
| `site/img/` | Logos and photos |
| `scripts/fetch_mcp.py` | Reads the ticket and change lists through the Zoho MCP server |
| `scripts/build_reports.py` | Splits tickets per report and encrypts the details; `REPORTS` at the top sets which tickets each report shows |
| `.github/workflows/refresh.yml` | Runs every 10 minutes (and on every change) and publishes the site |

## Secrets (Settings → Secrets and variables → Actions)
| Secret | Purpose |
|---|---|
| `ZOHO_MCP_URL` | Zoho MCP server address (from the Zoho MCP console → Connect) |
| `REPORT_PASSWORD` | Password for Log in on the detailed reports |

## Check after every change
Each report's total must match the helpdesk and tally with its breakdowns.

## Access
Anyone with the link can open the summary figures; ticket details need Log in. For staff-only access, put Entra ID SSO or Cloudflare Access in front of the domain.
