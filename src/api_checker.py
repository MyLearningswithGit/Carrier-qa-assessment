"""
api_checker.py  —  Provided module
===================================
This file is provided to you as part of the assessment.
Do NOT modify it. Write your unit tests in tests/unit/test_api_checker.py.

The module contains three utility functions used by the synthetic canary
to validate and process responses from the DummyJSON API before publishing
metrics to CloudWatch.

Your task: write a comprehensive pytest unit test suite that covers every
function, every branch, every documented exception, and at least one
boundary / edge case per function that is NOT explicitly described in the
docstrings below.
"""

from __future__ import annotations


# ── Constants ────────────────────────────────────────────────────────────────

REQUIRED_PRODUCT_FIELDS: frozenset[str] = frozenset({
    "id", "title", "price", "rating", "stock", "category", "thumbnail",
})

VALID_RATING_RANGE: tuple[float, float] = (0.0, 5.0)
MAX_REASONABLE_PRICE: float = 1_000_000.0


# ── Public API ───────────────────────────────────────────────────────────────

def validate_product(product: dict) -> list[str]:
    """
    Validate a single product object returned by GET /products/{id}.

    Checks performed (in order):
      1. All fields in REQUIRED_PRODUCT_FIELDS are present.
      2. ``id`` is a positive integer.
      3. ``title`` is a non-empty string.
      4. ``price`` is a finite float (or int) greater than 0 and not
         exceeding MAX_REASONABLE_PRICE.
      5. ``rating`` is a float (or int) within VALID_RATING_RANGE (inclusive).
      6. ``stock`` is a non-negative integer.
      7. ``category`` is a non-empty string.
      8. ``thumbnail`` is a string that starts with "https://".

    Args:
        product: A dictionary representing a product object. Must not be None.

    Returns:
        A list of human-readable error strings, one per failed check.
        Returns an empty list if the product is fully valid.

    Raises:
        TypeError: If ``product`` is not a dict.

    Examples:
        >>> validate_product({
        ...     "id": 1, "title": "Phone", "price": 549.99,
        ...     "rating": 4.5, "stock": 10, "category": "smartphones",
        ...     "thumbnail": "https://cdn.dummyjson.com/phone.jpg"
        ... })
        []

        >>> validate_product({"id": -1, "title": "", "price": 0,
        ...                   "rating": 6, "stock": -1, "category": "",
        ...                   "thumbnail": "http://insecure.com/img.jpg"})
        ['id must be a positive integer',
         'title must be a non-empty string',
         'price must be greater than 0',
         'rating 6 is outside valid range 0.0–5.0',
         'stock must be a non-negative integer',
         'category must be a non-empty string',
         'thumbnail must start with https://']
    """
    if not isinstance(product, dict):
        raise TypeError(f"product must be a dict, got {type(product).__name__}")

    errors: list[str] = []

    # ── 1. Required field presence ───────────────────────────────────────────
    missing = REQUIRED_PRODUCT_FIELDS - product.keys()
    for field in sorted(missing):
        errors.append(f"missing required field: {field}")

    if missing:
        # Cannot validate field values if the fields are absent
        return errors

    # ── 2. id ────────────────────────────────────────────────────────────────
    if not isinstance(product["id"], int) or isinstance(product["id"], bool) \
            or product["id"] <= 0:
        errors.append("id must be a positive integer")

    # ── 3. title ─────────────────────────────────────────────────────────────
    if not isinstance(product["title"], str) or not product["title"].strip():
        errors.append("title must be a non-empty string")

    # ── 4. price ─────────────────────────────────────────────────────────────
    price = product["price"]
    if not isinstance(price, (int, float)) or isinstance(price, bool):
        errors.append("price must be a number")
    elif price <= 0:
        errors.append("price must be greater than 0")
    elif price > MAX_REASONABLE_PRICE:
        errors.append(f"price {price} exceeds maximum reasonable value {MAX_REASONABLE_PRICE}")
    elif price != price:  # NaN check  (float('nan') != float('nan') is True)
        errors.append("price must be a finite number")

    # ── 5. rating ────────────────────────────────────────────────────────────
    rating = product["rating"]
    if not isinstance(rating, (int, float)) or isinstance(rating, bool):
        errors.append("rating must be a number")
    else:
        lo, hi = VALID_RATING_RANGE
        if not (lo <= rating <= hi):
            errors.append(f"rating {rating} is outside valid range {lo}–{hi}")

    # ── 6. stock ─────────────────────────────────────────────────────────────
    if not isinstance(product["stock"], int) or isinstance(product["stock"], bool) \
            or product["stock"] < 0:
        errors.append("stock must be a non-negative integer")

    # ── 7. category ──────────────────────────────────────────────────────────
    if not isinstance(product["category"], str) or not product["category"].strip():
        errors.append("category must be a non-empty string")

    # ── 8. thumbnail ─────────────────────────────────────────────────────────
    if not isinstance(product["thumbnail"], str) \
            or not product["thumbnail"].startswith("https://"):
        errors.append("thumbnail must start with https://")

    return errors


# ────────────────────────────────────────────────────────────────────────────

def calculate_cart_total(cart: dict) -> float:
    """
    Calculate the expected total price of a cart returned by
    GET /carts/user/{userId}.

    The total is defined as the sum of  (price * quantity)  for every
    product in ``cart["products"]``, rounded to two decimal places.

    This function is used to cross-check the ``total`` field returned by
    the API against a locally computed value. A mismatch indicates a
    potential pricing or rounding bug in the upstream service.

    Args:
        cart: A dictionary with at minimum a ``"products"`` key whose value
              is a list of dicts. Each product dict must contain:
                - ``"price"``    (int or float, > 0)
                - ``"quantity"`` (int, >= 1)

    Returns:
        The sum of (price × quantity) for all products, rounded to 2 d.p.
        Returns 0.0 if the products list is empty.

    Raises:
        TypeError:  If ``cart`` is not a dict, or ``products`` is not a list.
        KeyError:   If the ``"products"`` key is absent from ``cart``.
        ValueError: If any product is missing ``"price"`` or ``"quantity"``,
                    or if ``price`` <= 0, or if ``quantity`` < 1.

    Examples:
        >>> calculate_cart_total({
        ...     "products": [
        ...         {"price": 10.00, "quantity": 2},
        ...         {"price": 5.50,  "quantity": 1},
        ...     ]
        ... })
        25.5

        >>> calculate_cart_total({"products": []})
        0.0
    """
    if not isinstance(cart, dict):
        raise TypeError(f"cart must be a dict, got {type(cart).__name__}")

    products = cart["products"]  # intentional KeyError if missing

    if not isinstance(products, list):
        raise TypeError(f"cart['products'] must be a list, got {type(products).__name__}")

    total = 0.0
    for i, item in enumerate(products):
        if "price" not in item:
            raise ValueError(f"product at index {i} is missing 'price'")
        if "quantity" not in item:
            raise ValueError(f"product at index {i} is missing 'quantity'")

        price    = item["price"]
        quantity = item["quantity"]

        if not isinstance(price, (int, float)) or isinstance(price, bool) or price <= 0:
            raise ValueError(
                f"product at index {i} has invalid price: {price!r} (must be a positive number)"
            )
        if not isinstance(quantity, int) or isinstance(quantity, bool) or quantity < 1:
            raise ValueError(
                f"product at index {i} has invalid quantity: {quantity!r} (must be an integer >= 1)"
            )

        total += price * quantity

    return round(total, 2)


# ────────────────────────────────────────────────────────────────────────────

def parse_auth_response(response: dict) -> tuple[str, int]:
    """
    Extract and validate the authentication token from a POST /auth/login
    response.

    The DummyJSON auth response has the shape::

        {
          "accessToken":  "<jwt-string>",
          "refreshToken": "<jwt-string>",
          "id":           1,
          "username":     "emilys",
          ...
        }

    This function extracts only what the canary needs: the access token and
    the length of the token as a proxy for whether it looks like a real JWT
    (three dot-separated segments).

    Args:
        response: A dictionary representing the parsed JSON body of the
                  POST /auth/login response.

    Returns:
        A tuple of (access_token: str, segment_count: int) where
        ``segment_count`` is the number of dot-separated parts of the token
        (a valid JWT always has exactly 3).

    Raises:
        TypeError:  If ``response`` is not a dict.
        KeyError:   If ``"accessToken"`` is not present in ``response``.
        ValueError: If ``accessToken`` is an empty string, is not a string,
                    or does not contain exactly two dots (i.e. is not a
                    3-segment JWT).

    Examples:
        >>> header  = "eyJhbGciOiJIUzI1NiJ9"
        >>> payload = "eyJ1c2VybmFtZSI6ImVtaWx5cyJ9"
        >>> sig     = "abc123signature"
        >>> parse_auth_response({"accessToken": f"{header}.{payload}.{sig}"})
        ('eyJhbGciOiJIUzI1NiJ9.eyJ1c2VybmFtZSI6ImVtaWx5cyJ9.abc123signature', 3)

        >>> parse_auth_response({"accessToken": "not-a-jwt"})
        ValueError: accessToken does not appear to be a valid JWT ...
    """
    if not isinstance(response, dict):
        raise TypeError(f"response must be a dict, got {type(response).__name__}")

    token = response["accessToken"]  # intentional KeyError if missing

    if not isinstance(token, str):
        raise ValueError(
            f"accessToken must be a string, got {type(token).__name__}"
        )
    if not token:
        raise ValueError("accessToken must not be an empty string")

    segments = token.split(".")
    if len(segments) != 3:
        raise ValueError(
            f"accessToken does not appear to be a valid JWT "
            f"(expected 3 dot-separated segments, got {len(segments)}): {token[:40]!r}..."
        )

    return token, len(segments)
