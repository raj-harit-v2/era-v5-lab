# Style guide for public text

This guide is for every text that the lab makes public: weekly updates, the dashboard text, the launch
announcement and the model card. Write for a reader who is smart but busy, and who may read English as a
second language.

Run the checker before you ask for a review:

```
python teams/11-release/style/check_style.py <your file>
```

The checker must give 0 errors. Add `--numbers` to list the numbers in your text that need TSAI approval.

## Rules the checker enforces

1. **Short sentences.** At most 25 words in a sentence. One idea per sentence.
2. **No em-dashes or en-dashes.** Use a full stop, a comma, a colon or "and". For a range, write "to":
   `24 to 31 Oct`. A plain hyphen in a word is fine.
3. **No email addresses.** Public text never contains an email address. Point readers to the public repository
   or to TSAI instead.
4. **No banned words.** These words promise too much, or say nothing. Write the fact instead.

The banned words (`check_style.py --self-test` fails if this list and the script differ):

`revolutionary`, `revolutionise`, `revolutionised`, `revolutionises`, `revolutionising`, `revolutionize`,
`revolutionized`, `revolutionizes`, `revolutionizing`, `groundbreaking`, `ground-breaking`, `breakthrough`,
`breakthroughs`, `game-changer`, `game-changers`, `game-changing`, `cutting-edge`, `state-of-the-art`, `SOTA`,
`world-class`, `best-in-class`, `world's first`, `first-ever`, `unprecedented`, `unparalleled`, `unmatched`,
`paradigm shift`, `paradigm shifts`, `disruptive`, `synergy`, `synergies`, `leverage`, `leveraged`, `leverages`,
`leveraging`, `utilise`, `utilised`, `utilises`, `utilising`, `utilize`, `utilized`, `utilizes`, `utilizing`,
`seamless`, `seamlessly`, `magic`, `magical`, `magically`, `incredible`, `incredibly`, `amazing`, `amazingly`,
`awesome`, `mind-blowing`, `flawless`, `flawlessly`, `guarantee`, `guaranteed`, `guarantees`, `human-level`,
`superhuman`, `AGI`, `sentient`, `delve`, `delved`, `delves`, `delving`.

The technical phrase `magic number` is allowed. The word `magic` on its own is not.

| Instead of | Write |
|---|---|
| `a groundbreaking tokenizer` | a tokenizer that splits Kannada words into fewer pieces |
| `state-of-the-art results` | the score on a named benchmark, after TSAI approves the number |
| `we leverage the cluster` | we use the cluster |
| `seamless training` | training ran without a restart |

## Rules a reviewer checks

5. **Numbers need TSAI approval.** Ask TSAI before you publish any number. See `public_internal.md`. Until TSAI
   approves a number, write `[number: waiting for TSAI]` in its place. `--numbers` does not find every number
   written as a word, so the reviewer checks for those too. The week number and the date of the update need no
   approval, so `--numbers` skips `week 1` and dates up to the date on the `Date:` line, such as `31 Oct 2026`.
   It still lists a later date, because a future date needs approval. It also skips pull request numbers such as
   `#6`: they name a source and do not count anything.
6. **Say what we did.** Write about work that is done. Do not promise dates, sizes or results.
7. **Names need consent.** Name a person only if they signed `consent_form.md`. Use the name the way
   they chose.
8. **Plain words.** Write "use", not "make use of". Write "start", not "commence". Write "about", not
   "approximately".
9. **Active voice.** Write "the Tokenizer team trained a tokenizer", not "a tokenizer was trained".
10. **Explain names once.** Spell out a short form the first time, for example "Post-training (the team that
    tunes the model after pre-training)".
11. **Dates and times.** Write dates as `31 Oct 2026`. Give times in IST.
12. **Spelling.** Use British spelling: labelled, organise, colour.
13. **Internal stays internal.** If you are not sure that something is public, treat it as internal and ask in
    the G11 group.

## How a text becomes public

1. The writer drafts the text and runs the checker until it gives 0 errors.
2. The writer opens a pull request. The repository is public, so the pull request is public too. It may hold
   only facts that are already public, and `[number: waiting for TSAI]` for a number that TSAI has not approved.
3. Each team lead gives an OK for the text about their team. The writer marks it in the review record of the
   pull request.
4. The G11 lead reviews the pull request. A pull request from the lead also needs a comment from a team member.
5. TSAI approves the text in the pull request.
6. The G11 lead merges it only after TSAI approves. Then the text may be published.
