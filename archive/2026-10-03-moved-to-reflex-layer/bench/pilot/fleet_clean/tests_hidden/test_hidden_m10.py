from fleet.m10 import summarize_10


def test_hidden_10():
    assert summarize_10([7, 0, 5]) == 26
