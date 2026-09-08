# Argentine Senate stenographic transcripts, 2000–2024

A speaker-attributed corpus of what was said on the floor of the Argentine
Senate: every stenographic record (*versión taquigráfica*) the chamber's portal
still serves for its sittings between February 2000 and December 2024, parsed
from the Senate's own PDFs into passages, each with the speaker label the page
printed, the person that label resolves to, and the caucus that person sat with
on the day.

Version 0.4.37 — the version number is the parser's, because the parser is what
determines the content.

| | |
| --- | --- |
| Sittings | 559 held, 558 parsed |
| Passages | 233,408 rows |
| Speech | 151,761 passages, 18.40 million words |
| Stenographer's notes, typed | 31,955 |
| All rows together | 21.46 million words, of which 2.58 million are page matter kept only for tracing (`type == "furniture"`) |
| Passages with no speaker | 1,109 (0.5%) |
| Resolved (sitting, label) pairs | 16,311 |

Coverage is complete from 2004 onward: every sitting the portal lists for those
years is here. Before that it thins out fast, because the portal lists the
sittings but no longer serves the files — 34 of 47 for 2003, 4 of 47 for 2002,
10 of 83 for 2001, 3 of 75 for 2000. Nothing before 2000 is served at all.

## What is in this bundle

```
data/processed/senado/blocks/*.parquet   the corpus, one file per sitting (558)
data/processed/senado/speakers.parquet   each printed label resolved to a person and a caucus
data/processed/senado/parse_stats.csv    40 counts per sitting of what the parser did to it
data/raw/senado/bloques_archivados/      34 Internet Archive captures of a Senate page
reference/senado/                        rosters, roll-call caucus readings, hand-dated caucuses
reference/gold/                          36 pages annotated by hand, and what they were scored against
raw_data_manifest.csv                    every source PDF: sha256, source URL, size, download time
scripts/                                 the pipeline that produced all of it
pyproject.toml, uv.lock                  the exact environment it was produced in
docs/DATA_DICTIONARY.md                  what every column holds and what not to assume about it
CHECKSUMS.sha256                         a SHA-256 for every other file here
```

**The source PDFs are not redistributed.** They are the Senate's to publish, not
this project's. `raw_data_manifest.csv` identifies each one by checksum and
source URL, and `scripts/download.py` fetches them again, so the corpus can be
rebuilt rather than taken on trust.

The archived pages under `data/raw/senado/bloques_archivados/` are the
exception: they are captures of a Senate page that no longer exists anywhere,
and the caucus of the pre-2005 years cannot be rebuilt without them. Each row
derived from them carries the archive URL it came from.

## Using it

```python
import pandas as pd
from pathlib import Path

blocks = Path("data/processed/senado/blocks")
corpus = pd.concat([pd.read_parquet(p) for p in sorted(blocks.glob("*.parquet"))],
                   ignore_index=True)
speakers = pd.read_parquet("data/processed/senado/speakers.parquet")

speech = corpus[corpus["type"] == "speech"]
named = speech.merge(speakers, on=["session_id", "speaker_raw"], how="left")
```

Read [docs/DATA_DICTIONARY.md](docs/DATA_DICTIONARY.md) before drawing anything
from it. Three things there are worth knowing in advance, because each of them
will quietly mislead you otherwise:

- **`office_only` is 28% of the floor and is deliberately nameless.** Before
  about 2016 the record prints "Sr. Presidente" with no surname; the chair
  changes hands within a sitting and the page does not say who holds it. Any
  name there would be a guess. Dropping those rows as missing data loses a
  quarter of the corpus, most of it the chair conducting business.
- **`elected_ticket` is the list a senator stood on; `bloc` is the caucus they
  sat with.** They fall in different political camps for 18.9% of floor speech,
  mostly provincial alliances whose senators sit with a national caucus. For
  anything about how the chamber divided, use the caucus.
- **Count turns by `turn_id`, not by rows.** A turn interrupted by applause, or
  split across a page break, is several rows.

## Rebuilding it from the sources

```sh
uv sync
uv run scripts/download.py          # fetch the PDFs the manifest names
uv run scripts/parse.py             # PDFs -> per-sitting Parquet + parse_stats.csv
uv run scripts/extract_authorities.py
uv run scripts/resolve_speakers.py  # -> speakers.parquet
uv run scripts/eval_gold.py         # score against the 36 annotated pages
uv run scripts/check_gold.py        # check the annotations against the PDFs
```

The dependency versions are pinned on purpose. pdfplumber's character-level
extraction changes between releases, and the parser's repairs are calibrated
against the output of the version in `uv.lock`; a different one will not
reproduce these numbers.

## How far it has been checked

- **36 pages annotated by hand**, spanning 2003–2024 and shipped in
  `reference/gold/`: boundary and attribution F1 = 0.996, 124 of 125 turns,
  the same score on the printed label alone and on the label carried with the
  turn's opening words. Stenographer's notes: precision 1.000, recall 0.935,
  29 of 31. Treat 0.996 as the small sample it is — one miss in 125 turns puts
  the 95% interval on recall at 0.956 to 0.999, the turns come from 24
  documents, and 24 of the 36 pages are 2020 or later.
- **Every parsed sitting audited against its own PDF**: no page apparatus
  inside a speech turn outside the two scanned sittings, no turn carrying a
  second speaker's label, no document yielding more text than it prints.
  98,601 passages were probed against the source and 0.120% could not be
  located, no sitting above 1% once the two scans are set aside.
- **5,463 turns read blind** across nine rounds by a reader never shown the
  parser's answer, and re-asked of this build: 5,416 still resolve to the
  person the round recorded, none resolves to anybody else, and 47 cannot be
  re-asked — 43 quote words the page prints under two different names. Those
  records are not in this deposit; the count is what they produced.
- **Caucus**: 97.6% of senators' floor passages carry one — 83.2% confirmed,
  13.1% marked anachronistic because the Senate's own record names a caucus
  that did not exist on the day of the sitting, 1.1% undatable, 0.1% disputed.
  Those are kept and marked, never corrected or dropped.

## What it gets wrong

- **Two sittings of November 2001 are scans read by character recognition** —
  `2001-11-21_r72` and `2001-11-29_r74`. Their text is unreliable; they are
  flagged in `parse_stats.csv` and should be excluded from text analysis.
- **One sitting does not parse at all**: 29 November 2001, which never reached
  quorum and so has no session opening for the parser to find. It is reported
  in `parse_stats.csv` rather than dropped silently.
- **1,109 passages carry no speaker, and they are not one thing.** 362 are in
  those two scans. 321 are three sittings whose record is mostly an inserted
  document — lists of judicial appointments, decree texts. Of the remaining
  426, 155 are a word or less: a stray full stop, a single letter, an orphan
  "(Guinle)", a contents-page "Volver". At least 42 are real floor speech that
  lost its label, such as "Señor presidente: voy a ser muy breve…". That count
  comes from matching how a turn opens, so it is a floor, not a total.
- **91 printed speaker labels still leave no row of their own.**
- **36 notes reading "-Okay" are attributed to the chair but typed as notes.**
  The page prints "Sra. Presidente.- Okay.", so she said it; the typesetter set
  it in italics, which is the only thing that makes the parser call a line a
  note. Four sittings of 2016.
- **Roughly a fifth of each document is dropped on purpose** — contents pages,
  attendance rolls, appendices, inserted documents that were never spoken. The
  median sitting keeps 79.0% of its printed text.
- **The text is what the page prints, not what was said.** A stenographic
  record is edited, and senators correct their own words afterwards.

## Checking what you downloaded

```sh
shasum -a 256 -c CHECKSUMS.sha256
```

Run from the unpacked directory. It covers every file in the bundle except
itself; the archive's own SHA-256 is published beside the archive.

## Licence

Two different things are in here and they are not under the same terms.

- **The corpus and the reference tables** — everything under
  `data/`, `reference/`, and `raw_data_manifest.csv` — are licensed
  [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/): reusable,
  including commercially, on condition of attribution.
- **The code** in `scripts/` is MIT ([LICENSE](LICENSE)).
- **The transcripts themselves** are the Argentine Senate's. They are not
  relicensed here and not redistributed. Cite the chamber as publisher, with
  the sitting date and the per-sitting URL from `raw_data_manifest.csv`. The
  portal publishes no licence page. The governing framework is Argentina's
  access-to-information law (Ley 27.275), which obliges the state to publish in
  formats that permit reuse and redistribution; that is the basis on which this
  derived corpus is released, and it is a reading of the law rather than a
  grant from the chamber.

[LICENSE-DATA](LICENSE-DATA) states the split and lists exactly what each side
covers.

## Citing it

> Ripamonti, J. P. (2026). *Argentine Senate stenographic transcripts,
> 2000–2024: a speaker-attributed corpus* (version 0.4.37) [Data set]. Zenodo.
> <https://doi.org/10.5281/zenodo.22661020>

Version 0.4.37 has its own DOI, above. To cite the corpus rather than one
release of it, use the concept DOI, which always resolves to the latest:
<https://doi.org/10.5281/zenodo.22661019>.

[CITATION.cff](CITATION.cff) carries both in machine-readable form.
