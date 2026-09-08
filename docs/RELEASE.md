# Releasing the corpus so other people can use and cite it

What has to be true before a version of this corpus goes out, how to build it,
and how it should be cited. The dataset itself is not in this repository — the
repository holds the code, the reference tables and the verification records —
so a release is a separate, frozen bundle.

## What goes out

| Part | Where it comes from | Why it is in the release |
| --- | --- | --- |
| The passages, one file per sitting | `data/processed/senado/blocks/*.parquet` | The corpus itself. |
| The resolved speakers | `data/processed/senado/speakers.parquet` | Turns a printed label into a person, and into the caucus they sat with. |
| The caucus observations | `reference/senado/bloque_observado.csv` | Every day one senator's caucus was actually recorded, with the record it came from and how far it can be trusted. |
| The archived bloc-roster pages | `data/raw/senado/bloques_archivados/` | HTML, 17 captures, of which 16 carry names — the seventeenth (14 June 2002) is a truncated Wayback snapshot with no roster in it, kept because it is evidence of the gap. The only copies of a Senate page that no longer exists; the pre-2005 caucus cannot be rebuilt without them. |
| The parse record | `data/processed/senado/parse_stats.csv` | 40 counts per sitting of what the parser did to it, so every repair can be recomputed rather than trusted. |
| The provenance manifest | `raw_data_manifest.csv` | Checksum, source URL and download time of every source file. |
| The reference tables | `reference/senado/` | Roster snapshots, hand-dated caucuses, observed authorities. |
| The verification records | `reference/verification/`, `reference/gold/` | The nine blind reads and the hand-annotated pages, so the accuracy claims can be re-checked and not merely believed. |
| The documentation | `docs/DATA_DICTIONARY.md`, `docs/RELEASE.md`, the release notes, `SOURCES.md`, `README.md`, `TODO.md` | What the columns mean, where it came from, what its limits are. `TODO.md` is in because the README and the release notes cite its phases as the record of what was repaired and on what evidence. |
| The analysis and its figures | `notebooks/analysis.ipynb`, the two figures the README displays | Without them the shipped README shows missing images and links to a notebook that is not there. |
| The citation metadata | `CITATION.cff` | Author, title, version and licence in the form a reference manager can read. |
| The licence | `LICENSE-DATA` | What the data may be used for. The code's MIT licence does not cover it. |

The source PDFs are **not** redistributed. They are the Senate's to publish, the
manifest identifies each one by checksum and URL, and `scripts/download.py`
fetches them again. This is the same arrangement other parliamentary corpora
use where the source cannot be passed on: release the pipeline and a
record-level manifest, so anyone with access to the sources rebuilds the exact
corpus.

The archived bloc-roster pages under `data/raw/senado/bloques_archivados/` are
kept, because unlike the PDFs they are copies of pages that no longer exist
anywhere else and the analysis cannot be re-run without them. Each row derived
from them carries the archive URL it came from.

## Before a release goes out

Each of these must pass, and the numbers they print belong in the release notes.

```bash
uv run scripts/parse.py --force
```

```bash
uv run scripts/fetch_archived_blocs.py --offline && uv run scripts/build_bloc_observations.py && uv run scripts/resolve_speakers.py
```

```bash
uv run scripts/eval_gold.py && uv run scripts/check_gold.py
```

```bash
uv run scripts/audit_parse.py
```

```bash
uv run scripts/check_blind_reads.py
```

- The parse finishes with one known failure — a November 2001 sitting that never
  reached quorum, so it has no opening to find.
- Boundary and attribution against the hand-annotated pages: F1 = 0.996 (124
  of 125 turns), on the label alone and on the label with the turn's opening
  words alike. Events: precision 1.00, recall 0.935 (29 of 31).
- The annotations themselves still check out against the source files: 36 of 36.
  What that check asks is that each annotated turn's opening words are printed
  on the page immediately after that speaker's own label. It used to look the
  label and the words up separately, so the words only had to appear somewhere
  further down — which passed an annotation crediting one senator's words to
  another, the error the gold set exists to rule out. Moving one turn's words
  onto another speaker's label on each of the 23 usable pages, the old check
  caught none of them and this one catches all 23.
- The audit's invariants hold: no page apparatus inside a speech turn outside
  the two scanned sittings, no turn carrying a second speaker's label, no text
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
- Every answer recorded in the nine blind reads still resolves to the same
  speaker in the re-parsed corpus: `check_blind_reads.py` re-asks all 5,463 and
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

  43 records cannot be re-asked because the page prints their words under two
  different names, and the record says which page and which words but never
  which of two identical turns the reader was looking at. Those are reported
  as unaskable, not as holding.
- The notebook re-executes with no errors and its figures are regenerated.
- `README.md`, `SOURCES.md` and `docs/DATA_DICTIONARY.md` carry the new parser
  version and the new row counts.
- `speakers.parquet` was rebuilt from the same parse as the blocks. It is
  derived from them and goes stale silently: `n_blocks` once disagreed with
  the passages in 35 (sitting, label) pairs because a parser repair had landed
  and the table had not been regenerated. Run the command above in order.

## Versioning

The release version is the parser version that produced it. A release is worth
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

> Ripamonti, J. (2026). *Argentine Senate stenographic transcripts, 2000–2024:
> a speaker-attributed corpus* (version 0.4.37) [Data set]. Zenodo.
> <https://doi.org/10.5281/zenodo.22661020>

## Where to put it

A release needs a permanent identifier, which GitHub alone does not give.
Zenodo mints a DOI for each version and keeps one that always points at the
latest, accepts files of this size, and is what social-science and digital-
humanities datasets are normally cited from. Publishing there is a decision for
the author, not something the pipeline should do on its own.

The bundle is roughly 100 MB of Parquet plus a few MB of reference tables,
records and documentation — small enough that it needs no special handling.
0.4.37 came out at 92 MB across 671 files, 67 MB packed.

Build it from the repository root, after the checks above have passed:

```bash
uv run scripts/make_release.py --force
```

The script is the table above in code. It keeps every file at the path the
repository gives it — the release notes stay under `docs/releases/` — because
the shipped Markdown links by relative path and flattening the tree breaks
them. The one link that cannot travel, the README's pointer to `DATA.md`, is
rewritten to name the repository instead, and the build stops if that link is
not found rather than passing silently. It then walks every Markdown file in
the bundle and refuses to write the archive if any relative link points at a
file the bundle does not carry: the first 0.4.37 bundle went out with eight
such links, to the notebook, the figures, the roadmap and, from the release
notes, to the licence.

`CHECKSUMS.sha256` goes in the bundle so a downloader can verify every file,
and the release notes carry the checksum of the archive itself. The bundle
lives outside the repository, beside the data it is cut from, because `data/`
is not in Git.

Release notes go in `docs/releases/<version>.md` and travel inside the bundle.
The version is tagged in Git as `v<version>` once the notes are committed.

## Depositing it on Zenodo

The upload is done by hand. Zenodo can take a release straight from GitHub, but
only from a public repository, and this one is private; `.zenodo.json` in the
repository root is written for the day that changes, and until then it is the
record of what to type into the form.

**Reserve the DOI before publishing, not after.** The upload form has a Reserve
DOI button, which hands out the version's DOI while the deposit is still a
draft. Take it before uploading the archive, because four documents in the
bundle carry the citation and they should carry the DOI with it:

- `CITATION.cff` — the commented `identifiers` block at the end
- `README.md` — the citation in the Source section
- `docs/RELEASE.md` — the citation above
- `docs/releases/<version>.md` — the citation at the end of the notes

Put it in all four, rebuild the bundle so the shipped copies carry it, then
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
