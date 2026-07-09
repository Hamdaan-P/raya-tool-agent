"""
prayer_times.py

Standalone tool for fetching Islamic prayer times using the free Aladhan API
(https://aladhan.com/prayer-times-api). No AI/Gemini code lives in this file —
it is a plain function that any agent (or a human) can call directly.
"""

from datetime import datetime

import requests

# Base URL for the "timings by city" endpoint. The date is inserted into the
# path, and city/country are passed as query parameters.
ALADHAN_URL = "https://api.aladhan.com/v1/timingsByCity/{date}"

# The only prayers we care about, in the order we want them returned.
PRAYERS_WANTED = ["Fajr", "Dhuhr", "Asr", "Maghrib", "Isha"]


def get_prayer_times(city: str, country: str, date: str = None) -> dict:
    """
    Fetch prayer timings for a given city/country on a given date.

    Args:
        city: City name, e.g. "Chennai".
        country: Country name, e.g. "India".
        date: Date string in DD-MM-YYYY format. If None, today's date is used.

    Returns:
        On success: {"success": True, "city", "country", "date", "timings": {...}}
        On failure: {"success": False, "error": "<short plain-English reason>"}
    """
    # If no date was given, default to today's date in the DD-MM-YYYY format
    # that the Aladhan API expects.
    if date is None:
        date = datetime.now().strftime("%d-%m-%Y")

    # Build the full URL by inserting the date into the path.
    url = ALADHAN_URL.format(date=date)

    # City and country are sent as query string parameters, e.g.
    # ?city=Chennai&country=India
    params = {"city": city, "country": country}

    try:
        # timeout=10 stops the request from hanging forever if the API
        # or network is unresponsive.
        response = requests.get(url, params=params, timeout=10)

        # Non-200 status (e.g. 400 for unknown city) is a failure case.
        if response.status_code != 200:
            return {
                "success": False,
                "error": f"API returned status code {response.status_code}",
            }

        # Parse the JSON body. This can raise if the body isn't valid JSON.
        payload = response.json()

        # Aladhan wraps real responses in {"code": 200, "status": "OK", "data": {...}}.
        # A non-200 "code" here means the API itself rejected the request
        # (e.g. it couldn't geocode the city), even though HTTP status was 200.
        if payload.get("code") != 200:
            return {
                "success": False,
                "error": payload.get("status", "API reported an error"),
            }

        data = payload["data"]

        # The full timings dict includes extra entries (Sunrise, Sunset,
        # Imsak, etc.) that we don't want — filter down to just our 5 prayers.
        all_timings = data["timings"]
        timings = {name: all_timings[name] for name in PRAYERS_WANTED}

        # Prefer the human-readable date from the API response if present,
        # falling back to the date we requested.
        readable_date = data.get("date", {}).get("readable", date)

        return {
            "success": True,
            "city": city,
            "country": country,
            "date": readable_date,
            "timings": timings,
        }

    except requests.exceptions.Timeout:
        return {"success": False, "error": "Request timed out"}
    except requests.exceptions.RequestException:
        # Covers connection errors, DNS failures, etc.
        return {"success": False, "error": "Network error while contacting the API"}
    except (KeyError, ValueError, TypeError):
        # Covers unexpected JSON shape (missing keys) or JSON decode errors.
        return {"success": False, "error": "Unexpected response format from API"}


if __name__ == "__main__":
    # Test 1: a known, real city — expected to succeed.
    today = datetime.now().strftime("%d-%m-%Y")
    result1 = get_prayer_times("Chennai", "India", today)
    print("Test 1 (success expected): Chennai, India")
    print(result1)

    print()

    # Test 2: a made-up city — expected to fail gracefully.
    result2 = get_prayer_times("Atlantisburg", "Nowhere")
    print("Test 2 (failure expected): Atlantisburg, Nowhere")
    print(result2)
