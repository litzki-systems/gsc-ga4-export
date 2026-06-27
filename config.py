"""
Central configuration: constants, mappings, report definitions.
"""
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()

SCOPES = [
    "https://www.googleapis.com/auth/webmasters.readonly",
    "https://www.googleapis.com/auth/analytics.readonly",
]

CREDENTIALS_FILE = SCRIPT_DIR / "credentials.json"
TOKEN_FILE       = SCRIPT_DIR / "gsc_ga4_token.json"
ENV_FILE         = SCRIPT_DIR / ".env"
OUTPUT_DIR       = SCRIPT_DIR / "gsc_export_output"

ROW_LIMIT = 25000
PSI_TOP_N = 50
PSI_DELAY = 1.0

# GSC + GA4 mapping — loaded from .env
def _load_ga4_map():
    _env = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if line and "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                _env[k.strip()] = v.strip()
    return {k[4:]: v for k, v in _env.items() if k.startswith("GA4_")}

GA4_MAP  = _load_ga4_map()
GA4_ONLY = {}

# Weekly auto-run properties (overridden by .env WEEKLY_PROPERTIES)
WEEKLY_DEFAULTS = [
    "sc-domain:example.com",
    "sc-domain:example.org",
    "sc-domain:example.net",
]

DATE_RANGES = {
    "7 Days":      7,
    "14 Days":     14,
    "28 Days":     28,
    "Quarter":     90,
    "Year":        365,
    "All Time":    None,
}

ALL_REPORTS = [
    ("GSC: Queries",             "queries"),
    ("GSC: Pages",               "pages"),
    ("GSC: Discover",            "discover"),
    ("GSC: Coverage / Sitemaps", "coverage"),
    ("GA4: Page Performance",    "ga4"),
    ("GA4: Traffic Sources",     "ga4_sources"),
    ("Merge: GSC + GA4",         "merge"),
    ("Merge: MoM Comparison",    "mom"),
    ("Analysis: CTR Opportunity","ctr_opp"),
    ("Analysis: Cannibalization","cannib"),
    ("Core Web Vitals (PSI)",    "cwv"),
]

# PSI URL limits: headless vs manual
PSI_TOP_N_HEADLESS = 10
PSI_TOP_N_MANUAL   = 50

THEME = "dark"  # "dark" | "light"


def load_env():
    env = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if line and "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env


def safe_filename(prop):
    return (prop.replace("sc-domain:", "")
                .replace("https://", "").replace("http://", "")
                .replace("/", "_").replace(".", "_").strip("_"))


def normalise_url(url):
    u = url.rstrip("/").lower()
    u = u.replace("https://", "").replace("http://", "")
    if u.startswith("www."):
        u = u[4:]
    return u
