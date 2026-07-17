"""Central configuration for Ask Neevalay (the parent-facing assistant).

Reads settings from environment variables (a local .env in development, or
Streamlit secrets when deployed to Streamlit Community Cloud).
"""
import os
from pathlib import Path

from dotenv import load_dotenv

# Load a local .env if present (no-op in production where env vars are set).
load_dotenv()

# --- Paths ---
ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
ASSETS_DIR = ROOT_DIR / "assets"
FAVICON_PATH = ASSETS_DIR / "favicon.png"          # SQUARE badge (tab icon + chat avatar)
LOGO_PATH = ASSETS_DIR / "logo.png"                # portrait brand mark
HEADER_LOGO_PATH = ASSETS_DIR / "logo_horizontal.png"   # full horizontal wordmark for the masthead
EMBEDDINGS_PATH = DATA_DIR / "knowledge.npz"       # numpy vectors
CHUNKS_PATH = DATA_DIR / "chunks.json"             # text + metadata


def _get(name: str, default: str = "") -> str:
    """Read a setting from env first, then Streamlit secrets if available."""
    value = os.getenv(name)
    if value:
        return value
    try:  # Streamlit secrets are optional and only exist when deployed.
        import streamlit as st

        if name in st.secrets:
            return str(st.secrets[name])
    except Exception:
        pass
    return default


# --- LLM (Groq, open models) ---
GROQ_API_KEY = _get("GROQ_API_KEY")        # one key, or several comma-separated
GROQ_API_KEY2 = _get("GROQ_API_KEY2", "")  # optional 2nd-account key for failover
GROQ_MODEL = _get("GROQ_MODEL", "llama-3.3-70b-versatile")          # primary
GROQ_MODEL_FALLBACK = _get("GROQ_MODEL_FALLBACK", "llama-3.1-8b-instant")  # lighter

# Ordered answer-model chain: the app tries the primary, then falls back to the
# lighter model when the primary is rate-limited / out of its daily free quota —
# so parents keep getting answers instead of an error. Override with a
# comma-separated GROQ_MODELS if you want a custom chain.
_models_raw = _get("GROQ_MODELS", "")
if _models_raw:
    GROQ_MODELS = [m.strip() for m in _models_raw.split(",") if m.strip()]
else:
    GROQ_MODELS = [GROQ_MODEL, GROQ_MODEL_FALLBACK]
_seen = set()
GROQ_MODELS = [m for m in GROQ_MODELS if m and not (m in _seen or _seen.add(m))]

# --- Retrieval / RAG ---
EMBED_MODEL = _get("EMBED_MODEL", "BAAI/bge-small-en-v1.5")
RAG_TOP_K = int(_get("RAG_TOP_K", "5"))
RAG_MIN_SCORE = float(_get("RAG_MIN_SCORE", "0.25"))

# --- Leads & analytics (optional Supabase; dark until configured) ---
SUPABASE_URL = _get("SUPABASE_URL", "")
SUPABASE_KEY = _get("SUPABASE_KEY", "")        # service_role key — server-side only
# Optional: POST each captured lead to this URL (Zapier / Make / n8n / Edge
# Function) so the school gets a WhatsApp/email alert. Leave blank to just store.
LEAD_WEBHOOK_URL = _get("LEAD_WEBHOOK_URL", "")
# Gentle abuse guard: max parent messages per browser session before we nudge
# them to WhatsApp (protects the shared Groq daily quota on a public endpoint).
MAX_MESSAGES_PER_SESSION = int(_get("MAX_MESSAGES_PER_SESSION", "25"))

# Programmes offered (for the lead form's "interested in" picker).
PROGRAMMES = [
    "Playgroup (2–3 yrs)", "Nursery (3–4 yrs)", "Kindergarten (4–6 yrs)",
    "Daycare", "Enrichment", "Not sure yet",
]

# --- School identity ---
SCHOOL_NAME = "Neevalay Tots"
BRAND_NAME = "Ask Amma"
MASCOT_NAME = "Amma"
BRAND_EYEBROW = "Nurturing Roots, Shaping the Future"
BRAND_TAGLINE = ("Ask me about Neevalay Tots — our programmes, approach, "
                 "admissions and daily care.")
WEBSITE_URL = "https://neevalay.com"

# --- Contact / lead capture ---
PHONE = "+91 97117 52584"
WHATSAPP_URL = "https://wa.me/919711752584"
CALL_URL = "tel:+919711752584"
EMAIL = "hello@neevalay.com"
# The site moved to WordPress pretty URLs; the old .html paths now 404.
CONTACT_URL = "https://neevalay.com/contact/"                # general enquiry form
# The public "apply" front door is the Stage 2 Registration form (Fluent Forms).
# The full Stage 3 enrolment form lives at /admission/ and is shared privately
# with families the school has accepted.
ADMISSION_URL = "https://neevalay.com/register/"             # Stage 2 registration
VISIT_URL = "https://neevalay.com/programme-enquiries/"      # book-a-visit request form

# --- Brand palette (from the school's designer) ---
COLOR_AQUA = "#5CCCCC"    # Primary — Soft Aqua
COLOR_GOLD = "#F9C764"    # Secondary — Warm Gold
COLOR_BASE = "#F8F9F5"    # Neutral base — Soft Off-White
COLOR_CLAY = "#D77A61"    # Accent / CTA — Clay Terracotta
COLOR_SLATE = "#6D8478"   # Sage Slate (muted text)
COLOR_TEXT = "#3B4A44"    # Deeper slate for body text (readability/contrast)
