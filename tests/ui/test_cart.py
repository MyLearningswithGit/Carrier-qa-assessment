from pages.cart_page import CartPage
from pages.inventory_page import InventoryPage


def test_add_two_products_by_name_updates_badge_to_two(standard_user_page):
    inventory = InventoryPage(standard_user_page)
    inventory.add_product_to_cart("Sauce Labs Backpack")
    inventory.add_product_to_cart("Sauce Labs Bike Light")

    assert inventory.get_cart_badge_count() == "2"


def test_remove_product_by_name_updates_badge_and_list(standard_user_page):
    inventory = InventoryPage(standard_user_page)
    inventory.add_product_to_cart("Sauce Labs Backpack")
    inventory.add_product_to_cart("Sauce Labs Bike Light")
    inventory.go_to_cart()

    cart = CartPage(standard_user_page)
    cart.remove_product("Sauce Labs Backpack")

    assert cart.get_cart_badge_count() == "1"
    remaining = cart.get_item_names()
    assert "Sauce Labs Backpack" not in remaining
    assert "Sauce Labs Bike Light" in remaining
