from fleet.m20 import summarize_20


def test_hidden_20():
    assert summarize_20([7, 0, 5]) == 62
