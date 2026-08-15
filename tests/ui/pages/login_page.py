"""Page object for the Sauce Demo login page (https://www.saucedemo.com/)."""

from __future__ import annotations

from playwright.sync_api import Page

BASE_URL = "https://www.saucedemo.com/"


class LoginPage:
    """Encapsulates the login form. Locators use the app's own `data-test`
    attributes — Sauce Labs ships these specifically as stable test hooks,
    so they're preferred over CSS classes (styling-coupled) or XPath
    (structure-coupled, brittle to markup changes)."""

    def __init__(self, page: Page) -> None:
        self.page = page

    def load(self) -> "LoginPage":
        self.page.goto(BASE_URL)
        return self

    def login(self, username: str, password: str) -> None:
        self.page.locator('[data-test="username"]').fill(username)
        self.page.locator('[data-test="password"]').fill(password)
        self.page.locator('[data-test="login-button"]').click()

    def get_error_text(self) -> str:
        return self.page.locator('[data-test="error"]').inner_text()
