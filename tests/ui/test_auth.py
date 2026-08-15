from pages.login_page import LoginPage


def test_standard_user_logs_in_and_lands_on_inventory(page):
    login_page = LoginPage(page).load()
    login_page.login("standard_user", "secret_sauce")

    page.wait_for_url("**/inventory.html")
    assert page.title() == "Swag Labs"


def test_locked_out_user_sees_lockout_message(page):
    login_page = LoginPage(page).load()
    login_page.login("locked_out_user", "secret_sauce")

    assert "Sorry, this user has been locked out." in login_page.get_error_text()


def test_empty_credentials_shows_error(page):
    login_page = LoginPage(page).load()
    login_page.login("", "")

    assert login_page.get_error_text() != ""
