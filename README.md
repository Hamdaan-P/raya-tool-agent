# Raya Tool Agent

Raya is a small command-line AI assistant for Islamic utility tasks. It is a
**tool-using agent**: instead of only chatting, it can decide to call real
tools — prayer times, date conversion, Zakat calculation, and Quran/hadith
lookup — to answer questions it could not answer on its own.

The agent loop (plan → act → observe → repeat) is **hand-written**. No agent
framework runs the loop for us — that was the point of the task.

---

## Demo video

A 3-minute screen recording showing all four required cases — a single-tool
request, a multi-tool request handled in one reply, the ask-first Zakat
guardrail, and a tool-failure handled gracefully — each with its trace:

**https://1drv.ms/v/c/0638a91271557bcf/IQCaFm_Pojy9QKyO61_Ht4CfAXqcogN6BiwBpAE-KcxQ-QM?e=17bPh1**

---

---

## What Raya can do

Raya exposes four tools. The model chooses which one(s) to call — nothing in
the code hardcodes "if the question says Zakat, call the calculator."

| Tool | What it does | Data source |
|------|--------------|-------------|
| `get_prayer_times` | Five daily prayer times for a city + country | Aladhan API |
| `convert_date` | Convert a date between Gregorian and Hijri | Aladhan API |
| `calculate_zakat` | Zakat owed against the nisab threshold | MetalpriceAPI (live gold/silver prices) |
| Quran / hadith lookup | A verse or hadith with its source reference | Al Quran Cloud, fawazahmed0 hadith |

One question can trigger **more than one tool**. For example, "How much Zakat
do I owe, and what is today's Hijri date?" makes Raya call the Zakat
calculator and the date converter, then combine both into one answer.

---

## Setup

**1. Requirements**
- Python 3.9 or newer
- A Google Gemini API key (free tier is enough)
- A MetalpriceAPI key (free tier is enough) — used for live gold/silver prices
  in the Zakat calculation

**2. Install dependencies**
```
pip install -r requirements.txt
```
This installs `google-genai`, `requests`, and `python-dotenv`.

**3. Add your API keys**
Create a file named `.env` in the project root with both keys:
```
GEMINI_API_KEY=your-gemini-key-here
METAL_PRICE_API_KEY=your-metalpriceapi-key-here
```
Without the metal price key, the other three tools still work, but the Zakat
calculator returns a clean "METAL_PRICE_API_KEY is not set" error.

**4. Run Raya**
```
python agent.py
```
Type your question at the `You:` prompt. Type `quit`, `exit`, or `q` to leave.

*(On Windows, run `chcp 65001` first so Arabic and Hijri month names display
correctly.)*

---

## Model and APIs used

- **Model:** `gemini-3.5-flash`, using Gemini's native function calling.
  Automatic function calling is **turned off** on purpose, so our own loop
  stays in control (the task required a from-scratch loop).
- **Prayer times & date conversion:** Aladhan API
- **Quran:** Al Quran Cloud API
- **Hadith:** fawazahmed0 hadith CDN
- **Zakat:** calculated in code against live gold/silver prices from MetalpriceAPI

The tools do real work — they call live APIs, not hardcoded values.

---

## How the agent loop works (in plain words)

The heart of Raya is a loop in `agent.py` called `run_agent`. Each time round
the loop, one message goes to the model and one reply comes back. I think of
the reply as an **envelope** that can hold several pages.

Each round, the loop reads the whole envelope and takes one of three exits:

1. **The model asked for tools.** The envelope contains one or more tool
   "work orders." The loop runs every tool it finds, writes down each result,
   and loops again so the model can read those results and decide what's next.
   This is the **observe** step — handing results back is what makes it an
   agent and not a one-shot script.
2. **The model gave a final answer.** The envelope is just text, no tool
   request. That text is the answer, and the loop stops.
3. **The model sent nothing useful.** An empty round. The loop gives it a
   small nudge to get back on track, up to two times, then stops.

An important detail: the loop reads **every page** of the envelope, not just
the first. The model sometimes writes a short note like "Let me check that"
*before* the actual tool request. An earlier version only looked at the first
page, so it mistook that note for the final answer and skipped the tool. The
fixed loop scans all pages, so a note can never hide a real tool request, and
several tool requests in one envelope all get run.

### How does the agent decide when to stop?

It stops in one of three ways:
- **The goal is met** — the model sends a plain text answer with no tool
  request. That answer is returned to the user and the loop ends.
- **It runs out of rounds** — there is a hard cap (`MAX_ITERATIONS = 10`). If
  the model somehow keeps going without ever finishing, the loop gives up
  honestly instead of running forever. A loop with no stop condition is a bug.
- **The model stalls** — if a round comes back empty, the loop nudges it back
  on track, but only twice (`MAX_BLANK_NUDGES = 2`). After that it stops
  rather than looping on nothing.

### What happens when a tool fails?

Every tool is written to **never crash and never fake an answer**. On failure
— a bad city, a network timeout, an API error — a tool returns a plain result
that says `success: False` with a short reason, instead of raising an error or
inventing data. The loop hands that failure back to the model, and the model
tells the user honestly what went wrong (for example, "I couldn't find prayer
times for that city"). It does **not** make up a time.

This matters most for religious content. Raya never invents a verse, a hadith,
or a ruling. If a reference does not exist, the lookup returns a clean
"not found" and the agent says so. For an Islamic assistant, a wrong citation
is worse than no answer, so refusing is the correct behaviour.

There is also a guardrail on Zakat: if the user does not say which nisab
standard (gold or silver) to use, the agent **asks first** instead of
assuming, because a wrong assumption would produce a religiously incorrect
number.

---

## The trace

Every run prints a trace so you can see exactly what happened: the round
number, which tool was called (`[TOOL CALL]`), the arguments (`[ARGS]`), what
the tool returned (`[RESULT]`), and the final answer (`[FINAL ANSWER]`). If a
feature can't be seen in the trace, it isn't really done.

---

## Project structure

```
agent.py              The hand-written plan-act-observe loop + CLI
schemas.py            Tool descriptions the model reads (name, purpose, inputs)
tools/
  prayer_times.py     get_prayer_times (Aladhan)
  date_converter.py   convert_date (Aladhan)
  zakat.py            calculate_zakat (live metal prices)
  references.py       Quran + hadith lookup
test_loop_offline.py  Offline tests for the loop (no network, no Gemini calls)
requirements.txt      Dependencies
```

## Running the offline tests

```
python test_loop_offline.py
```
These check the loop's tricky cases (a text note before a tool call, several
tool calls in one reply, and an empty model response) without using the
network or any Gemini quota.
