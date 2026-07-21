# ar_congress

Corpus of Argentine Senate stenographic session transcripts ("versiones
taquigráficas"): acquisition, parsing into structured speaker-attributed
text blocks, and (eventually) analysis.

## Status (July 2026)

- 90 sessions (2020–2024) downloaded, with a provenance manifest
  ([raw_data_manifest.csv](raw_data_manifest.csv): sha256, source URLs,
  download timestamps).
- Parser writes per-session Parquet block tables to `data/processed/senado/`.
- Analysis: not started. Roadmap in [TODO.md](TODO.md).

## Layout

- `scripts/download.py` — fetch session PDFs + metadata sidecars from the
  Senate open-data portal.
- `scripts/parse.py` — parse PDFs into per-session Parquet block tables
  (one row per speech turn / stenographer note), plus per-session logs and
  a `parse_stats.csv` quality table.
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
