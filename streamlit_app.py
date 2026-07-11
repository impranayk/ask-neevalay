"""Ask Neevalay — a warm, brand-matched RAG assistant for Neevalay Tots.

Stack: Groq (open LLMs) for generation + retrieval over a curated knowledge base.
Visual design uses the school's palette (Soft Aqua / Warm Gold / Clay Terracotta
on a Soft Off-White base) with rounded, friendly Quicksand + Nunito Sans type.
"""
import base64
import html
import re
import uuid
from functools import lru_cache

import streamlit as st

from chatbot import config, llm, rag, store

# High-intent parent questions where a one-tap action panel helps. (No trailing
# word-boundary so prefixes catch their variants: admiss→admissions, enrol→
# enrolment, program→programme, timing→timings, hour→hours, etc.)
_QUESTION_INTENT = re.compile(
    r"\b(book|visit|tour|appointment|schedule|apply|admiss|enrol|regist|join|"
    r"waitlist|seat|availab|fee|cost|price|pricing|contact|call|whatsapp|phone|"
    r"enquir|inquir|reach|timing|hour|daycare|program|curriculum|enrichment|"
    r"nursery|playgroup|kindergarten)",
    re.I,
)
# The answer itself directing the parent to get in touch / book.
_ANSWER_CONTACT = re.compile(
    r"(whatsapp|contact us|call us|book a|booking|enquir|inquir|reach us|"
    r"wa\.me|\+91|visit us)",
    re.I,
)


_ADMISSION_RE = re.compile(r"\b(apply|admiss|enrol|register|registration)", re.I)
_FEES_RE = re.compile(r"\b(fee|cost|price|pricing|charge)", re.I)


def _wants_action(question: str, answer: str) -> bool:
    return bool(_QUESTION_INTENT.search(question or "")
                or _ANSWER_CONTACT.search(answer or ""))


def _cta_spec(question: str, answer: str):
    """Pick a context-appropriate action panel, or None if not warranted.

    Buttons are (label, url, is_primary). Intent priority: admission > fees >
    everyone else gets the book-a-visit nudge.
    """
    if not _wants_action(question, answer):
        return None
    # Classify by the PARENT'S QUESTION, not the answer — answers often contain
    # page/link titles like "Admission Form" that would skew the intent.
    text = question or ""
    wa = ("WhatsApp us", config.WHATSAPP_URL, False)
    call = ("Call us", config.CALL_URL, False)
    if _ADMISSION_RE.search(text):
        return {"lead": "Ready to apply?",
                "buttons": [("Admission form", config.ADMISSION_URL, True), wa, call]}
    if _FEES_RE.search(text):
        return {"lead": "Want the details?",
                "buttons": [("Ask on WhatsApp", config.WHATSAPP_URL, True),
                            ("Contact us", config.CONTACT_URL, False), call]}
    return {"lead": "Ready to visit us?",
            "buttons": [("Book a visit", config.VISIT_URL, True), wa, call]}


# ----------------------------------------------------------------------------- assets
@lru_cache(maxsize=1)
def _data_uri(path) -> str:
    """Return a base64 data URI for a PNG asset, or '' if missing."""
    try:
        if path.exists():
            b64 = base64.b64encode(path.read_bytes()).decode()
            return f"data:image/png;base64,{b64}"
    except Exception:
        pass
    return ""


@lru_cache(maxsize=1)
def logo_image():
    """PIL image for the page icon + assistant avatar (falls back to a sprout).

    Prefer the SQUARE favicon so the browser-tab icon isn't stretched; fall back
    to the portrait logo only if the favicon is missing."""
    try:
        from PIL import Image

        for p in (config.FAVICON_PATH, config.LOGO_PATH):
            if p.exists():
                return Image.open(p)
    except Exception:
        pass
    return "🌱"


SUGGESTIONS = [
    "Which programmes do you offer, and for what ages?",
    "What is your teaching approach?",
    "How do I book a visit or apply?",
    "What are your timings and daycare options?",
]

st.set_page_config(
    page_title=config.BRAND_NAME,
    page_icon=logo_image(),
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ----------------------------------------------------------------------------- styling
st.markdown(
    """
<style>
/* Official brand type: Nunito (headlines) + Nunito Sans (body) */
@import url('https://fonts.googleapis.com/css2?family=Nunito:wght@600;700;800&family=Nunito+Sans:wght@400;600;700&display=swap');

:root {
  --aqua: #5CCCCC; --aqua-dark: #3fb0b0; --aqua-soft: #EAF7F7;
  --gold: #F9C764; --clay: #D77A61; --clay-dark: #c15f47;
  --base: #F8F9F5; --card: #ffffff; --slate: #6D8478;
  --text: #3B4A44; --border: #E6EAE3;
}

html, body, [class*="css"], .stApp { font-family: 'Nunito Sans', sans-serif; color: var(--text); }
.stApp { background: var(--base); }

/* Hide Streamlit chrome + the Community Cloud badge */
#MainMenu, footer, [data-testid="stToolbar"], [data-testid="stDecoration"],
[data-testid="stStatusWidget"], [data-testid="stAppViewerBadge"],
[data-testid="stAppDeployButton"],
[class*="viewerBadge"], [class*="_viewerBadge"], [class*="ViewerBadge"],
[class*="_profileContainer"], [class*="profileContainer"],
a[href*="streamlit.io"], a[href*="streamlit.app"] { display: none !important; }
header[data-testid="stHeader"] { background: transparent; height: 0; }
.st-key-new_chat { margin-top: 6px; }

.block-container { max-width: 800px; padding-top: 1.5rem; padding-bottom: 6rem; }

/* ---- Masthead ---- */
.nv-masthead { display: flex; flex-direction: column; align-items: flex-start; gap: 2px; }
.nv-logo { height: clamp(42px, 11vw, 54px); width: auto; max-width: 100%; }
.nv-title { font-family: 'Nunito', sans-serif !important; color: var(--text);
            font-size: clamp(24px, 6.5vw, 34px); font-weight: 800; letter-spacing: .2px;
            line-height: 1 !important; margin: 0 !important; }
.nv-title .accent { color: var(--aqua); }
.nv-eyebrow { font-family: 'Nunito', sans-serif; color: var(--slate);
              font-size: clamp(11px, 3vw, 12.5px); font-weight: 700; letter-spacing: .3px;
              margin: 4px 0 0 !important; }
.nv-rule { height: 3px; border: 0; border-radius: 3px; margin: 14px 0 12px;
           background: linear-gradient(90deg, var(--aqua) 0%, var(--gold) 100%); }

/* ---- Contact / lead-capture bar ---- */
.nv-contactbar { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin: 0 0 6px; }
.nv-cta { display: inline-flex; align-items: center; gap: 6px; text-decoration: none !important;
          font-weight: 700; font-size: 13.5px; border-radius: 999px; padding: 8px 16px;
          transition: all .15s; }
.nv-cta-primary { background: var(--clay); color: #fff !important;
                  box-shadow: 0 2px 8px rgba(215,122,97,.30); }
.nv-cta-primary:hover { background: var(--clay-dark); transform: translateY(-1px); }
.nv-cta-ghost { background: #fff; color: var(--text) !important; border: 1.5px solid var(--border); }
.nv-cta-ghost:hover { border-color: var(--aqua); color: var(--aqua-dark) !important; }
.nv-cta-link { color: var(--aqua-dark) !important; font-weight: 700; font-size: 13px;
               text-decoration: none !important; padding: 8px 6px; }

/* ---- Chat messages (every stChatMessage is a Neevu reply) ---- */
[data-testid="stChatMessage"] { background: transparent; padding: .35rem 0;
  gap: 10px; align-items: flex-start; }
[data-testid="stChatMessage"] > img { width: 40px; height: 40px; border-radius: 11px;
  border: 1.5px solid var(--border); background: #fff; padding: 4px; box-sizing: border-box;
  object-fit: contain; }
/* the reply sits in a soft rounded card, its corner pointing at the avatar */
[data-testid="stChatMessageContent"] { background: #fff; border: 1px solid var(--border);
  border-radius: 5px 16px 16px 16px; padding: 4px 18px 8px;
  box-shadow: 0 2px 14px rgba(59,74,68,.05); }
[data-testid="stChatMessageContent"] p,
[data-testid="stChatMessageContent"] li { font-size: 15.5px; line-height: 1.75; }
[data-testid="stChatMessageContent"] strong { color: #2f3b36; font-weight: 700; }
[data-testid="stChatMessageContent"] a { color: var(--clay); text-decoration: none;
  border-bottom: 1px solid rgba(215,122,97,.45); font-weight: 600; }
[data-testid="stChatMessageContent"] a:hover { border-bottom-color: var(--clay); }
[data-testid="stChatMessageContent"] h1, [data-testid="stChatMessageContent"] h2,
[data-testid="stChatMessageContent"] h3 { font-family: 'Nunito', sans-serif; font-weight: 800;
  color: var(--text); margin: .5rem 0 .3rem; }
/* friendly rounded list markers, alternating aqua / gold */
[data-testid="stChatMessageContent"] ul { list-style: none; padding-left: 2px; margin: .45rem 0; }
[data-testid="stChatMessageContent"] li { position: relative; padding-left: 22px; margin: 7px 0; }
[data-testid="stChatMessageContent"] li::before { content: ""; position: absolute; left: 2px;
  top: .62em; width: 9px; height: 9px; border-radius: 50%; background: var(--aqua); }
[data-testid="stChatMessageContent"] li:nth-child(even)::before { background: var(--gold); }
/* "Neevu is typing…" indicator */
.nv-typing { display: inline-flex; align-items: center; gap: 6px; padding: 4px 2px; }
.nv-typing span { width: 9px; height: 9px; border-radius: 50%; background: var(--aqua);
  display: inline-block; animation: nv-blink 1.2s infinite ease-in-out both; }
.nv-typing span:nth-child(2) { background: var(--gold); animation-delay: .18s; }
.nv-typing span:nth-child(3) { background: var(--clay); animation-delay: .36s; }
@keyframes nv-blink { 0%, 80%, 100% { transform: scale(.6); opacity: .35; }
  40% { transform: scale(1); opacity: 1; } }

/* ---- User question bubble (right, aqua tint) ---- */
.nv-user-row { display: flex; justify-content: flex-end; margin: 14px 0 6px; }
.nv-user-bubble { background: var(--aqua-soft); color: var(--text); border: 1px solid #cfeeee;
  border-right: 3px solid var(--aqua); border-radius: 16px 16px 4px 16px;
  padding: 10px 15px; max-width: 82%; font-size: 15px; line-height: 1.55; white-space: pre-wrap; }

/* ---- Empty-state intro + suggestion chips ---- */
.nv-intro { color: var(--slate); font-size: 15px; margin: 4px 0 14px; line-height: 1.6; }
.nv-follow-label { color: var(--slate); font-size: 11.5px; font-weight: 700; letter-spacing: .5px;
  text-transform: uppercase; margin: 16px 0 6px; opacity: .8; }
/* Contextual one-tap action panel under booking/contact answers */
.nv-answer-cta { display: flex; flex-wrap: wrap; align-items: center; gap: 8px;
  background: var(--aqua-soft); border: 1px solid #cfeeee; border-radius: 14px;
  padding: 12px 14px; margin: 14px 0 2px; }
.nv-cta-lead { font-weight: 700; font-size: 13.5px; color: var(--text); margin-right: 2px; }
.nv-lead-done { background: var(--aqua-soft); border: 1px solid #cfeeee; border-radius: 12px;
  padding: 10px 14px; margin: 8px 0; color: var(--aqua-dark); font-weight: 700; font-size: 14px; }
/* ---- Friendly fallback card (model can't answer → WhatsApp/Call) ---- */
.nv-error-card { background: #FEFBF2; border: 1px solid #F0D9AE; border-radius: 14px;
  padding: 13px 16px; margin: 6px 0; }
.nv-error-text { color: var(--text); font-size: 15px; line-height: 1.6; margin-bottom: 10px; }
.nv-error-cta { display: flex; flex-wrap: wrap; gap: 8px; }
/* ---- Lead-capture card ("Prefer we call you?") — warm, on-brand ---- */
[class*="st-key-nvlead_"] details { border: 1.5px solid #cfeeee !important; border-radius: 14px !important;
  background: var(--aqua-soft) !important; box-shadow: 0 2px 10px rgba(59,74,68,.05) !important; }
[class*="st-key-nvlead_"] summary { font-family: 'Nunito', sans-serif !important; font-weight: 800 !important;
  color: var(--text) !important; font-size: 14.5px !important; }
[class*="st-key-nvlead_"] summary [data-testid="stIconMaterial"],
[class*="st-key-nvlead_"] summary svg { color: var(--clay) !important; fill: var(--clay) !important; }
/* the "Request a callback" submit as the clay CTA (matches the site's Book-a-visit) */
[class*="st-key-nvlead_"] [data-testid="stFormSubmitButton"] button { background: var(--clay) !important;
  color: #fff !important; border: 0 !important; border-radius: 999px !important; font-weight: 800 !important;
  font-family: 'Nunito', sans-serif !important; box-shadow: 0 2px 8px rgba(215,122,97,.28) !important; }
[class*="st-key-nvlead_"] [data-testid="stFormSubmitButton"] button:hover { background: var(--clay-dark) !important;
  transform: translateY(-1px); }
[class*="st-key-nvlead_"] [data-baseweb="input"],
[class*="st-key-nvlead_"] [data-baseweb="select"] > div:first-child { border-radius: 10px !important; }
div[data-testid="stButton"] > button {
  border: 1.5px solid var(--border); background: #fff; color: var(--text);
  border-radius: 999px; padding: 9px 16px; font-size: 13.5px; font-weight: 600;
  text-align: left; transition: all .15s; }
div[data-testid="stButton"] > button:hover {
  border-color: var(--aqua); color: var(--aqua-dark); background: var(--aqua-soft); }
.st-key-new_chat button { border: 1.5px solid var(--aqua) !important; color: var(--aqua-dark) !important;
  text-align: center !important; }
.st-key-new_chat button:hover { background: var(--aqua) !important; color: #fff !important; }

/* ---- Chat input ---- */
[data-testid="stChatInput"] { border: 1.5px solid var(--aqua) !important; border-radius: 16px !important;
  background: #fff !important; }
[data-testid="stChatInput"] > div { border: 0 !important; background: transparent !important; }
[data-testid="stChatInput"]:focus-within { box-shadow: 0 0 0 3px rgba(92,204,204,.20) !important; }
[data-testid="stChatInputSubmitButton"] { background: var(--aqua) !important; border-radius: 12px !important; }
[data-testid="stChatInputSubmitButton"]:hover { background: var(--aqua-dark) !important; }
[data-testid="stChatInputSubmitButton"] svg { color: #fff !important; fill: #fff !important; }

/* ---- Sidebar ---- */
[data-testid="stSidebar"] { background: #fff; border-right: 1px solid var(--border); }
</style>
""",
    unsafe_allow_html=True,
)


# ----------------------------------------------------------------------------- components
def clear_chat():
    st.session_state.messages = []
    st.session_state.pop("pending", None)


def render_contactbar():
    st.markdown(
        f"""
        <div class="nv-contactbar">
          <a class="nv-cta nv-cta-primary" href="{config.WHATSAPP_URL}" target="_blank">Book a visit</a>
          <a class="nv-cta nv-cta-ghost" href="{config.CALL_URL}">Call us</a>
          <a class="nv-cta-link" href="{config.CONTACT_URL}" target="_blank">Contact us <svg viewBox="0 0 24 24" width="11" height="11" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:-1px"><path d="M8 16 16 8"/><path d="M9 8h7v7"/></svg></a>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_header():
    if "mini" in st.query_params:
        _, right = st.columns([2, 1])
        with right:
            st.button("↺  New chat", key="new_chat", on_click=clear_chat,
                      use_container_width=True)
        return
    header_logo = _data_uri(config.HEADER_LOGO_PATH)
    left, right = st.columns([5, 1.4], vertical_alignment="center")
    with left:
        if header_logo:
            brand = (f'<img class="nv-logo" src="{header_logo}" '
                     f'alt="{config.SCHOOL_NAME}">')
        else:
            brand = ('<h1 class="nv-title">Ask <span class="accent">Neevalay</span></h1>')
        st.markdown(
            f"""
            <div class="nv-masthead">
              {brand}
              <p class="nv-eyebrow">Parent Assistant · here to help you and your little one</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with right:
        st.button("↺  New chat", key="new_chat", on_click=clear_chat,
                  use_container_width=True)
    st.markdown('<hr class="nv-rule">', unsafe_allow_html=True)
    render_contactbar()


def render_sidebar():
    with st.sidebar:
        st.markdown(f"### {config.BRAND_NAME}")
        st.caption(f"Your friendly guide to {config.SCHOOL_NAME}. "
                   "I answer from the school's own information.")
        st.markdown(f"[neevalay.com]({config.WEBSITE_URL})")
        st.divider()
        st.caption(f"WhatsApp / Call: {config.PHONE}")
        st.caption(f"Email: {config.EMAIL}")
        st.caption("Open Mon–Sat, 8:00 AM – 7:00 PM")
        if store.enabled():
            st.divider()
            render_lead_form("sidebar")
        st.divider()
        st.caption("Knowledge base: " + ("ready" if rag.has_knowledge() else "not built yet"))
        if st.button("Clear conversation", use_container_width=True):
            st.session_state.messages = []
            st.rerun()


def render_user(text: str):
    st.markdown(
        f'<div class="nv-user-row"><div class="nv-user-bubble">'
        f'{html.escape(text)}</div></div>',
        unsafe_allow_html=True,
    )


def pick_suggestion(question: str):
    st.session_state.pending = question


def render_followups(items, midx):
    """Related next-question chips shown under the latest answer."""
    st.markdown('<p class="nv-follow-label">You might also ask</p>',
                unsafe_allow_html=True)
    cols = st.columns(2)
    for i, q in enumerate(items):
        cols[i % 2].button(q, key=f"fu_{midx}_{i}", use_container_width=True,
                           on_click=pick_suggestion, args=(q,))


def render_error_card(rate_limited: bool = False):
    """A warm, on-brand fallback when the model can't answer — turns a dead-end
    into a WhatsApp/Call hand-off instead of a bare error line."""
    lead = ("We're getting a lot of questions right now"
            if rate_limited else "I'm having a little trouble answering right now")
    st.markdown(
        f'<div class="nv-error-card"><div class="nv-error-text">{lead} — but our '
        'team would be delighted to help you directly. Reach us here:</div>'
        '<div class="nv-error-cta">'
        f'<a class="nv-cta nv-cta-primary" href="{config.WHATSAPP_URL}" target="_blank">WhatsApp us</a>'
        f'<a class="nv-cta nv-cta-ghost" href="{config.CALL_URL}">Call us</a>'
        '</div></div>',
        unsafe_allow_html=True,
    )


def render_answer_cta(spec):
    """One-tap action panel, tailored to the question's intent."""
    btns = ""
    for label, url, primary in spec["buttons"]:
        cls = "nv-cta-primary" if primary else "nv-cta-ghost"
        target = ' target="_blank"' if url.startswith("http") else ""
        btns += f'<a class="nv-cta {cls}" href="{url}"{target}>{label}</a>'
    st.markdown(
        f'<div class="nv-answer-cta"><span class="nv-cta-lead">{spec["lead"]}</span>'
        f'{btns}</div>',
        unsafe_allow_html=True,
    )


def render_lead_form(key: str, *, compact: bool = False):
    """Capture a callback request (name + phone + programme) inside the chat and
    store it. Only shown when the Supabase store is configured."""
    if not store.enabled():
        return
    if st.session_state.get("lead_done"):
        st.markdown('<div class="nv-lead-done">✓ Thank you! Our team will '
                    'reach out to you shortly.</div>', unsafe_allow_html=True)
        return
    with st.container(key=f"nvlead_{key}"), \
            st.expander("Prefer we call you? Leave your number", icon=":material/call:"):
        with st.form(f"lead_{key}", clear_on_submit=False):
            c1, c2 = st.columns(2)
            name = c1.text_input("Your name", key=f"lead_name_{key}")
            phone = c2.text_input("Phone / WhatsApp", key=f"lead_phone_{key}")
            email = st.text_input("Email (optional)", key=f"lead_email_{key}",
                                  placeholder="you@email.com")
            prog = st.selectbox("Interested in",
                                getattr(config, "PROGRAMMES", ["General enquiry"]),
                                key=f"lead_prog_{key}")
            submitted = st.form_submit_button("Request a callback",
                                              use_container_width=True)
        if submitted:
            digits = re.sub(r"\D", "", phone or "")
            if not name.strip() or len(digits) < 10:
                st.warning("Please add your name and a valid phone number.")
            elif store.create_lead(name=name, phone=phone, email=email, programme=prog,
                                   source="chat",
                                   session_id=st.session_state.get("sid")):
                st.session_state.lead_done = True
                st.rerun()
            else:
                msg = ("Sorry, I couldn't save that just now — please WhatsApp "
                       f"us at {config.PHONE} and we'll help you right away.")
                # Add ?debug to the URL to see the exact API error inline.
                if "debug" in st.query_params and store.last_error():
                    msg += f"\n\n**Debug:** `{store.last_error()}`"
                st.warning(msg)


def render_empty_state():
    st.markdown(
        f'<p class="nv-intro">Hi, I\'m <b>{config.MASCOT_NAME}</b> — your friendly '
        f'guide to {config.SCHOOL_NAME}. Ask me about our programmes, approach, '
        'admissions or daily care — or start with one of these:</p>',
        unsafe_allow_html=True,
    )
    cols = st.columns(2)
    for i, q in enumerate(SUGGESTIONS):
        cols[i % 2].button(q, key=f"sug_{i}", use_container_width=True,
                           on_click=pick_suggestion, args=(q,))


# ----------------------------------------------------------------------------- app
def main():
    # The 'Built with Streamlit' badge + viewer chrome are hidden by the CSS block
    # above (a[href*="streamlit.io/.app"], viewerBadge, etc.) — no JS needed.
    render_sidebar()
    render_header()

    if not config.GROQ_API_KEY:
        st.warning(
            "**Setup needed:** add a free Groq API key to run the assistant.\n\n"
            "1. Get a key at https://console.groq.com/keys\n"
            "2. Locally: copy `.env.example` to `.env` and paste the key.\n"
            "3. On Streamlit Cloud: add `GROQ_API_KEY` in **Settings → Secrets**."
        )

    if "messages" not in st.session_state:
        st.session_state.messages = []
    st.session_state.setdefault("sid", uuid.uuid4().hex[:12])

    if not st.session_state.messages and not st.session_state.get("pending"):
        render_empty_state()

    for msg in st.session_state.messages:
        if msg["role"] == "user":
            render_user(msg["content"])
        else:
            with st.chat_message("assistant", avatar=logo_image()):
                st.markdown(msg["content"])

    # Under the most recent answer: a one-tap action panel (if intent) + chips.
    msgs = st.session_state.messages
    if msgs and msgs[-1]["role"] == "assistant":
        last = msgs[-1]
        if last.get("cta"):
            render_answer_cta(last["cta"])
            render_lead_form(len(msgs) - 1)          # callback capture on high intent
        if last.get("followups"):
            render_followups(last["followups"], len(msgs) - 1)

    typed = st.chat_input(f"Ask {config.MASCOT_NAME} about Neevalay Tots…")
    prompt = typed or st.session_state.pop("pending", None)
    if not prompt:
        return

    # Gentle abuse guard: cap messages per session so a public endpoint can't burn
    # the shared Groq daily quota. Hand the parent to WhatsApp instead.
    if sum(1 for m in msgs if m["role"] == "user") >= getattr(config, "MAX_MESSAGES_PER_SESSION", 25):
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.session_state.messages.append({
            "role": "assistant",
            "content": f"I've loved chatting with you! 🌱 For anything more, our "
                       f"team will be delighted to help you directly on WhatsApp at "
                       f"**{config.PHONE}**.",
            "cta": {"lead": "Let's continue there:",
                    "buttons": [("WhatsApp us", config.WHATSAPP_URL, True),
                                ("Call us", config.CALL_URL, False)]},
        })
        st.rerun()

    st.session_state.messages.append({"role": "user", "content": prompt})
    render_user(prompt)

    with st.chat_message("assistant", avatar=logo_image()):
        if not config.GROQ_API_KEY:
            st.error("Add your Groq API key first (see the message above).")
            st.session_state.messages.pop()
            return

        typing = st.empty()
        typing.markdown(
            '<div class="nv-typing"><span></span><span></span><span></span></div>',
            unsafe_allow_html=True,
        )
        results = rag.retrieve(prompt)
        context = rag.format_context(results)
        typing.empty()

        history = [
            {"role": m["role"], "content": m["content"]}
            for m in st.session_state.messages[:-1]
        ][-6:]

        try:
            answer = st.write_stream(llm.stream_answer(prompt, context, history))
        except Exception as exc:
            print(f"[llm] answer failed: {type(exc).__name__}: {exc}")  # → app logs
            render_error_card(rate_limited=llm._is_rate_limit(exc))
            st.session_state.messages.pop()
            return

    followups = llm.suggest_followups(prompt, answer)
    cta = _cta_spec(prompt, answer)
    # Analytics: what parents ask + whether we had grounded info for it (best-effort).
    store.log_question(prompt, answered=bool(results),
                       top_score=(results[0]["score"] if results else 0.0),
                       session_id=st.session_state.get("sid"))
    st.session_state.messages.append(
        {"role": "assistant", "content": answer, "followups": followups, "cta": cta}
    )
    st.rerun()


if __name__ == "__main__":
    main()
