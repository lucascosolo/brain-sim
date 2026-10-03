from fleet.m24 import summarize_24


def test_hidden_24():
    assert summarize_24([7, 0, 5]) == 6.0
