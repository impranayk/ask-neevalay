"""Optional Supabase store for Ask Neevalay — captured leads + question analytics.

Entirely optional: if SUPABASE_URL / SUPABASE_KEY aren't set, `enabled()` is
False and both features degrade quietly (nothing is persisted; the chat is
unaffected). Talks to Supabase over the PostgREST REST API via httpx, using the
service_role (secret) key server-side only.

Tables (see EMBED_AND_DB.md):
    leads(id, created_at, name, phone, child_age, programme, message, source, session_id)
    chat_logs(id, created_at, question, answered, top_score, session_id)
"""
from typing import Optional

from . import config


def _cfg(name: str, default: str = "") -> str:
    """Read a config value defensively — a missing attribute (e.g. an app running
    a stale build mid-deploy) degrades to 'off' instead of crashing the app."""
    return getattr(config, name, default)


def enabled() -> bool:
    return bool(_cfg("SUPABASE_URL") and _cfg("SUPABASE_KEY"))


def _headers() -> dict:
    key = _cfg("SUPABASE_KEY")
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }


def _rest(table: str) -> str:
    return f"{_cfg('SUPABASE_URL').rstrip('/')}/rest/v1/{table}"


def _insert(table: str, row: dict) -> bool:
    """Best-effort insert — never raises to the caller (a logging/lead failure
    must not break the chat)."""
    if not enabled():
        return False
    try:
        import requests

        r = requests.post(_rest(table), headers=_headers(), json=row, timeout=15)
        r.raise_for_status()
        return True
    except Exception as exc:
        # Surface the reason in the Streamlit Cloud logs (Manage app → logs) so a
        # rejected write — e.g. wrong key or an RLS block — is diagnosable, without
        # ever leaking to the parent-facing UI.
        resp = getattr(exc, "response", None)
        status = getattr(resp, "status_code", "?")
        body = (getattr(resp, "text", "") or "")[:300]
        print(f"[store] insert into {table} failed (HTTP {status}): {body} — {exc}")
        return False


def create_lead(*, name: str, phone: str, programme: str = None,
                child_age: str = None, message: str = None,
                source: str = "chat", session_id: str = None) -> bool:
    """Store a parent enquiry, and (if configured) fan it out to a webhook so the
    school gets a WhatsApp/email alert."""
    row = {
        "name": (name or "").strip(),
        "phone": (phone or "").strip(),
        "programme": programme,
        "child_age": (child_age or "").strip() or None,
        "message": (message or "").strip() or None,
        "source": source,
        "session_id": session_id,
    }
    ok = _insert("leads", row)
    _notify_webhook(row)
    return ok


def _notify_webhook(row: dict) -> None:
    """Fire-and-forget POST so a no-code automation (Zapier/Make/n8n) can turn a
    lead into a WhatsApp/email alert. Silent if unset or on error."""
    url = _cfg("LEAD_WEBHOOK_URL")
    if not url:
        return
    try:
        import requests

        requests.post(url, json=row, timeout=10)
    except Exception:
        pass


def log_question(question: str, answered: bool, top_score: float = 0.0,
                 session_id: str = None) -> None:
    """Record a question for analytics (what parents ask; what goes unanswered)."""
    _insert("chat_logs", {
        "question": (question or "")[:500],
        "answered": bool(answered),
        "top_score": round(float(top_score or 0.0), 4),
        "session_id": session_id,
    })
