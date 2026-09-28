"""
OAuth 2.0 authentication for GSC + GA4.
"""
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from google.analytics.data_v1beta import BetaAnalyticsDataClient

from config import SCOPES, CREDENTIALS_FILE, TOKEN_FILE


class AuthRequiresBrowser(RuntimeError):
    """Raised when a full OAuth sign-in is needed but no browser can be used."""


def get_credentials(interactive=True, log=None):
    """Return usable OAuth credentials.

    interactive=False (headless/cron) refuses to start the browser-based sign-in
    flow — run_local_server() would block forever on a machine with no browser.
    It raises AuthRequiresBrowser instead, so an unattended run fails fast.
    """
    def note(msg):
        if log:
            log(msg)

    creds = None
    if TOKEN_FILE.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
        except Exception as e:
            note(f"    Stored token unreadable ({e}) — re-authenticating.")
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                note(f"    Token refresh failed ({e}) — full sign-in required.")
                creds = None
        if not creds:
            if not CREDENTIALS_FILE.exists():
                raise FileNotFoundError(
                    f"{CREDENTIALS_FILE} not found.\n"
                    "Google Cloud Console → Credentials → OAuth 2.0 Client ID → Desktop App."
                )
            if not interactive:
                raise AuthRequiresBrowser(
                    f"OAuth sign-in required, but no browser is available.\n"
                    f"Run `python3 main.py` once interactively to create "
                    f"{TOKEN_FILE.name}, then re-run --headless."
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
            creds = flow.run_local_server(port=0)
        TOKEN_FILE.write_text(creds.to_json())
        TOKEN_FILE.chmod(0o600)
    return creds


def get_services(interactive=True, log=None):
    creds = get_credentials(interactive=interactive, log=log)
    gsc   = build("searchconsole", "v1", credentials=creds)
    ga4   = BetaAnalyticsDataClient(credentials=creds)
    return gsc, ga4


def fetch_all_gsc_properties(gsc):
    result = gsc.sites().list().execute()
    return [s["siteUrl"] for s in result.get("siteEntry", [])]
