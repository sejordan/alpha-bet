from alphabet.wordsmith import Dictionary, fill_template


def test_fill_template_matches_fixed_positions():
    dictionary = Dictionary(["cat", "cot", "cut", "dog"])
    result = fill_template(dictionary, [None, "o", "t"])
    assert sorted(result) == ["cot"]


def test_fill_template_returns_all_for_empty_template():
    dictionary = Dictionary(["at", "to", "go"])
    result = fill_template(dictionary, [None, None])
    assert sorted(result) == ["at", "go", "to"]


def test_fill_template_cache_is_per_dictionary_instance():
    d1 = Dictionary(["cat"])
    d2 = Dictionary(["dog"])
    assert fill_template(d1, [None, None, None]) == ["cat"]
    assert fill_template(d2, [None, None, None]) == ["dog"]


def test_is_valid_uses_dictionary_membership():
    dictionary = Dictionary(["alpha", "beta"])
    assert dictionary.is_valid("alpha")
    assert not dictionary.is_valid("gamma")
