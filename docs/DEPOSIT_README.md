# Argentine Senate stenographic transcripts, 1998–2026

A speaker-attributed corpus of what was said on the floor of the Argentine
Senate: every stenographic record (*versión taquigráfica*) the chamber's portal
still serves for its sittings between February 1998 and September 2026, parsed
from the Senate's own files into passages, each with the speaker label the page
printed, the person that label resolves to, and the caucus that person sat with
on the day.

Version 0.5.8 — the version number is the PDF parser's, because the parser is
what determines the content. Most sittings of 1998–2003 come from the chamber's
HTML export and are read by `scripts/parse_html.py`, at 0.5.11-html.

| | |
| --- | --- |
| Sittings | 818 held, 817 parsed |
| Passages | 440,347 rows |
| Speech | 244,662 passages, 25.30 million words |
| Stenographer's notes, typed | 69,206 |
| All rows together | 29.63 million words, the rest being headings and page matter kept only for tracing (`type == "furniture"`) |
| Passages the parser could not attribute | 6,514 (1.48%), most of them matter inserted into the record without being spoken |
| (sitting, label) pairs | 23,922, of which 22,708 resolve to a person |

Coverage is complete from 2002 onward: every sitting the portal lists for those
years is here. Before that it is partial, because the portal lists the sittings
but no longer serves every file — 51 of 73 for 1998, 47 of 74 for 1999, 46 of
75 for 2000, 44 of 83 for 2001. Of the 882 sittings the portal lists before
1998, exactly one is still served: an impeachment tribunal of 18 December 1997,
a photocopy saved as page images with no text in it, which is why it is the one
sitting that does not parse.

The code is developed in the open at
<https://github.com/jpripamonti/ar_congress>, whose working log, `TODO.md`,
records every change to the parser with the evidence for it. Where this
README or the data dictionary cites that log or a commit, that is where to
find it.

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
data/raw/senado/fichas_archivadas/       Internet Archive captures of senators' own pages, 2 February 1998
reference/senado/                        rosters, roll-call caucus readings, hand-dated caucuses
reference/gold/                          72 PDF pages annotated for scoring
reference/gold_html/                     24 HTML stretches annotated for scoring, each read twice
raw_data_manifest.csv                    every source file: sha256, source URL, format, size, provisional or not
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

corpus = pd.read_parquet("data/processed/senado/blocks")  # the whole folder
speakers = pd.read_parquet("data/processed/senado/speakers.parquet")

speech = corpus[corpus["type"] == "speech"]
named = speech.merge(speakers.drop(columns="session_date"),
                     on=["session_id", "speaker_raw"], how="left")
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
  sat with.** They fall in different political camps for 16.5% of floor speech,
  mostly provincial alliances whose senators sit with a national caucus. For
  anything about how the chamber divided, use the caucus.
- **Count turns by `turn_id`, not by rows.** A turn interrupted by applause, or
  split across a page break, is several rows.

## Rebuilding it from the sources

```sh
uv sync
uv run scripts/download.py --from-manifest  # every file the manifest names, checked by SHA-256
uv run scripts/parse.py --force     # PDFs -> per-sitting Parquet + parse_stats.csv
uv run scripts/parse_html.py --force # the 1998-2003 HTML exports, into the same tables
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

The download is 819 files, 1.1 GB, fetched one at a time with a pause
between requests so as not to load the Senate's site: allow a little over an
hour. `--force` is needed because the bundle already holds the parsed
tables, and without it the parsers skip every sitting whose table exists.
The steps that build one table out of all the sources —
`extract_authorities.py`, `extract_chair_caucus.py`, `check_gold.py` and
the source checks of `audit_parse.py` — stop and name what is missing if any
file they read is not there, rather than write a partial table.
`make_manifest.py` is the maintainer's tool for a fresh download and is not
part of the rebuild: it needs the portal's metadata record saved beside each
file, which `--from-manifest` does not fetch, and refuses without it.

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

The audit is a list of things to look at, not a pass or fail: it exits with
status 1 whenever it lists anything, and on this build it lists 13 — among
them the seven turns that open in lower case, the few labels printed with a
stray parenthesis and the two sittings whose opening note gives the wrong
year, each of them printed that way on the page. The checks marked "must be
0" are the ones that must be 0, and they are. Re-parsing rewrites
`parse_stats.csv` with the time of the run and how long each sitting took, so
`CHECKSUMS.sha256` stops matching that one file after a rebuild; it is for
checking the download, not the rebuild. The checks also write their detail
(`gold_eval.csv`, `gold_html_eval.csv`, `audit_source.csv`,
`blind_read_check.csv`) beside the tables; those files are not shipped.

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

- **72 PDF pages annotated from the page images**, spanning 1998–2024, and
  shipped in `reference/gold/` — the annotations for all 72, and the
  rendered image of 41 of them in `reference/gold/pages/`; the other 31 are
  checked against their PDFs, which `download.py --from-manifest` fetches.
  Every annotation was made by a language model (Claude) reading the
  rendered page, and no person has checked them. How independent of the
  parser they are differs by batch: the first 24 pages were annotated in the
  sessions that were building the parser, and nothing records whether its
  output was in view; the next 12 were read from the rendered page rather
  than from the parser's output; the 36 added in September 2026 were read
  against a written brief without the parser's answer, twice, in two separate
  runs of the same model, and the two readings agree on every turn start —
  which shows the brief was read the same way twice, not that the reading is
  right. Scored against them: boundary and attribution F1 = 1.000, 310 of 310 turns,
  the same on the printed label alone and on the label carried with the turn's
  opening words. Stenographer's notes: precision and recall 1.000, 82 of 82.
  Read the interval, not the point: a perfect 310 still puts the 95% interval
  on recall at 0.988 to 1.000, and the 72 pages come from 60 documents, the
  turns from 41 of them.
- **24 stretches of the HTML era**, about 7,000 characters each, cut on the
  source file by offset and never at a boundary the parser found, annotated
  the same way: the same model, twice, from the same brief. The two readings
  agree on all 195 turn starts, and both score 195 of 195, notes included.
- **Every parsed sitting audited against its own source file**: no page apparatus inside a speech
  turn outside the three scans, no turn carrying a second speaker's label
  outside the scans (8 inside them), no
  document yielding more text than it prints (0 of 817), and every one of
  14,443 labels of the HTML era's commonest shape — a bold run that begins at
  the heading above — attributed to its own speaker. 153,480 passages were
  probed against the source and 81 could not be located (0.053%), 69 of them
  in the two scans; with the scans set aside it is 12 of 153,219 (0.008%), no
  sitting above 1%. 7 passages of 244,662 open in lower case under a new
  speaker, each on a whole word, and every one is printed that way.
- **6,819 turns read blind** across thirteen rounds, each by a language model
  reading the rendered page (for the HTML era, the source file) and never
  shown the parser's answer, and
  re-asked of this build: 6,516 still resolve to the
  person the round recorded and none resolves to anybody else. 303 cannot be
  re-asked — 264 quote words the page prints under two different names, 33 are
  passages a repair has since taken out of speech, 5 quote too damaged to locate,
  and 1 has no words recorded.
  Those records are not in this deposit; the count is what they produced.
- **29 turns checked by a person against the page images** (for the six
  sittings of 1998–2003, against the source text, which has no pages), one a year from
  1998 to 2026: all 29 agree with the parser. The person saw each page with
  the passage marked and the parser's answer beside it, and took about four
  minutes for the 29, so this is a check that the answer is plausible on the
  page, not a blind reading. The record of it stays in the repository.
- **Caucus**: 98.7% of senators' passages, in the chair or on the floor,
  carry one — 87.8% confirmed,
  9.4% marked anachronistic because the Senate's own record names a caucus
  that did not exist on the day of the sitting, 0.7% disputed, 0.6%
  undatable, and 0.2% inferred across a gap or deduced from the chamber's
  official count per caucus. Those are kept and marked, never corrected or
  dropped. The chamber publishes a count of senators per caucus for each
  renewal; set beside it on 1 March of 1999, 2000, 2002 and 2004, the corpus
  differs by one senator in seven caucus counts. `scripts/check_bloc_counts.py`
  lists the caucus's senators where the corpus has one too many and names
  nobody where it has one too few; the 2002 shortfall is a senator missing
  from the roster, not a caucus wrongly given.

## What it gets wrong

- **309 of the 819 source files, mostly 2002–2015, are the Senate's
  provisional record**, the uncorrected version it publishes first; 170 more
  do not say. The corpus reads whichever version the portal served, and
  `provisional` in `raw_data_manifest.csv` says which each file is.
- **Three sittings are scans read by character recognition**:
  `2001-11-21_r72`, `2001-11-29_r74`, and the 1997 tribunal, which yields
  nothing at all. Their text is unreliable; `parse_stats.csv` flags them
  (`scanned_page_share`), and they should be excluded from text analysis.
- **6,514 passages carry no speaker, and most of them were never spoken.** In
  the HTML era 83% of those words stand inside a run of inserted matter —
  speeches handed in for the record and never delivered, and the bills read
  into it. In the PDF era 89% of those words stand in a run the page opens
  with a note ending "…es el siguiente:" or "…son los siguientes:" — bills,
  work plans, lists of titles.
- **19 printed speaker labels still open a turn that leaves no row.** 6 are in
  the November 2001 scan, and 3 are the secretary's label of 16 June 1999
  printed over an Orden del Día with nothing of his own after it. The other
  10 are labels whose words the page gives only as a note in its own
  paragraph ("— Contenido no inteligible.", a remark made off the
  microphone, "(Lee)" over a document), or as a document or list that is
  nobody's. Whether such a label opens a turn is a question of definition,
  left open rather than decided silently.
- **112 speech passages carry a label that resolves to nobody** (0.05%), and 45
  one that fits more than one senator; the label is kept either way.
- **The 1998–1999 caucus has gaps.** No roster of the chamber's caucuses
  survives for those years, so they are rebuilt from the chair's own calls,
  senators' statements on the floor and archived personal pages. 2,100
  senators' passages (1.3%) carry no caucus, 97 of them in 1998–1999; most of
  the rest fall in 2014 (578), 2005 (437), 2006 (248) and 2015 (219).
- **Roughly a fifth of each document is dropped on purpose** — contents pages,
  attendance rolls, appendices, inserted documents that were never spoken.
  The median sitting keeps 82.2% of its printed text.
- **The text is what the page prints, not what was said.** A stenographic
  record is edited, and senators correct their own words afterwards.

## Checking what you downloaded

```sh
shasum -a 256 -c CHECKSUMS.sha256
```

Run from the unpacked directory. It covers every file in the bundle except
itself; the archive's own SHA-256 is published beside the archive.

## Licence

Three kinds of material are in here, under different terms.

- **What this project added** is
  [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/): reusable,
  including commercially, with attribution. That is the structure of the
  corpus and everything said about each passage — its type, speaker label,
  turn, section and page — together with the resolved speakers and caucuses,
  the compiled reference tables, the annotations and the manifest.
- **The Senate's words and documents are not relicensed.** That covers the
  `text` column, which reproduces the record, the page images and HTML
  fragments the annotations are checked against, the Senate's own list of
  senators (`senadores_historico.json`), and the archived Senate pages under
  `data/raw/senado/`. Argentine copyright law (Ley 11.723, art. 27) allows
  parliamentary speeches to be published, but not for profit without the
  speaker's authorisation. Commercial use of the text is therefore a matter
  between the user and the rights holders. Cite the chamber as publisher, with
  the sitting date and the per-sitting URL from `raw_data_manifest.csv`. The
  source files are not redistributed.
- **The code** in `scripts/`, and the prose of the documentation, are MIT
  ([LICENSE](LICENSE)).

[LICENSE-DATA](LICENSE-DATA) lists exactly what each part covers.

## Citing it

> Ripamonti, J. P. (2026). *Argentine Senate stenographic transcripts,
> 1998–2026: a speaker-attributed corpus* (version 0.5.8) [Data set]. Zenodo.
> <https://doi.org/10.5281/zenodo.22661019>

That is the concept DOI, which always resolves to the latest version. Cite it
unless the exact bytes matter.

[CITATION.cff](CITATION.cff) carries the same in machine-readable form.
