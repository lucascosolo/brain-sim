from fleet.m01 import summarize_01


def test_hidden_01():
    assert summarize_01([7, 0, 5]) == 14
