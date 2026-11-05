# Boilerplate texts

Text that is in benchmark items but also in millions of other documents. `build_fingerprints.py`
does not write a gram when at least half of its words are inside a run of 8 words from one of
these files (see `fpset.Boilerplate`).

- `*.txt` except `lorem-ipsum.txt`: licence texts from SPDX license-list-data, tag `v3.25.0`
  (`https://raw.githubusercontent.com/spdx/license-list-data/v3.25.0/text/<id>.txt`, CC0).
  SWE-bench patches add new files with these headers.
- `lorem-ipsum.txt`: the standard placeholder text.

Measured on the 38 sample packs (19,000 documents): the licence header of Apache-2.0 alone gave
about 220 false hits through SWE-bench Live and Pro.

To add boilerplate, add a `.txt` file here and rebuild. The set records the sha256 of each file.

`scoped/`: files for one benchmark only. A benchmark names them in `benchmarks.toml` (key `boilerplate`), and
the other benchmarks do not use them.

- `scoped/heldout_g5_v1.txt`: 5 passages cut from G5 held-out documents (a GMAT Club timer, a CC BY licence
  line, Home Assistant code, Springer notes and a book-series text). They are also on many other web pages.
  Without this file, the held-out entry flagged 22 of the 19,000 sample-pack documents. With it: 0.
