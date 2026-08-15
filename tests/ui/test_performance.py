import time

from pages.login_page import LoginPage

MAX_LOAD_SECONDS = 10


def test_performance_glitch_user_inventory_loads_within_10_seconds(page):
    login_page = LoginPage(page).load()

    # perf_counter() is a monotonic clock unaffected by system clock
    # adjustments — the right tool for measuring elapsed wall-clock
    # duration, as opposed to time.time() which can jump backwards.
    start = time.perf_counter()
    login_page.login("performance_glitch_user", "secret_sauce")
    page.wait_for_selector('[data-test="inventory-list"]')
    elapsed = time.perf_counter() - start

    print(f"\nperformance_glitch_user inventory load time: {elapsed:.2f}s")

    assert elapsed < MAX_LOAD_SECONDS, (
        f"inventory took {elapsed:.2f}s to load, expected under {MAX_LOAD_SECONDS}s"
    )
