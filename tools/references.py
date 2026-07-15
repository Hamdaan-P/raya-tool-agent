"""
references.py

Standalone tool for retrieving Quran verses and hadith from public APIs,
always paired with their source reference and attribution.

This tool NEVER invents, approximates, or substitutes a "nearby" result. If a
requested reference does not exist in the source, it returns a clean
not-found failure dict — never a guess, never a paraphrase, never a
best-effort match.
"""

import requests

# Al Quran Cloud lets us fetch several editions of the same ayah in one call.
# We always include "quran-uthmani" (the Arabic text) alongside whatever
# translation edition was requested, separated by a comma.
QURAN_URL = "https://api.alquran.cloud/v1/ayah/{surah}:{ayah}/editions/quran-uthmani,{translation_edition}"

# The fawazahmed0 hadith dataset is served as static JSON files on jsdelivr's
# CDN, keyed by "{language}-{collection}" edition and hadith number.
HADITH_URL = "https://cdn.jsdelivr.net/gh/fawazahmed0/hadith-api@1/editions/{edition}/{number}.min.json"

# Only these collections are supported, to avoid guessing at (or hitting) an
# edition identifier that doesn't actually exist in the dataset.
ALLOWED_COLLECTIONS = ["bukhari", "muslim", "abudawud", "tirmidhi", "nasai", "ibnmajah"]

# Human-readable labels for the language codes used in the reference string.
LANGUAGE_LABELS = {"eng": "English", "ara": "Arabic", "urd": "Urdu"}


def get_quran_verse(surah: int, ayah: int, translation_edition: str = "en.asad") -> dict:
    """
    Fetch a single Quran verse (ayah), in Arabic and in translation.

    Args:
        surah: Surah (chapter) number, 1-114.
        ayah: Ayah (verse) number within the surah.
        translation_edition: Al Quran Cloud edition identifier for the
            translation, e.g. "en.asad".

    Returns:
        On success: {"success": True, "type": "quran", "reference",
                      "arabic", "text", "edition", "source"}
        On failure: {"success": False, "error": "<short plain-English reason>"}
    """
    # Schema declares these as INTEGER, but coerce anyway so a float like
    # 1.0 can never reach the URL.
    surah, ayah = int(surah), int(ayah)
    url = QURAN_URL.format(surah=surah, ayah=ayah, translation_edition=translation_edition)

    try:
        # timeout=10 stops the request from hanging forever if the API
        # or network is unresponsive.
        response = requests.get(url, timeout=10)

        # A non-200 status means the reference wasn't found (e.g. surah/ayah
        # out of range, or an unknown translation edition) — this is not an
        # error to hide behind, it's a real "does not exist" result.
        if response.status_code != 200:
            return {"success": False, "error": f"Verse {surah}:{ayah} not found"}

        payload = response.json()

        # Belt-and-braces: even with a 200 status, only trust a "code": 200
        # payload with the expected two-edition array.
        if payload.get("code") != 200:
            return {"success": False, "error": f"Verse {surah}:{ayah} not found"}

        data = payload["data"]
        arabic_entry, translation_entry = data[0], data[1]

        surah_name = translation_entry["surah"]["englishName"]

        return {
            "success": True,
            "type": "quran",
            "reference": f"Surah {surah_name} ({surah}:{ayah})",
            "arabic": arabic_entry["text"],
            "text": translation_entry["text"],
            "edition": translation_entry["edition"]["name"],
            "source": "Al Quran Cloud (alquran.cloud)",
        }

    except requests.exceptions.Timeout:
        return {"success": False, "error": "Request timed out"}
    except requests.exceptions.RequestException:
        # Covers connection errors, DNS failures, etc.
        return {"success": False, "error": "Network error while contacting the API"}
    except (KeyError, IndexError, ValueError, TypeError):
        # Covers unexpected JSON shape (missing keys, wrong array length) or
        # JSON decode errors.
        return {"success": False, "error": "Unexpected response format from API"}


def get_hadith(collection: str, number: int, language: str = "eng") -> dict:
    """
    Fetch a single hadith by collection and number.

    Args:
        collection: One of ALLOWED_COLLECTIONS, e.g. "bukhari".
        number: The hadith number within that collection.
        language: Language code for the edition, e.g. "eng".

    Returns:
        On success: {"success": True, "type": "hadith", "reference", "text", "source"}
        On failure: {"success": False, "error": "<short plain-English reason>"}
    """
    # Reject unknown collections before making any network call — we only
    # want to query editions we know actually exist in the dataset.
    if collection not in ALLOWED_COLLECTIONS:
        return {
            "success": False,
            "error": f"Unknown collection '{collection}'. Allowed: {', '.join(ALLOWED_COLLECTIONS)}",
        }

    # Schema declares this as INTEGER, but coerce anyway so a float like
    # 1.0 can never reach the URL (1.0.min.json does not exist on the CDN).
    number = int(number)
    edition = f"{language}-{collection}"
    url = HADITH_URL.format(edition=edition, number=number)

    try:
        # timeout=10 stops the request from hanging forever if the API
        # or network is unresponsive.
        response = requests.get(url, timeout=10)

        # A missing hadith file (bad number or bad edition) comes back as a
        # non-200, non-JSON response — treat any non-200 as "not found".
        if response.status_code != 200:
            return {"success": False, "error": f"Hadith {collection} #{number} not found"}

        payload = response.json()

        # Each file holds a "hadiths" list; for a single-number lookup it
        # should contain exactly one entry with the text we want.
        hadiths = payload["hadiths"]
        text = hadiths[0]["text"]

        language_label = LANGUAGE_LABELS.get(language, language)

        return {
            "success": True,
            "type": "hadith",
            "reference": f"{collection} ({language_label}) #{number}",
            "text": text,
            "source": "fawazahmed0 Hadith API (community-maintained public dataset)",
        }

    except requests.exceptions.Timeout:
        return {"success": False, "error": "Request timed out"}
    except requests.exceptions.RequestException:
        # Covers connection errors, DNS failures, etc.
        return {"success": False, "error": "Network error while contacting the API"}
    except (KeyError, IndexError, ValueError, TypeError):
        # Covers unexpected JSON shape (missing keys, empty list) or JSON
        # decode errors.
        return {"success": False, "error": "Unexpected response format from API"}


if __name__ == "__main__":
    import sys

    # Arabic verse/hadith text falls outside the Windows console's default
    # cp1252 encoding — switch stdout to UTF-8 so printing results doesn't crash.
    sys.stdout.reconfigure(encoding="utf-8")

    # Test 1: a real, well-known verse — Ayat al-Kursi.
    result1 = get_quran_verse(2, 255)
    print("Test 1 (Quran success): Surah 2, Ayah 255 (Ayat al-Kursi)")
    print(result1)

    print()

    # Test 2: surah 200 does not exist — must fail cleanly, not guess.
    result2 = get_quran_verse(200, 5)
    print("Test 2 (Quran not found): Surah 200, Ayah 5")
    print(result2)

    print()

    # Test 3: a real, well-known hadith — the first hadith in Sahih al-Bukhari.
    result3 = get_hadith("bukhari", 1)
    print("Test 3 (Hadith success): bukhari #1")
    print(result3)

    print()

    # Test 4: a hadith number far beyond the collection's range — not found.
    result4 = get_hadith("bukhari", 999999)
    print("Test 4 (Hadith not found): bukhari #999999")
    print(result4)

    print()

    # Test 5: an unsupported collection — rejected before any API call.
    result5 = get_hadith("nonexistent", 1)
    print("Test 5 (invalid collection): nonexistent #1")
    print(result5)
