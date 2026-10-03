from fleet.m27 import summarize_27


def test_hidden_27():
    assert summarize_27([7, 0, 5]) == 14
