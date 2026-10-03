from fleet.m19 import summarize_19


def test_summarize_19():
    assert summarize_19([1, 2, 3, 4]) == 5.5
