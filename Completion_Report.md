# Project Completion Report — Raya Tool Agent

**Intern:** Hamdaan
**Task assigner:** Omar Ahmed
**Reviewing Tech Lead:** Yousef
**Task:** Agents & Tool-Calling (#1) — The Tool-Using Agent
**Team:** ZaryahPlus · AI Engineering Track
**Status:** Complete — resubmission after code review

---

## 1. Summary

Raya is a command-line tool-using agent for Islamic utility tasks. Given a
question, the model decides which tools to call, the agent runs them, feeds the
results back, and the model either continues or gives a final answer. The
plan–act–observe loop is written from scratch — no framework runs it.

This report covers the completed project, including the fixes made after
Yousef's code review of 13 July 2026. All review findings have been addressed
and verified.

---

## 2. What was built

**Four tools**, each doing real work against live APIs or data:

| Tool | Purpose | Source |
|------|---------|--------|
| `get_prayer_times` | Five daily prayer times for a city + country | Aladhan API |
| `convert_date` | Gregorian ↔ Hijri date conversion | Aladhan API |
| `calculate_zakat` | Zakat owed against the nisab threshold | MetalpriceAPI (live gold/silver) |
| Quran / hadith lookup | A verse or hadith with its source reference | Al Quran Cloud, fawazahmed0 hadith |

**A hand-written agent loop** (`run_agent` in `agent.py`) that scans every part
of the model's reply, runs every tool it requests, feeds each result back, and
stops when the goal is met, when a hard iteration cap is reached, or after an
empty-round nudge limit.

**A readable trace** on every run: round number, tool called, arguments,
result, and final answer.

**Offline tests** (`test_loop_offline.py`) covering the loop's tricky cases
without using the network or any Gemini quota.

---

## 3. How the requirements were met

- **The model chooses the tools.** Tool selection comes from the schemas and
  the model, not from keyword routing in code.
- **Multi-step works.** A single question ("How much Zakat do I owe, and what
  is today's Hijri date?") triggers two tool calls, chained and combined into
  one answer. Shown in the demo video.
- **It refuses honestly.** When no tool fits or a reference doesn't exist, the
  agent says so instead of inventing. Religious content is never fabricated.
- **It recovers from failure.** Tools return a clean `success: False` on error
  rather than crashing; the agent reads that and reports it honestly.
- **Every run is traceable.** The trace is printed for each run and is visible
  in the demo video.
- **The Zakat guardrail.** If the user doesn't state the nisab standard (gold
  or silver), the agent asks first rather than assuming — enforced in the
  schema and the system prompt.

---

## 4. Code review response (Yousef, 13 July 2026)

All findings were addressed and verified (diffs checked; offline tests pass).

| # | Finding | Severity | Resolution |
|---|---------|----------|------------|
| 1 | Loop only inspected `parts[0]` — a text preamble made it skip the tool | BLOCKER | Loop now scans all parts for function calls |
| 2 | Parallel/multi-part calls dropped → history mismatch | MAJOR | Every call executed; one function-response filed per call |
| 3 | `surah`/`ayah`/hadith `number` typed as float (NUMBER) | MAJOR | Changed to INTEGER + `int()` coercion before URL building |
| 4 | Model ID `gemini-3.5-flash` unverified | VERIFY | Pulled into `MODEL_ID` constant; verified live via `models.list()` — resolves |
| 5 | Two different result shapes (`success` vs `status`/`message`) | MINOR | Unified to `{"success": False, "error": ...}` |
| 6 | Hadith reference hardcoded "(English)" | MINOR | Label derived from the language argument |
| 7 | `candidates[0]` unguarded — empty response could crash | MINOR | Guard added; prints a clean message, no crash |

---

## 5. Testing

- **Offline loop tests** (`test_loop_offline.py`), 3/3 passing, no network or
  Gemini use: a text preamble before a call, two calls in one reply, and an
  empty candidate list. These act as regression tests for review findings 1, 2,
  and 7.
- **Live verification:** the model ID was confirmed against the live model list
  before any demo run.
- **Tool-level testing:** each tool's failure path was exercised directly
  (bad city, unknown hadith collection, out-of-range reference) to confirm it
  returns a clean failure rather than raising or fabricating.
- **Demo runs:** the four required scenarios were run live and recorded.

---

## 6. Known limitations

- **Loose upstream geocoding.** The Aladhan prayer-times API sometimes resolves
  a clearly-invalid city name to real coordinates and returns success, rather
  than a not-found. This is an upstream behaviour, not a bug in Raya's code —
  tested and documented. For a reliably-invalid input, the tool returns a clean
  failure as intended. Scoped as a known limitation for this task.
- **Free-tier API constraints.** During demo recording the Gemini free tier
  intermittently returned 503 (high demand), which required waiting and
  retrying. This inflated the total call count and is a constraint of the free
  tier, not the agent.

---

## 7. Deliverables

- GitHub repository with README (setup, model + APIs, agent loop explained, and
  the two required written answers).
- Demo video (linked in the README) showing the four required cases with traces.
- Offline test suite.
- This completion report.

---

## 8. Notes

- Gemini call usage for the whole task was higher than the planned budget,
  mainly due to free-tier 503 retries during recording. Exact count not tracked
  through the retries; the code fixes and all offline tests cost zero Gemini
  calls by design.
- Harmless environment noise (a `google-auth` Python 3.9 deprecation warning)
  is documented and requires no action.
