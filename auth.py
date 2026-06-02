"""
OAuth 2.0 authentication for GSC + GA4.
"""
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from google.analytics.data_v1beta import BetaAnalyticsDataClient

from config import SCOPES, CREDENTIALS_FILE, TOKEN_FILE


def get_credentials():
    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CREDENTIALS_FILE.exists():
                raise FileNotFoundError(
                    f"{CREDENTIALS_FILE} not found.\n"
                    "Google Cloud Console → Credentials → OAuth 2.0 Client ID → Desktop App."
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
            creds = flow.run_local_server(port=0)
        TOKEN_FILE.write_text(creds.to_json())
    return creds


def get_services():
    creds = get_credentials()
    gsc   = build("searchconsole", "v1", credentials=creds)
    ga4   = BetaAnalyticsDataClient(credentials=creds)
    return gsc, ga4


def fetch_all_gsc_properties(gsc):
    result = gsc.sites().list().execute()
    return [s["siteUrl"] for s in result.get("siteEntry", [])]
