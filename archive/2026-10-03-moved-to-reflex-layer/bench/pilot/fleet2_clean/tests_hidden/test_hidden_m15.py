from fleet.m15 import summarize_15


def test_hidden_15():
    assert summarize_15([7, 0, 5]) == 50
