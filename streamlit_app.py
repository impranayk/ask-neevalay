"""Ask Neevalay — a warm, brand-matched RAG assistant for Neevalay Tots.

Stack: Groq (open LLMs) for generation + retrieval over a curated knowledge base.
Visual design uses the school's palette (Soft Aqua / Warm Gold / Clay Terracotta
on a Soft Off-White base) with rounded, friendly Quicksand + Nunito Sans type.
"""
import base64
import html
import re
from functools import lru_cache

import streamlit as st

from chatbot import config, llm, rag

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
    text = f"{question} {answer}"
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
    """PIL image for the page icon + assistant avatar (falls back to a sprout)."""
    try:
        from PIL import Image

        if config.LOGO_PATH.exists():
            return Image.open(config.LOGO_PATH)
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

/* ---- Chat messages ---- */
[data-testid="stChatMessage"] { background: transparent; padding: .3rem 0; }
[data-testid="stChatMessage"] p, [data-testid="stChatMessage"] li { font-size: 15.5px; line-height: 1.7; }
[data-testid="stChatMessage"] a { color: var(--clay); text-decoration: none;
  border-bottom: 1px solid rgba(215,122,97,.4); }
[data-testid="stChatMessage"] h1, [data-testid="stChatMessage"] h2, [data-testid="stChatMessage"] h3 {
  font-family: 'Nunito', sans-serif; font-weight: 800; color: var(--text); }
/* Soft card around the assistant reply */
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) {
  background: var(--card); border: 1px solid var(--border); border-radius: 16px;
  padding: 6px 18px; box-shadow: 0 2px 12px rgba(59,74,68,.05); }

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
          <a class="nv-cta-link" href="{config.CONTACT_URL}" target="_blank">Contact us ↗</a>
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
def _hide_streamlit_badge():
    """Hide the Community Cloud 'Built with Streamlit' bar + Fullscreen link."""
    st.html(
        """<script>
        (function(){
          function scrub(d){ if(!d) return; try{
            d.querySelectorAll('a[href*="streamlit.io"],a[href*="streamlit.app"]').forEach(function(a){a.style.display='none';if(a.parentElement){a.parentElement.style.display='none';}});
            Array.prototype.forEach.call(d.querySelectorAll('button,a,span'),function(el){if(el.childElementCount===0){var t=(el.textContent||'').trim();if(t==='Fullscreen'||t==='Built with Streamlit'){var p=el.closest('div');if(p){p.style.display='none';}}}});
          }catch(e){} }
          function kill(){ scrub(document); try{ if(window.parent&&window.parent!==window){ scrub(window.parent.document); } }catch(e){} }
          setInterval(kill,400); kill();
        })();
        </script>""",
        unsafe_allow_javascript=True,
    )


def main():
    _hide_streamlit_badge()
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
        if last.get("followups"):
            render_followups(last["followups"], len(msgs) - 1)

    typed = st.chat_input(f"Ask {config.MASCOT_NAME} about Neevalay Tots…")
    prompt = typed or st.session_state.pop("pending", None)
    if not prompt:
        return

    st.session_state.messages.append({"role": "user", "content": prompt})
    render_user(prompt)

    with st.chat_message("assistant", avatar=logo_image()):
        if not config.GROQ_API_KEY:
            st.error("Add your Groq API key first (see the message above).")
            st.session_state.messages.pop()
            return

        with st.spinner("Looking that up…"):
            results = rag.retrieve(prompt)
            context = rag.format_context(results)

        history = [
            {"role": m["role"], "content": m["content"]}
            for m in st.session_state.messages[:-1]
        ][-6:]

        try:
            answer = st.write_stream(llm.stream_answer(prompt, context, history))
        except Exception as exc:
            st.error(f"Sorry — something went wrong: {exc}")
            st.session_state.messages.pop()
            return

    followups = llm.suggest_followups(prompt, answer)
    cta = _cta_spec(prompt, answer)
    st.session_state.messages.append(
        {"role": "assistant", "content": answer, "followups": followups, "cta": cta}
    )
    st.rerun()


if __name__ == "__main__":
    main()
