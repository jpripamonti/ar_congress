# ar_congress

Corpus of Argentine Senate stenographic session transcripts ("versiones
taquigráficas"): acquisition, parsing into structured speaker-attributed
text blocks, and (eventually) analysis.

## Status (July 2026)

- 90 sessions (2020–2024) downloaded — verified complete against the live
  listing — with a provenance manifest
  ([raw_data_manifest.csv](raw_data_manifest.csv): sha256, source URLs,
  download timestamps).
- Corpus parsed (parser 0.3.1): ~22,000 speaker-attributed speech turns,
  ~5,900 typed stenographer events, per-session Parquet under
  `data/processed/senado/`. Gold-set evaluation on 24 stratified pages:
  utterance boundary+attribution F1 = 1.00, event recall = 1.00 (gold set
  pending owner audit — see [SOURCES.md](SOURCES.md)).
- Speakers resolved to persons (roster + authorities join): 99.95% of
  speech blocks carry a person_id with party/alliance and province.
- Analysis: not started. Roadmap in [TODO.md](TODO.md).

## Layout

- `scripts/download.py` — fetch session PDFs + metadata sidecars from the
  Senate open-data portal.
- `scripts/parse.py` — parse PDFs into per-session Parquet block tables
  (speech turns, typed events, headings), plus per-session logs and a
  `parse_stats.csv` quality table.
- `scripts/fetch_roster.py` — fetch senator roster datasets into
  `reference/senado/`.
- `scripts/resolve_speakers.py` — resolve speaker labels to persons
  (`data/processed/senado/speakers.parquet`).
- `scripts/eval_gold.py` — score the parser against the gold annotations
  in `reference/gold/`.
- `reference/` — versioned reference data: roster snapshots, hand-compiled
  authorities table, gold evaluation set. Provenance: [SOURCES.md](SOURCES.md).
- `data/` — symlink to the OneDrive working copy; not in git (see
  [DATA.md](DATA.md)).

## Setup

```sh
uv sync
uv run scripts/parse.py --help
uv run scripts/download.py --dry-run   # compare local holdings vs. the live listing
```

On a new machine, re-create the `~/PARA/_working-data` symlink first (see
DATA.md).

## Source

Senado de la Nación Argentina, open-data portal
(<https://www.senado.gob.ar/micrositios/DatosAbiertos/>).

Code in this repository is MIT-licensed (see [LICENSE](LICENSE)). The
transcripts themselves are published by the Senate; their terms of use are
documented separately as part of the corpus work.
