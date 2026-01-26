import pytest

from big_project.utils.iterables import chunked


def test_chunked_basic():
    assert list(chunked([1, 2, 3, 4, 5], 2)) == [[1, 2], [3, 4], [5]]


def test_chunked_size_must_be_positive():
    with pytest.raises(ValueError):
        list(chunked([1, 2], 0))
