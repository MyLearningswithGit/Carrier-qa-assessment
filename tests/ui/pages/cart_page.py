"""Page object for the Sauce Demo cart page (/cart.html)."""

from __future__ import annotations

from playwright.sync_api import Page


class CartPage:
    def __init__(self, page: Page) -> None:
        self.page = page

    def get_item_names(self) -> list[str]:
        return self.page.locator('[data-test="inventory-item-name"]').all_inner_texts()

    def remove_product(self, product_name: str) -> None:
        item = self.page.locator('[data-test="inventory-item"]').filter(has_text=product_name)
        item.get_by_role("button", name="Remove").click()

    def get_cart_badge_count(self) -> str:
        badge = self.page.locator('[data-test="shopping-cart-badge"]')
        return badge.inner_text() if badge.count() > 0 else "0"

    def go_to_checkout(self) -> None:
        self.page.locator('[data-test="checkout"]').click()
