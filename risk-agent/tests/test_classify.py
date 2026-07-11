from scoring.classify import is_relevant_heuristic


def test_relevant_headlines():
    assert is_relevant_heuristic({"headline": "Oil tanker seized in the strait"})
    assert is_relevant_heuristic({"headline": "New sanctions on a shipping firm"})
    assert is_relevant_heuristic({"headline": "OPEC signals steady crude exports"})


def test_word_boundary_avoids_false_positives():
    # 'oil' must not fire on 'boil'; 'port' must not fire on 'important'/'report'
    assert not is_relevant_heuristic({"headline": "Chef shares how to boil the perfect egg"})
    assert not is_relevant_heuristic({"headline": "An important report on local weather"})
    assert not is_relevant_heuristic({"headline": "City council debates park funding"})
