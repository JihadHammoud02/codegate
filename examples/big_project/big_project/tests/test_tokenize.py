from big_project.text.tokenize import tokenize


def test_tokenize_basic():
    assert tokenize("Hello, World!") == ["hello", "world"]


def test_tokenize_numbers_and_quotes():
    assert tokenize("A1 isn't B2") == ["a1", "isn't", "b2"]
