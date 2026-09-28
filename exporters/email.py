"""
E-Mail delivery via Resend API.
"""
import json
import base64
import urllib.request
import urllib.error
from pathlib import Path


def send_email(env, subject, body, attachments, log):
    """Send the report by email.

    Returns True when Resend accepted the message, False when the send failed,
    and None when email is not configured at all (a deliberate opt-out, which
    callers must not treat as an error).
    """
    api_key   = env.get("RESEND_API_KEY", "")
    to_addr   = env.get("RESEND_TO", "")
    from_addr = env.get("RESEND_FROM", "")

    if not all([api_key, to_addr, from_addr]):
        log("    E-Mail: RESEND_API_KEY, RESEND_TO oder RESEND_FROM fehlt – übersprungen.")
        return None

    try:
        attachs = [
            {
                "filename": Path(p).name,
                "content":  base64.b64encode(Path(p).read_bytes()).decode(),
            }
            for p in attachments
        ]
        payload = json.dumps({
            "from":        from_addr,
            "to":          [to_addr],
            "subject":     subject,
            "text":        body,
            "attachments": attachs,
        }).encode()

        req = urllib.request.Request(
            "https://api.resend.com/emails",
            data=payload,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type":  "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
        log(f"    E-Mail gesendet an {to_addr} (id: {result.get('id', '')})")
        return True

    except urllib.error.HTTPError as e:
        log(f"    Email ERROR {e.code}: {e.read().decode()}")
        return False
    except Exception as e:
        log(f"    Email ERROR: {e}")
        return False
