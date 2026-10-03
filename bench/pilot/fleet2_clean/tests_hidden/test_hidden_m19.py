from fleet.m19 import summarize_19


def test_hidden_19():
    assert summarize_19([7, 0, 5]) == 5.0
