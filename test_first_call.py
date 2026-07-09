"""
test_first_call.py

Temporary Phase 2 test script. Sends one question to Gemini with our tool
schemas attached and shows whether the model chose a tool call or answered
in plain text. Does NOT execute any tool.
"""

import os
import sys

from dotenv import load_dotenv

# 1. Load GEMINI_API_KEY from .env; bail out before touching the API if missing.
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("GEMINI_API_KEY is missing or empty. Set it in .env and re-run.")
    sys.exit(1)

# 2. Tool schemas that mirror the real functions in tools/.
from schemas import ALL_TOOLS

from google import genai
from google.genai import types

# 3. Client constructed with the key explicitly (not via env auto-pickup).
client = genai.Client(api_key=api_key)

# 4. Ask the question with tools attached; automatic_function_calling.disable=True
#    stops the SDK from executing any function itself.
response = client.models.generate_content(
    model="gemini-3.5-flash",
    contents="What is 15 Ramadan 1447 in the Gregorian calendar?",
    config=types.GenerateContentConfig(
        tools=ALL_TOOLS,
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    ),
)

# 5. Inspect the response: either a function_call part or plain text.
part = response.candidates[0].content.parts[0]
if part.function_call:
    print("MODEL CHOSE TOOL:", part.function_call.name)
    print("WITH ARGUMENTS:", dict(part.function_call.args))
else:
    print("MODEL ANSWERED IN TEXT:", response.text)
