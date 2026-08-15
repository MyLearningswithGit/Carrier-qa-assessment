"""Page object for the three-step Sauce Demo checkout flow
(/checkout-step-one.html -> /checkout-step-two.html -> /checkout-complete.html).

Not one of the three page objects the assessment names as a minimum
(LoginPage, InventoryPage, CartPage), but checkout is a distinct screen with
its own form and summary — folding it into CartPage would mix two unrelated
sets of locators/business logic into one class.
"""

from __future__ import annotations

from playwright.sync_api import Page


class CheckoutPage:
    def __init__(self, page: Page) -> None:
        self.page = page

    def fill_information(self, first_name: str, last_name: str, postal_code: str) -> None:
        self.page.locator('[data-test="firstName"]').fill(first_name)
        self.page.locator('[data-test="lastName"]').fill(last_name)
        self.page.locator('[data-test="postalCode"]').fill(postal_code)
        self.page.locator('[data-test="continue"]').click()

    def get_summary_item_names(self) -> list[str]:
        return self.page.locator('[data-test="inventory-item-name"]').all_inner_texts()

    def get_summary_item_prices(self) -> list[str]:
        return self.page.locator('[data-test="inventory-item-price"]').all_inner_texts()

    def finish(self) -> None:
        self.page.locator('[data-test="finish"]').click()

    def get_completion_header(self) -> str:
        return self.page.locator('[data-test="complete-header"]').inner_text()
