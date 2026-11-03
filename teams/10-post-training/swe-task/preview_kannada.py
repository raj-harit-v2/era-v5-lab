"""Generate an offline Kannada browser review from actual render/parse output."""

from __future__ import annotations

import argparse
import base64
from html import escape
import importlib.util
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


RENDER = load_module("kannada_preview_renderer", HERE.parent / "chat-format" / "render.py")
EXAMPLES = load_module("kannada_preview_examples", HERE / "kannada_examples.py")


def code_points(text: str) -> str:
    return " ".join(f"U+{ord(ch):04X}" for ch in text)


def font_resources() -> tuple[list[dict], str]:
    fonts, rules = [], []
    for name, path in (
        ("Noto Sans Kannada", "/usr/share/fonts/truetype/noto/NotoSansKannada-Regular.ttf"),
        ("Noto Serif Kannada", "/usr/share/fonts/truetype/noto/NotoSerifKannada-Regular.ttf"),
        ("Lohit Kannada", "/usr/share/fonts/truetype/lohit-kannada/Lohit-Kannada.ttf"),
    ):
        if not Path(path).is_file():
            continue
        contents = Path(path).read_bytes()
        alias = f"review-font-{len(fonts)}"
        encoded = base64.b64encode(contents).decode("ascii")
        fonts.append({"name": name, "alias": alias, "embedded": True})
        rules.append(f'@font-face{{font-family:"{alias}";font-weight:400;'
                     f'src:url(data:font/ttf;base64,{encoded}) format("truetype");}}')
    if not fonts:
        fonts.append({"name": "System font (unverified fallback)",
                      "alias": "Noto Sans Kannada", "embedded": False})
    return fonts, "\n".join(rules)


def generate_preview(output: Path) -> dict:
    rows, records = [], []
    for index, (label, source) in enumerate(EXAMPLES.CASES):
        messages = EXAMPLES.preservation_messages(source)
        outputs, transcripts = {}, {}
        for effort in EXAMPLES.EFFORTS:
            transcripts[effort] = RENDER.render(messages, effort=effort)
            outputs[effort] = RENDER.parse(transcripts[effort].encode("utf-8").decode("utf-8"))
        preserved = all(value == {"effort": effort, "messages": messages}
                        for effort, value in outputs.items())
        recovered = outputs["4k"]["messages"][1]["content"]
        records.append({"label": label, "input": source, "output": recovered,
                        "input_code_points": code_points(source),
                        "output_code_points": code_points(recovered),
                        "all_fields_preserved_at_all_efforts": preserved})
        rows.append(f'''<tr>
<th scope="row">{escape(label)}</th>
<td><span class="sample" lang="kn">{escape(source)}</span></td>
<td><span class="sample" lang="kn">{escape(recovered)}</span></td>
<td>{"PASS" if preserved else "FAIL"}</td>
<td><label>Visual review <select class="verdict" data-case="{index}">
<option value="pending">Not reviewed</option>
<option value="expected">Expected appearance</option>
<option value="unexpected">Unexpected appearance</option>
<option value="indistinguishable">No visible distinction in controls</option>
</select></label></td></tr>
<tr><td colspan="5"><details><summary>Code points and actual ChatML (4k)</summary>
<p>Input: <code>{code_points(source)}</code></p>
<p>Output: <code>{code_points(recovered)}</code></p>
<pre>{escape(transcripts["4k"])}</pre></details></td></tr>''')

    fonts, font_css = font_resources()
    data = {"cases": records, "fonts": fonts, "efforts": list(EXAMPLES.EFFORTS),
            "preview_version": 1, "meaning_of_pass": "Exact serialization preservation only"}
    serialized = json.dumps(data, ensure_ascii=True).replace("<", "\\u003c")
    options = "".join(f'<option value="{i}">{escape(font["name"])}</option>'
                      for i, font in enumerate(fonts))
    page = '''<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Kannada browser review — ind-kn-fw2</title>
<style>
FONT_CSS
:root{--sample-font:"INITIAL_FONT";color-scheme:light dark}
body{font-family:system-ui;margin:24px}main{max-width:1200px;margin:auto}
table{width:100%;border-collapse:collapse}td,th{text-align:left;padding:12px;
border-bottom:1px solid GrayText;vertical-align:top}th{font-weight:500}
.sample,pre{font-family:var(--sample-font),sans-serif;font-weight:400;
font-size:32px;line-height:2;white-space:pre-wrap;overflow-wrap:anywhere}
pre{font-size:20px}details,code{overflow-wrap:anywhere}
select,button,input,textarea{font:inherit;padding:8px;max-width:100%;box-sizing:border-box}
.controls{display:flex;flex-wrap:wrap;gap:16px;align-items:center}
textarea{display:block;width:100%;margin:12px 0}.table-wrap{overflow-x:auto}
@media(max-width:700px){body{margin:12px}.sample{font-size:26px}}
</style></head><body><main>
<h1>Kannada browser review</h1>
<p>PASS checks exact character preservation across every message field at all four
effort levels. Visual appearance is reviewed separately.</p>
<p>OnePlus is the sole ZWNJ fixture. The three RA rows are shaping controls;
different code points may look alike.</p>
<div class="controls"><label>Font <select id="font">FONT_OPTIONS</select></label>
<button id="download" type="button">Download visual review JSON</button></div>
<p id="font-state" role="status"></p>
<div class="table-wrap"><table><caption>Actual shared renderer output</caption>
<thead><tr><th>Case</th><th>Input</th><th>Recovered text</th>
<th>Preservation</th><th>Your visual review</th></tr></thead><tbody>
ROWS
</tbody></table></div>
<label>Review notes<textarea id="notes" rows="2"
placeholder="Describe unexpected shaping, differences, or indistinguishable controls."></textarea></label>
<p>Choose a verdict for each row, download the review, and capture a screenshot
showing the selected font and examples. No information is uploaded.</p>
<script type="application/json" id="review-data">REVIEW_DATA</script>
<script>
const data = JSON.parse(document.getElementById('review-data').textContent);
const picker = document.getElementById('font');
async function updateFont() {
  const font = data.fonts[Number(picker.value)];
  document.documentElement.style.setProperty('--sample-font', JSON.stringify(font.alias));
  const faces = await document.fonts.load('32px ' + JSON.stringify(font.alias));
  document.getElementById('font-state').textContent = font.embedded
    ? (faces.length ? 'Embedded font loaded: ' + font.name : 'Embedded font did not load.')
    : 'System fallback: actual font availability is unverified.';
}
picker.addEventListener('change', () => {
  document.querySelectorAll('.verdict').forEach(select => { select.value = 'pending'; });
  updateFont().catch(error => {
    document.getElementById('font-state').textContent = 'Font load failed: ' + error.message;
  });
});
document.getElementById('download').addEventListener('click', async () => {
  const font = data.fonts[Number(picker.value)];
  await document.fonts.ready;
  const review = {
    ...data, reviewed_at: new Date().toISOString(), browser_user_agent: navigator.userAgent,
    selected_font: font,
    embedded_font_loaded: font.embedded && document.fonts.check('32px ' + JSON.stringify(font.alias)),
    notes: document.getElementById('notes').value,
    cases: data.cases.map((item, index) => ({...item,
      visual_verdict: document.querySelector('.verdict[data-case="' + index + '"]').value}))
  };
  const url = URL.createObjectURL(new Blob([JSON.stringify(review, null, 2) + '\\n'],
    {type: 'application/json'}));
  const link = document.createElement('a');
  link.href = url; link.download = 'kannada_visual_review.json'; link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
});
updateFont().catch(error => {
  document.getElementById('font-state').textContent = 'Font load failed: ' + error.message;
});
</script></main></body></html>
'''
    # Replace only template fields; no user text is interpreted as markup or script.
    replacements = {"FONT_CSS": font_css, "INITIAL_FONT": fonts[0]["alias"],
                    "FONT_OPTIONS": options, "ROWS": "\n".join(rows), "REVIEW_DATA": serialized}
    page = re.sub(r"FONT_CSS|INITIAL_FONT|FONT_OPTIONS|ROWS|REVIEW_DATA",
                  lambda match: replacements[match.group()], page)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(page, encoding="utf-8")
    return {"preview": output.resolve().as_uri(), "cases": len(records),
            "all_fields_preserved_at_all_efforts": all(
                row["all_fields_preserved_at_all_efforts"] for row in records),
            "visual_review": "pending", "embedded_fonts": [font["name"] for font in fonts if font["embedded"]]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("/tmp/g10-kannada-preview.html"))
    args = parser.parse_args()
    print(json.dumps(generate_preview(args.output), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
