"""Admissions Assistant - guided programme finder + lead capture.

Design rule: which programme fits a child's age is a FACT, so it is computed
here, never left to the language model. The model only writes the warm, grounded
rationale ("why this fits your child"), and is forbidden from stating fees or
inventing anything not in the retrieved website context.
"""
from typing import List, Dict, Optional

# What a parent can say matters to them. Used to surface Daycare / Enrichment as
# add-ons and to colour the rationale - NOT to change the core age recommendation.
PRIORITIES = [
    "Play-based learning",
    "School readiness (reading, numbers)",
    "Full-day care while we work",
    "Extra activities (art, music, STEM)",
    "Social confidence & making friends",
    "A gentle first step away from home",
    "Montessori / Reggio approach",
    "Safety & hygiene",
]

START_WHEN = ["As soon as possible", "In 1-3 months", "Next term / next year",
              "Just exploring for now"]

# Core age bands (years). Ranges match the website programmes.
_BANDS = [
    (2.0, 3.0, "Playgroup", "our gentle first step for little ones aged 2 to 3"),
    (3.0, 4.0, "Nursery", "for curious 3 to 4 year-olds finding their independence"),
    (4.0, 6.0, "Kindergarten", "for 4 to 6 year-olds getting ready for big school"),
]


def recommend(age_years: Optional[float], priorities: List[str]) -> Dict:
    """Return the recommended programme for a child, deterministically.

    `programme` is the best-fit core programme (or None when the age sits outside
    2-6, which routes to a friendly 'let's talk' instead of a wrong guess).
    `addons` are Daycare / Enrichment surfaced from what the parent said matters.
    """
    prio = set(priorities or [])
    programme = fit_note = None
    too_young = too_old = False

    if age_years is not None:
        if age_years < 2.0:
            too_young = True
        elif age_years >= 6.0:
            too_old = True
        else:
            for lo, hi, name, note in _BANDS:
                if lo <= age_years < hi:
                    programme, fit_note = name, note
                    break

    addons = []
    if "Full-day care while we work" in prio:
        addons.append(("Daycare", "so your child is cared for through your full working day"))
    if "Extra activities (art, music, STEM)" in prio:
        addons.append(("Enrichment", "for art, music, movement and STEM beyond the core day"))

    return {
        "programme": programme,      # e.g. "Nursery", or None
        "fit_note": fit_note,        # short human phrase, or None
        "addons": addons,            # list of (name, why)
        "too_young": too_young,      # under 2
        "too_old": too_old,          # 6+
    }


def rationale_prompt(child_first: str, age_label: str, rec: Dict,
                     priorities: List[str], context: str) -> str:
    """Prompt for the warm 'why this fits' note. Grounded, no fees, no invention."""
    child = (child_first or "").strip() or "your child"
    prog = rec.get("programme")
    prio = ", ".join(priorities) if priorities else "a happy, confident start"
    addon_txt = ""
    if rec.get("addons"):
        addon_txt = ("You may also mention, in one short line, these as optional "
                     "add-ons: "
                     + "; ".join(f"{n} ({why})" for n, why in rec["addons"]) + ".\n")

    if prog:
        head = (f"A parent is exploring Neevalay Tots for {child} (age {age_label}). "
                f"Based on the child's age, the right core programme is **{prog}**. "
                f"What matters to this family: {prio}.\n\n")
        task = (f"Write a warm, personal 2-3 sentence note to the parent on why "
                f"{prog} is a lovely fit for {child}, connecting it to what they "
                f"care about. ")
    else:
        # Age sits outside 2-6: never force a programme.
        head = (f"A parent is exploring Neevalay Tots for {child} (age {age_label}), "
                f"which is outside our usual 2-6 programme ages. What matters to "
                f"them: {prio}.\n\n")
        task = (f"Write a warm 2-3 sentence note that does NOT assign a specific "
                f"programme, invites them to speak with the team about the best fit "
                f"for {child}'s age, and stays encouraging. ")

    return (
        head +
        "Use ONLY the Neevalay information below; do not invent programmes, ages, "
        "ratios, timings or facts not present here.\n\n"
        f"NEEVALAY INFORMATION:\n{context}\n\n"
        + task + addon_txt +
        "RULES:\n"
        "- NEVER state, estimate or hint at any fee, price, or cost. If fees come "
        "up, say the team shares current fees on a call/visit.\n"
        "- Use the child's FIRST name only; never ask for or use a surname.\n"
        "- Warm and specific, not salesy. No emoji. Plain hyphens, never dashes.\n"
        "- 2-3 sentences, no heading, no bullet points."
    )
