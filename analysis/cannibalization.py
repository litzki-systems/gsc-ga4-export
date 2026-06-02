"""
Keyword cannibalization: queries where multiple pages compete.
"""
from collections import defaultdict
from output.xlsx import WARN_FILL, BAD_FILL

HEADERS = ["query", "page", "clicks", "impressions", "ctr_pct",
           "position", "competing_pages"]


def run(gsc_query_page_raw):
    query_pages = defaultdict(list)
    for r in gsc_query_page_raw:
        query = r["keys"][0]
        page  = r["keys"][1]
        query_pages[query].append({
            "page":        page,
            "clicks":      r["clicks"],
            "impressions": r["impressions"],
            "ctr":         round(r["ctr"] * 100, 2),
            "position":    round(r["position"], 1),
        })

    rows = []
    for query, pages in query_pages.items():
        total_impressions = sum(p["impressions"] for p in pages)
        if len(pages) > 1 and total_impressions >= 50:
            for p in sorted(pages, key=lambda x: x["impressions"], reverse=True):
                rows.append({
                    "query":           query,
                    "page":            p["page"],
                    "clicks":          p["clicks"],
                    "impressions":     p["impressions"],
                    "ctr_pct":         p["ctr"],
                    "position":        p["position"],
                    "competing_pages": len(pages),
                })

    return sorted(rows, key=lambda x: (x["query"], -x["impressions"]))


def highlight(row):
    n = row.get("competing_pages", 0)
    if n >= 3: return BAD_FILL
    if n == 2: return WARN_FILL
    return None
