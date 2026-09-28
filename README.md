# GSC + GA4 Export

![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Linux-lightgrey.svg)

A local Python tool that pulls data from Google Search Console and Google Analytics 4, merges both sources, and exports structured XLSX reports — no SaaS dependency, no data leaving your machine.

![GSC + GA4 Export Header](docs/gsc-ga4-export-header.webp)

---

## Why I built this

Every reporting workflow I tried required either a paid SaaS subscription, a Google Sheets plugin that breaks on API updates, or a Python script that only does one thing. None of them merged GSC and GA4 data at the URL level, calculated month-over-month deltas, and flagged cannibalization in the same export.

This tool does all of that locally, in one run, with a clean XLSX output you can hand to a client or drop into a dashboard.

---

## What it does

- Fetches GSC queries, pages, Discover, and sitemap coverage
- Fetches GA4 page performance and traffic sources
- Merges GSC + GA4 data by URL into a single sheet
- Calculates month-over-month deltas for clicks, impressions, and position
- Identifies CTR opportunities: high impressions, low CTR, strong position
- Detects keyword cannibalization across pages
- Runs PageSpeed Insights for Core Web Vitals on top URLs
- Exports everything as a single XLSX with one tab per analysis

![GSC + GA4 Export Reports](docs/gsc-ga4-export-reports.webp)

---

## Reports

| Sheet | Description |
|---|---|
| 00 Summary | Overview of all sheets with click and impression totals |
| GSC Queries | All queries sorted by impressions |
| GSC Pages | All pages sorted by impressions |
| GSC Discover | Discover performance (if available) |
| GSC Coverage / Sitemaps | Sitemap submission and indexing status |
| GA4 Page Performance | Sessions, pageviews, bounce rate, engagement rate |
| GA4 Traffic Sources | Channel breakdown |
| Merge: GSC + GA4 | URL-level join of GSC and GA4 data |
| Merge: MoM Comparison | Month-over-month delta for all pages |
| Analysis: CTR Opportunity | Pages with high impressions and low CTR |
| Analysis: Cannibalization | Queries competing across multiple pages |
| Core Web Vitals (PSI) | LCP, INP, CLS, FCP for top URLs (mobile + desktop) |

---

## Requirements

- Python 3.10+ with Tkinter for the GUI. It ships with the python.org and Homebrew
  builds on macOS; on Debian/Ubuntu install it separately (`sudo apt install python3-tk`).
  Headless mode does not need it.
- A Google Cloud project with Search Console API and Analytics Data API enabled
- OAuth 2.0 credentials (Desktop app)
- Optional: PageSpeed Insights API key
- Optional: Resend account for email delivery

```bash
pip install -r requirements.txt
```

`requirements.txt` lists only what the project imports directly, with upper bounds so a
breaking major release cannot land unnoticed on an unattended run. For a byte-identical
environment — worth it for cron — install the fully pinned set instead:

```bash
pip install -r requirements.lock.txt
```

---

## Setup

**1. Google OAuth credentials**

- Go to [Google Cloud Console](https://console.cloud.google.com/)
- Create a project and enable: Search Console API, Google Analytics Data API
- Create OAuth 2.0 credentials (Desktop app)
- Download as `credentials.json` and place in the project root

**2. Environment variables**

```bash
cp .env.example .env
```

Edit `.env`:

```env
PSI_API_KEY=your_psi_api_key_here
REPORT_BRAND=Analytics Report
RESEND_API_KEY=your_resend_api_key_here
RESEND_TO=you@example.com
RESEND_FROM=reports@yourdomain.com
WEEKLY_PROPERTIES=sc-domain:yourdomain.com,sc-domain:otherdomain.com

# GSC property to GA4 measurement ID mapping
GA4_sc-domain:yourdomain.com=123456789
GA4_sc-domain:otherdomain.com=987654321
```

`REPORT_BRAND` is the title on the XLSX summary sheet and the GUI footer. It defaults to
the neutral `Analytics Report`, so the tool ships unbranded — set it to your own name if
you hand the reports to clients.

**3. Run**

```bash
python3 main.py
```

On first run, a browser window opens for Google OAuth authentication. The token saves to `gsc_ga4_token.json` for subsequent runs.

---

## Headless / cron mode

```bash
python3 main.py --headless
```

Runs with the properties defined in `WEEKLY_PROPERTIES` and sends results by email if
`RESEND_API_KEY`, `RESEND_TO` and `RESEND_FROM` are all set.

`WEEKLY_PROPERTIES` is required in headless mode — there are no built-in defaults, and the
run exits with code `2` if it is unset.

---

## Privacy & security

This repository contains **no** property names, no GA4 IDs, no credentials, and no exported
data. Everything that identifies you or a client lives in files that are git-ignored:

| File | Contents | Tracked? |
|---|---|---|
| `.env` | API keys, GSC properties, GA4 ID mapping | no (`.env.example` is the template) |
| `credentials.json` | Google OAuth client secret | no (`credentials.example.json` is the template) |
| `gsc_ga4_token.json` | OAuth token, written with mode `0600` | no |
| `gsc_export_output/` | Generated XLSX/CSV reports with client data | no |

Before pushing a fork or a change, check that nothing sensitive slipped in:

```bash
git diff --cached | grep -niE "sc-domain:|GA4_|_API_KEY=|client_secret|/Users/"
```

All API calls go to Google and — only if you enable it — Resend. No other service receives
your data.

---

## Project structure

```
├── main.py              # GUI entry point
├── runner.py            # Export orchestration
├── config.py            # Constants, mappings, report definitions
├── auth.py              # Google OAuth flow
├── exporters/
│   ├── gsc.py           # GSC data fetchers
│   ├── ga4.py           # GA4 data fetchers
│   ├── psi.py           # PageSpeed Insights fetcher
│   └── email.py         # Resend email delivery
├── analysis/
│   ├── cannibalization.py
│   ├── ctr_opportunity.py
│   └── mom.py           # Month-over-month comparison
├── output/
│   └── xlsx.py          # XLSX formatting and export
├── docs/                # Screenshots
├── requirements.txt     # Direct dependencies, version ranges
├── requirements.lock.txt # Fully pinned environment
├── .env.example
└── credentials.example.json
```

---

## License

MIT — © 2026 [Litzki Systems LLC](https://litzki-systems.com)
