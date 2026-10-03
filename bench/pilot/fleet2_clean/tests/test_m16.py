from fleet.m16 import summarize_16


def test_summarize_16():
    assert summarize_16([1, 2, 3, 4]) == 8.0
