"""
test_loop_offline.py

Exercises the plan-act-observe loop in agent.py (run_agent) with ZERO
network calls. No real Gemini API call and no real tool API call ever
happens: the Gemini client is replaced with a ScriptedClient that hands
back pre-built fake responses, and agent.TOOL_FUNCTIONS is replaced with
fakes that just record what they were called with.

Plain script, no pytest — run with: python test_loop_offline.py
"""

import sys

import agent


# --- Fakes duck-typed to the Gemini response shape run_agent reads --------
# run_agent only ever touches: response.candidates, candidate.content,
# content.parts, part.function_call (.name/.args) and part.text. These
# fakes implement exactly that surface and nothing more.

class FakeCall:
    def __init__(self, name, args):
        self.name = name
        self.args = args


class FakePart:
    def __init__(self, text=None, function_call=None):
        self.text = text
        self.function_call = function_call


class FakeContent:
    def __init__(self, parts, role="model"):
        self.parts = parts
        self.role = role


class FakeCandidate:
    def __init__(self, content):
        self.content = content


class FakeResponse:
    def __init__(self, candidates):
        self.candidates = candidates


class ScriptedClient:
    """Stands in for genai.Client: hands back scripted responses in order."""

    class _Models:
        def __init__(self, outer):
            self._outer = outer

        def generate_content(self, model=None, contents=None, config=None):
            self._outer.call_count += 1
            return self._outer._responses.pop(0)

    def __init__(self, responses):
        self._responses = list(responses)
        self.call_count = 0
        self.models = ScriptedClient._Models(self)


# Real tool names run_tool dispatches on, captured before we start
# overwriting agent.TOOL_FUNCTIONS in each scenario.
TOOL_NAMES = list(agent.TOOL_FUNCTIONS.keys())


def make_fake_tools(calls_log):
    """Fresh fake tools for one scenario; each records (name, kwargs) and
    returns instantly, so no scenario's call count can leak into another's.
    """
    def make_one(name):
        def fake(**kwargs):
            calls_log.append((name, kwargs))
            return {"success": True, "data": "fake result"}
        return fake

    return {name: make_one(name) for name in TOOL_NAMES}


def count_function_response_turns(conversation):
    """Count conversation entries that are a real types.Content function-
    response turn (the ones run_agent appends after calling a tool)."""
    count = 0
    for entry in conversation:
        parts = getattr(entry, "parts", None) or []
        for part in parts:
            if getattr(part, "function_response", None) is not None:
                count += 1
    return count


# --- Scenario A: text preamble before the call (review finding 1) --------

def scenario_a_preamble_then_call():
    calls_log = []
    agent.TOOL_FUNCTIONS = make_fake_tools(calls_log)

    round1 = FakeResponse(candidates=[FakeCandidate(FakeContent(parts=[
        FakePart(text="Let me check that."),
        FakePart(function_call=FakeCall(
            "get_prayer_times", {"city": "Chennai", "date": "15-07-2026"}
        )),
    ]))])
    round2 = FakeResponse(candidates=[FakeCandidate(FakeContent(parts=[
        FakePart(text="Fajr is at 4:38 AM."),
    ]))])

    agent.client = ScriptedClient([round1, round2])

    answer, conversation = agent.run_agent("When is Fajr in Chennai?")

    tool_calls = [c for c in calls_log if c[0] == "get_prayer_times"]
    assert len(tool_calls) == 1, f"expected 1 get_prayer_times call, got {len(tool_calls)}"
    assert answer == "Fajr is at 4:38 AM.", f"unexpected answer: {answer!r}"

    print("PASS: scenario A (preamble before call does not skip the tool)")


# --- Scenario B: two calls in one response (review finding 2) ------------

def scenario_b_parallel_calls():
    calls_log = []
    agent.TOOL_FUNCTIONS = make_fake_tools(calls_log)

    round1 = FakeResponse(candidates=[FakeCandidate(FakeContent(parts=[
        FakePart(function_call=FakeCall(
            "calculate_zakat",
            {"cash": 1000, "gold_grams": 0, "silver_grams": 0, "nisab_standard": "silver"},
        )),
        FakePart(function_call=FakeCall(
            "convert_date", {"direction": "to_hijri"}
        )),
    ]))])
    round2 = FakeResponse(candidates=[FakeCandidate(FakeContent(parts=[
        FakePart(text="Here is your answer."),
    ]))])

    agent.client = ScriptedClient([round1, round2])

    answer, conversation = agent.run_agent("Zakat and today's Hijri date please.")

    zakat_calls = [c for c in calls_log if c[0] == "calculate_zakat"]
    date_calls = [c for c in calls_log if c[0] == "convert_date"]
    assert len(zakat_calls) == 1, f"expected 1 calculate_zakat call, got {len(zakat_calls)}"
    assert len(date_calls) == 1, f"expected 1 convert_date call, got {len(date_calls)}"

    response_turns = count_function_response_turns(conversation)
    assert response_turns == 2, f"expected 2 function-response turns, got {response_turns}"

    print("PASS: scenario B (both parallel calls answered, history balanced)")


# --- Scenario C: empty candidates (minor guard) ---------------------------

def scenario_c_empty_candidates():
    calls_log = []
    agent.TOOL_FUNCTIONS = make_fake_tools(calls_log)

    round1 = FakeResponse(candidates=[])
    agent.client = ScriptedClient([round1])

    answer, conversation = agent.run_agent("Anything, doesn't matter.")

    assert "no response" in answer.lower(), f"unexpected answer: {answer!r}"

    print("PASS: scenario C (empty candidates handled without raising)")


if __name__ == "__main__":
    scenarios = [
        ("A", scenario_a_preamble_then_call),
        ("B", scenario_b_parallel_calls),
        ("C", scenario_c_empty_candidates),
    ]

    passed = 0
    for label, scenario in scenarios:
        try:
            scenario()
            passed += 1
        except AssertionError as e:
            print(f"FAIL: scenario {label}: {e}")

    print(f"{passed}/{len(scenarios)} scenarios passed")
    sys.exit(0 if passed == len(scenarios) else 1)
