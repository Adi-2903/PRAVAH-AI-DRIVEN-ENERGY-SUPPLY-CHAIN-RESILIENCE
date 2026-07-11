"""Assign a severity label to an event.

Severity uses the GDELT Goldstein scale when available (-10 most conflictual ..
+10 most cooperative) and falls back to headline keywords otherwise. Values are
the four the frozen schema allows: low, medium, high, critical.

Keywords are matched on **word boundaries** (regex \b) so short words don't
false-match inside longer ones — e.g. 'war' must not fire on 'warship', and
'strike' must not fire inside another word.
"""
import re
from typing import Optional

SEVERITIES = ("low", "medium", "high", "critical")

# Regex fragments; `\w*` suffix means "this stem and its inflections"
# (seiz -> seize/seized/seizure). Everything is matched case-insensitively.
_CRITICAL = re.compile(
    r"\b(attack\w*|strike\w*|missile\w*|seiz\w*|blockade\w*|war|explosion\w*|"
    r"tanker hit|drone hit|closed the strait|shut the strait|shut down the strait)\b",
    re.IGNORECASE,
)
_HIGH = re.compile(
    r"\b(sanction\w*|threat\w*|clash\w*|drone\w*|hijack\w*|military|escalat\w*|"
    r"warship\w*|naval|embargo\w*|seize)\b",
    re.IGNORECASE,
)


_RANK = {"low": 0, "medium": 1, "high": 2, "critical": 3}


def severity_from_goldstein(goldstein: Optional[float]) -> Optional[str]:
    if goldstein is None:
        return None
    if goldstein <= -7:
        return "critical"
    if goldstein <= -4:
        return "high"
    if goldstein <= -1:
        return "medium"
    return "low"


def classify_severity(event: dict) -> str:
    """Severity is the STRONGEST signal among: a critical keyword, a high
    keyword, and the Goldstein band. Taking the max (rather than letting one
    source preempt the others) stops a mildly-cooperative Goldstein value from
    silently downgrading an explicit 'sanctions'/'embargo' headline to low.
    """
    headline = event.get("headline") or ""
    candidates = ["low"]  # floor
    if _CRITICAL.search(headline):
        candidates.append("critical")
    if _HIGH.search(headline):
        candidates.append("high")
    g = severity_from_goldstein(event.get("goldstein_scale"))
    if g:
        candidates.append(g)
    return max(candidates, key=_RANK.__getitem__)
