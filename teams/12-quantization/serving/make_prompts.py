"""Write the 100 fixed serving prompts (prompts_v1.jsonl) and their tool schemas (tools_v1.json).

    python teams/12-quantization/serving/make_prompts.py        # rewrites both files next to this script

Rows: {"id", "category", "lang", "effort", "messages", "tools" (names in tools_v1.json, or null), "expect"}.
  chat         25  no tools; any answer. Checks content and no marker in content.
  reason       25  arithmetic with one integer answer, effort 1k / 4k / 16k. Checks the reasoning field.
  tool         30  tools offered, the question needs one. Checks tool_calls: name, JSON arguments, required keys.
  tool_result  10  a tool call and its result already in the history. Checks the final content.
  no_tool      10  all tools offered, the question needs none. Checks that no tool is called.
expect.answer is informative (does the stand-in get it right), not a pass condition of the serving check.
Languages: en, hi, ta, te, kn, bn, mr. The prompts are our own (not from an eval set), so serve_check may store
the responses.
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
EFFORTS = ("1k", "4k", "16k")


def _fn(name, desc, props, required):
    return {"type": "function", "function": {"name": name, "description": desc, "parameters": {
        "type": "object", "properties": props, "required": required}}}


TOOLS = {
    "get_weather": _fn("get_weather", "Current weather for a city.", {
        "city": {"type": "string", "description": "City name"},
        "unit": {"type": "string", "enum": ["c", "f"], "description": "Temperature unit"}}, ["city"]),
    "calculator": _fn("calculator", "Evaluate an arithmetic expression exactly.", {
        "expression": {"type": "string", "description": "For example (2+3)*4"}}, ["expression"]),
    "search_web": _fn("search_web", "Search the web and return result titles and links.", {
        "query": {"type": "string"},
        "max_results": {"type": "integer", "minimum": 1, "maximum": 10}}, ["query"]),
    "read_file": _fn("read_file", "Read a text file from the workspace.", {
        "path": {"type": "string", "description": "Relative or absolute path"}}, ["path"]),
    "convert_currency": _fn("convert_currency", "Convert an amount between currencies at today's rate.", {
        "amount": {"type": "number"},
        "from_currency": {"type": "string", "description": "ISO code, for example USD"},
        "to_currency": {"type": "string", "description": "ISO code, for example INR"}},
        ["amount", "from_currency", "to_currency"]),
    "get_time": _fn("get_time", "Current local time in an IANA time zone.", {
        "timezone": {"type": "string", "description": "For example Asia/Kolkata"}}, ["timezone"]),
}
ALL = list(TOOLS)

CHAT = [
    ("en", "Explain what a mixture-of-experts language model is in two sentences."),
    ("en", "Write a haiku about monsoon rain."),
    ("en", "Give three tips for writing clear commit messages."),
    ("en", "What is the capital of Australia?"),
    ("en", "Summarize the plot of Romeo and Juliet in one sentence."),
    ("en", "Translate 'Good morning, how are you?' into Hindi."),
    ("en", "List the planets of the solar system in order from the Sun."),
    ("en", "What does the HTTP status code 404 mean?"),
    ("en", "Suggest a name for a cat that loves cardboard boxes."),
    ("en", "Explain the difference between a list and a tuple in Python."),
    ("hi", "भारत की राजधानी क्या है?"),
    ("hi", "मुझे एक छोटी कहानी सुनाइए जिसमें एक तोता हो।"),
    ("hi", "समुद्र तल पर पानी किस तापमान पर उबलता है?"),
    ("hi", "योग के तीन लाभ बताइए।"),
    ("ta", "தமிழ்நாட்டின் தலைநகரம் எது?"),
    ("ta", "மழையைப் பற்றி ஒரு சிறிய கவிதை எழுதுங்கள்."),
    ("ta", "திருக்குறளை எழுதியவர் யார்?"),
    ("te", "తెలంగాణ రాజధాని ఏది?"),
    ("te", "ఆరోగ్యంగా ఉండటానికి మూడు చిట్కాలు చెప్పండి."),
    ("te", "సూర్యుడు ఏ దిశలో ఉదయిస్తాడు?"),
    ("kn", "ಕರ್ನಾಟಕದ ರಾಜಧಾನಿ ಯಾವುದು?"),
    ("kn", "ಕನ್ನಡದಲ್ಲಿ ಒಂದು ಗಾದೆ ಹೇಳಿ."),
    ("bn", "পশ্চিমবঙ্গের রাজধানী কী?"),
    ("bn", "রবীন্দ্রনাথ ঠাকুর কে ছিলেন?"),
    ("mr", "महाराष्ट्राची राजधानी कोणती?"),
]

REASON = [
    ("en", "What is 17 × 23?", 391),
    ("en", "A train travels at 60 km/h for 2.5 hours. How many kilometres does it travel?", 150),
    ("en", "If 3 pencils cost 12 rupees, how many rupees do 7 pencils cost?", 28),
    ("en", "What is the sum of the integers from 1 to 20?", 210),
    ("en", "A rectangle is 8 cm long and 5 cm wide. What is its area in square centimetres?", 40),
    ("en", "How many minutes are there in 3.5 hours?", 210),
    ("en", "What is 15% of 240?", 36),
    ("en", "Ravi has 45 marbles, gives away 17, then buys 12 more. How many marbles does he have now?", 40),
    ("en", "What is the next number in the sequence 2, 6, 12, 20, 30, ...?", 42),
    ("en", "What is 2 to the power of 10?", 1024),
    ("en", "After a 20% discount a shirt costs 800 rupees. What was the original price in rupees?", 1000),
    ("en", "How many days are there in a leap year?", 366),
    ("en", "What is the least common multiple of 4, 6 and 10?", 60),
    ("en", "If x + 7 = 19, what is 3x?", 36),
    ("en", "What is 144 divided by 12, plus 9?", 21),
    ("en", "A bus has 40 seats and three quarters of them are filled. How many seats are empty?", 10),
    ("en", "How many edges does a cube have?", 12),
    ("en", "What is the greatest common divisor of 84 and 126?", 42),
    ("en", "What is the remainder when 100 is divided by 7?", 2),
    ("hi", "एक दुकान में 5 पेन 35 रुपये के हैं। 9 पेन कितने रुपये के होंगे?", 63),
    ("hi", "1 से 10 तक की सभी सम संख्याओं का योग कितना है?", 30),
    ("ta", "ஒரு வகுப்பில் 32 மாணவர்கள் உள்ளனர். அவர்களில் 3/8 பேர் பெண்கள். எத்தனை பெண்கள்?", 12),
    ("te", "ఒక పుస్తకం ధర 120 రూపాయలు. 4 పుస్తకాల ధర ఎంత?", 480),
    ("kn", "ಒಂದು ವಾರದಲ್ಲಿ ಎಷ್ಟು ಗಂಟೆಗಳಿವೆ?", 168),
    ("bn", "৮ এবং ৭ এর গুণফল কত?", 56),
]

# (lang, prompt, expected tool, offered tools)
TOOL = [
    ("en", "What's the weather in Bengaluru right now?", "get_weather", ["get_weather", "get_time"]),
    ("en", "Is it raining in Mumbai today?", "get_weather", ["get_weather", "search_web"]),
    ("en", "Tell me the temperature in Delhi in Fahrenheit.", "get_weather", ["get_weather", "calculator"]),
    ("hi", "चेन्नई में आज मौसम कैसा है?", "get_weather", ["get_weather", "get_time"]),
    ("ta", "மதுரையில் இன்று வானிலை எப்படி உள்ளது?", "get_weather", ["get_weather", "search_web"]),
    ("te", "హైదరాబాద్‌లో ఇప్పుడు వాతావరణం ఎలా ఉంది?", "get_weather", ALL),
    ("en", "Use the calculator to compute 12345 * 6789.", "calculator", ["calculator", "search_web"]),
    ("en", "What is the square root of 98765.4321? Use a tool.", "calculator", ["calculator", "get_time"]),
    ("en", "Compute (17.5 + 22.25) / 3.1 with the calculator.", "calculator", ALL),
    ("en", "Calculate 2^31 - 1 exactly.", "calculator", ["calculator", "read_file"]),
    ("hi", "कैलकुलेटर से 987 × 654 निकालिए।", "calculator", ["calculator", "get_weather"]),
    ("kn", "ಕ್ಯಾಲ್ಕುಲೇಟರ್ ಬಳಸಿ 4521 ಅನ್ನು 37 ರಿಂದ ಭಾಗಿಸಿ.", "calculator", ["calculator", "convert_currency"]),
    ("en", "Search the web for the latest vLLM release notes.", "search_web", ["search_web", "read_file"]),
    ("en", "Find recent news about the Chandrayaan mission.", "search_web", ["search_web", "get_time"]),
    ("en", "Look up who won the most recent FIFA World Cup.", "search_web", ALL),
    ("en", "Search for papers on load balancing in mixture-of-experts models.", "search_web", ["search_web", "calculator"]),
    ("bn", "ওয়েবে খুঁজে দেখুন: কলকাতার সেরা মিষ্টির দোকান।", "search_web", ["search_web", "get_weather"]),
    ("en", "Read the file src/main.py and tell me what it does.", "read_file", ["read_file", "search_web"]),
    ("en", "Open README.md and summarize it.", "read_file", ["read_file", "calculator"]),
    ("en", "Show me the contents of config/settings.yaml.", "read_file", ALL),
    ("en", "What's in the file /etc/hostname?", "read_file", ["read_file", "get_time"]),
    ("ta", "tests/test_utils.py கோப்பைப் படித்துச் சொல்லுங்கள்.", "read_file", ["read_file", "search_web"]),
    ("en", "Convert 250 US dollars to Indian rupees.", "convert_currency", ["convert_currency", "calculator"]),
    ("en", "How much is 1000 INR in euros?", "convert_currency", ALL),
    ("en", "Convert 75.5 British pounds to Japanese yen.", "convert_currency", ["convert_currency", "search_web"]),
    ("hi", "500 यूरो कितने भारतीय रुपये होते हैं?", "convert_currency", ["convert_currency", "get_weather"]),
    ("en", "What time is it in Tokyo?", "get_time", ["get_time", "get_weather"]),
    ("en", "What's the current time in the Asia/Kolkata time zone?", "get_time", ALL),
    ("en", "Tell me the time in New York.", "get_time", ["get_time", "search_web"]),
    ("te", "లండన్‌లో ఇప్పుడు సమయం ఎంత?", "get_time", ["get_time", "calculator"]),
]

# (lang, user prompt, tool, arguments, tool result, expected substring in the answer or None)
TOOL_RESULT = [
    ("en", "What's the weather in Bengaluru?", "get_weather", {"city": "Bengaluru"},
     {"city": "Bengaluru", "temp_c": 24, "condition": "light rain"}, "24"),
    ("en", "Use the calculator to compute 12345 * 6789.", "calculator", {"expression": "12345 * 6789"},
     "83810205", "83810205"),
    ("en", "Convert 250 US dollars to Indian rupees.", "convert_currency",
     {"amount": 250, "from_currency": "USD", "to_currency": "INR"},
     {"amount": 250, "from": "USD", "to": "INR", "result": 20875.0}, "20875"),
    ("en", "What time is it in Tokyo?", "get_time", {"timezone": "Asia/Tokyo"},
     {"timezone": "Asia/Tokyo", "time": "14:05"}, "14:05"),
    ("en", "Open README.md and summarize it.", "read_file", {"path": "README.md"},
     "# Demo\nA tiny command-line tool that prints today's date in ISO format.\n", None),
    ("en", "Search the web for the latest vLLM release notes.", "search_web", {"query": "vLLM release notes"},
     [{"title": "vLLM v0.33.0 release notes", "url": "https://example.com/vllm-0.33.0"}], "0.33"),
    ("hi", "चेन्नई में आज मौसम कैसा है?", "get_weather", {"city": "Chennai"},
     {"city": "Chennai", "temp_c": 31, "condition": "humid"}, "31"),
    ("ta", "999 × 111 ஐக் கணக்கிடுங்கள்.", "calculator", {"expression": "999 * 111"}, "110889", "110889"),
    ("te", "లండన్‌లో ఇప్పుడు సమయం ఎంత?", "get_time", {"timezone": "Europe/London"},
     {"timezone": "Europe/London", "time": "08:30"}, "8:30"),
    ("en", "What's the weather in Delhi?", "get_weather", {"city": "Delhi"}, {"error": "service unavailable"}, None),
]

NO_TOOL = [
    ("en", "Say hello in Tamil."),
    ("en", "What is 2 + 2?"),
    ("en", "Write one sentence about the ocean."),
    ("en", "What is the opposite of the word 'ancient'?"),
    ("en", "Name one primary colour."),
    ("en", "Spell the word 'necessary'."),
    ("en", "Who wrote Hamlet?"),
    ("hi", "'धन्यवाद' को अंग्रेज़ी में क्या कहते हैं?"),
    ("ta", "'வணக்கம்' என்பதன் பொருள் என்ன?"),
    ("te", "ఒక రంగు పేరు చెప్పండి."),
]


def _user(text):
    return [{"role": "user", "content": text}]


def rows():
    out = []
    for i, (lang, text) in enumerate(CHAT, 1):
        out.append({"id": f"chat-{i:02d}", "category": "chat", "lang": lang, "effort": None,
                    "messages": _user(text), "tools": None, "expect": {"content": True}})
    for i, (lang, text, ans) in enumerate(REASON, 1):
        out.append({"id": f"reason-{i:02d}", "category": "reason", "lang": lang, "effort": EFFORTS[(i - 1) % 3],
                    "messages": _user(text), "tools": None,
                    "expect": {"reasoning": True, "content": True, "answer": str(ans)}})
    for i, (lang, text, tool, offered) in enumerate(TOOL, 1):
        out.append({"id": f"tool-{i:02d}", "category": "tool", "lang": lang, "effort": None,
                    "messages": _user(text), "tools": offered, "expect": {"tool": tool}})
    for i, (lang, text, tool, args, result, ans) in enumerate(TOOL_RESULT, 1):
        call_id = f"call_{i:02d}"
        msgs = _user(text) + [
            {"role": "assistant", "content": None, "tool_calls": [
                {"id": call_id, "type": "function",
                 "function": {"name": tool, "arguments": json.dumps(args, ensure_ascii=False)}}]},
            {"role": "tool", "tool_call_id": call_id,
             "content": result if isinstance(result, str) else json.dumps(result, ensure_ascii=False)}]
        expect = {"content": True, "no_tool": True}
        if ans:
            expect["answer_substring"] = ans
        out.append({"id": f"tool_result-{i:02d}", "category": "tool_result", "lang": lang, "effort": None,
                    "messages": msgs, "tools": [tool], "expect": expect})
    for i, (lang, text) in enumerate(NO_TOOL, 1):
        out.append({"id": f"no_tool-{i:02d}", "category": "no_tool", "lang": lang, "effort": None,
                    "messages": _user(text), "tools": ALL, "expect": {"content": True, "no_tool": True}})
    return out


def main():
    data = rows()
    assert len(data) == 100 and len({r["id"] for r in data}) == 100
    for r in data:
        assert all(t in TOOLS for t in r["tools"] or [])
    with open(HERE / "prompts_v1.jsonl", "w", encoding="utf-8") as f:
        for r in data:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(HERE / "tools_v1.json", "w", encoding="utf-8") as f:
        json.dump(TOOLS, f, ensure_ascii=False, indent=1)
        f.write("\n")
    print(f"wrote {len(data)} prompts and {len(TOOLS)} tools")


if __name__ == "__main__":
    main()
