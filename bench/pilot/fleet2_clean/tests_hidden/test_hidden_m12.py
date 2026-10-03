from fleet.m12 import summarize_12


def test_hidden_12():
    assert summarize_12([7, 0, 5]) == 62
