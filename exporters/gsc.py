"""
GSC data fetchers: Queries, Pages, Discover, Coverage.
"""
import time
from config import ROW_LIMIT


def paginate_performance(gsc, prop, dimensions, date_start, date_end,
                         log, search_type="web"):
    rows, start_row = [], 0
    while True:
        body = {
            "startDate":  date_start,
            "endDate":    date_end,
            "dimensions": dimensions,
            "rowLimit":   ROW_LIMIT,
            "startRow":   start_row,
            "searchType":  search_type,
        }
        resp  = gsc.searchanalytics().query(siteUrl=prop, body=body).execute()
        batch = resp.get("rows", [])
        rows.extend(batch)
        if len(batch) < ROW_LIMIT:
            break
        start_row += ROW_LIMIT
        time.sleep(0.3)
    return rows


def fetch_queries(gsc, prop, date_start, date_end, log):
    log("    GSC: Queries")
    raw = paginate_performance(gsc, prop, ["query"], date_start, date_end, log)
    return sorted([{
        "query":       r["keys"][0],
        "clicks":      r["clicks"],
        "impressions": r["impressions"],
        "ctr":         round(r["ctr"] * 100, 2),
        "position":    round(r["position"], 1),
    } for r in raw], key=lambda x: x["impressions"], reverse=True)


def fetch_pages(gsc, prop, date_start, date_end, log):
    log("    GSC: Pages")
    raw = paginate_performance(gsc, prop, ["page"], date_start, date_end, log)
    return raw, sorted([{
        "page":        r["keys"][0],
        "clicks":      r["clicks"],
        "impressions": r["impressions"],
        "ctr":         round(r["ctr"] * 100, 2),
        "position":    round(r["position"], 1),
    } for r in raw], key=lambda x: x["impressions"], reverse=True)


def fetch_discover(gsc, prop, date_start, date_end, log):
    log("    GSC: Discover")
    raw = paginate_performance(
        gsc, prop, ["page"], date_start, date_end, log, search_type="discover")
    if not raw:
        log("    GSC: Discover – no data")
        return []
    return sorted([{
        "page":        r["keys"][0],
        "clicks":      r["clicks"],
        "impressions": r["impressions"],
        "ctr":         round(r["ctr"] * 100, 2),
    } for r in raw], key=lambda x: x["impressions"], reverse=True)


def fetch_sitemaps(gsc, prop, log, on_error=None):
    log("    GSC: Coverage/Sitemaps")
    try:
        result = gsc.sitemaps().list(siteUrl=prop).execute()
        return [{
            "path":            sm.get("path", ""),
            "type":            sm.get("type", ""),
            "lastSubmitted":   sm.get("lastSubmitted", ""),
            "lastDownloaded":  sm.get("lastDownloaded", ""),
            "isPending":       sm.get("isPending", False),
            "isSitemapsIndex": sm.get("isSitemapsIndex", False),
            "warnings":        sum(w.get("count", 0) for w in sm.get("warnings", [])
                                   if isinstance(w, dict)),
            "errors":          sum(e.get("count", 0) for e in sm.get("errors", [])
                                   if isinstance(e, dict)),
            "submittedUrls":   next((c.get("count", 0) for c in sm.get("contents", [])
                                     if isinstance(c, dict) and c.get("type") == "web"), 0),
        } for sm in result.get("sitemap", [])]
    except Exception as e:
        log(f"    WARNING Sitemaps: {e}")
        if on_error:
            on_error(f"GSC sitemaps ({prop}): {e}")
        return []


PAGES_HEADERS   = ["page", "clicks", "impressions", "ctr", "position"]
QUERIES_HEADERS = ["query", "clicks", "impressions", "ctr", "position"]
DISCOVER_HEADERS= ["page", "clicks", "impressions", "ctr"]
SITEMAPS_HEADERS= ["path", "type", "lastSubmitted", "lastDownloaded", "isPending",
                   "isSitemapsIndex", "warnings", "errors", "submittedUrls"]
