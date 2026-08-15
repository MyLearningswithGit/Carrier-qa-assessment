from pages.cart_page import CartPage
from pages.checkout_page import CheckoutPage
from pages.inventory_page import InventoryPage


def test_checkout_end_to_end_completes_order(standard_user_page):
    product_name = "Sauce Labs Backpack"

    inventory = InventoryPage(standard_user_page)
    # Captured from the inventory page rather than hard-coded, so this test
    # verifies the checkout summary is actually consistent with the catalog
    # price at run time, not just equal to a number we happen to remember.
    expected_price = inventory.get_product_price(product_name)
    inventory.add_product_to_cart(product_name)
    inventory.go_to_cart()

    cart = CartPage(standard_user_page)
    cart.go_to_checkout()

    checkout = CheckoutPage(standard_user_page)
    checkout.fill_information("Jane", "Doe", "12345")

    assert product_name in checkout.get_summary_item_names()
    assert expected_price in checkout.get_summary_item_prices()

    checkout.finish()
    assert checkout.get_completion_header() == "Thank you for your order!"
