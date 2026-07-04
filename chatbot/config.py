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
LOGO_PATH = ASSETS_DIR / "logo.png"                # brand icon (avatar + tab icon)
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
GROQ_API_KEY = _get("GROQ_API_KEY")
GROQ_MODEL = _get("GROQ_MODEL", "llama-3.3-70b-versatile")

# --- Retrieval / RAG ---
EMBED_MODEL = _get("EMBED_MODEL", "BAAI/bge-small-en-v1.5")
RAG_TOP_K = int(_get("RAG_TOP_K", "5"))
RAG_MIN_SCORE = float(_get("RAG_MIN_SCORE", "0.25"))

# --- School identity ---
SCHOOL_NAME = "Neevalay Tots"
BRAND_NAME = "Ask Neevalay"
MASCOT_NAME = "Neevu"
BRAND_EYEBROW = "Nurturing Roots, Shaping the Future"
BRAND_TAGLINE = ("Ask me about Neevalay Tots — our programmes, approach, "
                 "admissions and daily care.")
WEBSITE_URL = "https://neevalay.com"

# --- Contact / lead capture ---
PHONE = "+91 97117 52584"
WHATSAPP_URL = "https://wa.me/919711752584"
CALL_URL = "tel:+919711752584"
EMAIL = "hello@neevalay.com"
CONTACT_URL = "https://neevalay.com/contact.html"            # general enquiry form
ADMISSION_URL = "https://neevalay.com/admission-form.html"   # admissions application

# --- Brand palette (from the school's designer) ---
COLOR_AQUA = "#5CCCCC"    # Primary — Soft Aqua
COLOR_GOLD = "#F9C764"    # Secondary — Warm Gold
COLOR_BASE = "#F8F9F5"    # Neutral base — Soft Off-White
COLOR_CLAY = "#D77A61"    # Accent / CTA — Clay Terracotta
COLOR_SLATE = "#6D8478"   # Sage Slate (muted text)
COLOR_TEXT = "#3B4A44"    # Deeper slate for body text (readability/contrast)
