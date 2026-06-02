"""
PageSpeed Insights fetcher.
"""
import json
import time
import urllib.request
import urllib.parse

from output.xlsx import WARN_FILL, BAD_FILL


def fetch_psi(url, api_key, strategy="mobile"):
    params   = urllib.parse.urlencode({
        "url": url, "key": api_key,
        "strategy": strategy, "category": "performance",
    })
    endpoint = f"https://www.googleapis.com/pagespeedonline/v5/runPagespeed?{params}"
    try:
        with urllib.request.urlopen(endpoint, timeout=30) as r:
            data = json.loads(r.read())
        fid  = data.get("loadingExperience", {}).get("metrics", {})
        cats = data.get("lighthouseResult", {}).get("categories", {})

        lh_audits = data.get("lighthouseResult", {}).get("audits", {})

        def fv(key, lh_key=None):
            m = fid.get(key, {})
            v = m.get("percentile", "")
            r = m.get("category", "")
            if v == "" and lh_key:
                lh = lh_audits.get(lh_key, {})
                v  = round(lh.get("numericValue", 0)) if lh.get("numericValue") else ""
                r  = "LIGHTHOUSE"
            return v, r

        lcp_v, lcp_r = fv("LARGEST_CONTENTFUL_PAINT_MS", "largest-contentful-paint")
        inp_v, inp_r = fv("INTERACTION_TO_NEXT_PAINT", "interactive")
        cls_v, cls_r = fv("CUMULATIVE_LAYOUT_SHIFT_SCORE", "cumulative-layout-shift")
        fcp_v, fcp_r = fv("FIRST_CONTENTFUL_PAINT_MS", "first-contentful-paint")
        score        = cats.get("performance", {}).get("score")

        return {
            "url":           url,
            "strategy":      strategy,
            "perf_score":    round(score * 100) if score is not None else "",
            "lcp_ms":        lcp_v, "lcp_rating": lcp_r,
            "inp_ms":        inp_v, "inp_rating": inp_r,
            "cls":           cls_v, "cls_rating": cls_r,
            "fcp_ms":        fcp_v, "fcp_rating": fcp_r,
            "overall_rating": data.get("loadingExperience", {}).get("overall_category", ""),
        }
    except Exception as e:
        return {
            "url": url, "strategy": strategy, "perf_score": "",
            "lcp_ms": "", "lcp_rating": "", "inp_ms": "", "inp_rating": "",
            "cls": "", "cls_rating": "", "fcp_ms": "", "fcp_rating": "",
            "overall_rating": f"ERROR: {e}",
        }


def run_psi_batch(urls, api_key, top_n, delay, log):
    urls = urls[:top_n]
    rows = []
    total = len(urls) * 2
    for i, url in enumerate(urls):
        for strategy in ("mobile", "desktop"):
            done = i * 2 + (0 if strategy == "mobile" else 1)
            log(f"    PSI [{done+1}/{total}] {strategy}: {url[:55]}")
            rows.append(fetch_psi(url, api_key, strategy))
            time.sleep(delay)
    return rows


def highlight(row):
    r = row.get("overall_rating", "")
    if r == "SLOW":    return BAD_FILL
    if r == "AVERAGE": return WARN_FILL
    return None


HEADERS = ["url", "strategy", "perf_score",
           "lcp_ms", "lcp_rating", "inp_ms", "inp_rating",
           "cls", "cls_rating", "fcp_ms", "fcp_rating", "overall_rating"]
