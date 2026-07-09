"""
zakat.py

Standalone tool for calculating Zakat (Islamic almsgiving) using live gold
and silver prices from the MetalpriceAPI (https://metalpriceapi.com/). No
AI/Gemini code lives in this file — it is a plain function that any agent
(or a human) can call directly.
"""

import os

import requests
from dotenv import load_dotenv

# Load environment variables (e.g. METAL_PRICE_API_KEY) from a .env file in
# the project root, so the key never has to be hardcoded here.
load_dotenv()

# Base URL for the "latest" prices endpoint. api_key/base/currencies are
# passed as query parameters.
METALPRICE_URL = "https://api.metalpriceapi.com/v1/latest"

# One troy ounce, the unit MetalpriceAPI prices metals in, converted to grams.
GRAMS_PER_TROY_OUNCE = 31.1035

# Nisab thresholds (the minimum wealth at which Zakat becomes due), expressed
# as the equivalent weight of gold or silver, per traditional Islamic rulings.
NISAB_GOLD_GRAMS = 87.48
NISAB_SILVER_GRAMS = 612.36

# Zakat is 2.5% of qualifying wealth held above the nisab threshold.
ZAKAT_RATE = 0.025


def calculate_zakat(
    cash: float = 0,
    gold_grams: float = 0,
    silver_grams: float = 0,
    currency: str = "INR",
    nisab_standard: str = "silver",
) -> dict:
    """
    Calculate Zakat due on a mix of cash, gold, and silver holdings.

    Args:
        cash: Cash and cash-equivalent savings, in `currency`.
        gold_grams: Gold holdings, in grams.
        silver_grams: Silver holdings, in grams.
        currency: Currency code to price the metals in, e.g. "INR".
        nisab_standard: Which metal's nisab threshold to use — "gold" or
            "silver". Silver is the more commonly used (and lower) standard.

    Returns:
        On success: {"success": True, "currency", "nisab_standard",
                      "total_wealth", "nisab_threshold", "above_nisab",
                      "zakat_due", "breakdown": {...}}
        On failure: {"success": False, "error": "<short plain-English reason>"}
    """
    # Validate nisab_standard up front, before touching the network at all.
    if nisab_standard not in ("gold", "silver"):
        return {
            "success": False,
            "error": "nisab_standard must be 'gold' or 'silver'",
        }

    # The API key must be present in the environment (loaded from .env above).
    api_key = os.getenv("METAL_PRICE_API_KEY")
    if not api_key:
        return {"success": False, "error": "METAL_PRICE_API_KEY is not set"}

    # Query params: fetch gold (XAU) and silver (XAG) rates priced in `currency`.
    params = {"api_key": api_key, "base": currency, "currencies": "XAU,XAG"}

    try:
        # timeout=10 stops the request from hanging forever if the API
        # or network is unresponsive.
        response = requests.get(METALPRICE_URL, params=params, timeout=10)

        # Non-200 status (e.g. bad API key, bad currency) is a failure.
        if response.status_code != 200:
            return {
                "success": False,
                "error": f"API returned status code {response.status_code}",
            }

        # Parse the JSON body. This can raise if the body isn't valid JSON.
        payload = response.json()

        # MetalpriceAPI sets "success": false (with an "error" object) when
        # the request itself was rejected, even though HTTP status was 200.
        if not payload.get("success"):
            return {
                "success": False,
                "error": payload.get("error", {}).get(
                    "message", "API reported an error"
                ),
            }

        # Direct "<BASE><METAL>" fields give the price of one troy ounce of
        # the metal in the requested currency (e.g. "INRXAU" -> INR per oz gold).
        rates = payload["rates"]
        price_per_ounce_gold = rates[f"{currency}XAU"]
        price_per_ounce_silver = rates[f"{currency}XAG"]

        # Convert troy-ounce prices to per-gram prices, since holdings are
        # supplied in grams.
        price_per_gram_gold = price_per_ounce_gold / GRAMS_PER_TROY_OUNCE
        price_per_gram_silver = price_per_ounce_silver / GRAMS_PER_TROY_OUNCE

        # Value each holding and total everything up.
        gold_value = gold_grams * price_per_gram_gold
        silver_value = silver_grams * price_per_gram_silver
        total_wealth = cash + gold_value + silver_value

        # The nisab threshold is the value of a fixed weight of gold or
        # silver, priced at today's rates.
        if nisab_standard == "gold":
            nisab_threshold = NISAB_GOLD_GRAMS * price_per_gram_gold
        else:
            nisab_threshold = NISAB_SILVER_GRAMS * price_per_gram_silver

        # Zakat is only due once total wealth meets or exceeds the threshold.
        above_nisab = total_wealth >= nisab_threshold
        zakat_due = total_wealth * ZAKAT_RATE if above_nisab else 0

        return {
            "success": True,
            "currency": currency,
            "nisab_standard": nisab_standard,
            "total_wealth": round(total_wealth, 2),
            "nisab_threshold": round(nisab_threshold, 2),
            "above_nisab": above_nisab,
            "zakat_due": round(zakat_due, 2),
            "breakdown": {
                "cash": cash,
                "gold_value": round(gold_value, 2),
                "silver_value": round(silver_value, 2),
                "gold_price_per_gram": round(price_per_gram_gold, 2),
                "silver_price_per_gram": round(price_per_gram_silver, 2),
            },
        }

    except requests.exceptions.Timeout:
        return {"success": False, "error": "Request timed out"}
    except requests.exceptions.RequestException:
        # Covers connection errors, DNS failures, etc.
        return {"success": False, "error": "Network error while contacting the API"}
    except (KeyError, ValueError, TypeError):
        # Covers missing rate keys, unexpected JSON shape, or decode errors.
        return {"success": False, "error": "Unexpected response format from API"}


if __name__ == "__main__":
    # Test 1: well above nisab, using the silver standard.
    result1 = calculate_zakat(
        cash=1200000, gold_grams=50, currency="INR", nisab_standard="silver"
    )
    print("Test 1 (above nisab, silver standard): cash=1200000, gold_grams=50")
    print(result1)

    print()

    # Test 2: modest cash only, using the (higher) gold standard — likely below nisab.
    result2 = calculate_zakat(cash=50000, currency="INR", nisab_standard="gold")
    print("Test 2 (likely below nisab, gold standard): cash=50000")
    print(result2)

    print()

    # Test 3: gold holdings only, no cash or silver.
    result3 = calculate_zakat(gold_grams=100, currency="INR", nisab_standard="silver")
    print("Test 3 (gold only): gold_grams=100")
    print(result3)

    print()

    # Test 4: invalid nisab_standard — expected to fail without calling the API.
    result4 = calculate_zakat(nisab_standard="platinum")
    print("Test 4 (failure expected): nisab_standard='platinum'")
    print(result4)
