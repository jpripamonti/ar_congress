# Roadmap

Phased plan from the July 2026 adversarial review. Target: a research-grade,
citable corpus.

## Phase 1 — restructure & persist (done, July 2026)

- [x] Flatten repo to `scripts/` layout; delete empty scaffolding
- [x] Persist parser output: per-session Parquet + logs + `parse_stats.csv`
      under `data/processed/senado/`
- [x] Tag stenographer blocks (`type="stenographer_note"`) instead of deleting
      them — the original TODO here: they carry context (e.g. incidents that
      never appear as spoken words). Keeping them also stops turn fusion
      across events.
- [x] Harden downloader: atomic writes, `%PDF` validation, session-identity
      resume, listing archive, reunion-aware filenames
- [x] Parse all 90 sessions with parser 0.2.0; triage `parse_stats.csv`

## Phase 2 — corpus quality (research-grade)

- [ ] Subtype stenographer/event rows (`vote_action` / `pause` / `applause` /
      `incident` / `timestamp` / `stage_note`), ParlaMint-style; distinguish
      true events from inline-italic fragments
- [ ] Per-document calibration: modal body size + positional (bbox)
      header/footer detection. The exact `== 12.0` rules were calibrated on
      one ilovepdf-recompressed PDF (10.1 pt); most of the corpus is
      Word-native 10.0 pt — failure rate correlates with session type.
- [ ] Restore font family to the block-grouping key (currently headings can
      fuse with speaker labels; only style+size break blocks)
- [ ] Speaker → person resolution: roster table (Senate open data) with
      person_id, role, party/bloc, province; chair parentheticals as join key
- [ ] Evaluation: 24-page stratified gold set (every year × session type,
      including the ilovepdf outlier); report boundary F1, attribution
      accuracy, event recall; per-session acceptance gates, quarantine
      failures instead of averaging over them
- [ ] Choose a license; document source-data terms and citation

## Phase 3 — first analysis

- [ ] One notebook: load the corpus, one real chart (e.g. speaking share by
      bloc over time), result into README
- [ ] Document the sampling frame: 52/90 sessions are ESPECIAL (COVID
      remote-procedure era), 2020 has 32 sessions vs 12 in 2023, Asambleas
      (President speaking) are not Senate debate

## Explicitly not building

Packaging/PyPI, docs site, utils wrappers, test-file mirror, separate
analysis modules before a notebook needs them. Diputados and pre-2020
(the archived listing has 1,814 rows back to the 90s) wait until the Senate
corpus is queryable end-to-end.
