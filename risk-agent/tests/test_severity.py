from scoring.severity import severity_from_goldstein, classify_severity


def test_goldstein_bands():
    assert severity_from_goldstein(-8) == "critical"
    assert severity_from_goldstein(-5) == "high"
    assert severity_from_goldstein(-2) == "medium"
    assert severity_from_goldstein(3) == "low"
    assert severity_from_goldstein(None) is None


def test_keyword_overrides_goldstein():
    # a mild Goldstein but an unambiguous critical keyword → critical
    ev = {"headline": "Missile strike on oil tanker", "goldstein_scale": -1.0}
    assert classify_severity(ev) == "critical"


def test_keyword_fallback_when_no_goldstein():
    ev = {"headline": "New sanctions announced on shipping firm", "goldstein_scale": None}
    assert classify_severity(ev) == "high"
    assert classify_severity({"headline": "Routine port update", "goldstein_scale": None}) == "low"


def test_word_boundary_war_does_not_match_warship():
    # 'warship' must NOT be tagged critical by the 'war' keyword; it's a 'high'
    # word, but a mild Goldstein of -2 classifies it medium (Goldstein wins).
    ev = {"headline": "US Navy warship escorts crude tanker", "goldstein_scale": -2.0}
    assert classify_severity(ev) == "medium"
    # bare 'war' as a whole word still fires critical
    assert classify_severity({"headline": "Fears of war in the region", "goldstein_scale": None}) == "critical"
    # 'warship' with no Goldstein falls through to the 'high' keyword
    assert classify_severity({"headline": "A warship was spotted", "goldstein_scale": None}) == "high"
