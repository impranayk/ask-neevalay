"""Groq-backed generation using open-source models (Llama 3, ...).

The system prompt makes the assistant ("Neevu") warm, parent-friendly, strictly
grounded in Neevalay's information, and safe for a preschool audience.
"""
import re
from typing import Iterator, List, Dict

from groq import Groq

from . import config

# A small, fast model is plenty for generating short follow-up prompts.
FOLLOWUP_MODEL = "llama-3.1-8b-instant"

SYSTEM_PROMPT = (
    f"You are {config.MASCOT_NAME}, the warm and friendly AI guide for "
    f"{config.SCHOOL_NAME}, a research-driven premium preschool in New Delhi "
    f"(\"{config.BRAND_EYEBROW}\"). You help parents with questions about our "
    "programmes, learning approach, admissions, timings and daily care.\n\n"
    "HOW TO ANSWER:\n"
    "- LANGUAGE — ALWAYS reply in the SAME language the parent used in their "
    "latest message. If they wrote in English, reply ONLY in English. If they "
    "wrote in Hindi, reply in Hindi. When in doubt, use English. Never switch "
    "the language on your own.\n"
    "- Be warm, reassuring and concise. Use simple, parent-friendly language, "
    "short sentences, and bullet points where helpful. This is a premium "
    "school, so stay polished — use emojis sparingly, if at all.\n"
    "- Base your answers ONLY on the Neevalay information given in the context. "
    "Do NOT invent fees, dates, addresses, staff ratios, policies, or any fact "
    "that is not in the context.\n"
    "- Each context snippet has a Title and a URL from neevalay.com. When it "
    "helps, point the parent to the relevant page as a Markdown link using its "
    "exact URL from the context (e.g. our [Meet Our Team](URL) page). Only use "
    "URLs that appear in the context — never invent a link.\n"
    "- If the answer is not in the context (for example exact fees, the precise "
    "address, seat availability, or transport), do not guess. Warmly invite the "
    "parent to connect with our team or book a visit, and share our WhatsApp / "
    "phone so they can take the next step.\n"
    "- Never give medical, health, emergency, legal or financial advice. For a "
    "child's health concern or an emergency, gently suggest contacting a doctor "
    "or local emergency services (in India, dial 112).\n"
    "- Do not ask for, or store, a child's sensitive personal details.\n"
    "- When it feels natural, gently encourage booking a campus visit — it is "
    "the best way to experience Neevalay.\n\n"
    f"CONTACT: WhatsApp / Phone {config.PHONE} · {config.EMAIL} · "
    f"{config.WEBSITE_URL}"
)


def _groq_keys():
    keys = []
    for v in (config.GROQ_API_KEY, config.GROQ_API_KEY2):
        keys += [k.strip() for k in (v or "").split(",") if k.strip()]
    seen, out = set(), []
    for k in keys:
        if k not in seen:
            seen.add(k)
            out.append(k)
    return out


def _is_rate_limit(exc) -> bool:
    s = str(exc).lower()
    return ("rate_limit" in s or "429" in s or "tokens per day" in s
            or getattr(exc, "status_code", None) == 429)


def _complete(*, models=None, **kw):
    """One completion (streaming or not) with automatic failover on a rate-limit /
    daily-quota error: it tries each model in `models` (or the single `model=`),
    and for each, every configured key. It only moves on for rate-limit errors —
    any other error surfaces at once. So when the primary model is out of quota it
    silently drops to the lighter fallback, and parents keep getting answers."""
    keys = _groq_keys()
    if not keys:
        raise RuntimeError(
            "GROQ_API_KEY is not set. Copy .env.example to .env and add your "
            "free key from https://console.groq.com/keys"
        )
    if not models:
        models = [kw.pop("model")]
    else:
        kw.pop("model", None)
    last = None
    for model in models:
        for key in keys:
            try:
                return Groq(api_key=key).chat.completions.create(model=model, **kw)
            except Exception as exc:
                last = exc
                if _is_rate_limit(exc):
                    continue          # next key, then next (lighter) model
                raise                 # a real error → surface immediately
    raise last                        # every model+key was rate-limited


def build_messages(question: str, context: str, history: List[Dict]) -> List[Dict]:
    """Assemble the chat payload: system + prior turns + grounded user turn."""
    messages: List[Dict] = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(history)

    if context:
        user_content = (
            "Use the following information about Neevalay Tots to answer the "
            "parent's question.\n\n"
            f"---\n{context}\n---\n\nQuestion: {question}"
        )
    else:
        user_content = (
            f"{question}\n\n(No specific Neevalay information was found for this "
            "question — answer warmly and, if it needs school-specific details, "
            "invite them to contact our team or book a visit.)"
        )

    messages.append({"role": "user", "content": user_content})
    return messages


def suggest_followups(question: str, answer: str) -> List[str]:
    """Return up to 3 short, on-topic follow-up questions in the parent's voice."""
    if not _groq_keys():
        return []
    system = (
        "You suggest what a parent might naturally ask next while chatting with "
        f"{config.SCHOOL_NAME}, a preschool. Given the parent's question and the "
        "assistant's answer, propose 3 short follow-up questions the parent may "
        "have next. Rules: write from the PARENT's point of view; max 8 words; "
        "each ends with '?'; each must be answerable from the school's info "
        "(programmes, ages, admissions, fees, timings, daycare, enrichment, "
        "safety, approach, location); prefer moving toward booking a visit when "
        "natural; do NOT repeat the question already asked. Return ONLY the three "
        "questions, one per line, with no numbering or bullets."
    )
    user = f"Parent asked: {question}\n\nAssistant answered: {answer[:600]}"
    try:
        resp = _complete(
            model=FOLLOWUP_MODEL,
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": user}],
            temperature=0.5,
            max_tokens=90,
        )
        text = resp.choices[0].message.content or ""
    except Exception:
        return []
    out = []
    for line in text.splitlines():
        q = re.sub(r'^[\s\-\*\d\.\)"]+', "", line).strip().strip('"').strip()
        if q.endswith("?") and 6 <= len(q) <= 80 and q.lower() != question.lower():
            out.append(q)
    return out[:3]


def stream_answer(question: str, context: str, history: List[Dict]) -> Iterator[str]:
    """Yield the answer token-by-token for a live typing effect."""
    messages = build_messages(question, context, history)
    completion = _complete(
        models=config.GROQ_MODELS, messages=messages,
        temperature=0.35, max_tokens=800, stream=True,
    )
    for chunk in completion:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta
