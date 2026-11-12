# Medicine sheet: en-nemotroncc-synth (AJJAPUSIVA)

All 500 source documents have full-read labels: **401 clean, 93 fix and 6 drop**. Each label includes the document ID, verdict, disease evidence and a concise review note. Source checks and factual corrections are distinguished from the repository's disease taxonomy.

| Code | Label occurrences |
|---|---:|
| B4 | 2 |
| B5 | 1 |
| C1 | 48 |
| C3 | 34 |
| C4 | 7 |
| C5 | 2 |
| F1 | 7 |
| F3 | 3 |

Counts are document occurrences; a document can have multiple codes. A clean label means no listed disease was identified, rather than a guarantee that every source claim is correct.

The candidates below cover the four codes occurring more than five times: C1, C3, C4 and F1, plus bounded B4, C5 and F3 decisions. Exact source-ID and SHA-256 guards keep document-specific operations confined to reviewed examples. The original Parquet and local comparison artifacts are outside this submission.

## Validation and gold-set results

All seven medicines and their combined execution pass Data A's runner:

| Evaluation set | Documents | Changed | Dropped | Errors | Result |
|---|---:|---:|---:|---:|---|
| Data A published en-nemotroncc-synth snapshot | 96 | 0 | 0 | 0 | PASS |
| Local current two-reader candidate set | 326 | 0 | 0 | 0 | PASS |

The first row uses [Data A PR140's published gold IDs](https://github.com/patilvijay23/era-v5-lab/blob/1086dd64c65aff53c825a3bc2d12c3b996472da1/teams/01-data-a/gold/en-nemotroncc-synth_gold.csv). The second is a separate local calculation from PR68 commit7ebcc8b and PR5 commit9558ec0; it is not Data A's published refresh. Each set requires two distinct full/clean readers with no contrary fix/drop vote. All96 published IDs remain eligible in the current sheets.

Runner source: [Data A PR140, commit1086dd64](https://github.com/patilvijay23/era-v5-lab/blob/1086dd64c65aff53c825a3bc2d12c3b996472da1/teams/01-data-a/tools/harm_test.py). Its small-set limit is `max(1, floor(1% × N))`:1 affected document for96;3 for326. Zero affected documents also satisfies a strict1% limit. These are measured gold checks, distinct from local sample controls.

- All500 CSV IDs match the source pack; every read value is full. Schema, single-line notes, evidence and verdict/code consistency checked.
- Each Python block is independently executable and uses Data A's `medicine_<code>(doc)` interface. Drops use `("drop", "")`.
- Positive sample controls: C1 changes3 and drops1; C3 creates3 contextual outputs; C4 changes3; F1 changes3; B4 changes1; C5 drops2; F3 drops3. Combined output matches the previously checked medicine algorithms on all500 source inputs.
- Changed-input and unrelated-ID guards, idempotence, split reconstruction, contextual provenance and Q&A preservation checked. The original Parquet checksum is unchanged; no cleaned full-pack export is included.
- The independent modern Swift example and six blackjack settlement cases passed local checks; RPG fragments were checked against documentation.

Exact-ID/hash candidates are intentionally confined to reviewed examples. A gold pass does not establish general cleaning effectiveness on unseen documents.

## Runner interface

Pass this file directly to Data A's runner; no external adapter or extra submitted file is needed. Download the gold CSV and runner tools outside this submission folder and supply the original pack:

```bash
python -I /path/to/data-a/tools/harm_test.py \
  --pack /path/to/en-nemotroncc-synth.parquet \
  --gold /path/to/en-nemotroncc-synth_gold.csv \
  --rules diagnosis/submissions/en-nemotroncc-synth/AJJAPUSIVA/medicine.md \
  --rule all --report /path/to/local/harm-report.json
```

## Medicine 1 — C1: reviewed boilerplate spans

1. **Disease:** C1, 48 labelled occurrences. This candidate removes three exact spans and excludes one recommendation-only record:
   - `3cd12d535137ab2f`: `The Awesomer is reader-supported. When you buy through links on our si` at offset 0.
   - `701cacaccdb06931`: `Citation Disclaimer: These citations have been automatically generated` at offset 45.
   - `76b4036d49000599`: `Enter your email address to follow this blog and receive notifications` at offset 2211.
2. **Medicine:** remove the reviewed span only when its document ID and source hash match.
3. **Action:** fix the three spans; drop only recommendation-only record `beb73cd7cb9e50fd` (source row192), which has no main article. Other reviewed exclusions remain in their own code sections.
4. **Harm test:** Data A runner:0 of96 published gold documents changed or dropped; PASS. Separate local two-reader check:0 of326 changed or dropped; PASS.
5. **Side effects:** a disclaimer or subscription passage can be substantive in another context. These offsets must not be generalized to other documents.

```python
import hashlib

def _source_hash(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def _c1_text(doc_id, text):
    spans = {'3cd12d535137ab2f': ('3cd12d535137ab2f29d7b8a38461d7c3e35610d67581e5e57df0999e49918a80', 0, 180), '701cacaccdb06931': ('701cacaccdb06931da002988266d4a60dc9f4b9152b3a2462d8d8ac262dd0939', 45, 287), '76b4036d49000599': ('76b4036d49000599952ad548de4cdee33afdeb27b5df3e12b44067c012a1b9be', 2211, 2304)}
    rule = spans.get(doc_id)
    if rule is None or _source_hash(text) != rule[0]:
        return text
    return text[:rule[1]] + text[rule[2]:]

def medicine_c1(doc):
    excluded = {'beb73cd7cb9e50fd': 'beb73cd7cb9e50fda82be15af9d6453327cb697656d1b9c499dd6642c7d1593c'}
    if excluded.get(doc['doc_id']) == _source_hash(doc['text']):
        return ('drop', '')
    return _c1_text(doc['doc_id'], doc['text'])
```


## Medicine 2 — C3: contextual boundary reconstruction

1. **Disease:** C3, 34 labelled occurrences. Three sentence/verse continuation pairs:
   - `a147d6925833c136` → `fe0100ca641983cc`: “great was his” → “desire to win”.
   - `ee6655c72b3799da` → `89a8e620955b1040`: “Thus to behold the day” → “Which sees the beauteous Kriemhild”.
   - `84649d75dd11ae14` → `bca8eefdcfb28646`: “over the grassy” → “plain”.
2. **Medicine:** join the two reviewed article bodies with a separator, retaining both source IDs and each generated Q&A separately. The self-contained runner interface embeds the three exact reviewed continuations and serializes the existing contextual result as JSON. Both original source hashes must match. Other section-level and internal-omission classifications remain identified by their evidence in the label sheet; this candidate covers only the explicit continuation pairs above.
3. **Action:** return a derived contextual record for each of the three left-source IDs; retain the original records. JSON preserves body, both source IDs and separate Q&A. This is a contextual output contract, not a plain-prose concatenation or a general adjacency rule.
4. **Harm test:** Data A runner:0 of96 published gold documents changed or dropped; PASS. Separate local two-reader check:0 of326 changed or dropped; PASS.
5. **Side effects:** incorrect adjacency can merge unrelated text. Matching hashes do not establish that every neighbouring document should be joined; use only the listed pair identities.

```python
import hashlib

def _source_hash(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

import json

def _c3_pair(left_id, left, right_id, right):
    pairs = {('a147d6925833c136', 'fe0100ca641983cc'): ('a147d6925833c1363b68666dd55c988c133223eced68d43cacc02d70fb0691e0', 'fe0100ca641983ccb5cc98a67b4f0095934c3da502a4793cebc0be7051b7a224'), ('ee6655c72b3799da', '89a8e620955b1040'): ('ee6655c72b3799dacd976bf36a2a009c70cb5cefdd0c4b4396f78f6a16f558bf', '89a8e620955b10402627a2686535abdf7d821d542c0c0f52a6f37b37b766522d'), ('84649d75dd11ae14', 'bca8eefdcfb28646'): ('84649d75dd11ae14397b9cda227514f8de584f19c092a106ed119dd030373536', 'bca8eefdcfb2864690c54dd866aad2d3194135c99dbca1dab1eba7f3e79f0c2f')}
    expected = pairs.get((left_id, right_id))
    if expected != (_source_hash(left), _source_hash(right)):
        return None
    (left_body, left_marker, left_qa) = left.partition('\n\nQuestion:')
    (right_body, right_marker, right_qa) = right.partition('\n\nQuestion:')
    return {'source_ids': (left_id, right_id), 'body': left_body + ' ' + right_body, 'source_qa': (left_marker + left_qa, right_marker + right_qa)}

def medicine_c3(doc):
    continuations = {'a147d6925833c136': {'doc_id': 'fe0100ca641983cc', 'text': "desire to win the beautiful warrior-maiden for his wife, and he determined forthwith to try his fortune. Vainly did Siegfried seek to dissuade him, warning him of Brunhild's marvellous strength, but Gunther was firm. Moreover, by Hagen's counsel he urged Siegfried to go with him, and aid him in his venture; nor was Siegfried averse to sharing the danger; but first he drew a promise from Gunther that should his wooing be successful he would grant him in return the hand of his sister Kriemhild. Thereupon all was made ready for the voyage. Gunther would fain have taken with him thirty thousand of his stoutest warriors, but Siegfried warned him that force would avail him little against the stalwart Icelanders. Only in knightly fashion might Brunhild be won. So none went with them save Hagen and his brother Dankwart.\nThen Gunther and Siegfried betook themselves to Kriemhild, and made known their desire for rich court dresses for themselves and their companions. Kriemhild besought them not to undertake so dangerous a venture, for in her heart was a foreboding of evil; but when she saw it was of no avail she promised them the garments. In seven weeks she, with thirty of her women, prepared four splendid suits of silk and other rich stuffs adorned with costly furs and precious stones.\nMeanwhile, a ship had been laden with ample\nstore of viands and good Rhenish wine, and in this the four gallant knights now embarked with their steeds and armor. The sail was spread, the oars unlocked, and presently a fresh breeze bore them gayly down the Rhine and out into the open sea. But Kriemhild sat at her window watching, till at last they passed from sight and all the world was blotted out by her tears.\nSiegfried was the helmsman. On the twelfth day Iceland loomed before them, its lofty towers rising boldly from the mirror-like surface of the water. Now a sudden fancy seized Siegfried, and he told his comrades that not as a king's son would he appear in Iceland, but as vassal to King Gunther.\nAs the ship drew near the mighty castle of Isenstein they saw that the windows were filled with fair damsels; whereupon Siegfried asked the King which of them seemed to him the most beautiful. Gunther pointed out the tallest, a stately maiden clad all in purest white, who, Siegfried declared, was no other than Brunhild herself. But anon they all vanished from the windows and hastened to adorn themselves, that they might welcome the knights as was their due. Siegfried, in his part of vassal, led forth from the ship a horse bridled with gold, and held the stirrup for King Gunther to mount, and thereafter fetched his own horse and followed. The King's steed and his rider were magnificently decked with gold and\njewels, while behind rode Hagen and his brother Dankwart, clad all in sable and mounted on coal-black horses.\n\nQuestion: What was Siegfried's initial reaction to Gunther's plan? Answer: He tried to dissuade Gunther, warning him of Brunhild's strength\n\nQuestion: Who was the helmsman of the ship? Answer: Siegfried"}, 'ee6655c72b3799da': {'doc_id': '89a8e620955b1040', 'text': 'Which sees the beauteous Kriemhild\nEnthroned, with us to stay.\nWith praises of her virtue,\nLet all the country ring!\nNow shall our dear son Siegfried\nHenceforward reign as King."\nThe Betrayal\nHagen now bethought him of a plan whereby he might learn from Kriemhild the secret of Siegfried\'s vulnerable spot. Some of his men donned the garb of foreign messengers and appeared at the court, with a false challenge from Lendeger and Lendegast, the two Kings Siegfried had formerly vanquished. Again Gunther wavered in his purpose, at the thought of such treachery toward Siegfried, who had ever been his loyal friend, and of whose innocence moreover he felt sure; but Hagen\'s evil counsel once more prevailed, and the voice of his conscience was stifled.\nSiegfried soon perceived that something was amiss, and questioning Gunther as to the cause of his silence and gloom, drew from him that the Saxon and Danish Kings had sworn vengeance and were coming to lay waste the land. Whereupon he avowed himself ready and eager to meet Gunther\'s foes again in battle.\nJoyfully the hero made ready to depart, and Hagen, who had declared he would ride with them, went to take leave of Kriemhild. She besought him to be no longer angry with her for the words she had spoken to Brunhild, adding:\n"I have been punished enough for my folly in my lord Siegfried\'s displeasure!"\n"All is forgotten, fair lady," replied Hagen.\nNor is it save for love of King Siegfried that I go with him to this war. Should there be aught wherein it may avail, be sure he shall not lack my aid."\nThen was Kriemhild overjoyed and began therewith to sound the praises of her lord, dwelling on the love and loyalty he had ever shown toward Burgundy, and her fear lest through his reckless valor he might perchance hazard his life.\nWhereupon the wily Hagen answered: "Me-thinks there can be no danger to thy lord, since he is proof against all harm; yet tell me, I pray thee, if by any chance this be not so, that I may know how best to secure his safety."\nAt this, Kriemhild opened her heart to Hagen, and having full faith in his honesty and loyalty, confided to him how, when Siegfried had covered himself with the fat of the dragons, a linden leaf\nhad fallen between his shoulders, leaving one spot wherein he might come to harm. Thereupon she charged him anew to guard Siegfried well, lest in the heat of battle some foe should wound him from the rear. Overjoyed with the success of his strategy, Hagen counselled Kriemhild to mark this spot upon Siegfried\'s garment, that he might be the better able to shield him, and vowing to bide faithfully at his side in battle, took his leave.\n\nQuestion: Who is the main character in this text? Answer: Siegfried\n\nQuestion: Who are the two kings that supposedly challenge Gunther? Answer: Lendeger and Lendegast\n\nQuestion: What does Kriemhild fear might happen to Siegfried? Answer: Kriemhild fears that Siegfried might hazard his life due to his reckless valor'}, '84649d75dd11ae14': {'doc_id': 'bca8eefdcfb28646', 'text': 'plain, all the huntsmen following. Siegfried was the swifter; coming first to the spring he laid aside his sword, bow, and shield, and leaned his spear against a linden tree. Had he but drunk his fill now and taken up his arms once more, all Hagen\'s base scheming would have been undone, for none had dared to assail the hero armed and on his guard. But restraining his thirst, he waited till Gunther as sovereign prince should first have tasted of the spring. The King was third to reach the spot, the others lagging far behind, for upon them had come a sudden fear and trembling. Kneeling by the spring, he drank and thereafter stooped Siegfried also to dip up the clear cold water in his hand. Now was Hagen\'s time. Swiftly and noiselessly he bore away the hero\'s sword and bow. Ill indeed had it fared with the false knight had Siegfried marked his act; but little thought had he of such foul plot to reward his loyalty. Seizing the spear, Hagen hurled it with all his force at Siegfried\'s back, and so well had he marked the spot shown him by the cross Kriemhild had wrought that the weapon pierced deep into the breast of the hero and there remained. The shameful deed was done, and truly never was there crime on all the earth more foul than this.\nThe red blood spouted from the wound upon\nthe bow of the assassin, and he fled; for, though wounded to the death, yet was Siegfried terrible in his wrath. Springing to his feet, the hero sought his weapons, but they were gone; whereupon with shield aloft he rushed after Hagen and smote him therewith so powerfully that it burst asunder, scattering a shower of jewels all about. Hagen was stretched upon. the ground, and it seemed his end had come. But now the strength fled from Siegfried, a deadly pallor over-spread his countenance, and he sank upon the ground, his life blood staining the grass and flowers crimson. Then Hagen arose and drew nigh, his dark features lit with savage joy at the success of his evil work.\nGunther, too, approached, and after him came the rest of the huntsmen, and a deathly stillness reigned as all gazed upon the dying hero. At last Siegfried broke the silence. In noble wrath he spoke:\n"Ye dastards! to slay me from behind, and this as meed for all the service I have rendered you!"\nThe glance of the hero, wounded unto death, appalled the stoutest hearts; rough cheeks were wet with tears; and even from Gunther\'s breast was forced a cry of anguish. But Siegfried was not deceived thereby. Clearly now he saw the whole treacherous plot.\n"Too late is it now, King Gunther of Burgundy, to bewail the evil thou thyself hast wrought; better for thee had it been left undone."\nTHEDEATHOF SIEGFRIED.\n\nQuestion: Why didn\'t Siegfried drink from the spring immediately? Answer: He waited for King Gunther, as the sovereign prince, to drink first.\n\nQuestion: What happened to Siegfried\'s strength after he wounded Hagen? Answer: His strength fled, and he sank to the ground, dying from his wound.\n\nQuestion: What did Siegfried say to the others before he died? Answer: He accused them of treachery and cowardice for killing him from behind.'}}
    right = continuations.get(doc['doc_id'])
    if right is None:
        return doc['text']
    result = _c3_pair(doc['doc_id'], doc['text'], right['doc_id'], right['text'])
    return doc['text'] if result is None else json.dumps(result, ensure_ascii=False)
```


## Medicine 3 — C4: separate reviewed topic blocks

1. **Disease:** C4, 7 labelled occurrences. Three reviewed examples:
   - `a14eaa5e58baf3c3`: topic shifts at offsets 188, 338 and 409. First boundary text: `Australia's English has distinct accents and vocabulary`.
   - `5958fb6996158153`: topic shifts at offsets 386, 689, 897 and 1270. First boundary text: `Disruptive technologies span from the automobile to the`.
   - `6cd78f812660687b`: a separate vehicle question starts at offset 1650. First boundary text: `i have a 2003 chev s-10 pickup with automatic/ 4 cyl I `.
2. **Medicine:** split at the reviewed, zero-based character boundaries without changing or discarding any source character. Boundaries are explicit review decisions, rather than recovered original page metadata.
3. **Action:** the split helper emits fragments with source ID, fragment index and original bounds. The single-document runner returns those unchanged fragments separated by blank lines; the source text remains reconstructable.
4. **Harm test:** Data A runner:0 of96 published gold documents changed or dropped; PASS. Separate local two-reader check:0 of326 changed or dropped; PASS.
5. **Side effects:** a topic shift can be intentional. Apply only to the three source hashes; do not split an article solely because it covers several subjects.

```python
import hashlib

def _source_hash(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def _c4_split(doc_id, text):
    rules = {'a14eaa5e58baf3c3': ('a14eaa5e58baf3c30dcd36d4155a9170f88417fee5af4636c8ae212fb04c4624', [188, 338, 409]), '5958fb6996158153': ('5958fb699615815368c5862162fed173c7e5d92fb0760dbd2115ca3e18edbe51', [386, 689, 897, 1270]), '6cd78f812660687b': ('6cd78f812660687b04cb5ab5131b8c53fbf7a6e7771c3d97f05aab4e579f96d6', [1650])}
    rule = rules.get(doc_id)
    if rule is None or _source_hash(text) != rule[0]:
        return [{'source_id': doc_id, 'fragment': 1, 'start': 0, 'end': len(text), 'text': text}]
    bounds = [0] + rule[1] + [len(text)]
    return [{'source_id': doc_id, 'fragment': index, 'start': start, 'end': end, 'text': text[start:end]} for (index, (start, end)) in enumerate(zip(bounds, bounds[1:]), 1)]

def _c4_text(doc_id, text):
    parts = _c4_split(doc_id, text)
    return text if len(parts) == 1 else '\n\n'.join((p['text'] for p in parts))

def medicine_c4(doc):
    return _c4_text(doc['doc_id'], doc['text'])
```


## Medicine 4 — F1: remove private contact/testimonial material

1. **Disease:** F1, 7 labelled occurrences. Values are excluded from evidence and code:
   - `12693fe362d15d0d`: contact name at offset 1087; phone at offset 1110.
   - `d75b731d61eb6433`: customer name at offset 858.
   - `6700f6a8840e9c51`: contact name at offset 1201; email at offset 1215.
2. **Medicine:** return the reviewed privacy-safe replacement only for a matching source ID and hash. The lookup contains output text and hashes, never the removed personal values.
3. **Action:** fix. Named contact/testimonial material is removed; accompanying historical or factual qualifications are retained in the reviewed output.
4. **Harm test:** Data A runner:0 of96 published gold documents changed or dropped; PASS. Separate local two-reader check:0 of326 changed or dropped; PASS.
5. **Side effects:** removing an entire contact or testimonial passage loses surrounding context. Public professional attribution is not automatically private personal data; do not generalize this decision to every name.

```python
import hashlib

def _source_hash(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def _f1_text(doc_id, text):
    reviewed = {'12693fe362d15d0d': ('12693fe362d15d0d98db6692a8a1f47d34481adf85677a5bf359aab419e51dca', 'Mindfulness and Self-Compassion Workshop\n\nThe Father Mychal Judge Center for Recovery presents a two-part workshop, "Introduction to Mindfulness and Self-Compassion," as part of its Mind Body Spirit Series. Led by Mark Dagnall, LADAC, CRC, this workshop is designed for individuals in recovery and their caregivers, aiming to provide a general understanding of mindfulness and self-compassion for overall well-being and recovery.\n\nThe workshop focuses on teaching meditation techniques, both formal and informal, to help participants develop non-judgmental awareness of the present moment. This is an excellent opportunity to explore and enjoy a mindfulness practice in a comfortable, loose-fitting attire.\n\nThe workshop is held over two sessions:\n- Session 1: Wednesday, March 19, 2014, from 5:30 PM to 7:30 PM\n- Session 2: Wednesday, March 26, 2014, from 5:30 PM to 7:30 PM\n\nBoth sessions take place in the Clare Conference Room on the 4th floor of St. Anthony Shrine. The cost is $20 per session or $35 for both sessions.'), 'd75b731d61eb6433': ('d75b731d61eb64339140e502e6399133daccf255e1db55799a97b537ce98bef7', 'Purpose: A Notion database template for benchmarking analysis to help solopreneurs, entrepreneurs, startups, and SMEs track performance and identify improvement areas.\nCreator\'s Motivation: "What cannot be measured cannot be improved."\nBenefits:\n- Identify improvement areas in the company/project.\n- Learn from the competition.\n- Monitor company/project performance.\n- Identify productivity points.\nTarget Users:\n- Entrepreneurs, startups, and SMEs.\n- Professionals in finance, marketing, sales, operations, human resources, or internationalization departments.\nFeatures:\n- Over 600 indicators and metrics for benchmarking.\n- Onboarding guide and creation hub for customizing metrics.\n- Introductory guide to benchmarking and use cases.'), '6700f6a8840e9c51': ('6700f6a8840e9c5116d5f8cb805209b7e0c158d012717164e872d5dd93657a3b', "Transition Process:\n- Involves stopping harvesting in one area and preparing for the new area within 24-56 hours.\n- Requires coordination among multiple departments: drivers, sanitation, food safety, maintenance, etc.\n- Happens twice a year for many row-crop growers.\n- Logistically challenging due to simultaneous moves and varied customer needs.\n\nD'Arrigo Brothers:\n- First grower to ship fresh produce from the West Coast to the East Coast (1926).\n- Moves entire growing operations, including equipment and staff, from Yuma, Arizona to Salinas, California annually.\n- Equipment moved: 34 buses, 70 harvesters, 30 forklifts and tractors, 12 storage trailers, and 20 heavy trucks.\n- Transition process spans 1.5 months.\n\nPRO*ACT's Role:\n- Assists suppliers and customers with communication during the transition process.\n- Helps D'Arrigo Brothers communicate with the entire supply chain about product timing, availability, and quality.\n\n2021 Transition Dates:\n- Spring move starts on April 5, 2021.\n- Suppliers loading in Salinas on April 5: Mann Packing, Duda, Church Brothers, Nunes, Salad Farms.\n- Later transitions: Ippolito (April 12), Taylor Farms (April 19), Greengate (April 26).")}
    entry = reviewed.get(doc_id)
    if entry is None or _source_hash(text) != entry[0]:
        return text
    return entry[1]

def medicine_f1(doc):
    return _f1_text(doc['doc_id'], doc['text'])
```


## Medicine 5 — B4: exact billing-heading placeholder

1. **Disease:** B4,2 labelled occurrences. This optional candidate covers `d2fb665c40af5edb`, `Total Due After -DATE-:` at offset326; embedded writing-template directions remain a separate document-specific decision.
2. **Medicine:** replace the exact heading only when it occurs once.
3. **Action:** fix; do not infer a calendar date.
4. **Harm test:**0 of96 published gold documents changed or dropped; PASS. Separate local candidate check:0 of326; PASS.
5. **Side effects:** an intentionally quoted billing template can match. Repeated headings are left unchanged; this is not a general date repair.

```python
def medicine_b4(doc):
    text = doc['text']
    old = "Total Due After -DATE-:"
    return text.replace(old, "Total Due After the Due Date:", 1) if text.count(old) == 1 else text
```

## Medicine 6 — C5: exact reviewed exclusions

1. **Disease:** C5,2 labelled occurrences. The evidence and offsets are in `labels.csv` for `f27860217811cf33` and `ce52c449f250761e`.
2. **Medicine:** exclude only the reviewed source identities and hashes below.
3. **Action:** drop the complete record, including generated Q&A.
4. **Harm test:**0 of96 published gold documents changed or dropped; PASS. Separate local candidate check:0 of326; PASS.
5. **Side effects:** whole-record exclusion loses any useful material in that record. Do not generalize this list into a keyword/topic filter.

```python
import hashlib

def _source_hash(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def medicine_c5(doc):
    exclusions = {'f27860217811cf33': 'f27860217811cf3306b4d8e5c37345587d6252e1a4fd3826d995e47190fd40cb', 'ce52c449f250761e': 'ce52c449f250761e9889951b8c51f26d34fc5135bcd20300261b6169943df709'}
    return ('drop', '') if exclusions.get(doc['doc_id']) == _source_hash(doc['text']) else doc['text']
```

## Medicine 7 — F3: exact reviewed exclusions

1. **Disease:** F3,3 labelled occurrences. The evidence and offsets are in `labels.csv`; this is below the mandatory medicine threshold.
2. **Medicine:** exclude only the reviewed source identities and hashes below. Ordinary religious, gambling, medical and literary subject matter does not by itself trigger this rule.
3. **Action:** drop the complete record, including generated Q&A.
4. **Harm test:**0 of96 published gold documents changed or dropped; PASS. Separate local candidate check:0 of326; PASS.
5. **Side effects:** whole-record exclusion loses context. The reviewed-ID decisions must not be broadened into an unreviewed topic filter.

```python
import hashlib

def _source_hash(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def medicine_f3(doc):
    exclusions = {'67cd7f8dca56480d': '67cd7f8dca56480d8edd3d67e9d7e2151041478396ff01c8d72cc985acdd4bdd', 'ef65e5b6d0cda5a5': 'ef65e5b6d0cda5a55c4562ab524991044b2ffda7fbe62057e6bda9f5364ebdab', '06cfe5719541e863': '06cfe5719541e863bed260475ed925693ed9a8f4ece5161b3c5b58c8ad3ffaf8'}
    return ('drop', '') if exclusions.get(doc['doc_id']) == _source_hash(doc['text']) else doc['text']
```

B5 has one labelled occurrence: a source-specific malformed-sigma correction, rather than a generalized formula-repair rule. Source retrieval limits and separate factual corrections remain in individual label notes.

## Selected source references

- [The Nibelungs, matching Upton edition](https://www.gutenberg.org/cache/epub/73227/pg73227-images.html): literary transcription and continuation checks.
- [IJSR publisher PDF](https://www.ijsr.net/archive/v8i3/ART20195931.pdf): the work-immersion study and its methods.
- [Swift official documentation](https://raw.githubusercontent.com/swiftlang/swift-book/main/TSPL.docc/LanguageGuide/TheBasics.md): optional values and unwrapping.
- [IBM READE reference](https://www.ibm.com/docs/en/i/7.4.0?topic=codes-reade-read-equal-key): keyed-record processing.
- [AAP newborn assessment](https://www.aap.org/en/patient-care/newborn-infant-and-early-childhood-nutrition/newborn-and-infant-health-assessment-and-promotion/first-office-visit-3-5-days/): feeding and weight evaluation.
- [IOC REDs consensus](https://doi.org/10.1136/bjsports-2023-106994): athlete-health terminology.
- [Kansas published blackjack rules](https://sos.ks.gov/publications/Register/Volume-41/Issues/Issue-24/06-16-22-50240.html): insurance stake and payout context.
- [Women's Sports Foundation 2016 record](https://www.womenssportsfoundation.org/education/title-ix-and-the-rise-of-female-athletes-in-america/): participation-statistic correction.
- [U.S. Copyright Office NFT study](https://copyright.gov/policy/nft-study/): token ownership and intellectual-property distinctions.

Source checks distinguish retrieved originals, matching replacement pages, independent references and unavailable pages. The linked references support specific corrections; they are not a claim that every original URL was recovered.

## Reproduction fingerprints

- Executable medicine code SHA-256: `4dd1f137101c216227e5763d8e73ff125e9d36114df9fb6f8eef4f365b9f3b03`.
- Published96-ID gold CSV SHA-256 (local LF-normalized copy): `fea23baa61b2e684294eaf7eb3f2457cf278e4a9aab0b67caf3a2e7d18882f40`.
- Local326-ID candidate CSV SHA-256: `4d976d9eb82d34cd38d793c122d5205f400fb16668be733ed3d483605289d382`.
- Original Parquet SHA-256: `0f1c3a9866ada7fb5ea2a244135d9766375351bec366c13cd9c5abfb3d82573c`.

Reports and downloaded evaluation assets stay outside the submission folder; this sheet records the measured counts and pinned source provenance.
