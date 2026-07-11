"""Classify whether an event is relevant to India's oil-supply risk.

Heuristic keyword classifier by default. If ``GEMINI_API_KEY`` is set (and the
``google-generativeai`` package is installed) it uses Gemini 2.5 Flash instead,
falling back to the heuristic on any error. This keeps the agent fully testable
standalone with no key, while dropping in a real LLM when one is available.
"""
import os
import re

# Matched on word boundaries so 'oil' doesn't fire on 'boil'/'spoil' and 'port'
# doesn't fire on 'important'/'report'. `\w*` covers inflections.
_RELEVANT = re.compile(
    r"\b(oil|crude\w*|tanker\w*|refiner\w*|strait\w*|shipping|ship|sanction\w*|"
    r"ports?|vessel\w*|opec|pipeline\w*|embargo\w*|naval|maritime|export\w*|"
    r"barrel\w*|brent|petroleum|chokepoint\w*|"
    # geopolitical-escalation terms: for corridor-scoped GDELT results these are
    # genuine risk signals even when the headline never says 'oil'/'tanker'.
    r"blockade\w*|escalat\w*|tension\w*|conflict\w*|closure\w*|hijack\w*|seiz\w*)\b",
    re.IGNORECASE,
)


def is_relevant_heuristic(event: dict) -> bool:
    return bool(_RELEVANT.search(event.get("headline") or ""))


def classify_event(event: dict) -> dict:
    """Return a copy of the event annotated with ``relevant``, ``category`` and
    ``classifier`` (which classifier produced the labels)."""
    if os.environ.get("GEMINI_API_KEY"):
        try:
            return _classify_gemini(event)
        except Exception:
            pass  # graceful fallback to the heuristic below

    out = dict(event)
    relevant = is_relevant_heuristic(event)
    out["relevant"] = relevant
    out["category"] = "energy_supply_risk" if relevant else "other"
    out["classifier"] = "heuristic"
    return out


def _classify_gemini(event: dict) -> dict:
    import json
    import google.generativeai as genai

    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    model = genai.GenerativeModel("gemini-2.5-flash")
    prompt = (
        "You classify news headlines for an India oil-supply-chain risk system. "
        "Reply with ONLY compact JSON like {\"relevant\": true, \"category\": \"...\"}. "
        "relevant=true if the headline could affect crude oil supply, shipping "
        "corridors, tankers, refineries, sanctions or prices reaching India. "
        "category is a short slug.\n\nHeadline: " + (event.get("headline") or "")
    )
    resp = model.generate_content(prompt)
    text = (resp.text or "").strip().strip("`")
    if text.lower().startswith("json"):
        text = text[4:].strip()
    data = json.loads(text)
    out = dict(event)
    out["relevant"] = bool(data.get("relevant"))
    out["category"] = data.get("category") or "unknown"
    out["classifier"] = "gemini-2.5-flash"
    return out
