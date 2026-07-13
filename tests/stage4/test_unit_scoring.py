"""
test_unit_scoring.py — Stage 4 unit tests for the risk-agent scoring layer.

Pure functions, no network, no DB: the corridor mapper, severity classifier,
relevance classifier, and the aggregate risk model (bounds, clamping, recency,
confidence, key-event ordering).
"""
from datetime import datetime, timedelta, timezone

import pytest

from scoring.corridor_map import corridor_for_country, corridor_for_text, assign_corridor
from scoring.severity import severity_from_goldstein, classify_severity
from scoring.classify import is_relevant_heuristic
from scoring.risk_model import compute_risk, alert_level_for, recency_factor

AS_OF = datetime(2026, 7, 11, tzinfo=timezone.utc)


def _ev(severity, days_ago=1, goldstein=None, headline=None):
    return {
        "headline": headline or f"{severity} event",
        "severity": severity,
        "event_date": AS_OF - timedelta(days=days_ago),
        "goldstein_scale": goldstein,
        "relevant": True,
    }


# ── corridor mapping ────────────────────────────────────────────────────────
class TestCorridorMap:
    def test_country_to_corridor(self):
        assert corridor_for_country("SAU") == "hormuz"
        assert corridor_for_country("irn") == "hormuz"      # case-insensitive
        assert corridor_for_country("RUS") == "redsea"
        assert corridor_for_country("NGA") == "cape"
        assert corridor_for_country("IND") == "domestic"
        assert corridor_for_country(None) is None
        assert corridor_for_country("ZZZ") is None

    def test_keyword_to_corridor(self):
        assert corridor_for_text("Tanker seized in the Strait of Hormuz") == "hormuz"
        assert corridor_for_text("Houthi drone hits ship in the Red Sea") == "redsea"
        assert corridor_for_text("More crude via the Cape of Good Hope") == "cape"
        assert corridor_for_text("An ordinary day with no signals") is None

    def test_keyword_beats_country(self):
        ev = {"headline": "Red Sea attack disrupts shipping", "country_code": "SAU"}
        assert assign_corridor(ev) == "redsea"

    def test_word_boundary_no_false_corridor(self):
        # 'aden' as a whole word maps to redsea, but must not fire inside 'garden'
        assert corridor_for_text("Gulf of Aden patrols increased") == "redsea"
        assert corridor_for_text("A garden party in the suburbs") is None

    def test_cape_route_avoid_suez_maps_to_cape(self):
        # regression (audit M1): "take the Cape … to avoid Suez" mentions 'suez'
        # (a redsea keyword) but is a cape-route event; cape must win.
        headline = "More tankers take the Cape of Good Hope route to avoid Suez"
        assert corridor_for_text(headline) == "cape"


# ── severity ────────────────────────────────────────────────────────────────
class TestSeverity:
    def test_goldstein_bands(self):
        assert severity_from_goldstein(-8) == "critical"
        assert severity_from_goldstein(-5) == "high"
        assert severity_from_goldstein(-2) == "medium"
        assert severity_from_goldstein(3) == "low"
        assert severity_from_goldstein(None) is None

    def test_critical_keyword_overrides(self):
        assert classify_severity({"headline": "Missile strike on tanker", "goldstein_scale": -1.0}) == "critical"

    def test_keyword_fallback_without_goldstein(self):
        assert classify_severity({"headline": "New sanctions on shipping firm", "goldstein_scale": None}) == "high"
        assert classify_severity({"headline": "Routine port notice", "goldstein_scale": None}) == "low"

    def test_war_does_not_match_warship(self):
        # not critical (word boundary); high because 'warship' is a HIGH keyword
        assert classify_severity({"headline": "US Navy warship escorts tanker", "goldstein_scale": -2.0}) == "high"
        assert classify_severity({"headline": "Fears of war grow", "goldstein_scale": None}) == "critical"

    def test_cooperative_goldstein_does_not_suppress_high_keyword(self):
        # regression (audit M2): strongest signal wins, not Goldstein-preempts.
        ev = {"headline": "Fresh sanctions and embargo on tanker fleet", "goldstein_scale": 0.5}
        assert classify_severity(ev) == "high"


# ── relevance classifier ────────────────────────────────────────────────────
class TestClassify:
    def test_relevant(self):
        assert is_relevant_heuristic({"headline": "Oil tanker seized in strait"})
        assert is_relevant_heuristic({"headline": "OPEC signals steady crude exports"})

    def test_word_boundary_false_positives(self):
        assert not is_relevant_heuristic({"headline": "How to boil the perfect egg"})     # not 'oil'
        assert not is_relevant_heuristic({"headline": "An important local report"})        # not 'port'
        assert not is_relevant_heuristic({"headline": "City council debates funding"})

    def test_recall_improvements(self):
        # regression (audit M3): plural 'ports' and geopolitical escalation terms
        assert is_relevant_heuristic({"headline": "Two ports closed after storm"})
        assert is_relevant_heuristic({"headline": "Iran-Israel tensions escalate sharply"})


# ── aggregate risk model ────────────────────────────────────────────────────
class TestRiskModel:
    def test_alert_thresholds(self):
        assert alert_level_for(80) == "critical"
        assert alert_level_for(75) == "critical"    # boundary inclusive
        assert alert_level_for(60) == "high"
        assert alert_level_for(40) == "elevated"
        assert alert_level_for(30) == "elevated"    # boundary inclusive
        assert alert_level_for(10) == "low"
        assert alert_level_for(0) == "low"

    def test_recency_decay(self):
        assert recency_factor(AS_OF - timedelta(days=1), AS_OF) == 1.0
        assert recency_factor(AS_OF - timedelta(days=7), AS_OF) == 1.0     # boundary
        assert recency_factor(AS_OF - timedelta(days=40), AS_OF) == 0.2
        assert 0.2 < recency_factor(AS_OF - timedelta(days=18), AS_OF) < 1.0

    def test_no_events_returns_baseline(self):
        r = compute_risk("hormuz", [], AS_OF, data_sources=["fixtures"])
        assert r["score"] == 60.0
        assert r["alert_level"] == "high"
        assert r["key_events"] == []

    def test_bounds_always_hold(self):
        for corridor in ("hormuz", "redsea", "cape", "domestic"):
            r = compute_risk(corridor, [_ev("critical", goldstein=-9) for _ in range(20)],
                             AS_OF, data_sources=["fixtures", "gdelt"])
            assert 0.0 <= r["score"] <= 100.0
            assert 0.0 <= r["confidence"] <= 1.0
            assert r["alert_level"] in ("low", "elevated", "high", "critical")

    def test_score_clamps_at_100(self):
        r = compute_risk("hormuz", [_ev("critical", goldstein=-10) for _ in range(30)],
                         AS_OF, data_sources=["fixtures", "gdelt"])
        assert r["score"] == 100.0
        assert r["alert_level"] == "critical"

    def test_key_events_sorted_and_capped(self):
        events = [_ev("low"), _ev("critical"), _ev("medium"), _ev("high"),
                  _ev("critical"), _ev("low"), _ev("high")]
        r = compute_risk("hormuz", events, AS_OF, data_sources=["fixtures"])
        assert len(r["key_events"]) == 5                     # top-5 only
        assert r["key_events"][0]["severity"] == "critical"  # most severe first

    def test_output_shape(self):
        r = compute_risk("redsea", [_ev("high")], AS_OF, data_sources=["fixtures"])
        for key in ("score", "confidence", "alert_level", "reasoning_trail", "key_events", "data_sources"):
            assert key in r
        assert isinstance(r["reasoning_trail"], list) and r["reasoning_trail"]

    def test_data_sources_deduped(self):
        r = compute_risk("hormuz", [_ev("low")], AS_OF, data_sources=["fixtures", "fixtures", "gdelt"])
        assert r["data_sources"] == ["fixtures", "gdelt"]

    def test_naive_event_date_does_not_crash(self):
        # regression (audit L2): a naive event_date must not raise on aware/naive
        # subtraction inside the recency math.
        naive_event = {"headline": "x", "severity": "high",
                       "event_date": datetime(2026, 7, 9), "goldstein_scale": None,
                       "relevant": True}
        r = compute_risk("hormuz", [naive_event], AS_OF, data_sources=["fixtures"])
        assert 0.0 <= r["score"] <= 100.0

    def test_unknown_severity_normalized(self):
        # regression (audit L3): a bogus severity must degrade to 'low', never
        # break the frozen KeyEvent enum.
        bad = {"headline": "weird", "severity": "apocalyptic",
               "event_date": AS_OF, "goldstein_scale": None, "relevant": True}
        r = compute_risk("hormuz", [bad], AS_OF, data_sources=["fixtures"])
        for ev in r["key_events"]:
            assert ev["severity"] in ("low", "medium", "high", "critical")
