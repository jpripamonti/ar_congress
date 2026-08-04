# ar_congress

Corpus of Argentine Senate stenographic session transcripts ("versiones
taquigráficas"): acquisition, parsing into structured speaker-attributed
text blocks, and analysis.

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
- Corpus parsed (parser 0.4.10): 152,577 speaker-attributed speech blocks
  and 31,923 typed stenographer events in 242,238 rows, as per-session
  Parquet under `data/processed/senado/`. One session fails to parse — a
  November 2001 sitting that never reached quorum, so it has no session
  opening to find. Text the parser cannot attribute to a speaker is 1,884
  rows (0.8%), and a handful of sessions account for most of it: sittings
  whose record is mostly an inserted document (two impeachment dossiers, a
  printed bill text, a list of judicial appointments) rather than floor
  debate.
- Two layers of verification, because they answer different questions.
  **On a hand-annotated sample** — 36 stratified pages spanning 2003–2024 —
  utterance boundary+attribution F1 = 1.00 (124 of 125 turns), event
  precision 1.00 and recall 0.94, no speech leaking onto contents pages. The
  annotations have themselves been checked back against the source PDFs
  (`scripts/check_gold.py`, 36 of 36 pass) — a second machine reading, not an
  independent human audit. **On all 559 sessions** (`scripts/audit_parse.py`):
  no turn carries a second speaker's label, no label is absorbed by the section
  title above it, one page's footer leaks into speech, no text is written out
  twice, and a median 79.5% of each document's printed text is kept (the rest —
  contents pages, attendance rolls, appendices — is dropped by design). Two
  sittings of November 2001 are scans with OCR text and should be excluded from
  any text analysis; the parser flags them. **On 1,798 pages read blind** — every
  page rendered as an image and read by an agent that was never shown the
  parser's answer, then compared — the two agree on who is speaking in
  [300 of 300](reference/verification/blind_read_300.csv),
  [497 of 500](reference/verification/blind_read_500.csv) and
  [993 of 998](reference/verification/blind_read_1000.csv) on three samples that
  do not overlap, spread across every year of the span. Every case left over was
  checked afterwards against the page image and the parser is right in all of
  them — mostly pages that print the quoted phrase twice, so the reader could not
  know which occurrence was meant. Earlier rounds of the same read are what
  exposed four of the defects fixed in 0.4.7–0.4.10; the 1,498 pages drawn since
  the last fix found nothing further. Details and figures:
  [SOURCES.md](SOURCES.md).
- Speakers resolved to persons: **70% of all speech blocks name a person**,
  with the ticket they were elected on and their province. A further 28% is
  a chamber office speaking under its bare title ("Sr. Presidente", "Sr.
  Secretario", no surname), which is how the transcripts printed it before
  about 2016. **These are deliberately left without a person.** The chair
  changes hands during a sitting and the page does not say who holds it, so
  any name would be a guess; the sitting's own cover page names two or more
  presiding officers in 282 of the 559 sessions. They are marked as
  office-known-person-unstated. Another 1.3% is correctly out of scope —
  parties and witnesses at the impeachment trials, deputies, foreign heads
  of state, officials of other institutions. **Genuine lookup failures are
  down to 0.1%** (220 blocks), nearly all of them invited outside speakers
  at public hearings, named by surname alone.
- Analysis over the whole span: [notebooks/analysis.ipynb](notebooks/analysis.ipynb).
  Roadmap in [TODO.md](TODO.md).

## Results

![Senate floor words by year and party family](figures/floor_words_by_year.png)

- The Peronist/Justicialist family holds 30% to 56% of floor words in the
  fully held years, median 48%, across four changes of national government.
  It is the largest single family in 18 of those 21 years; in 2013, 2014 and
  2015 the provincial-and-other bucket was larger, but that bucket is a
  residual holding many separate alliances rather than one family — and
  regrouping the same speech by the caucus each senator actually sat in makes
  the peronist family the largest in every one of the twenty years the caucus
  data covers.
![The same floor speech grouped by ticket and by caucus](figures/ticket_vs_caucus.png)

- **What moved is mostly the labels, and the caucus data now shows it rather
  than merely warning about it.** By ticket, provincial and other alliances
  held 30–46% of floor words to 2016 and 13–15% from 2020, while the
  radical/Cambiemos family went the other way (9–25% before 2019, 30–39%
  after) — a chamber that looks realigned at a stroke. Group the identical
  speech by caucus and the step disappears: radical/Cambiemos sits at 23–37%
  throughout, and provincial and other alliances end 2022–2024 at 16–20%
  rather than 13%. Senators did not change sides in 2019; the tickets they had
  been elected on consolidated into two national coalitions. All 62 caucuses are
  dated by hand ([blocs_manual.csv](reference/senado/blocs_manual.csv)), each
  against the sitting that attests it, because the Senate records a caucus once
  per mandate and backdates it over the whole term.
- The 2020–2023 collapse was mostly fewer sittings, not quieter ones. Floor
  words fell 6.4-fold, which splits into a 3.9-fold fall in sittings held
  (31 to 8) and only a 1.65-fold fall in words per sitting. By 2024 a
  sitting was as long as ever; there were simply twelve of them.
- The chamber has been getting steadily more disorderly since about 2013.
  Recorded incidents per 10,000 floor words ran near 1 through the 2000s
  and peaked at 12.3 in 2023 — roughly a tenfold rise, beginning well
  before the remote sittings of 2020. This is a measurement only possible
  because stenographer events are preserved and typed rather than deleted.

Methodological caveats (incomplete holdings before 2004, session-type mix,
chairs excluded) are documented in the notebook and in
[SOURCES.md](SOURCES.md). The caucus view carries its own: the Senate records
a caucus once per mandate and stores the one the senator **ended** it in,
projected backwards over the whole term. All 62 caucuses are dated by hand
against the sittings that attest them, but a senator who crossed the floor
mid-term is still invisible, four caucuses rest on the mandate calendar alone,
6.9% of floor words end up with no caucus and are excluded — unevenly, so 2017
and 2018 keep only about three quarters of theirs — and the records begin only
in 2005.

## Layout

- `scripts/download.py` — fetch session PDFs + metadata sidecars from the
  Senate open-data portal.
- `scripts/parse.py` — parse PDFs into per-session Parquet block tables
  (speech turns, typed events, headings), plus per-session logs and a
  `parse_stats.csv` quality table.
- `scripts/fetch_roster.py` — fetch senator roster datasets into
  `reference/senado/`.
- `scripts/fetch_blocs.py` — read one roll-call record per sitting date back
  to 2005 into `reference/senado/bloques_por_fecha.csv`: which caucus each
  senator sat with, which the roster publishes only for sitting members.
- `scripts/map_blocs.py` — collapse those readings into per-senator caucus
  spells and file each caucus under the analysis's party families.
- `scripts/extract_authorities.py` — read each sitting's masthead into
  `reference/senado/authorities_observed.csv`: who presided and who sat at
  the secretaries' table, per sitting.
- `scripts/resolve_speakers.py` — resolve speaker labels to persons
  (`data/processed/senado/speakers.parquet`).
- `scripts/eval_gold.py` — score the parser against the gold annotations
  in `reference/gold/`.
- `scripts/check_gold.py` — check those annotations against the source PDFs.
- `scripts/audit_parse.py` — audit every session against its PDF: apparatus
  leaking into speech, undetected speaker changes, duplicated or invented
  text, coverage, scans. `--sample N` also writes a review sheet of N turns
  to be checked by eye against the printed page.
- `reference/verification/` — the four blind reads: what the parser said, what an
  independent reader saw on the page, and whether they agree. 998 pages in the
  last round, 500 before it, 300 before that, 50 in the first.
- `reference/` — versioned reference data: roster snapshots, authorities
  tables, gold evaluation set. Provenance: [SOURCES.md](SOURCES.md).
- `data/` — symlink to the OneDrive working copy; not in git (see
  [DATA.md](DATA.md)).

## Setup

```sh
uv sync
uv run scripts/parse.py --help
uv run scripts/download.py --dry-run   # compare local holdings vs. the live listing
```

The pipeline runs in this order: `download.py` → `parse.py` →
`extract_authorities.py` → `resolve_speakers.py`, then `eval_gold.py` and
`check_gold.py` to verify.

On a new machine, re-create the `~/PARA/_working-data` symlink first (see
DATA.md).

## Source

Senado de la Nación Argentina, open-data portal
(<https://www.senado.gob.ar/micrositios/DatosAbiertos/>).

Code in this repository is MIT-licensed (see [LICENSE](LICENSE)). The
transcripts themselves are published by the Senate; their terms of use are
documented separately as part of the corpus work.
