# tests/unit/conftest.py
#
# Most unit tests for api_checker.py require no fixtures —
# all inputs are constructed directly in each test function.
#
# _log_test_execution below is the one addition: an autouse fixture that
# prints each test's node id before/after it runs. It exists so
# pytest-html's report shows something for every test instead of its own
# "No log output captured." fallback — which fires whenever a test
# produced no captured output at all (true for all 46 tests here, since
# they're pure assert statements with no print()/logging calls of their
# own). Verified empirically (not assumed) that this fixture's output
# attaches to the same row pytest-html displays for a passing test,
# rather than spawning a separate ::setup row — an earlier attempt using
# a pytest_runtest_call hookwrapper instead of a fixture was tried first
# and discarded because its print output escaped pytest's capture
# mechanism entirely (visible raw in the terminal, never attributed to
# any report section) due to hook-nesting order against pytest's own
# capture plugin.

import pytest


@pytest.fixture(autouse=True)
def _log_test_execution(request):
    print(f"\n▶ RUNNING {request.node.nodeid}")
    yield
    print(f"✔ FINISHED {request.node.nodeid}")
