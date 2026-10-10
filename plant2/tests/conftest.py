def pytest_configure(config):
    config.addinivalue_line("markers", "slow: full kill-test runs (minutes); deselect with -m 'not slow'")
