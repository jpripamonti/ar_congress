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
- First analysis: [notebooks/analysis.ipynb](notebooks/analysis.ipynb).
  Roadmap in [TODO.md](TODO.md).

## First results

![Senate floor words by year and alliance lineage](figures/floor_words_by_year.png)

- Senator floor speech collapsed six-fold from the 2020 remote-session
  peak (1.35M words) to the 2023 election-year trough (0.21M), with only
  a partial 2024 rebound.
- The Frente de Todos / UP lineage held roughly half of floor words in
  every year; La Libertad Avanza enters in 2024 with 7%.
- The chamber got rowdier as it got quieter: recorded incidents per
  10,000 floor words quadrupled 2020→2023 and stayed elevated — a
  measurement only possible because stenographer events are preserved
  and typed rather than deleted.

Methodological caveats (sampling frame, alliance-vs-caucus, exclusions)
are documented in the notebook.

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
