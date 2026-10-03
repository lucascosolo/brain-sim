import pytest


def pytest_addoption(parser):
    parser.addoption("--record", action="store_true", default=False,
                     help="also run tests marked 'record' (retired as Stage 0 requirements, "
                          "kept as a record)")


def pytest_configure(config):
    config.addinivalue_line("markers", "kill: slow Stage 0 kill tests")
    config.addinivalue_line("markers", "s1: slow Stage 1 tests")
    config.addinivalue_line(
        "markers",
        "record: retired as a Stage 0 requirement; kept as a record, run only with --record")


def pytest_collection_modifyitems(config, items):
    if config.getoption("--record"):
        return
    dropped = [it for it in items if it.get_closest_marker("record")]
    if dropped:
        config.hook.pytest_deselected(items=dropped)
        items[:] = [it for it in items if not it.get_closest_marker("record")]
