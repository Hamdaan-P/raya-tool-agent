"""
schemas.py

Gemini function-calling schemas for the tools in tools/. Each
types.FunctionDeclaration below mirrors the real signature of the matching
tool function exactly (name and parameter names), so the model's tool calls
can be dispatched straight through without translation.
"""

from google.genai import types

# --- get_prayer_times (tools/prayer_times.py) ---------------------------
# def get_prayer_times(city: str, country: str, date: str = None) -> dict
get_prayer_times_declaration = types.FunctionDeclaration(
    name="get_prayer_times",
    description=(
        "Get the five daily Islamic prayer times (Fajr, Dhuhr, Asr, Maghrib, "
        "Isha) for a city on a given date. Use when the user asks when a "
        "prayer is or for a prayer timetable."
    ),
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "city": types.Schema(
                type=types.Type.STRING,
                description="City name, e.g. 'Chennai'.",
            ),
            "country": types.Schema(
                type=types.Type.STRING,
                description=(
                    "Country the city is in, e.g. 'India'. Needed to "
                    "disambiguate cities."
                ),
            ),
            "date": types.Schema(
                type=types.Type.STRING,
                description="Date as DD-MM-YYYY. If omitted, today is used.",
            ),
        },
        # date is optional (defaults to None in the real function), so only
        # city and country are required here.
        required=["city", "country"],
    ),
)

# --- convert_date (tools/date_converter.py) ------------------------------
# def convert_date(date: str = None, direction: str = "to_hijri") -> dict
convert_date_declaration = types.FunctionDeclaration(
    name="convert_date",
    description=(
        "Convert a date between the Gregorian and Hijri (Islamic) calendars, "
        "in either direction."
    ),
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "date": types.Schema(
                type=types.Type.STRING,
                description=(
                    "Date to convert as DD-MM-YYYY. If omitted, today is used."
                ),
            ),
            "direction": types.Schema(
                type=types.Type.STRING,
                enum=["to_hijri", "to_gregorian"],
                description=(
                    "'to_hijri' = Gregorian to Hijri; 'to_gregorian' = Hijri "
                    "to Gregorian."
                ),
            ),
        },
        # direction is required (the model must always choose a direction);
        # date is optional and defaults to today when converting to Hijri.
        required=["direction"],
    ),
)

# --- calculate_zakat (tools/zakat.py) ------------------------------------
# def calculate_zakat(cash=0, gold_grams=0, silver_grams=0,
#                      currency="INR", nisab_standard="silver") -> dict
calculate_zakat_declaration = types.FunctionDeclaration(
    name="calculate_zakat",
    description=(
        "Calculate Zakat owed on cash, gold and silver using live metal "
        "prices and the nisab threshold. Returns amount owed, or zero if "
        "wealth is below nisab. The user must explicitly state which nisab "
        "standard (gold or silver) to use — if they have not stated one, do "
        "NOT call this tool yet; ask the user to choose gold or silver first."
    ),
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "cash": types.Schema(
                type=types.Type.NUMBER,
                description="Cash/savings held, in the given currency.",
            ),
            "gold_grams": types.Schema(
                type=types.Type.NUMBER,
                description="Grams of gold owned. Use 0 if none.",
            ),
            "silver_grams": types.Schema(
                type=types.Type.NUMBER,
                description="Grams of silver owned. Use 0 if none.",
            ),
            "currency": types.Schema(
                type=types.Type.STRING,
                description=(
                    "3-letter currency code, e.g. 'INR'. Defaults to INR."
                ),
            ),
            "nisab_standard": types.Schema(
                type=types.Type.STRING,
                enum=["gold", "silver"],
                description=(
                    "Which nisab threshold to use — 'gold' or 'silver'. This "
                    "is the user's explicit choice, never assume it. If the "
                    "user has not stated a standard, do NOT call this tool "
                    "yet — ask them to choose gold or silver first."
                ),
            ),
        },
        # cash, gold_grams and silver_grams are required per the task spec
        # (the model should always state amounts explicitly, using 0 for
        # anything the user doesn't hold); currency and nisab_standard have
        # real defaults in the function itself.
        required=["cash", "gold_grams", "silver_grams"],
    ),
)

# --- get_quran_verse (tools/references.py) -------------------------------
# def get_quran_verse(surah: int, ayah: int, translation_edition: str = "en.asad") -> dict
get_quran_verse_declaration = types.FunctionDeclaration(
    name="get_quran_verse",
    description=(
        "Retrieve a specific Quran verse by surah and ayah number, returned "
        "with its edition/source attribution. Only returns verified text "
        "from the API; never invents a verse."
    ),
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "surah": types.Schema(
                type=types.Type.INTEGER,
                description="Surah number, 1 to 114.",
            ),
            "ayah": types.Schema(
                type=types.Type.INTEGER,
                description="Ayah number within the surah.",
            ),
            # Named "translation_edition" (not "edition") to match the real
            # function's parameter name in tools/references.py.
            "translation_edition": types.Schema(
                type=types.Type.STRING,
                description=(
                    "Translation edition id, e.g. 'en.asad'. Defaults to "
                    "en.asad."
                ),
            ),
        },
        required=["surah", "ayah"],
    ),
)

# --- get_hadith (tools/references.py) -------------------------------------
# def get_hadith(collection: str, number: int, language: str = "eng") -> dict
get_hadith_declaration = types.FunctionDeclaration(
    name="get_hadith",
    description=(
        "Retrieve a specific hadith by collection and number, with source "
        "attribution. Only returns verified text from the API; never "
        "fabricates a hadith."
    ),
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "collection": types.Schema(
                type=types.Type.STRING,
                enum=["bukhari", "muslim", "abudawud", "tirmidhi", "nasai", "ibnmajah"],
                description="Hadith collection name.",
            ),
            "number": types.Schema(
                type=types.Type.INTEGER,
                description="Hadith number within the collection.",
            ),
            "language": types.Schema(
                type=types.Type.STRING,
                description="Language code, e.g. 'eng'. Defaults to eng.",
            ),
        },
        required=["collection", "number"],
    ),
)

# Bundle every declaration into a single Tool for the Gemini SDK.
ALL_TOOLS = [
    types.Tool(
        function_declarations=[
            get_prayer_times_declaration,
            convert_date_declaration,
            calculate_zakat_declaration,
            get_quran_verse_declaration,
            get_hadith_declaration,
        ]
    )
]
