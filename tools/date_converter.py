"""
date_converter.py

Standalone tool for converting between Gregorian and Hijri (Islamic) calendar
dates using the free Aladhan API (https://aladhan.com/calendar-date-converter/).
No AI/Gemini code lives in this file — it is a plain function that any agent
(or a human) can call directly.
"""

from datetime import datetime

import requests

# Base URLs for the two conversion directions. The date is inserted into the path.
GREGORIAN_TO_HIJRI_URL = "https://api.aladhan.com/v1/gToH/{date}"
HIJRI_TO_GREGORIAN_URL = "https://api.aladhan.com/v1/hToG/{date}"


def convert_date(date: str = None, direction: str = "to_hijri") -> dict:
    """
    Convert a date between the Gregorian and Hijri calendars.

    Args:
        date: Date string in DD-MM-YYYY format. If None and direction is
            "to_hijri", today's Gregorian date is used. If None and direction
            is "to_gregorian", this is a failure (we cannot guess "today" in
            the Hijri calendar without also calling the API).
        direction: Either "to_hijri" or "to_gregorian".

    Returns:
        On success: {"success": True, "direction", "input_date",
                      "converted_date", "readable", "calendar"}
        On failure: {"success": False, "error": "<short plain-English reason>"}
    """
    # Validate direction up front, before touching the network at all.
    if direction not in ("to_hijri", "to_gregorian"):
        return {
            "success": False,
            "error": "direction must be 'to_hijri' or 'to_gregorian'",
        }

    # Fill in "today" only when converting from Gregorian — we have no local
    # way to know "today" in Hijri terms, so that case must fail instead.
    if date is None:
        if direction == "to_hijri":
            date = datetime.now().strftime("%d-%m-%Y")
        else:
            return {
                "success": False,
                "error": "A Hijri date is required when converting to Gregorian",
            }

    # Pick the endpoint and the calendar name of the *result* we're producing.
    if direction == "to_hijri":
        url = GREGORIAN_TO_HIJRI_URL.format(date=date)
        target_calendar = "hijri"
    else:
        url = HIJRI_TO_GREGORIAN_URL.format(date=date)
        target_calendar = "gregorian"

    try:
        # timeout=10 stops the request from hanging forever if the API
        # or network is unresponsive.
        response = requests.get(url, timeout=10)

        # Non-200 status (e.g. 500 for an invalid/unparsable date) is a failure.
        if response.status_code != 200:
            return {
                "success": False,
                "error": f"API returned status code {response.status_code}",
            }

        # Parse the JSON body. This can raise if the body isn't valid JSON.
        payload = response.json()

        # Aladhan wraps real responses in {"code": 200, "status": "OK", "data": {...}}.
        # A non-200 "code" here means the API itself rejected the request,
        # even though the HTTP status was 200.
        if payload.get("code") != 200:
            return {
                "success": False,
                "error": payload.get("status", "API reported an error"),
            }

        # The response always contains both "hijri" and "gregorian" sub-objects
        # (one is the echoed input, the other is the converted result) — we
        # only need the one matching our target calendar.
        target = payload["data"][target_calendar]

        converted_date = target["date"]

        # Build a human-readable string like "24 Muharram 1448" or "09 July 2026"
        # from the day, month name, and year of the target calendar.
        readable = f"{target['day']} {target['month']['en']} {target['year']}"

        return {
            "success": True,
            "direction": direction,
            "input_date": date,
            "converted_date": converted_date,
            "readable": readable,
            "calendar": target_calendar,
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
    import sys

    # Hijri month names (e.g. "Muharram") can contain characters outside the
    # Windows console's default cp1252 encoding — switch stdout to UTF-8 so
    # printing these test results doesn't crash.
    sys.stdout.reconfigure(encoding="utf-8")

    # Test 1: convert today's Gregorian date to Hijri.
    today = datetime.now().strftime("%d-%m-%Y")
    result1 = convert_date(today, direction="to_hijri")
    print("Test 1 (Gregorian -> Hijri): today's date")
    print(result1)

    print()

    # Test 2 (round-trip): take the Hijri date from Test 1 and convert it
    # back to Gregorian, then check it matches the date we started with.
    print("Test 2 (round-trip: Hijri -> Gregorian)")
    if result1["success"]:
        result2 = convert_date(result1["converted_date"], direction="to_gregorian")
        print(result2)
        if result2["success"]:
            matches = result2["converted_date"] == today
            print(f"Matches today's date ({today})? {matches}")
    else:
        print("Skipped — Test 1 did not succeed, so there is nothing to convert back.")

    print()

    # Test 3: an invalid date — expected to fail gracefully.
    result3 = convert_date("99-99-9999", "to_hijri")
    print("Test 3 (failure expected): invalid date 99-99-9999")
    print(result3)
