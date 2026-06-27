"""
GA4 data fetchers: Pages, Traffic Sources.
"""
import traceback
from google.analytics.data_v1beta.types import (
    RunReportRequest, Dimension, Metric, DateRange
)


def fetch_pages(ga4, property_id, date_start, date_end, log):
    log("    GA4: Page Performance")
    req = RunReportRequest(
        property=f"properties/{property_id}",
        dimensions=[Dimension(name="pagePath"), Dimension(name="pageTitle")],
        metrics=[
            Metric(name="sessions"),
            Metric(name="screenPageViews"),
            Metric(name="bounceRate"),
            Metric(name="averageSessionDuration"),
            Metric(name="engagementRate"),
        ],
        date_ranges=[DateRange(start_date=date_start, end_date=date_end)],
        limit=25000,
    )
    try:
        resp = ga4.run_report(req)
        rows = [{
            "page_path":       row.dimension_values[0].value,
            "page_title":      row.dimension_values[1].value,
            "sessions":        int(row.metric_values[0].value),
            "pageviews":       int(row.metric_values[1].value),
            "bounce_rate":     round(float(row.metric_values[2].value) * 100, 2),
            "avg_duration_s":  round(float(row.metric_values[3].value), 1),
            "engagement_rate": round(float(row.metric_values[4].value) * 100, 2),
        } for row in resp.rows]
        return sorted(rows, key=lambda x: x["sessions"], reverse=True)
    except Exception as e:
        log(f"    GA4 ERROR: {e}\n{traceback.format_exc()}")
        return []


def fetch_sources(ga4, property_id, date_start, date_end, log):
    log("    GA4: Traffic Sources")
    req = RunReportRequest(
        property=f"properties/{property_id}",
        dimensions=[Dimension(name="sessionDefaultChannelGroup")],
        metrics=[
            Metric(name="sessions"),
            Metric(name="screenPageViews"),
            Metric(name="bounceRate"),
            Metric(name="engagementRate"),
            Metric(name="conversions"),
        ],
        date_ranges=[DateRange(start_date=date_start, end_date=date_end)],
        limit=100,
    )
    try:
        resp = ga4.run_report(req)
        rows = [{
            "channel":         row.dimension_values[0].value,
            "sessions":        int(row.metric_values[0].value),
            "pageviews":       int(row.metric_values[1].value),
            "bounce_rate":     round(float(row.metric_values[2].value) * 100, 2),
            "engagement_rate": round(float(row.metric_values[3].value) * 100, 2),
            "conversions":     int(row.metric_values[4].value),
        } for row in resp.rows]
        return sorted(rows, key=lambda x: x["sessions"], reverse=True)
    except Exception as e:
        log(f"    GA4 sources ERROR: {e}")
        return []


PAGES_HEADERS   = ["page_path", "page_title", "sessions", "pageviews",
                   "bounce_rate", "avg_duration_s", "engagement_rate"]
SOURCES_HEADERS = ["channel", "sessions", "pageviews", "bounce_rate",
                   "engagement_rate", "conversions"]
