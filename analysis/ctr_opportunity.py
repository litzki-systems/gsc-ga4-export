"""
CTR Opportunity analysis: pages with high impressions, low CTR, good position.
"""
from output.xlsx import WARN_FILL, BAD_FILL

HEADERS = ["page", "impressions", "clicks", "ctr_pct", "position",
           "click_potential", "priority"]


def run(gsc_pages_raw):
    rows = []
    for r in gsc_pages_raw:
        impr = r["impressions"]
        ctr  = round(r["ctr"] * 100, 2)
        pos  = round(r["position"], 1)
        if impr >= 100 and ctr < 3.0 and pos <= 20:
            potential = int(impr * 0.05) - r["clicks"]
            rows.append({
                "page":            r["keys"][0],
                "impressions":     impr,
                "clicks":          r["clicks"],
                "ctr_pct":         ctr,
                "position":        pos,
                "click_potential": max(potential, 0),
                "priority":        "HOCH"    if pos <= 10 and ctr < 2 else
                                   "MITTEL"  if pos <= 15 else
                                   "NIEDRIG",
            })
    return sorted(rows, key=lambda x: x["click_potential"], reverse=True)


def highlight(row):
    p = row.get("priority", "")
    if p == "HOCH":   return BAD_FILL
    if p == "MITTEL": return WARN_FILL
    return None
