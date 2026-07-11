from scoring.corridor_map import corridor_for_country, corridor_for_text, assign_corridor


def test_country_mapping():
    assert corridor_for_country("SAU") == "hormuz"
    assert corridor_for_country("irn") == "hormuz"   # case-insensitive
    assert corridor_for_country("NGA") == "cape"
    assert corridor_for_country("RUS") == "redsea"
    assert corridor_for_country("IND") == "domestic"
    assert corridor_for_country(None) is None
    assert corridor_for_country("XXX") is None


def test_keyword_mapping():
    assert corridor_for_text("Tanker seized in the Strait of Hormuz") == "hormuz"
    assert corridor_for_text("Houthi drone hits ship in the Red Sea") == "redsea"
    assert corridor_for_text("More crude takes the Cape of Good Hope route") == "cape"
    assert corridor_for_text("A story about nothing in particular") is None


def test_assign_prefers_keyword_over_country():
    # country says hormuz, but the headline clearly references the Red Sea
    ev = {"headline": "Red Sea attack disrupts shipping", "country_code": "SAU"}
    assert assign_corridor(ev) == "redsea"
