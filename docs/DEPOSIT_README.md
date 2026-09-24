# Argentine Senate stenographic transcripts, 1998–2026

A speaker-attributed corpus of what was said on the floor of the Argentine
Senate: every stenographic record (*versión taquigráfica*) the chamber's portal
still serves for its sittings between February 1998 and September 2026, parsed
from the Senate's own files into passages, each with the speaker label the page
printed, the person that label resolves to, and the caucus that person sat with
on the day.

Version 0.5.7 — the version number is the PDF parser's, because the parser is
what determines the content. The sittings of 1998–2003 come from the chamber's
HTML export and are read by `scripts/parse_html.py`, at 0.5.10-html.

| | |
| --- | --- |
| Sittings | 818 held, 817 parsed |
| Passages | 439,686 rows |
| Speech | 245,722 passages, 25.72 million words |
| Stenographer's notes, typed | 69,376 |
| All rows together | 29.63 million words, the rest being headings and page matter kept only for tracing (`type == "furniture"`) |
| Passages the parser could not attribute | 5,210 (1.19%), most of them matter inserted into the record without being spoken |
| Resolved (sitting, label) pairs | 23,961 |

Coverage is complete from 2002 onward: every sitting the portal lists for those
years is here. Before that it is partial, because the portal lists the sittings
but no longer serves every file — 51 of 73 for 1998, 47 of 74 for 1999, 46 of
75 for 2000, 44 of 83 for 2001. Of the 882 sittings the portal lists before
1998, exactly one is still served: an impeachment tribunal of 18 December 1997,
a photocopy saved as page images with no text in it, which is why it is the one
sitting that does not parse.

The portal serves the same URL as a PDF from 2004 on and as the chamber's own
HTML export for most of 1998–2003. Both are read, and every row carries the
`source_format` it came from. One sitting, 29 October 2003, is served twice
under two reunión numbers; it is parsed once, under the number its own masthead
prints.

## What is in this bundle

```
data/processed/senado/blocks/*.parquet   the corpus, one file per sitting (817)
data/processed/senado/speakers.parquet   each printed label resolved to a person and a caucus
data/processed/senado/parse_stats.csv    what the parser did to each sitting, counted
data/raw/senado/bloques_archivados/      Internet Archive captures of the Senate's bloc roster, 2000–2004
data/raw/senado/fichas_archivadas/       Internet Archive captures of senators' own pages, 1997–1998
reference/senado/                        rosters, roll-call caucus readings, hand-dated caucuses
reference/gold/                          72 PDF pages annotated by hand
reference/gold_html/                     24 HTML stretches annotated by hand, each read twice
raw_data_manifest.csv                    every source file: sha256, source URL, format, size, download time
scripts/                                 the pipeline that produced all of it
pyproject.toml, uv.lock                  the exact environment it was produced in
docs/DATA_DICTIONARY.md                  what every column holds and what not to assume about it
CHECKSUMS.sha256                         a SHA-256 for every other file here
```

**The source files are not redistributed.** They are the Senate's to publish,
not this project's. `raw_data_manifest.csv` identifies each one by checksum and
source URL, and `scripts/download.py` fetches them again, so the corpus can be
rebuilt rather than taken on trust.

The archived pages under `data/raw/senado/` are the exception: they are
captures of Senate pages that no longer exist, and the caucus of the years
before 2005 cannot be rebuilt without them. Each row derived from them carries
the archive URL it came from.

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

- **`office_only` is 22% of the floor and is deliberately nameless.** Before
  about 2016 the record prints "Sr. Presidente" with no surname; the chair
  changes hands within a sitting and the page does not say who holds it. Any
  name there would be a guess. Dropping those rows as missing data loses a
  fifth of the corpus, most of it the chair conducting business.
- **`elected_ticket` is the list a senator stood on; `bloc` is the caucus they
  sat with.** They fall in different political camps for 17.0% of floor speech,
  mostly provincial alliances whose senators sit with a national caucus. For
  anything about how the chamber divided, use the caucus.
- **Count turns by `turn_id`, not by rows.** A turn interrupted by applause, or
  split across a page break, is several rows.

## Rebuilding it from the sources

```sh
uv sync
uv run scripts/download.py --from-manifest  # every file the manifest names, checked by SHA-256
uv run scripts/parse.py             # PDFs -> per-sitting Parquet + parse_stats.csv
uv run scripts/parse_html.py        # the 1998-2003 HTML exports, into the same tables
uv run scripts/extract_authorities.py
uv run scripts/build_bloc_observations.py
uv run scripts/deduce_bloc_from_counts.py
uv run scripts/build_bloc_observations.py
uv run scripts/resolve_speakers.py  # -> speakers.parquet
uv run scripts/check_bloc_counts.py # the caucuses against the chamber's official counts
uv run scripts/eval_gold.py         # score against the 72 annotated PDF pages
uv run scripts/check_gold.py        # check those annotations against the PDFs
uv run scripts/eval_gold_html.py    # score against the 24 annotated HTML stretches
uv run scripts/check_gold_html.py   # how far the two readings of each stretch agree
uv run scripts/audit_parse.py       # every sitting against its own source file
```

`--from-manifest` fetches each file from the URL the manifest records, saves
it under the name the manifest records, and keeps it only if its SHA-256
matches; a file the portal now serves with different bytes is set aside and
reported. That is what makes the rebuild exact: the parser reads each
sitting's identity from the manifest row of the same file name, and the
annotated pages name their files. Without the flag, `download.py` does
something else — it fetches whatever the portal lists today, for 2020–2024
unless told otherwise, under the current naming scheme — which extends a
collection rather than rebuilding this one.

`build_bloc_observations.py` runs twice on purpose: the caucuses deduced from
the official counts are one of its inputs, and the deduction needs the first
pass. Without the source files, the caucus chain (`build_bloc_observations.py`
to `check_bloc_counts.py`), `eval_gold.py`, `check_gold_html.py` and
`audit_parse.py --skip-source` still run on the shipped tables, so the
published figures for those can be checked before downloading anything. The
parsers, `extract_authorities.py`, `check_gold.py`, `eval_gold_html.py` and
the source checks of `audit_parse.py` need the sources.

The other scripts in `scripts/` built the reference tables that ship in
`reference/senado/` — `fetch_roster.py`, `fetch_blocs.py`,
`fetch_archived_blocs.py`, `fetch_archived_profiles.py`,
`extract_chair_caucus.py`, `extract_declared_caucus.py` — or the manifest
(`make_manifest.py`), or are modules the others import (`map_blocs.py`,
`provenance.py`, `session_kind.py`). They are shipped so every table can be
traced to the code that made it; re-running the fetchers reaches the Senate's
site and the Internet Archive today, and is not needed to rebuild this
release.

The dependency versions are pinned on purpose. pdfplumber's character-level
extraction changes between releases, and the parser's repairs are calibrated
against the output of the version in `uv.lock`; a different one will not
reproduce these numbers.

## How far it has been checked

- **72 PDF pages annotated by hand**, spanning 1998–2024 — 36 of them read
  twice by annotators who never saw each other's reading, and the two readings
  agree on every turn start — shipped in `reference/gold/`: boundary and attribution F1 = 1.000, 310 of 310 turns,
  the same on the printed label alone and on the label carried with the turn's
  opening words. Stenographer's notes: precision and recall 1.000, 82 of 82.
  Read the interval, not the point: a perfect 310 still puts the 95% interval
  on recall at 0.988 to 1.000, and the turns come from 55 documents.
- **24 stretches of the HTML era annotated by hand**, about 7,000 characters
  each, cut on the source file by offset and never at a boundary the parser
  found; two readers, who agree on all 195 turn starts. Both readings score
  195 of 195, notes included.
- **Every parsed sitting audited against its own source file**: no page apparatus inside a speech
  turn outside the three scans, no turn carrying a second speaker's label, no
  document yielding more text than it prints (0 of 817), and every one of
  14,443 labels of the HTML era's commonest shape — a bold run that begins at
  the heading above — attributed to its own speaker. 154,247 passages were
  probed against the source and 0.072% could not be located, no sitting above
  1% once the scans are set aside. 8 turns of 245,722 open mid-word, and every
  one is printed that way.
- **6,819 turns read blind** across thirteen rounds by readers never shown the
  parser's answer, and re-asked of this build: 6,529 still resolve to the
  person the round recorded and none resolves to anybody else. 290 cannot be
  re-asked — 264 quote words the page prints under two different names, 20 are
  passages a repair has since taken out of speech, 6 quote too little to find.
  Those records are not in this deposit; the count is what they produced.
- **29 turns checked by a person against the page images**, one a year from
  1998 to 2026: all 29 agree with the parser.
- **Caucus**: 98.6% of senators' floor passages carry one — 90.0% confirmed,
  7.0% marked anachronistic because the Senate's own record names a caucus
  that did not exist on the day of the sitting, 0.8% disputed, 0.6%
  undatable, and 0.2% inferred across a gap or deduced from the chamber's
  official count per caucus. Those are kept and marked, never corrected or
  dropped. The chamber publishes a count of senators per caucus for each
  renewal; set beside it on 1 March of 1999, 2000, 2002 and 2004, the corpus
  differs by one senator in seven caucus counts, and
  `scripts/check_bloc_counts.py` lists who is behind each.

## What it gets wrong

- **Three sittings are scans read by character recognition**:
  `2001-11-21_r72`, `2001-11-29_r74`, and the 1997 tribunal, which yields
  nothing at all. Their text is unreliable; `parse_stats.csv` flags them
  (`scanned_page_share`), and they should be excluded from text analysis.
- **5,210 passages carry no speaker, and most of them were never spoken.** In
  the HTML era 83% of those words stand inside a run of inserted matter —
  speeches handed in for the record and never delivered, and the bills read
  into it.
- **19 printed speaker labels still open a turn that leaves no row.** 6 are in
  the November 2001 scan; most of the rest are the secretary's label followed
  by the document he reads, which the page sets as a heading or an inserted
  text. Whether that document is his turn is a question of definition, left
  open rather than decided silently.
- **166 speech passages carry a label that resolves to nobody** (0.1%), and 48
  one that fits more than one senator; the label is kept either way.
- **The 1998–1999 caucus has gaps.** No roster of the chamber's caucuses
  survives for those years, so they are rebuilt from the chair's own calls,
  senators' statements on the floor and archived personal pages. 2,120
  senators' passages (1.4%) carry no caucus, most of them there.
- **Roughly a fifth of each document is dropped on purpose** — contents pages,
  attendance rolls, appendices, inserted documents that were never spoken.
  The median sitting keeps 82.8% of its printed text.
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

- **The corpus and the reference tables** — `data/processed/senado/`,
  `reference/` and `raw_data_manifest.csv` — are licensed
  [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/): reusable,
  including commercially, on condition of attribution.
- **The archived pages** under `data/raw/senado/` are the Senate's pages as
  the Internet Archive captured them. They are not this project's work and
  are not relicensed here.
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
> 1998–2026: a speaker-attributed corpus* (version 0.5.7) [Data set]. Zenodo.
> <https://doi.org/10.5281/zenodo.22661019>

That is the concept DOI, which always resolves to the latest version. Cite it
unless the exact bytes matter.

[CITATION.cff](CITATION.cff) carries the same in machine-readable form.
