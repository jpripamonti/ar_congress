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
| The archived bloc-roster pages | `data/raw/senado/bloques_archivados/` | HTML, 16 captures. The only copies of a Senate page that no longer exists; the pre-2005 caucus cannot be rebuilt without them. |
| The parse record | `data/processed/senado/parse_stats.csv` | 40 counts per sitting of what the parser did to it, so every repair can be recomputed rather than trusted. |
| The provenance manifest | `raw_data_manifest.csv` | Checksum, source URL and download time of every source file. |
| The reference tables | `reference/senado/` | Roster snapshots, hand-dated caucuses, observed authorities. |
| The verification records | `reference/verification/`, `reference/gold/` | The eight blind reads and the hand-annotated pages, so the accuracy claims can be re-checked and not merely believed. |
| The documentation | `docs/DATA_DICTIONARY.md`, `SOURCES.md`, `README.md` | What the columns mean, where it came from, what its limits are. |

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

- The parse finishes with one known failure — a November 2001 sitting that never
  reached quorum, so it has no opening to find.
- Boundary and attribution against the hand-annotated pages: 1.00.
- The annotations themselves still check out against the source files: 36 of 36.
- The audit's invariants hold: no turn carries a second speaker's label, no text
  is written out twice, and the turns that open mid-word are printed that way.
- Every name on an archived bloc-roster page still resolves to a senator, and
  the only ones outside their mandate are the two known cases of the page
  lagging the chamber. `build_bloc_observations.py` stops if a name resolves to
  nobody and prints the lagging ones on every run.
- Every answer recorded in the eight blind reads still resolves to the same
  speaker in the re-parsed corpus.
- The notebook re-executes with no errors and its figures are regenerated.
- `README.md`, `SOURCES.md` and `docs/DATA_DICTIONARY.md` carry the new parser
  version and the new row counts.

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
and the verification — is the work in this repository. The code is MIT-licensed.
The derived tables and reference data should carry a licence that keeps them
reusable and asks for attribution; **CC BY 4.0** is the fitting choice and is
what the release should state.

A citation should name the corpus, its version, the span it covers and where it
lives, for example:

> Ripamonti, J. (2026). *Argentine Senate stenographic transcripts, 2000–2024:
> a speaker-attributed corpus* (version 0.4.22) [Data set].

## Where to put it

A release needs a permanent identifier, which GitHub alone does not give.
Zenodo mints a DOI for each version and keeps one that always points at the
latest, accepts files of this size, and is what social-science and digital-
humanities datasets are normally cited from. Publishing there is a decision for
the author, not something the pipeline should do on its own.

The bundle is roughly 100 MB of Parquet plus a few MB of reference tables and
records — small enough that it needs no special handling.
