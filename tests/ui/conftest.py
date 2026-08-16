# tests/ui/conftest.py
#
# Shared Playwright fixtures and the screenshot-on-failure hook.
#
# Browser parametrization (chromium/firefox) is NOT implemented here — it's
# handled by the pytest-playwright plugin's built-in `--browser` CLI flag,
# which already parametrizes every test using the `page` fixture across
# whichever browsers are passed on the command line. Reimplementing that
# would duplicate what the library gives for free.

import re

import pytest

from pages.login_page import LoginPage

STANDARD_USERNAME = "standard_user"
STANDARD_PASSWORD = "secret_sauce"


def _safe_filename(name: str) -> str:
    """Parametrized test ids look like 'test_foo[chromium]' — safe on
    macOS/Linux filesystems as-is, but this strips anything that isn't."""
    return re.sub(r"[^A-Za-z0-9_.\-\[\]]", "_", name)


@pytest.fixture(autouse=True)
def _log_test_execution(request):
    """Prints each test's node id before/after it runs, so pytest-html's
    report shows something for every test instead of its own "No log
    output captured." fallback — which otherwise fires for the 14 of 16
    UI tests that don't already call print() themselves (only the
    performance tests do). Verified empirically that this attaches to the
    same row pytest-html displays for a passing test rather than a
    separate ::setup row."""
    print(f"\n▶ RUNNING {request.node.nodeid}")
    yield
    print(f"✔ FINISHED {request.node.nodeid}")


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    if rep.when == "call" and rep.failed:
        page = item.funcargs.get("page")
        if page:
            path = f"reports/screenshots/{_safe_filename(item.name)}.png"
            page.screenshot(path=path, full_page=True)


@pytest.fixture
def standard_user_page(page):
    """A page already logged in as standard_user, on /inventory.html.

    Used by inventory/cart/checkout tests so each one starts from the same
    known state without repeating the login steps. Fresh per test — the
    underlying `page` fixture is function-scoped, so there's no shared
    mutable state between tests.
    """
    LoginPage(page).load().login(STANDARD_USERNAME, STANDARD_PASSWORD)
    page.wait_for_url("**/inventory.html")
    return page
