# ar_congress

Corpus of Argentine Senate stenographic session transcripts ("versiones
taquigráficas"): acquisition, parsing into structured speaker-attributed
text blocks, and (eventually) analysis.

## Status (July 2026)

- 559 session transcripts held, spanning 2000–2024. Coverage is complete
  from 2004 onward — every session the portal lists for those years is
  held. Before that it thins out fast, because the portal lists the
  sessions but no longer serves the files: 34 of 47 held for 2003, 4 of 47
  for 2002, 10 of 83 for 2001, 3 of 75 for 2000. Sessions are listed back
  to 1983, but nothing before 2000 is served at all, so 2000 is the hard
  floor. Every held session is in the provenance manifest
  ([raw_data_manifest.csv](raw_data_manifest.csv): sha256 of the PDF and
  its metadata sidecar, source URL, size, download time), regenerated from
  the files on disk by `scripts/make_manifest.py`. The 90 sessions fetched
  in January 2025 predate the download-timestamp field, so theirs is blank
  rather than guessed.
- Corpus parsed (parser 0.4.3): ~154,700 speaker-attributed speech blocks
  and ~28,000 typed stenographer events in 257,000 rows, as per-session
  Parquet under `data/processed/senado/`. One session fails to parse — a
  November 2001 sitting that never reached quorum, so it has no session
  opening to find. Text the parser cannot attribute to a speaker is 2,191
  blocks, and nine sessions account for most of it: sittings whose record
  is mostly an inserted document (two impeachment dossiers, a printed bill
  text, a list of judicial appointments) rather than floor debate. Gold-set
  evaluation on 36 stratified pages spanning 2003–2024: utterance
  boundary+attribution F1 = 1.00 (124 of 125 annotated turns), event
  recall = 0.90, no speech leaking onto contents pages (gold set pending
  owner audit — see [SOURCES.md](SOURCES.md)).
- Speakers resolved to persons (roster + authorities join) for 2020–2024:
  99.95% of speech blocks carry a person_id with party/alliance and
  province. The 2000–2019 sessions still need the officers table extended
  backwards before the same join runs over them.
- First analysis: [notebooks/analysis.ipynb](notebooks/analysis.ipynb).
  Roadmap in [TODO.md](TODO.md).

## First results

These cover 2020–2024 only; the earlier sessions are parsed but not yet
joined to person records.

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
