from fleet.m12 import summarize_12


def test_summarize_12():
    assert summarize_12([1, 2, 3, 4]) == 6.333
