from pages.inventory_page import InventoryPage

EXPECTED_PRODUCT_NAMES = {
    "Sauce Labs Backpack",
    "Sauce Labs Bike Light",
    "Sauce Labs Bolt T-Shirt",
    "Sauce Labs Fleece Jacket",
    "Sauce Labs Onesie",
    "Test.allTheThings() T-Shirt (Red)",
}


def test_all_six_products_visible_to_standard_user(standard_user_page):
    inventory = InventoryPage(standard_user_page)
    assert set(inventory.get_product_names()) == EXPECTED_PRODUCT_NAMES
