"""
Export runner: orchestrates all exporters and analyses per property.
"""
import sys
from datetime import datetime

from config import (
    OUTPUT_DIR, GA4_MAP, GA4_ONLY, weekly_properties,
    ALL_REPORTS, PSI_TOP_N_HEADLESS, PSI_DELAY,
    safe_filename, normalise_url,
)
from auth import get_services, AuthRequiresBrowser
from exporters import gsc as gsc_exp
from exporters import ga4 as ga4_exp
from exporters import psi as psi_exp
from exporters.email import send_email
from analysis import ctr_opportunity, cannibalization, mom as mom_mod
from output.xlsx import save_workbook_tabs, save_csv


def run_export(gsc, ga4_client, selected_props, selected_reports,
               date_start, date_end, fmt, psi_key, psi_top_n,
               do_send_mail, env, log, on_done):
    try:
        OUTPUT_DIR.mkdir(exist_ok=True)
        today      = datetime.today().strftime("%Y-%m-%d")
        prev_start, prev_end = mom_mod.prev_period(date_start, date_end)
        all_files  = []

        # Steps that fail without aborting the run. They used to be logged and
        # forgotten, so an unattended run reported success with data missing.
        failures = []
        # PSI degrades per URL and records the error in the report itself, so it
        # is reported but does not decide the exit code.
        soft_failures = []

        log(f"Period:     {date_start} → {date_end}")
        log(f"Comparison: {prev_start} → {prev_end}")
        log(f"Format:     {fmt.upper()}\n")

        for prop in selected_props:
            domain   = safe_filename(prop)
            prop_dir = OUTPUT_DIR / f"{domain}_{today}"
            prop_dir.mkdir(parents=True, exist_ok=True)
            ga4_id   = GA4_MAP.get(prop)
            log(f"  [{prop}]  GA4: {ga4_id or '—'}")
            tabs = []

            def add(name, rows, headers, hfn=None):
                if not rows:
                    return
                if fmt == "xlsx":
                    tabs.append((name, rows, headers, hfn) if hfn else (name, rows, headers))
                else:
                    all_files.append(
                        save_csv(rows, headers, prop_dir / f"{domain}_{name.lower().replace(' ','_').replace(':','')}.csv", log)
                    )

            # ── GSC Queries ───────────────────────────────────────────────────
            gsc_query_raw = []
            if any(r in selected_reports for r in ["queries", "cannib"]):
                gsc_query_raw = gsc_exp.paginate_performance(
                    gsc, prop, ["query"], date_start, date_end, log)
                if "queries" in selected_reports:
                    rows = sorted([{
                        "query": r["keys"][0], "clicks": r["clicks"],
                        "impressions": r["impressions"],
                        "ctr": round(r["ctr"]*100, 2), "position": round(r["position"], 1),
                    } for r in gsc_query_raw], key=lambda x: x["impressions"], reverse=True)
                    add("GSC Queries", rows, gsc_exp.QUERIES_HEADERS)

            # ── GSC Pages ─────────────────────────────────────────────────────
            gsc_pages_raw = []
            if any(r in selected_reports for r in ["pages","merge","mom","ctr_opp","cwv"]):
                gsc_pages_raw, page_rows = gsc_exp.fetch_pages(
                    gsc, prop, date_start, date_end, log)
                if "pages" in selected_reports:
                    add("GSC Pages", page_rows, gsc_exp.PAGES_HEADERS)

            # ── GSC Discover ──────────────────────────────────────────────────
            if "discover" in selected_reports:
                disc_rows = gsc_exp.fetch_discover(gsc, prop, date_start, date_end, log)
                add("GSC Discover", disc_rows, gsc_exp.DISCOVER_HEADERS)

            # ── GSC Coverage ──────────────────────────────────────────────────
            if "coverage" in selected_reports:
                sm_rows = gsc_exp.fetch_sitemaps(gsc, prop, log, on_error=failures.append)
                add("Coverage", sm_rows, gsc_exp.SITEMAPS_HEADERS)

            # ── GA4 Pages ─────────────────────────────────────────────────────
            ga4_rows = []
            if any(r in selected_reports for r in ["ga4","merge","mom"]) and ga4_id:
                ga4_rows = ga4_exp.fetch_pages(ga4_client, ga4_id, date_start, date_end, log,
                                               on_error=failures.append)
                if "ga4" in selected_reports:
                    add("GA4 Pages", ga4_rows, ga4_exp.PAGES_HEADERS)

            # ── GA4 Sources ───────────────────────────────────────────────────
            if "ga4_sources" in selected_reports and ga4_id:
                src_rows = ga4_exp.fetch_sources(ga4_client, ga4_id, date_start, date_end, log,
                                                 on_error=failures.append)
                add("GA4 Sources", src_rows, ga4_exp.SOURCES_HEADERS)

            # ── Merge GSC + GA4 ───────────────────────────────────────────────
            if "merge" in selected_reports and ga4_id and gsc_pages_raw:
                log("    Merge: GSC + GA4")
                base    = prop.replace("sc-domain:", "").rstrip("/")
                ga4_map = {}
                for g in ga4_rows:
                    full_url = f"https://{base}{g['page_path']}"
                    ga4_map[normalise_url(full_url)] = g
                merge_rows = []
                for gsc_r in gsc_pages_raw:
                    gsc_url = gsc_r["keys"][0]
                    g       = ga4_map.get(normalise_url(gsc_url), {})
                    merge_rows.append({
                        "url":             gsc_url,
                        "page_title":      g.get("page_title", ""),
                        "sessions":        g.get("sessions", ""),
                        "pageviews":       g.get("pageviews", ""),
                        "bounce_rate":     g.get("bounce_rate", ""),
                        "avg_duration_s":  g.get("avg_duration_s", ""),
                        "engagement_rate": g.get("engagement_rate", ""),
                        "gsc_clicks":      gsc_r.get("clicks", ""),
                        "gsc_impressions": gsc_r.get("impressions", ""),
                        "gsc_ctr":         round(gsc_r.get("ctr", 0)*100, 2),
                        "gsc_position":    round(gsc_r.get("position", 0), 1),
                    })
                merge_rows.sort(key=lambda x: x.get("gsc_clicks") or 0, reverse=True)
                hdrs = ["url","page_title","sessions","pageviews","bounce_rate",
                        "avg_duration_s","engagement_rate",
                        "gsc_clicks","gsc_impressions","gsc_ctr","gsc_position"]
                add("Merge GSC+GA4", merge_rows, hdrs)

            # ── MoM ───────────────────────────────────────────────────────────
            if "mom" in selected_reports and gsc_pages_raw:
                log("    MoM: Loading previous period")
                prev_raw  = gsc_exp.paginate_performance(
                    gsc, prop, ["page"], prev_start, prev_end, log)
                cur_pages = [{
                    "page": r["keys"][0], "clicks": r["clicks"],
                    "impressions": r["impressions"],
                    "ctr": round(r["ctr"]*100,2), "position": round(r["position"],1),
                } for r in gsc_pages_raw]
                prv_pages = [{
                    "page": r["keys"][0], "clicks": r["clicks"],
                    "impressions": r["impressions"],
                    "ctr": round(r["ctr"]*100,2), "position": round(r["position"],1),
                } for r in prev_raw]
                mom_rows = mom_mod.merge(cur_pages, prv_pages)
                add("MoM Comparison", mom_rows, mom_mod.HEADERS)

            # ── CTR Opportunity ───────────────────────────────────────────────
            if "ctr_opp" in selected_reports and gsc_pages_raw:
                log("    Analysis: CTR Opportunity")
                opp_rows = ctr_opportunity.run(gsc_pages_raw)
                add("CTR Opportunity", opp_rows, ctr_opportunity.HEADERS,
                    ctr_opportunity.highlight)
                log(f"    {len(opp_rows)} opportunities found")

            # ── Cannibalization ───────────────────────────────────────────────
            if "cannib" in selected_reports and gsc_query_raw:
                log("    Analysis: Cannibalization")
                qp_raw   = gsc_exp.paginate_performance(
                    gsc, prop, ["query","page"], date_start, date_end, log)
                can_rows = cannibalization.run(qp_raw)
                add("Cannibalization", can_rows, cannibalization.HEADERS,
                    cannibalization.highlight)
                unique_q = len(set(r["query"] for r in can_rows))
                log(f"    {unique_q} cannibalized queries found")

            # ── PSI ───────────────────────────────────────────────────────────
            if "cwv" in selected_reports and psi_key and gsc_pages_raw:
                log(f"    PSI: Top {psi_top_n} URLs (mobile + desktop)")
                urls = [r["keys"][0] for r in sorted(
                    gsc_pages_raw, key=lambda x: x["impressions"], reverse=True
                )]
                psi_rows = psi_exp.run_psi_batch(urls, psi_key, psi_top_n, PSI_DELAY, log,
                                                 on_error=soft_failures.append)
                add("Core Web Vitals", psi_rows, psi_exp.HEADERS, psi_exp.highlight)

            # ── Save XLSX ─────────────────────────────────────────────────────
            if fmt == "xlsx" and tabs:
                wb_path = prop_dir / f"{domain}_{today}.xlsx"
                f = save_workbook_tabs(tabs, wb_path, log)
                all_files.append(f)

            log("")

        # ── GA4-only properties ───────────────────────────────────────────────
        if "ga4" in selected_reports:
            for name, ga4_id in GA4_ONLY.items():
                log(f"  [GA4 only: {name}]")
                prop_dir = OUTPUT_DIR / f"{safe_filename(name)}_{today}"
                prop_dir.mkdir(parents=True, exist_ok=True)
                rows = ga4_exp.fetch_pages(ga4_client, ga4_id, date_start, date_end, log,
                                           on_error=failures.append)
                fname = safe_filename(name)
                if fmt == "xlsx":
                    wb_path = prop_dir / f"{fname}_{today}.xlsx"
                    f = save_workbook_tabs([("GA4 Pages", rows, ga4_exp.PAGES_HEADERS)], wb_path, log)
                else:
                    f = save_csv(rows, ga4_exp.PAGES_HEADERS, prop_dir / f"{fname}_ga4.csv", log)
                all_files.append(f)
                log("")

        # ── E-Mail ────────────────────────────────────────────────────────────
        if do_send_mail and all_files:
            log("  Sending email via Resend…")
            sent = send_email(
                env,
                subject=f"GSC/GA4 Export {today}",
                body=(f"Export vom {today}\n"
                      f"Period: {date_start} → {date_end}\n"
                      f"Comparison: {prev_start} → {prev_end}\n\n"
                      f"{len(all_files)} files, {len(selected_props)} properties."),
                attachments=all_files,
                log=log,
            )
            # None means "not configured", which is a deliberate opt-out.
            if sent is False:
                failures.append("Email delivery via Resend failed")

        if not all_files:
            failures.append("No report files were produced")

        # ── Outcome ───────────────────────────────────────────────────────────
        if soft_failures:
            log(f"\n{len(soft_failures)} URL(s) degraded (recorded in the report):")
            for f in soft_failures[:10]:
                log(f"  - {f}")
            if len(soft_failures) > 10:
                log(f"  … and {len(soft_failures) - 10} more")

        if failures:
            log(f"\nFAILED — {len(failures)} step(s) did not complete:")
            for f in failures:
                log(f"  - {f}")
            on_done(success=False)
        else:
            log("Done.")
            on_done(success=True)

    except Exception as e:
        import traceback
        log(f"\nERROR: {e}\n{traceback.format_exc()}")
        on_done(success=False)


def run_headless(env):
    props = weekly_properties(env)
    if not props:
        print(
            "ERROR: WEEKLY_PROPERTIES is not set in .env — nothing to export.\n"
            "Example: WEEKLY_PROPERTIES=sc-domain:example.com,sc-domain:example.org",
            file=sys.stderr,
        )
        sys.exit(2)
    reports = [k for _, k in ALL_REPORTS]
    psi_key = env.get("PSI_API_KEY", "")

    from datetime import timedelta
    today      = datetime.today()
    date_end   = today.strftime("%Y-%m-%d")
    date_start = (today - timedelta(days=28)).strftime("%Y-%m-%d")

    print(f"Headless mode: {len(props)} properties")

    def log(msg): print(msg)
    def on_done(success): sys.exit(0 if success else 1)

    try:
        gsc, ga4_client = get_services(interactive=False, log=log)
    except (AuthRequiresBrowser, FileNotFoundError) as e:
        # Both mean "a human has to set this up"; neither should surface as a
        # raw traceback in a cron mail.
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(3)

    run_export(
        gsc, ga4_client, props, reports,
        date_start, date_end,
        "xlsx", psi_key, PSI_TOP_N_HEADLESS,
        True, env, log, on_done,
    )
