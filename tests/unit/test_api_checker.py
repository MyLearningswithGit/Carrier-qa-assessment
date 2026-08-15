"""
tests/unit/test_api_checker.py — Part B

Unit tests for src/api_checker.py. No network access — every input is
constructed in-line or via the `valid_product` / `valid_cart` fixtures below.

Test classes are organized one-per-function-under-test so a reader can jump
straight to TestValidateProduct, TestCalculateCartTotal, or
TestParseAuthResponse without scanning the whole file.
"""

from __future__ import annotations

import math

import pytest

from src.api_checker import (
    MAX_REASONABLE_PRICE,
    calculate_cart_total,
    parse_auth_response,
    validate_product,
)


# ── Shared fixtures ─────────────────────────────────────────────────────────

@pytest.fixture
def valid_product() -> dict:
    """A product dict that satisfies every check in validate_product."""
    return {
        "id": 1,
        "title": "Phone",
        "price": 549.99,
        "rating": 4.5,
        "stock": 10,
        "category": "smartphones",
        "thumbnail": "https://cdn.dummyjson.com/phone.jpg",
    }


@pytest.fixture
def valid_cart() -> dict:
    return {
        "products": [
            {"price": 10.00, "quantity": 2},
            {"price": 5.50, "quantity": 1},
        ]
    }


# ── validate_product ─────────────────────────────────────────────────────────

class TestValidateProduct:

    def test_fully_valid_product_returns_empty_list(self, valid_product):
        assert validate_product(valid_product) == []

    def test_missing_two_fields_reports_exactly_those_two(self, valid_product):
        del valid_product["stock"]
        del valid_product["category"]

        errors = validate_product(valid_product)

        assert errors == [
            "missing required field: category",
            "missing required field: stock",
        ]

    def test_missing_fields_short_circuits_other_checks(self, valid_product):
        # id is also invalid (-1), but because a required field is missing,
        # the function returns immediately after the presence check — it
        # must not also report the invalid id.
        del valid_product["thumbnail"]
        valid_product["id"] = -1

        errors = validate_product(valid_product)

        assert errors == ["missing required field: thumbnail"]

    @pytest.mark.parametrize("bad_id", [0, -5, 1.0])
    def test_invalid_id_values(self, valid_product, bad_id):
        valid_product["id"] = bad_id
        assert "id must be a positive integer" in validate_product(valid_product)

    def test_id_as_bool_is_rejected(self, valid_product):
        # In Python, bool is a subclass of int: isinstance(True, int) is True
        # and True == 1. Without the explicit isinstance(..., bool) guard in
        # the source, a product with "id": True would silently pass as a
        # valid positive integer. The guard exists specifically to reject
        # booleans masquerading as ids.
        valid_product["id"] = True
        assert "id must be a positive integer" in validate_product(valid_product)

    @pytest.mark.parametrize(
        "bad_price, expected_error",
        [
            (0, "price must be greater than 0"),
            (-1, "price must be greater than 0"),
            (
                float("inf"),
                f"price inf exceeds maximum reasonable value {MAX_REASONABLE_PRICE}",
            ),
            ("9.99", "price must be a number"),
        ],
        ids=["zero", "negative", "infinite", "numeric-string"],
    )
    def test_invalid_price_values(self, valid_product, bad_price, expected_error):
        valid_product["price"] = bad_price
        assert expected_error in validate_product(valid_product)

    def test_price_at_max_reasonable_is_valid(self, valid_product):
        valid_product["price"] = MAX_REASONABLE_PRICE
        assert validate_product(valid_product) == []

    def test_price_just_above_max_reasonable_is_invalid(self, valid_product):
        valid_product["price"] = MAX_REASONABLE_PRICE + 0.01
        errors = validate_product(valid_product)
        assert any("exceeds maximum reasonable value" in e for e in errors)

    def test_price_nan_is_invalid(self, valid_product):
        # NaN fails every ordered comparison (nan <= 0 is False, nan > MAX is
        # False), so it falls through to the explicit `price != price` check
        # — this is the one branch in the source with no direct docstring
        # example, so it earns its own test.
        valid_product["price"] = float("nan")
        assert "price must be a finite number" in validate_product(valid_product)

    @pytest.mark.parametrize("bad_rating", [0.0, 5.0])
    def test_rating_boundary_values_are_valid(self, valid_product, bad_rating):
        valid_product["rating"] = bad_rating
        assert validate_product(valid_product) == []

    def test_rating_just_above_max_is_invalid(self, valid_product):
        valid_product["rating"] = 5.001
        errors = validate_product(valid_product)
        assert "rating 5.001 is outside valid range 0.0–5.0" in errors

    def test_thumbnail_insecure_scheme_is_invalid(self, valid_product):
        valid_product["thumbnail"] = "http://insecure.com/img.jpg"
        assert "thumbnail must start with https://" in validate_product(valid_product)

    def test_thumbnail_empty_string_is_invalid(self, valid_product):
        valid_product["thumbnail"] = ""
        assert "thumbnail must start with https://" in validate_product(valid_product)

    def test_stock_negative_is_invalid(self, valid_product):
        valid_product["stock"] = -1
        assert "stock must be a non-negative integer" in validate_product(valid_product)

    def test_stock_as_bool_is_rejected(self, valid_product):
        # Same bool-vs-int trap as id, applied to stock.
        valid_product["stock"] = False
        assert "stock must be a non-negative integer" in validate_product(valid_product)

    def test_none_raises_type_error(self):
        with pytest.raises(TypeError):
            validate_product(None)

    def test_list_raises_type_error(self):
        with pytest.raises(TypeError):
            validate_product([])

    def test_type_error_message_names_actual_type(self):
        with pytest.raises(TypeError, match="got NoneType"):
            validate_product(None)


# ── calculate_cart_total ─────────────────────────────────────────────────────

class TestCalculateCartTotal:

    def test_single_product(self):
        cart = {"products": [{"price": 10.00, "quantity": 2}]}
        assert calculate_cart_total(cart) == 20.0

    def test_floating_point_prices_round_to_two_decimals(self):
        cart = {
            "products": [
                {"price": 10.10, "quantity": 3},
                {"price": 5.05, "quantity": 1},
            ]
        }
        # 10.10*3 + 5.05 = 35.35 exactly, but floating point arithmetic can
        # land a hair off — approx guards against that while still proving
        # the two-decimal rounding contract.
        assert calculate_cart_total(cart) == pytest.approx(35.35)

    def test_empty_products_list_returns_zero(self):
        assert calculate_cart_total({"products": []}) == 0.0

    def test_missing_products_key_raises_key_error(self):
        with pytest.raises(KeyError):
            calculate_cart_total({})

    def test_products_as_dict_raises_type_error(self):
        with pytest.raises(TypeError):
            calculate_cart_total({"products": {"price": 10.0, "quantity": 1}})

    def test_missing_price_at_index_1_raises_value_error_naming_index(self):
        cart = {
            "products": [
                {"price": 10.0, "quantity": 1},
                {"quantity": 1},  # missing "price"
            ]
        }
        with pytest.raises(ValueError, match="index 1"):
            calculate_cart_total(cart)

    def test_missing_quantity_raises_value_error_naming_index(self):
        cart = {"products": [{"price": 10.0}]}
        with pytest.raises(ValueError, match="index 0"):
            calculate_cart_total(cart)

    @pytest.mark.parametrize("bad_quantity", [0, -1])
    def test_invalid_quantity_raises_value_error(self, bad_quantity):
        cart = {"products": [{"price": 10.0, "quantity": bad_quantity}]}
        with pytest.raises(ValueError):
            calculate_cart_total(cart)

    def test_quantity_of_one_is_valid(self):
        cart = {"products": [{"price": 10.0, "quantity": 1}]}
        assert calculate_cart_total(cart) == 10.0

    def test_quantity_as_bool_is_rejected(self):
        # Same bool-vs-int trap as validate_product's id/stock checks.
        cart = {"products": [{"price": 10.0, "quantity": True}]}
        with pytest.raises(ValueError):
            calculate_cart_total(cart)

    def test_price_non_positive_raises_value_error(self):
        cart = {"products": [{"price": 0, "quantity": 1}]}
        with pytest.raises(ValueError):
            calculate_cart_total(cart)

    def test_cart_as_string_raises_type_error(self):
        with pytest.raises(TypeError):
            calculate_cart_total("not-a-cart")


# ── parse_auth_response ──────────────────────────────────────────────────────

class TestParseAuthResponse:

    def test_valid_jwt_returns_token_and_segment_count(self):
        token = "header.payload.signature"
        result = parse_auth_response({"accessToken": token})
        assert result == (token, 3)

    def test_missing_access_token_raises_key_error(self):
        with pytest.raises(KeyError):
            parse_auth_response({})

    def test_empty_access_token_raises_value_error(self):
        with pytest.raises(ValueError, match="must not be an empty string"):
            parse_auth_response({"accessToken": ""})

    def test_access_token_as_int_raises_value_error(self):
        with pytest.raises(ValueError, match="must be a string"):
            parse_auth_response({"accessToken": 123})

    def test_access_token_as_none_raises_value_error(self):
        with pytest.raises(ValueError, match="must be a string"):
            parse_auth_response({"accessToken": None})

    def test_two_segment_token_raises_value_error_mentioning_count(self):
        with pytest.raises(ValueError, match="got 2"):
            parse_auth_response({"accessToken": "header.payload"})

    def test_four_segment_token_raises_value_error(self):
        with pytest.raises(ValueError, match="got 4"):
            parse_auth_response({"accessToken": "a.b.c.d"})

    def test_response_none_raises_type_error(self):
        with pytest.raises(TypeError):
            parse_auth_response(None)

    def test_extra_fields_in_response_are_ignored(self):
        # The canary only cares about accessToken; unrelated fields in the
        # real DummyJSON payload (refreshToken, id, username, ...) must not
        # affect parsing.
        response = {
            "accessToken": "header.payload.signature",
            "refreshToken": "irrelevant.refresh.token",
            "id": 1,
            "username": "emilys",
        }
        assert parse_auth_response(response) == ("header.payload.signature", 3)
