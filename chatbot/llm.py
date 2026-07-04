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
    "- Be warm, reassuring and concise. Use simple, parent-friendly language, "
    "short sentences, and bullet points where helpful. This is a premium "
    "school, so stay polished — use emojis sparingly, if at all.\n"
    "- Base your answers ONLY on the Neevalay information given in the context. "
    "Do NOT invent fees, dates, addresses, staff ratios, policies, or any fact "
    "that is not in the context.\n"
    "- If the answer is not in the context (for example exact fees, the precise "
    "address, seat availability, or transport), do not guess. Warmly invite the "
    "parent to connect with our team or book a visit, and share our WhatsApp / "
    "phone so they can take the next step.\n"
    "- Never give medical, health, emergency, legal or financial advice. For a "
    "child's health concern or an emergency, gently suggest contacting a doctor "
    "or local emergency services (in India, dial 112).\n"
    "- Do not ask for, or store, a child's sensitive personal details.\n"
    "- When it feels natural, gently encourage booking a campus visit — it is "
    "the best way to experience Neevalay.\n"
    "- If the parent writes in Hindi, reply in Hindi.\n\n"
    f"CONTACT: WhatsApp / Phone {config.PHONE} · {config.EMAIL} · "
    f"{config.WEBSITE_URL}"
)


def _client() -> Groq:
    if not config.GROQ_API_KEY:
        raise RuntimeError(
            "GROQ_API_KEY is not set. Copy .env.example to .env and add your "
            "free key from https://console.groq.com/keys"
        )
    return Groq(api_key=config.GROQ_API_KEY)


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
    if not config.GROQ_API_KEY:
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
        resp = _client().chat.completions.create(
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
    completion = _client().chat.completions.create(
        model=config.GROQ_MODEL,
        messages=messages,
        temperature=0.35,
        max_tokens=800,
        stream=True,
    )
    for chunk in completion:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta
