import pytest


def pytest_addoption(parser):
    parser.addoption("--runslow", action="store_true", help="run slow tests")


def pytest_configure(config):
    # Consumed by test_knapsack to opt in to the slow test case.
    pytest.run_slow = config.getoption("--runslow")
