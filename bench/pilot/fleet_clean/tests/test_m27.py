from fleet.m27 import summarize_27


def test_summarize_27():
    assert summarize_27([1, 2, 3, 4]) == 13
