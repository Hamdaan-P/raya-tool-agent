"""
agent.py

Dispatch map from Gemini FunctionDeclaration names (schemas.py) to the real
tool functions (tools/). No conversation loop, CLI, or Gemini call happens
here yet — this file only wires names to functions.
"""

import os
import sys

from dotenv import load_dotenv

# Load GEMINI_API_KEY (and friends) from .env.
load_dotenv()

from google import genai
from google.genai import types

# Tool schemas attached to Gemini calls.
from schemas import ALL_TOOLS

# The five real tool functions, imported directly from their modules since
# tools/__init__.py does not re-export them.
from tools.prayer_times import get_prayer_times
from tools.date_converter import convert_date
from tools.zakat import calculate_zakat
from tools.references import get_quran_verse, get_hadith

# Client setup for the Gemini API.
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("GEMINI_API_KEY is missing or empty. Set it in .env and re-run.")
    sys.exit(1)

client = genai.Client(api_key=api_key)

# Maps each FunctionDeclaration name in schemas.py to the actual function
# object to call when Gemini requests that tool. Keys must match the
# declaration names character for character.
TOOL_FUNCTIONS = {
    "get_prayer_times": get_prayer_times,
    "convert_date": convert_date,
    "calculate_zakat": calculate_zakat,
    "get_quran_verse": get_quran_verse,
    "get_hadith": get_hadith,
}


def run_tool(name, args):
    """
    Look up `name` in TOOL_FUNCTIONS and call it with `args` unpacked as
    keyword arguments. Never raises — unknown tools and unexpected errors
    are both returned as {"status": "error", "message": ...} instead.
    """
    print(f"[TOOL CALL] {name}")
    print(f"[ARGS] {args}")

    if name not in TOOL_FUNCTIONS:
        result = {"status": "error", "message": f"Unknown tool: {name}"}
        print(f"[RESULT] {result}")
        return result

    try:
        result = TOOL_FUNCTIONS[name](**args)
    except Exception as e:
        result = {"status": "error", "message": str(e)}

    print(f"[RESULT] {result}")
    return result


# Maximum plan-act-observe rounds before giving up on a question.
MAX_ITERATIONS = 10


def run_agent(question, history=None):
    """
    Manual plan-act-observe loop: send the conversation to the model, and if
    it responds with a function call, run the real tool and feed the result
    back in as a function response. Repeat until the model answers in text
    or MAX_ITERATIONS is reached. The model alone decides which tools (if
    any) to call — this function never inspects the question itself.

    `history` is an existing conversation list (as returned by a previous
    call), or None to start a new conversation. Returns (answer, conversation)
    so the caller can pass the updated conversation back in on the next turn.
    """
    conversation = history if history is not None else []
    conversation.append(types.Content(role="user", parts=[types.Part(text=question)]))

    config = types.GenerateContentConfig(
        tools=ALL_TOOLS,
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        system_instruction=(
            "Raya is an Islamic utility assistant. For Zakat calculations, "
            "never assume a nisab standard — if the user has not specified "
            "gold or silver, ask before calling the calculate_zakat tool. If "
            "the user's own wording already implies a currency (for example "
            "'rupees' or 'INR' implies Indian Rupees, 'dollars' or 'USD' "
            "implies US Dollars), use that currency directly without asking "
            "again; only ask about currency if the question gives no "
            "indication of one at all. If "
            "a question needs multiple tools, use all of them before "
            "answering. Never fabricate religious content or numbers. When a "
            "tool fails, report the failure honestly."
        ),
    )

    # Blank rounds (no function call, no text) get nudged back on track this
    # many times before we give up rather than burn remaining iterations.
    MAX_BLANK_NUDGES = 2
    blank_nudges_used = 0

    for round_number in range(1, MAX_ITERATIONS + 1):
        print(f"[ROUND {round_number}]")

        response = client.models.generate_content(
            model="gemini-3.5-flash",
            contents=conversation,
            config=config,
        )

        reply_content = response.candidates[0].content
        parts = reply_content.parts or []

        if parts and parts[0].function_call:
            part = parts[0]
            name = part.function_call.name
            args = dict(part.function_call.args)
            result = run_tool(name, args)

            # Append the model's own function-call turn, then the tool's
            # result as a function-response turn, and keep looping.
            conversation.append(reply_content)
            conversation.append(
                types.Content(
                    role="user",
                    parts=[types.Part.from_function_response(name=name, response=result)],
                )
            )
            continue

        # Robust text extraction (thinking-model safe): collect text from
        # every part that has it, skipping non-text parts like thought
        # signatures, instead of relying on response.text (which warns when
        # parts are mixed).
        final_text = "".join(p.text for p in parts if p.text)

        if not final_text:
            print("[NO TEXT] Model returned no function call and no text this round.")

            if blank_nudges_used >= MAX_BLANK_NUDGES:
                break

            blank_nudges_used += 1
            conversation.append(
                types.Content(
                    role="user",
                    parts=[types.Part(text=(
                        "Please continue: answer the user's original question now, "
                        "using the tool results already provided. If something is "
                        "missing, call the needed tool."
                    ))],
                )
            )
            continue

        print("[FINAL ANSWER]")
        return final_text, conversation

    message = (
        f"Could not complete the request within {MAX_ITERATIONS} iterations."
    )
    print(message)
    return message, conversation


# Real CLI: a chat loop with Raya, keeping conversation history across turns.
if __name__ == "__main__":
    # Hijri month names (e.g. "Muharram") can contain characters outside the
    # Windows console's default cp1252 encoding — switch stdout to UTF-8 so
    # printing tool results doesn't crash, same as tools/date_converter.py.
    sys.stdout.reconfigure(encoding="utf-8")

    print("Raya — your Islamic assistant. Type 'quit', 'exit', or 'q' to leave.")

    history = None
    while True:
        question = input("You: ")

        if question.strip() == "" or question.strip().lower() in ("quit", "exit", "q"):
            print("Raya: Goodbye!")
            break

        try:
            answer, history = run_agent(question, history)
        except Exception as e:
            print(f"Raya: Something went wrong: {e}")
            continue

        print(f"Raya: {answer}")
