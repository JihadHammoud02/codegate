import pytest

from big_project.math.stats import mean, variance


def test_mean():
    assert mean([1, 2, 3]) == pytest.approx(2.0)


def test_mean_empty():
    with pytest.raises(ValueError):
        mean([])


def test_variance():
    assert variance([1, 2, 3]) == pytest.approx(2 / 3)
