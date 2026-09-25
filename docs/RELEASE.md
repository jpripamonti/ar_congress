# Releasing the corpus so other people can use and cite it

What has to be true before a version of this corpus goes out, how to build it,
and how it should be cited. The dataset itself is not in this repository — the
repository holds the code, the reference tables and the verification records —
so a release is a separate, frozen bundle.

## What goes out

The dataset, the code that produces it, and what a stranger needs to use, check
and cite it — nothing else. `scripts/make_release.py` is the list in code, and
it names the pipeline script by script, so adding a script to the repository
is a decision about the release rather than an accident of a glob.

| Part | Where it comes from | Why it is in the release |
| --- | --- | --- |
| The passages, one file per sitting | `data/processed/senado/blocks/*.parquet` | The corpus itself. |
| The resolved speakers | `data/processed/senado/speakers.parquet` | Turns a printed label into a person, and into the caucus they sat with. |
| The parse record | `data/processed/senado/parse_stats.csv` | What the parser did to each sitting, counted, so every repair can be recomputed rather than trusted. |
| The archived Senate pages | `data/raw/senado/bloques_archivados/`, `data/raw/senado/fichas_archivadas/` | Internet Archive captures of the bloc roster (2000–2004) and of senators' own pages (1997–1998). The Senate pages no longer exist, and the caucus before 2005 cannot be rebuilt without them. |
| The reference tables | `reference/senado/` | Roster snapshots, caucus observations with their sources, hand-dated caucuses, observed authorities. |
| The accuracy sets | `reference/gold/`, `reference/gold_html/` | The annotated PDF pages and HTML stretches the accuracy figures are measured on. |
| The provenance manifest | `raw_data_manifest.csv` | Checksum, source URL, format and download time of every source file. |
| The pipeline | the scripts named in `make_release.py`, `pyproject.toml`, `uv.lock` | The sources are not redistributed and can be fetched again, which takes the code and the pinned versions it was calibrated against, since pdfplumber's character extraction changes between releases. |
| The documentation | `docs/DEPOSIT_README.md` (shipped as `README.md`), `docs/DATA_DICTIONARY.md` | What it is, how to load and rebuild it, how far it was checked, what it gets wrong; what every column means. |
| The citation and the terms | `CITATION.cff`, `LICENSE`, `LICENSE-DATA` | The citation in machine-readable form; MIT for the code, CC BY 4.0 for the data. |

What stays in the repository: the working log (`TODO.md`), this document, the
release notes, the parse logs, the blind-read records, the output of the
checks, the notebook and its figures, the listing snapshots. They are how the
corpus was made and checked, not part of what is published; the bundle's
README states what the checks printed on the released build.

Everything sits at the path the repository gives it, so every path the
documentation names is the path in the bundle, and the scripts run where it is
unpacked.

The source files are **not** redistributed. They are the Senate's to publish,
the manifest identifies each one by checksum and URL, and `scripts/download.py`
fetches them again. This is the same arrangement other parliamentary corpora
use where the source cannot be passed on: release the pipeline and a
record-level manifest, so anyone with access to the sources rebuilds the exact
corpus.

## Before a release goes out

Each of these must pass, and the numbers they print belong in the release notes.

```bash
uv run scripts/parse.py --force && uv run scripts/parse_html.py --force
```

```bash
uv run scripts/fetch_archived_blocs.py --offline && uv run scripts/build_bloc_observations.py && uv run scripts/deduce_bloc_from_counts.py && uv run scripts/build_bloc_observations.py && uv run scripts/resolve_speakers.py && uv run scripts/check_bloc_counts.py
```

```bash
uv run scripts/eval_gold.py && uv run scripts/check_gold.py && uv run scripts/eval_gold_html.py && uv run scripts/check_gold_html.py
```

```bash
uv run scripts/audit_parse.py
```

```bash
uv run scripts/check_blind_reads.py
```

- The PDF parse finishes with one known failure — the 1997 impeachment
  tribunal, a photocopy saved as page images with no text in it. The HTML
  parse finishes with none.
- Boundary and attribution against the 72 annotated PDF pages: F1 = 1.000
  (310 of 310 turns), on the label alone and on the label with the turn's
  opening words alike. Events: precision and recall 1.000 (82 of 82). Against
  the 24 HTML stretches, on either reading: 195 of 195, events included, and
  the two readings agree on every turn start.
- The annotations themselves still check out against the source files: 108 of
  108 (72 pages, 36 of them read twice).
  What that check asks is that each annotated turn's opening words are printed
  on the page immediately after that speaker's own label. It used to look the
  label and the words up separately, so the words only had to appear somewhere
  further down — which passed an annotation crediting one senator's words to
  another, the error the gold set exists to rule out. Moving one turn's words
  onto another speaker's label on each of the 23 usable pages, the old check
  caught none of them and this one catches all 23.
- The audit's invariants hold: no page apparatus inside a speech turn outside
  the scanned sittings, no turn carrying a second speaker's label, no text
  written out twice, and the turns that open mid-word are printed that way.
  The apparatus check counts toward the exit status; it used to be printed and
  not counted, and a leaked footer sat in the corpus for weeks while the audit
  reported nothing wrong.
- A block the audit's three long windows cannot find in the source is asked
  whether the whole of it can be rebuilt from the source in a handful of runs.
  It used to be asked only whether any one 24-character window of it was
  there, which was not a second chance but a hole: measured, genuine text
  checked against the WRONG sitting passed that test 28% of the time, and 24
  real characters vouched for an invented tail of any length. The test that
  replaced it separates: 98.4% of the blocks the long windows miss rebuild
  inside the eight runs allowed, most in two, and a genuine opening with an
  invented tail never does. Because each run must start after the last one
  ends, it also notices a turn whose own sentences came out shuffled — 98.8%
  of 12,987 real multi-sentence turns rebuild in their printed order and 3.6%
  shuffled. A few genuinely printed blocks are reported anyway — two in 243
  merely exceed the cap, and a line whose four ordinals the extractor cannot
  map cannot be rebuilt at any cap. They are a handful on a review list, and
  SOURCES.md works the case through.
- Every name on an archived bloc-roster page still resolves to a senator, and
  the only ones outside their mandate are the two known cases of the page
  lagging the chamber. `build_bloc_observations.py` stops if a name resolves to
  nobody and prints the lagging ones on every run.
- Every answer recorded in the thirteen blind reads still resolves to the same
  speaker in the re-parsed corpus: `check_blind_reads.py` re-asks all 6,819 and
  exits on the number that do not. Each record is settled against the turn that
  best carries the quoted words, not against every turn any window of them
  touches: the earlier version pooled the labels and asked only whether the
  recorded name was somewhere in the pool, so a coincidental match further down
  the page could mask a genuine reattribution — 136 of the 5,090 records this
  lookup settles were decided by such a pool. Where several turns carry the
  words equally well, every one of them must carry the recorded name: asking
  for one was still a hole, because a page that prints the same formula twice
  answers for a reattributed turn with its untouched twin. Reattributing one
  of the tied turns in all 380 records whose words more than one turn prints,
  the old rule noticed 6 and this one notices all 380.

  It tolerates the repairs the rounds themselves prompted — a quote carrying an
  unmapped glyph, an ordinal read as a capital E, a letter cut off a label —
  because those are the project's own progress and not damage; what it will not
  tolerate is the passage still being there under somebody else's name. The
  letter cut off a label is accepted only in the shape a repair actually leaves
  ("Sr. Presidente (Pinedo).- C", the terminator then a letter or two), not on
  any prefix: accepting any prefix would have read "Sra. González" and
  "Sra. González MT" — two senators the record disambiguates by initials — as
  one person.

  264 records cannot be re-asked because the page prints their words under
  two different names, and the record says which page and which words but
  never which of two identical turns the reader was looking at. Those are
  reported as unaskable, not as holding. So are the passages a repair has
  since taken out of speech, and a passage no speech on its page carries but
  something else on that page carries whole is one of them — it is looked for
  there before across the sitting, because across the sitting a single window
  of it turns up in another senator's speech and reads as a reattribution.
  That is what the committee meeting appended to 2014-09-03_r13 did to the two
  records read on its pages once the parser stopped attributing it to the
  sitting; the rule changes those two records and no other of the 6,819.
- The notebook re-executes with no errors and its figures are regenerated.
- `README.md`, `docs/DEPOSIT_README.md` and `docs/DATA_DICTIONARY.md` carry the
  new parser version and the new row counts. `DEPOSIT_README.md` is the one
  that ships, and it describes the release: its numbers change only when a
  release is cut, never to follow the working corpus in between.
- `speakers.parquet` was rebuilt from the same parse as the blocks. It is
  derived from them and goes stale silently: `n_blocks` once disagreed with
  the passages in 35 (sitting, label) pairs because a parser repair had landed
  and the table had not been regenerated. Run the command above in order.

## Versioning

The release version is the parser version that produced it — the PDF parser's,
`PARSER_VERSION` in `scripts/parse.py`, which is what `make_release.py` reads.
The HTML parser carries its own version with an `-html` suffix, and the release
notes name both. A release is worth
cutting when the corpus content changes — a repair that moves text or changes
who is credited with it — not when only the documentation moves. The parse
record and the per-sitting logs say exactly what changed, and the release notes
should say it in words: what was wrong, how many rows it touched, and what
evidence justified the repair.

## How it should be cited

Two things are being cited and they are not the same.

**The transcripts** are the Senate's. Cite the Senate as publisher, with the
sitting date and the per-sitting source URL from the manifest. The portal
publishes no licence page; the governing framework is Argentina's access-to-
information law (Ley 27.275), which obliges publication in formats that permit
reuse and redistribution. The full reasoning is in [SOURCES.md](../SOURCES.md).

**This corpus** — the parsing, the speaker resolution, the hand-dated caucuses
and the verification — is the work in this repository. The code is MIT-licensed
([LICENSE](../LICENSE)). The derived tables and the reference data are licensed
**CC BY 4.0**: reusable, including commercially, on condition of attribution.
The terms and the exact list of what they cover are in
[LICENSE-DATA](../LICENSE-DATA), and every release must carry that file.

A citation should name the corpus, its version, the span it covers and where it
lives, for example:

> Ripamonti, J. P. (2026). *Argentine Senate stenographic transcripts, 2000–2024:
> a speaker-attributed corpus* (version 0.4.37) [Data set]. Zenodo.
> <https://doi.org/10.5281/zenodo.22661020>

Version 0.4.37 has its own DOI, above. To cite the corpus rather than one
release of it, use the concept DOI, which always resolves to the latest:
<https://doi.org/10.5281/zenodo.22661019>.

## Where to put it

A release needs a permanent identifier, which GitHub alone does not give.
Zenodo mints a DOI for each version and keeps one that always points at the
latest, accepts files of this size, and is what social-science and digital-
humanities datasets are normally cited from. Publishing there is a decision for
the author, not something the pipeline should do on its own.

The bundle is a few hundred files of Parquet plus the reference tables, the
archived pages and the documentation — small enough that it needs no special
handling. 0.4.37 came out at 662 files and 68 MB packed; 0.5.8 at 1,250 files, 129 MB
unpacked and 96 MB packed.

Build it from the repository root, after the checks above have passed:

```bash
uv run scripts/make_release.py --force
```

The script is the table above in code. It keeps every file at the path the
repository gives it, because the shipped Markdown links by relative path and
flattening the tree breaks them, and it ships `docs/DEPOSIT_README.md` as the
bundle's `README.md`. It then walks every Markdown file in the bundle and
refuses to write the archive if any relative link points at a file the bundle
does not carry: the first 0.4.37 bundle went out with eight such links, to the
notebook, the figures, the roadmap and, from the release notes, to the licence.

`CHECKSUMS.sha256` goes in the bundle so a downloader can verify every file,
and the release notes carry the checksum of the archive itself. The bundle
lives outside the repository, beside the data it is cut from, because `data/`
is not in Git.

Release notes go in `docs/releases/<version>.md`.
They stay in the repository, and the bundle's README carries what a user needs
from them. The version is tagged in Git as `v<version>` once the notes are
committed.

## Depositing it on Zenodo

The upload is done by hand. Zenodo can take a release straight from GitHub, but
only from a public repository, and this one is private; `.zenodo.json` in the
repository root is written for the day that changes, and until then it is the
record of what to type into the form.

**Reserve the DOI before publishing, not after.** The upload form has a Reserve
DOI button, which hands out the version's DOI while the deposit is still a
draft; for a later version it is the New version button on the published
record, so the concept DOI carries over. Take it before uploading the archive,
because five documents carry the citation and they should carry the DOI with
it — the first two travel in the bundle:

- `CITATION.cff` — the `identifiers` block at the end
- `docs/DEPOSIT_README.md` — the citation at the end
- `README.md` — the citation under Licence and citation
- `docs/RELEASE.md` — the citation above
- `docs/releases/<version>.md` — the citation at the end of the notes

Put it in all five, rebuild the bundle so the shipped copies carry it, then
upload. Zenodo mints two DOIs: the one reserved here belongs to this version,
and a second, the concept DOI, always resolves to the latest version. Cite the
concept DOI in prose and the version DOI when the exact bytes matter.

What goes in the form:

| Field | Value |
| --- | --- |
| Upload type | Dataset |
| Title, authors, description, keywords | as in `.zenodo.json` |
| Version | the parser version, e.g. `0.4.37` |
| Language | Spanish (the transcripts; the documentation is English) |
| Licence | **CC BY 4.0** |
| Files | `ar_congress_senado_<version>.tar.gz` and its `.sha256` |

Zenodo records one licence per deposit, so it says CC BY 4.0, which is what the
data is under. The code inside the bundle is MIT, and the description and
`LICENSE-DATA` say so; the transcripts remain the Senate's and are not
redistributed. Upload the `.sha256` beside the archive because Zenodo's own
file checksums are MD5, so the SHA-256 is worth keeping where the archive is.

The Git tag `v<version>` marks the commit the notes were cut from. If the DOI
arrives after that tag was pushed, leave the tag where it is and let the
deposit be the citable object — a published tag is not worth moving for a line
of documentation.
