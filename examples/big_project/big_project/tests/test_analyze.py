from big_project.text.analyze import top_words


def test_top_words_counts():
    text = "spam spam eggs spam bacon eggs"
    assert top_words(text, n=2) == [("spam", 3), ("eggs", 2)]


def test_top_words_n_non_positive():
    assert top_words("anything", n=0) == []
