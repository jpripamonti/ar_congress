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

## Phase 2 — corpus quality (done, July 2026 — parser 0.3.1)

- [x] Events subtyped (timestamp/vote/pause/applause/laughter/incident/stage);
      inline italic fragments merged back into speech instead of splitting turns
- [x] Per-document calibration (body-size candidates with retry) + positional
      header AND footer strips keyed on cross-format invariants; unattributed
      debris fell 10,236 → ~130 rows corpus-wide
      (font family stays OUT of the grouping key on purpose: ilovepdf files
      rewrite fonts mid-heading; heading/label fusion is handled by the
      double-space split instead)
- [x] Speaker labels gated + turn_id semantics (a printed label opens a turn;
      speech resuming after an event stays in the same turn)
- [x] Speaker → person resolution (`scripts/resolve_speakers.py` + roster and
      authorities in `reference/senado/`): 99.95% of speech blocks resolved;
      residue is 16 blocks of explicit unmatched/ambiguous/out-of-scope
- [x] Gold-set evaluation (`reference/gold/`, `scripts/eval_gold.py`):
      boundary+attribution F1 = 1.00 (59/59), event recall 1.00,
      appendix leakage 0 on 24 stratified pages
- [x] SOURCES.md: terms (Ley 27.275), provenance, citation guidance

Owner-audit items carried forward:
- [ ] Verify the machine-assisted gold annotations (24 files, ~30 min read)
- [ ] Verify cabinet-chief tenure dates in authorities_manual.csv (marked)
- [ ] Decide the event convention for parenthesized applause (parser: event)
- [ ] Party/bloc caveat: historic roster gives electoral alliance, not caucus;
      caucus is only known for the sitting 72

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
