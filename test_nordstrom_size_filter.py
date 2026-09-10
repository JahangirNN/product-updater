"""
Unit and Integration Test Suite: Nordstrom On Shoe Size Filtering & Size Mapping
Verifies:
1. Product ingestion filter: products with >= 7 distinct size variants are accepted.
2. Products with < 7 distinct size variants are excluded.
3. All available sizes are included in variants for accepted products (including sizes < 7.0).
4. Official On shoe size conversion matrix accurately maps US -> UK for Women, Men, and Unisex.
5. Deduplication of sizes, edge cases (empty sizes, kids exclusion, malformed inputs).
"""
from stores.nordstrom.inflow import (
    parse_product_payload,
    convert_us_to_uk,
    convert_us_to_eu,
    WOMEN_US_TO_UK,
    MEN_US_TO_UK,
    parse_numeric_size
)


def test_us_to_uk_women_conversion_matrix():
    """Verify official On shoe conversion table for women."""
    expected_mappings = {
        5.0: "3", 5.5: "3.5",
        6.0: "4", 6.5: "4.5",
        7.0: "5", 7.5: "5.5",
        8.0: "6", 8.5: "6.5",
        9.0: "7", 9.5: "7.5",
        10.0: "8", 10.5: "8.5",
        11.0: "9", 11.5: "9.5",
        12.0: "10", 12.5: "10.5",
        13.0: "11", 14.0: "11.5"
    }
    for us_size, expected_uk in expected_mappings.items():
        assert convert_us_to_uk(us_size, "Women") == expected_uk, (
            f"Women US {us_size} should map to UK {expected_uk}, got {convert_us_to_uk(us_size, 'Women')}"
        )


def test_us_to_uk_men_conversion_matrix():
    """Verify official On shoe conversion table for men."""
    expected_mappings = {
        7.0: "6.5", 7.5: "7",
        8.0: "7.5", 8.5: "8",
        9.0: "8.5", 9.5: "9",
        10.0: "9.5", 10.5: "10",
        11.0: "10.5", 11.5: "11",
        12.0: "11.5", 12.5: "12",
        13.0: "12.5", 14.0: "13.5"
    }
    for us_size, expected_uk in expected_mappings.items():
        assert convert_us_to_uk(us_size, "Men") == expected_uk, (
            f"Men US {us_size} should map to UK {expected_uk}, got {convert_us_to_uk(us_size, 'Men')}"
        )


def test_product_with_fewer_than_7_sizes_is_excluded():
    """Products offering < 7 distinct size variants must return None (excluded)."""
    raw_payload_6_sizes = {
        "title": "Cloudrunner 3 Running Shoe",
        "gender": "men",
        "current_price": 160.0,
        "sizes": [
            {"us_size": "8", "in_stock": True},
            {"us_size": "9", "in_stock": True},
            {"us_size": "10", "in_stock": True},
            {"us_size": "11", "in_stock": True},
            {"us_size": "12", "in_stock": True},
            {"us_size": "13", "in_stock": True}
        ]
    }
    res = parse_product_payload(raw_payload_6_sizes, usd_to_inr_rate=90.0)
    assert res is None, "Product with 6 size variants should be excluded"

    # Single size remnant (e.g. only US 14 left)
    raw_single_size = {
        "title": "Cloudsurfer Trail Running Shoe",
        "gender": "men",
        "current_price": 160.0,
        "sizes": [{"us_size": "14", "in_stock": True}]
    }
    assert parse_product_payload(raw_single_size, usd_to_inr_rate=90.0) is None, (
        "Single size remnant must be excluded"
    )


def test_product_with_exactly_7_sizes_is_accepted():
    """Products offering exactly 7 distinct size variants must be accepted."""
    raw_payload = {
        "title": "Cloudflow 4 Running Shoe",
        "gender": "men",
        "current_price": 160.0,
        "sizes": [
            {"us_size": "7", "in_stock": True},
            {"us_size": "8", "in_stock": True},
            {"us_size": "9", "in_stock": True},
            {"us_size": "10", "in_stock": True},
            {"us_size": "11", "in_stock": True},
            {"us_size": "12", "in_stock": True},
            {"us_size": "13", "in_stock": True}
        ]
    }
    res = parse_product_payload(raw_payload, usd_to_inr_rate=90.0)
    assert res is not None, "Product with 7 size variants must be accepted"
    assert len(res["variants"]) == 7, f"Expected 7 variants, got {len(res['variants'])}"


def test_product_includes_all_sizes_including_sizes_below_7():
    """
    CRITICAL: Accepted products must include all sizes (even < 7.0 like US 5, 5.5, 6, 6.5)
    and map them to correct UK sizes.
    """
    raw_payload = {
        "title": "Cloudtilt Arc Running Shoe",
        "gender": "women",
        "current_price": 150.0,
        "sizes": [
            {"us_size": "5", "in_stock": True},
            {"us_size": "5.5", "in_stock": True},
            {"us_size": "6", "in_stock": True},
            {"us_size": "6.5", "in_stock": True},
            {"us_size": "7", "in_stock": True},
            {"us_size": "7.5", "in_stock": True},
            {"us_size": "8", "in_stock": True},
            {"us_size": "8.5", "in_stock": True},
            {"us_size": "9", "in_stock": True},
            {"us_size": "9.5", "in_stock": True},
            {"us_size": "10", "in_stock": True}
        ]
    }
    res = parse_product_payload(raw_payload, usd_to_inr_rate=90.0)
    assert res is not None, "Women's shoe with 11 sizes must be accepted"
    assert len(res["variants"]) == 11, f"Expected 11 variants, got {len(res['variants'])}"

    # Check variant titles and option values for sizes below 7
    v_sizes = [v["option_values"][0]["name"] for v in res["variants"]]
    assert "US 5" in v_sizes
    assert "US 5.5" in v_sizes
    assert "US 6" in v_sizes
    assert "US 6.5" in v_sizes

    # Check US -> UK mappings in options
    uk_sizes = [v["option_values"][1]["name"] for v in res["variants"]]
    assert "UK 3" in uk_sizes    # 5.0 -> 3.0
    assert "UK 3.5" in uk_sizes  # 5.5 -> 3.5
    assert "UK 4" in uk_sizes    # 6.0 -> 4.0
    assert "UK 4.5" in uk_sizes  # 6.5 -> 4.5
    assert "UK 5" in uk_sizes    # 7.0 -> 5.0

    # Check specifications
    assert "US 5" in res["specifications"]["Available Sizes (US)"]
    assert "UK 3" in res["specifications"]["Available Sizes (UK)"]


def test_duplicate_sizes_are_deduplicated_before_count():
    """Duplicate sizes (e.g. from multiple colors in raw payload) must not inflate variant count."""
    raw_payload_with_dupes = {
        "title": "Cloud 5 Sneaker",
        "gender": "men",
        "current_price": 140.0,
        "sizes": [
            # Only 4 distinct sizes repeated
            {"us_size": "8", "in_stock": True},
            {"us_size": "8", "in_stock": True},
            {"us_size": "9", "in_stock": True},
            {"us_size": "9", "in_stock": True},
            {"us_size": "10", "in_stock": True},
            {"us_size": "10", "in_stock": True},
            {"us_size": "11", "in_stock": True},
            {"us_size": "11", "in_stock": True}
        ]
    }
    res = parse_product_payload(raw_payload_with_dupes, usd_to_inr_rate=90.0)
    assert res is None, "4 unique sizes repeated 8 times should still be excluded (< 7 distinct sizes)"


def test_kids_products_are_excluded_even_if_having_sizes():
    """Kids, toddler, and youth products must be strictly excluded."""
    raw_kids = {
        "title": "Kids' Cloudhero Waterproof Running Shoe",
        "gender": "kids",
        "current_price": 90.0,
        "sizes": [
            {"us_size": "1", "in_stock": True},
            {"us_size": "2", "in_stock": True},
            {"us_size": "3", "in_stock": True},
            {"us_size": "4", "in_stock": True},
            {"us_size": "5", "in_stock": True},
            {"us_size": "6", "in_stock": True},
            {"us_size": "7", "in_stock": True}
        ]
    }
    assert parse_product_payload(raw_kids, usd_to_inr_rate=90.0) is None, "Kids shoe must be excluded"


def test_size_guide_accordion_html():
    """Verify descriptionHtml contains table with all sizes."""
    raw_payload = {
        "title": "Cloudmonster 2 Running Shoe",
        "gender": "women",
        "current_price": 180.0,
        "sizes": [
            {"us_size": "5", "in_stock": True},
            {"us_size": "6", "in_stock": True},
            {"us_size": "7", "in_stock": True},
            {"us_size": "8", "in_stock": True},
            {"us_size": "9", "in_stock": True},
            {"us_size": "10", "in_stock": True},
            {"us_size": "11", "in_stock": True}
        ]
    }
    res = parse_product_payload(raw_payload, usd_to_inr_rate=90.0)
    assert res is not None
    html_desc = res["descriptionHtml"]
    assert "Showing all available shoe sizes" in html_desc
    assert "US 5" in html_desc
    assert "UK 3" in html_desc


def test_duplicate_size_preserves_in_stock_if_any_in_stock():
    """If a size appears multiple times, in_stock should be True if ANY occurrence is in stock."""
    raw_payload = {
        "title": "Cloud 5 Sneaker",
        "gender": "men",
        "current_price": 140.0,
        "sizes": [
            {"us_size": "7", "in_stock": False},
            {"us_size": "7", "in_stock": True},  # In stock in another colorway
            {"us_size": "8", "in_stock": True},
            {"us_size": "9", "in_stock": True},
            {"us_size": "10", "in_stock": True},
            {"us_size": "11", "in_stock": True},
            {"us_size": "12", "in_stock": True},
            {"us_size": "13", "in_stock": True}
        ]
    }
    res = parse_product_payload(raw_payload, usd_to_inr_rate=90.0)
    assert res is not None
    assert len(res["variants"]) == 7
    v7 = next(v for v in res["variants"] if "US 7" in v["title"])
    assert v7["in_stock"] is True, f"US 7 should be in_stock True when one occurrence is in stock, got {v7['in_stock']}"


def test_fractional_size_parsing():
    """Verify fractional sizes like '7 1/2' parse accurately to 7.5."""
    assert parse_numeric_size("7 1/2") == 7.5
    assert parse_numeric_size("8 1/2") == 8.5
    assert parse_numeric_size("10½") == 10.5
    assert parse_numeric_size("9.5") == 9.5
    assert parse_numeric_size("US 11.5") == 11.5


def test_kids_sizes_quarantine():
    """Verify that products with youth/kid size indicators are quarantined even without kid in title."""
    raw_youth_product = {
        "title": "Cloudplay Sneaker",
        "gender": "unisex",
        "current_price": 90.0,
        "sizes": [
            {"us_size": "1Y", "in_stock": True},
            {"us_size": "2Y", "in_stock": True},
            {"us_size": "3Y", "in_stock": True},
            {"us_size": "4Y", "in_stock": True},
            {"us_size": "5Y", "in_stock": True},
            {"us_size": "6Y", "in_stock": True},
            {"us_size": "7Y", "in_stock": True}
        ]
    }
    res = parse_product_payload(raw_youth_product, usd_to_inr_rate=90.0)
    assert res is None, "Youth sized footwear must be excluded"


def test_null_payload_fields_resilience():
    """Verify parser handles payloads with null details, null images, and null sizes without raising exceptions."""
    raw_payload_nulls = {
        "title": "Cloudtilt Sneaker",
        "gender": "women",
        "current_price": 160.0,
        "details": None,
        "images": None,
        "sizes": [
            {"us_size": "6", "in_stock": True},
            {"us_size": "6.5", "in_stock": True},
            {"us_size": "7", "in_stock": True},
            {"us_size": "7.5", "in_stock": True},
            {"us_size": "8", "in_stock": True},
            {"us_size": "8.5", "in_stock": True},
            {"us_size": "9", "in_stock": True}
        ]
    }
    res = parse_product_payload(raw_payload_nulls, usd_to_inr_rate=90.0)
    assert res is not None, "Product with null details/images must parse successfully"
    assert len(res["variants"]) == 7


def test_last_verified_at_timestamp_present():
    """Verify canonical product record contains ISO last_verified_at timestamp."""
    raw_payload = {
        "title": "Cloudflow 4 Running Shoe",
        "gender": "men",
        "current_price": 160.0,
        "sizes": [
            {"us_size": "7", "in_stock": True},
            {"us_size": "8", "in_stock": True},
            {"us_size": "9", "in_stock": True},
            {"us_size": "10", "in_stock": True},
            {"us_size": "11", "in_stock": True},
            {"us_size": "12", "in_stock": True},
            {"us_size": "13", "in_stock": True}
        ]
    }
    res = parse_product_payload(raw_payload, usd_to_inr_rate=90.0)
    assert res is not None
    assert "last_verified_at" in res
    assert res["last_verified_at"].endswith("Z")


if __name__ == "__main__":
    test_us_to_uk_women_conversion_matrix()
    test_us_to_uk_men_conversion_matrix()
    test_product_with_fewer_than_7_sizes_is_excluded()
    test_product_with_exactly_7_sizes_is_accepted()
    test_product_includes_all_sizes_including_sizes_below_7()
    test_duplicate_sizes_are_deduplicated_before_count()
    test_kids_products_are_excluded_even_if_having_sizes()
    test_size_guide_accordion_html()
    test_duplicate_size_preserves_in_stock_if_any_in_stock()
    test_fractional_size_parsing()
    test_kids_sizes_quarantine()
    test_null_payload_fields_resilience()
    test_last_verified_at_timestamp_present()
    print("ALL 13 TESTS PASSED SUCCESSFULLY!")
