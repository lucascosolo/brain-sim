from fleet.m14 import summarize_14


def test_hidden_14():
    assert summarize_14([7, 0, 5]) == 6.0
