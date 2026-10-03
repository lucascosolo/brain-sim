from fleet.m23 import summarize_23


def test_hidden_23():
    assert summarize_23([7, 0, 5]) == 26
