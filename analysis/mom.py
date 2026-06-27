"""
Month-over-Month comparison: current vs previous period.
"""
from datetime import datetime, timedelta

HEADERS = [
    "page", "clicks", "impressions", "ctr", "position",
    "prev_clicks", "prev_impressions", "prev_position",
    "delta_clicks", "delta_impressions", "delta_position",
    "pct_clicks", "pct_impressions",
]


def prev_period(date_start, date_end):
    s     = datetime.strptime(date_start, "%Y-%m-%d")
    e     = datetime.strptime(date_end,   "%Y-%m-%d")
    delta = e - s
    return (
        (s - timedelta(days=delta.days + 1)).strftime("%Y-%m-%d"),
        (s - timedelta(days=1)).strftime("%Y-%m-%d"),
    )


def merge(cur_rows, prev_rows, key_field="page"):
    cur_map  = {r[key_field]: r for r in cur_rows}
    prev_map = {r[key_field]: r for r in prev_rows}
    all_keys = list(cur_map) + [k for k in prev_map if k not in cur_map]
    result   = []
    for k in all_keys:
        r    = cur_map.get(k, {key_field: k, "clicks": 0, "impressions": 0, "ctr": 0, "position": 0})
        prev = prev_map.get(k, {})

        def delta(field):
            c = r.get(field, 0) or 0
            p = prev.get(field, 0) or 0
            return round(c - p, 2)

        def pct(field):
            c = r.get(field, 0) or 0
            p = prev.get(field, 0) or 0
            if p == 0:
                return "" if c == 0 else "+100%"
            return f"{round((c - p) / p * 100, 1):+.1f}%"

        result.append({
            **r,
            "prev_clicks":       prev.get("clicks", ""),
            "prev_impressions":  prev.get("impressions", ""),
            "prev_position":     prev.get("position", ""),
            "delta_clicks":      delta("clicks"),
            "delta_impressions": delta("impressions"),
            "delta_position":    delta("position"),
            "pct_clicks":        pct("clicks"),
            "pct_impressions":   pct("impressions"),
        })
    return result
