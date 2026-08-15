"""Page object for the Sauce Demo product listing page (/inventory.html)."""

from __future__ import annotations

from playwright.sync_api import Page


class InventoryPage:
    """Product selection is always by exact product name, never by index —
    the inventory sort order is user-changeable on this app, so an
    index-based locator would silently break under a different sort."""

    def __init__(self, page: Page) -> None:
        self.page = page

    def get_product_names(self) -> list[str]:
        return self.page.locator('[data-test="inventory-item-name"]').all_inner_texts()

    def get_product_price(self, product_name: str) -> str:
        item = self.page.locator('[data-test="inventory-item"]').filter(has_text=product_name)
        return item.locator('[data-test="inventory-item-price"]').inner_text()

    def add_product_to_cart(self, product_name: str) -> None:
        item = self.page.locator('[data-test="inventory-item"]').filter(has_text=product_name)
        item.get_by_role("button", name="Add to cart").click()

    def get_cart_badge_count(self) -> str:
        badge = self.page.locator('[data-test="shopping-cart-badge"]')
        return badge.inner_text() if badge.count() > 0 else "0"

    def go_to_cart(self) -> None:
        self.page.locator('[data-test="shopping-cart-link"]').click()
