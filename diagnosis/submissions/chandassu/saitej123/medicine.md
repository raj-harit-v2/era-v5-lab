# Medicine sheet: chandassu (saitej123)

Source: `BodduSriPavan111/chandassu`. 4,651 Telugu padyams. The poem is `raw_padyam_text`. Licence on the dataset card: MIT.

## What was read

Each poem was read in full. The sheet below is only the rows a reader would mark. Two things show up again and again. Everything else was left alone on purpose.

Left alone:

- ZWNJ (U+200C) and ZWJ (U+200D). They are in the writing. 1,014 poems use them. They are not a disease.
- The hyphen in Andhranaayaka (`స్థల- చతురానన`) and the danda `।` in Laavanya. Those mark the yati, the pause in the line. A Telugu reader expects them.
- `n_aksharaalu_score` is `-1` on every jaathi and vupajaathi row (3,026). `prasa_score` is `-1` on every vupajaathi row (2,343). The count matches the class. The score is not used for that metre. It is not a hole in the poem.
- A finished verse such as Narayana mattebhamu `1956` (`సర్వంబున్‌ వసియించు నీతనువునన్‌…`) is a whole padyam. A low yati score from the dataset's own meter checker is not, by itself, a broken line.

## Medicine 1

1. **Disease:** B1, 1,134 poems, every one of them in the Vemana satakam. The line break was saved as the letters `_x000D_` (an exported carriage return) and then the paada. Examples: `3094` (next line `నీళ్ళ లోన మొసలి నిగిడి యేనుఁగుఁ బట్టు`), `3095` (next line `కులము లో నొకండు గుణవంతు డుండెనా`), `3096` (next line `పంది పిల్ల లీనుఁ బదియు నైదింటిని`). Each of these has the token four times, once before each paada. The makutam is still the real one: `విశ్వదాభిరామ వినర వేమ.`
2. **Medicine:** replace each `_x000D_` with a newline.
```python
def medicine_b1(text: str) -> str:
    return text.replace("_x000D_", "\n")
```
3. **Action:** fix the text.
4. **Harm test:** 200 padyams with no `_x000D_` — 0 changed (0.0%), 0 dropped (0.0%). Pass (<= 1%).
5. **Side effects:** a line that is quoting the characters `_x000D_` on purpose would change. In this set the token is only the Vemana export.

## Medicine 2

1. **Disease:** C3, 23 poems. The words are gone and dots stand in the line. The reader cannot finish the paada. Examples: `2891` (Sundariimani, utpalamala, the poem opens on `... ... ...` and the only clear close is `దైన్యము లెంచుదు సుందరీమణీ!`), `1754` (Madanagopala, seesamu, `దనుగుబ్బలగుమ్ము పద్మగంధి... ... ...`), `1771` (Madanagopala, teytageethi, `యుచున్నది మీ పాదసేవకొరకు... ... ...`). `1783` is dots from the first character.
2. **Medicine:** if the text contains `...` or `…`, drop the document. The missing words cannot be put back.
```python
def medicine_c3(text: str) -> str | None:
    if "..." in text or "…" in text:
        return None
    return text
```
3. **Action:** drop the document.
4. **Harm test:** the same 200 whole padyams — 0 changed (0.0%), 0 dropped (0.0%). Pass (<= 1%).
5. **Side effects:** a poem that uses three dots as a real pause, not as a hole, would be dropped. In this set the dots replace missing aksharas. The 23 rows are in Sundariimani, Venkateswara, Madanagopala, and Taadimallaraajagopaala.

One more row, not a medicine (it happens once): `2808`, Sumathi kandamu, the makutam is `సుమతీ!73`. The digits sit on the poem. Verdict in the sheet is fix.
