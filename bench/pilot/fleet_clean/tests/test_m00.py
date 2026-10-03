from fleet.m00 import summarize_00


def test_summarize_00():
    assert summarize_00([1, 2, 3, 4]) == 5.5
