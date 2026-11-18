"""Write `toolcall_v1.jsonl`: held-out tool-call prompts for the SFT evaluation (eval_v1.md).

Run: python gen_toolcall_v1.py   (writes the file next to this script, deterministic)

Each row is one prompt. `messages` is a chat-format v0 transcript that ends where the model must answer.
`expect` says what a correct answer is:
  {"calls": [{"name": ..., "arguments": {...}}, ...]}        exactly these calls, any order, ids ignored
  "loose": {"arg": "ci" | "nospace"}                          compare that argument ignoring case, or all spaces
  an argument value {"any_of": [a, b]}                        either value is accepted
  "must_contain": [...]                                       the reply holds every string
  "must_contain_any": [...]                                   the reply holds at least one string (ignoring case)
  "must_ask": true                                            the reply is a question (holds "?")
A row with no call needs a non-empty reply. Items are evaluation-only and are never trained on.
"""

from __future__ import annotations

import json
from pathlib import Path

SOURCE = (
    "original: written by Claude (AI assistant) for Ravi Naik (RaviNaik), 2026-11-15; not from any benchmark; "
    "evaluation-only (TSAI data rule, 3 Nov)"
)


def tool(name, description, props, required):
    return {
        "name": name,
        "description": description,
        "parameters": {"type": "object", "properties": props, "required": required},
    }


S, INT, N = {"type": "string"}, {"type": "integer"}, {"type": "number"}
TOOLS = {
    "get_weather": tool(
        "get_weather",
        "Current weather for a city.",
        {"city": S, "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]}},
        ["city"],
    ),
    "set_alarm": tool("set_alarm", "Set an alarm.", {"time": S, "label": S}, ["time"]),
    "search_files": tool(
        "search_files",
        "Find files whose name matches a glob pattern.",
        {"pattern": S, "directory": S},
        ["pattern"],
    ),
    "convert_currency": tool(
        "convert_currency",
        "Convert an amount between two currencies.",
        {"amount": N, "from_currency": S, "to_currency": S},
        ["amount", "from_currency", "to_currency"],
    ),
    "create_event": tool(
        "create_event",
        "Create a calendar event.",
        {"title": S, "date": S, "attendees": {"type": "array", "items": S}},
        ["title", "date"],
    ),
    "run_tests": tool("run_tests", "Run the tests under a path.", {"path": S, "verbose": {"type": "boolean"}}, ["path"]),
    "translate": tool("translate", "Translate text.", {"text": S, "target_language": S}, ["text", "target_language"]),
    "calculate": tool("calculate", "Evaluate an arithmetic expression.", {"expression": S}, ["expression"]),
    "send_message": tool("send_message", "Send a chat message to a contact.", {"to": S, "text": S}, ["to", "text"]),
    "read_file": tool("read_file", "Read a text file.", {"path": S, "max_lines": INT}, ["path"]),
}
SYSTEM = "You can call tools. Answer with a tool call only when a tool is needed and every required argument is known."


def call(name, **arguments):
    return {"name": name, "arguments": arguments}


def anyof(*values):
    return {"any_of": list(values)}


def row(rid, kind, tools, user, expect, extra_messages=None):
    system = SYSTEM + "\nTools: " + json.dumps([TOOLS[t] for t in tools], ensure_ascii=False, sort_keys=True)
    messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    messages += extra_messages or []
    return {"id": rid, "kind": kind, "tools": tools, "messages": messages, "expect": expect, "source": SOURCE}


ROWS = [
    # one call, plain arguments
    row("tc-single-01", "single", ["get_weather", "set_alarm"], "What is the weather in Pune right now, in celsius?",
        {"calls": [call("get_weather", city="Pune", unit="celsius")]}),
    row("tc-single-02", "single", ["get_weather", "set_alarm"], "Set an alarm for 06:30 with the label gym.",
        {"calls": [call("set_alarm", time="06:30", label="gym")]}),
    row("tc-single-03", "single", ["search_files", "read_file"], "Find every file ending in .log inside /var/app.",
        {"calls": [call("search_files", pattern="*.log", directory="/var/app")]}),
    row("tc-single-04", "single", ["convert_currency", "calculate"], "Convert 250 USD to EUR.",
        {"calls": [call("convert_currency", amount=250, from_currency="USD", to_currency="EUR")]}),
    row("tc-single-05", "single", ["create_event", "send_message"], "Put 'Design review' on 2026-12-03 with Asha and Ravi.",
        {"calls": [call("create_event", title="Design review", date="2026-12-03", attendees=["Asha", "Ravi"])]}),
    row("tc-single-06", "single", ["run_tests", "read_file"], "Run the tests in tests/unit with verbose output.",
        {"calls": [call("run_tests", path="tests/unit", verbose=True)]}),
    row("tc-single-07", "single", ["calculate", "convert_currency"], "Compute (17 * 23) + 4.",
        {"calls": [call("calculate", expression="(17 * 23) + 4")], "loose": {"expression": "nospace"}}),
    row("tc-single-08", "single", ["read_file", "search_files"], "Show me the first 20 lines of README.md.",
        {"calls": [call("read_file", path="README.md", max_lines=20)]}),
    row("tc-single-09", "single", ["send_message", "create_event"], "Send Meera the exact text 'the build is green'.",
        {"calls": [call("send_message", to="Meera", text="the build is green")], "loose": {"text": "ci"}}),
    row("tc-single-10", "single", ["get_weather", "translate"], "Give me the temperature in Delhi in fahrenheit.",
        {"calls": [call("get_weather", city="Delhi", unit="fahrenheit")]}),
    # Indic text inside arguments
    row("tc-indic-01", "indic_args", ["get_weather", "translate"], "चेन्नई का मौसम बताओ, सेल्सियस में।",
        {"calls": [call("get_weather", city=anyof("चेन्नई", "Chennai"), unit="celsius")], "loose": {"city": "ci"}}),
    row("tc-indic-02", "indic_args", ["translate", "calculate"], "Translate 'कृपया दरवाज़ा बंद करें' into English.",
        {"calls": [call("translate", text="कृपया दरवाज़ा बंद करें", target_language="English")],
         "loose": {"target_language": "ci"}}),
    row("tc-indic-03", "indic_args", ["send_message", "set_alarm"], "ராமுவுக்கு 'நாளை சந்திப்போம்' என்று செய்தி அனுப்பு.",
        {"calls": [call("send_message", to=anyof("ராமு", "ராமுவுக்கு"), text="நாளை சந்திப்போம்")]}),
    row("tc-indic-04", "indic_args", ["create_event", "get_weather"], "ಯುಗಾದಿ ಹಬ್ಬ ಎಂಬ ಕಾರ್ಯಕ್ರಮವನ್ನು 2027-03-30 ರಂದು ರಚಿಸಿ.",
        {"calls": [call("create_event", title=anyof("ಯುಗಾದಿ ಹಬ್ಬ", "ಯುಗಾದಿ"), date="2027-03-30")]}),
    # several calls in one answer (order does not matter)
    row("tc-multi-01", "multi", ["get_weather", "set_alarm"], "Weather in Mumbai and in Kolkata, both in celsius.",
        {"calls": [call("get_weather", city="Mumbai", unit="celsius"), call("get_weather", city="Kolkata", unit="celsius")]}),
    row("tc-multi-02", "multi", ["get_weather", "set_alarm"], "Set an alarm for 07:00 called run, and tell me the weather in Hyderabad.",
        {"calls": [call("set_alarm", time="07:00", label="run"), call("get_weather", city="Hyderabad")]}),
    row("tc-multi-03", "multi", ["read_file", "run_tests"], "Read setup.cfg and also run the tests in tests/.",
        {"calls": [call("read_file", path="setup.cfg"), call("run_tests", path="tests/")]}),
    # right tool among close ones
    row("tc-pick-01", "pick", ["read_file", "search_files", "run_tests"], "Which files in src match *.py?",
        {"calls": [call("search_files", pattern="*.py", directory="src")]}),
    row("tc-pick-02", "pick", ["calculate", "convert_currency", "translate"], "Convert 5000 INR to USD.",
        {"calls": [call("convert_currency", amount=5000, from_currency="INR", to_currency="USD")]}),
    row("tc-pick-03", "pick", ["send_message", "create_event", "set_alarm"], "Schedule 'Lunch' on 2026-11-30.",
        {"calls": [call("create_event", title="Lunch", date="2026-11-30")]}),
    row("tc-pick-04", "pick", ["translate", "calculate", "read_file"], "Say 'good morning' in Tamil.",
        {"calls": [call("translate", text="good morning", target_language="Tamil")],
         "loose": {"target_language": "ci", "text": "ci"}}),
    # no tool needed
    row("tc-none-01", "no_call", ["get_weather", "calculate"], "Hi! How are you today?", {"calls": []}),
    row("tc-none-02", "no_call", ["calculate", "read_file"], "Explain in one sentence what a hash map is.",
        {"calls": [], "must_contain_any": ["key", "hash"]}),
    row("tc-none-03", "no_call", ["get_weather", "set_alarm"], "Why is the sky blue?",
        {"calls": [], "must_contain_any": ["scatter", "rayleigh", "wavelength"]}),
    row("tc-none-04", "no_call", ["translate", "send_message"], "भारत की राजधानी क्या है?",
        {"calls": [], "must_contain_any": ["दिल्ली", "Delhi"]}),
    row("tc-none-05", "no_call", ["run_tests", "read_file"], "What does the word 'idempotent' mean?",
        {"calls": [], "must_contain_any": ["same", "repeat", "again", "multiple times"]}),
    # a required argument is missing: ask, do not call
    row("tc-ask-01", "missing_arg", ["set_alarm", "get_weather"], "Set an alarm for me.", {"calls": [], "must_ask": True}),
    row("tc-ask-02", "missing_arg", ["send_message", "create_event"], "Send a message to Karthik.", {"calls": [], "must_ask": True}),
    row("tc-ask-03", "missing_arg", ["convert_currency", "calculate"], "Convert some money to yen.", {"calls": [], "must_ask": True}),
    # the tool result is already in the transcript: answer from it, no new call
    row("tc-result-01", "after_result", ["get_weather", "set_alarm"], "Weather in Pune in celsius?",
        {"calls": [], "must_contain": ["27"]},
        [{"role": "assistant", "tool_calls": [call("get_weather", city="Pune", unit="celsius")]},
         {"role": "tool", "content": "{\"temperature\": 27, \"unit\": \"celsius\", \"sky\": \"clear\"}"}]),
    row("tc-result-02", "after_result", ["calculate", "convert_currency"], "What is 12 * 12?",
        {"calls": [], "must_contain": ["144"]},
        [{"role": "assistant", "tool_calls": [call("calculate", expression="12 * 12")]},
         {"role": "tool", "content": "144"}]),
    row("tc-result-03", "after_result", ["search_files", "read_file"], "List the .md files in docs.",
        {"calls": [], "must_contain": ["guide.md", "faq.md"]},
        [{"role": "assistant", "tool_calls": [call("search_files", pattern="*.md", directory="docs")]},
         {"role": "tool", "content": "[\"docs/guide.md\", \"docs/faq.md\"]"}]),
]


# Rows with Indic text carry `review`: hi and kn are reviewed by a native speaker, ta is not yet.
INDIC_REVIEW = {
    "tc-indic-01": True, "tc-indic-02": True, "tc-none-04": True, "tc-indic-04": True, "tc-indic-03": False,
}
for _r in ROWS:
    if _r["id"] in INDIC_REVIEW:
        _r["review"] = ("wording reviewed by a native speaker" if INDIC_REVIEW[_r["id"]]
                        else "wording not reviewed by a native speaker")


def main() -> None:
    out = Path(__file__).with_name("toolcall_v1.jsonl")
    ids = [r["id"] for r in ROWS]
    assert len(ids) == len(set(ids))
    with out.open("w", encoding="utf-8", newline="\n") as f:
        for r in ROWS:
            f.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
    print(f"wrote {len(ROWS)} rows to {out}")


if __name__ == "__main__":
    main()
