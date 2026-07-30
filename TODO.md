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

Owner-audit items, closed in Phase 5:
- [x] Verify the machine-assisted gold annotations — `scripts/check_gold.py`
      re-reads all 36 annotated pages against the source PDFs; 36 of 36 pass.
      A second machine reading, not an independent human audit.
- [x] Verify cabinet-chief tenure dates in authorities_manual.csv — each
      cross-checked against official announcements of the swearing-in, and
      against the sittings where the record names the officeholder. No row
      rests on a Boletín Oficial decree, and the notes now say so.
- [x] Decide the event convention for parenthesized applause — it stays an
      event. Nobody utters "aplausos"; the note is the stenographer recording
      what the chamber did. The parser was made consistent about it.
- [x] Party/bloc caveat — the resolved-speaker column is now named
      `party_or_alliance`, the resolver prints the caveat on every run, and
      SOURCES.md explains where the two diverge.

## Phase 3 — first analysis (done, July 2026)

- [x] notebooks/analysis.ipynb: floor words by year × alliance lineage
      (stacked bars, validated palette), chamber-temperature event rates,
      top speakers; headline chart + findings in README
- [x] Sampling frame documented in the notebook (COVID-era ESPECIAL skew,
      2020: 32 sessions vs 2023: 12, Asambleas excluded from floor-speech
      analyses, alliance-lineage ≠ caucus)

## Phase 4 — backward extension (in progress, July 2026 — parser 0.4.0)

Owner chose to widen coverage before publishing.

- [x] Feasibility probe across 1983–2019. **The portal lists 1,814 sessions
      back to 1983 and every row carries a download URL, but nothing before
      2000 is actually served** — 10 of 10 sampled requests across 1983–1999
      return a 404 or an HTML error page. The real extension universe is
      2000–2019 = 669 sessions. Every file from 2000 on is a true text PDF,
      so no OCR is needed anywhere, and the 12-point body-text invariant
      holds across the whole span.
- [x] Ingest 2010–2019 (219 sessions). Corpus is now **309 sessions,
      2010–2024**, 0 parse errors.
- [x] Parser 0.4.0 — the 2000–2013 layout family. Those years shatter a
      single speaker label across style runs (bold "Sr. Presidente" +
      normal "(Pampuro)" + bold ". –"), and the leftover punctuation shard
      used to be read as a section heading, which dropped the running
      speaker and orphaned every following paragraph. Also: single-character
      style flips (a lone "º" or period) that split one sentence into three
      blocks; the 2013 convention of repeating only the bare parenthetical
      "(Rojkés de Alperovich)" for later chair turns; the U+2212 minus sign
      used as the em-dash in some years; and post-session appendix debris.
      Two 2010–2013 sessions went from 45% and 68% unattributed text to 1%
      each. Gold set unchanged: F1 = 1.00.
- [x] Ingest 2000–2009. 250 more sessions retrieved, 200 URLs dead — and
      the dead ones cluster by year (72 in 2000, 72 in 2001, 43 in 2002,
      13 in 2003, none from 2004 on). **The corpus is now complete from
      2004 onward and partial for 2000–2003; that is a portal limit, not a
      gap we can close.** Corpus: 559 sessions, 1 parse failure (a
      November 2001 sitting with no quorum, hence no session opening).
- [x] Parser 0.4.1–0.4.3 for the 2000–2009 layouts: section titles fused
      onto chair labels (with and without a separating space), a lone
      space breaking "Sr." from "Presidente", appended roll-call plates
      with their own running header and page numbers (now cut by a general
      rule — a line repeating at the SAME HEIGHT on five or more pages),
      and decorative bullets in fonts with no character mapping.
      Unattributed text across the whole span: 2,191 blocks in 257,000
      rows, median 0.2–0.4% per session in the 2000s and 0.0% from 2010.
      Nine sessions sit above 10%, all of them sittings whose record is
      mostly an inserted document rather than floor debate.
- [x] Speaker → person resolution re-run over the whole span. 63% of speech
      blocks name a person. The chair speaking under its bare office title
      ("Sr. Presidente") — 28% of blocks — is recorded as office-known,
      person-unstated **by decision, not by failure**: the chair rotates
      within a sitting and the page never says who holds it, so naming one
      would be inventing an attribution.
- [x] Close the remaining 9% of genuine lookup failures — see Phase 5.
- [x] Add gold-annotated pages per era; re-run the evaluation. 12 pages
      added (two per era back to 2003), and they immediately earned their
      keep: the modern-only set scored 1.00 while the widened set scored
      0.91 and exposed two real defects, fixed in parser 0.4.4. Back to
      F1 = 1.00 (124/125 turns) on 36 pages spanning 2003–2024.
- [x] Regenerate the provenance manifest — now 559 rows, rebuilt from the
      files on disk by `scripts/make_manifest.py` instead of by hand

## Phase 5 — close the open items (done, July 2026 — parser 0.4.6)

- [x] Parser 0.4.6 for the label debris the backward extension exposed.
      One 2004 file draws its dashes, quotes and inverted question marks in
      a subsetted Courier whose character map is wrong, so an em dash came
      out as a literal "C" and swallowed each turn's opening words into the
      speaker label; every glyph was read off its own contexts and mapped
      back, guarded by a run-length test so the sittings that really do set
      text in Courier are untouched. Also: labels where both brackets are
      bold and the chair's surname sits in roman between them, speech glued
      into the bold label after its terminator, and terminators drawn from a
      symbol font with no Unicode mapping.
- [x] Officers resolved from the sittings' own mastheads.
      `scripts/extract_authorities.py` reads the masthead of all 559
      sittings — who presided, who sat at the secretaries' table, with full
      names — into `reference/senado/authorities_observed.csv`, and the
      resolver folds those observations into tenure spans. This is what the
      earlier note meant by "the evidence is in hand".
- [x] National executive added to the hand-compiled table: presidents of the
      Nation and cabinet chiefs back to 1999, each sourced to the sitting
      where the record names them.
- [x] Office families, so the record's looseness does not put the wrong
      person behind the words. A prosecretario is called "Sr. Secretario"
      and any presiding officer is called "Sr. Presidente", but a
      prosecretario is never the chair — and "vicepresidencia de la Nación"
      contains "presidencia de la Nación" letter for letter, which had the
      Vice-President answering for the President's Asamblea speeches.
- [x] Impeachment sittings: when the chamber sits as a court it hears the
      accused, the prosecutors, counsel and expert witnesses. No roster of
      this chamber covers them, so they are typed out of scope rather than
      counted as failures.
- [x] Result: genuine lookup failures fell from 9% of speech blocks to 0.1%
      (217 blocks), and persons named rose from 63% to 70%. The residue is
      invited outside speakers at public hearings, named by surname alone.
- [x] Event subtypes widened to cover disorder however the stenographer
      words it — senators talking over each other was the commonest form and
      used to fall through untyped, which undercounted every incident rate.
- [x] Analysis re-run over the whole 2000–2024 span; figures regenerated.

## Phase 6 — verify the whole corpus, not a sample (done, July 2026)

The gold set covers 36 pages, 0.08% of the corpus. `scripts/audit_parse.py`
checks every session for things that must never happen, and found real faults
the sample could not have reached.

- [x] Undetected speaker changes: 71 places where the typesetter set the label
      in roman instead of bold, so it ran on inside the previous speaker's
      paragraph and one senator was credited with another's words. The parser
      now recognises a complete printed label (title, name, ". —" terminator)
      after a finished sentence, whatever its weight. Down to 0.
- [x] Page apparatus leaking into speech: 1 case left in 154,875 turns.
- [x] Text written out twice by the block splitting: 0 sessions.
- [x] **Two sittings (21 and 29 November 2001) are scans with OCR text**, not
      born-digital transcripts. The parser detects a page-sized image behind
      the characters, records `scanned_page_share`, and warns; the audit
      excludes them from its counts. This contradicts the Phase 4 note that
      claimed no file from 2000 on needed OCR.
- [ ] Words run together at line joins ("reemplazala expresión") because the
      parser reads characters in stored order and loses the spaces the layout
      implies. Affects tokenisation and word counts, not attribution.

## Phase 7 — read the pages blind (done, July 2026 — parser 0.4.8)

The audit checks that no rule was broken; it cannot tell whether the RIGHT
person is behind the words. So the 50 sampled turns were read independently:
each page rendered as an image and given to an agent that was never told the
parser's answer, asked only "who does this page say is speaking here?", and the
two answers compared afterwards.

- [x] 50 of 50 agree on the speaker; the quoted words were found on the page in
      all 50; no reader saw page apparatus inside the paragraph.
- [x] Earlier passes disagreed twice, and the reader was right both times.
      First: the section title swallows the speaker label printed after it,
      because the two share one bold run and the PDF drops the space between
      them. 1,693 titles in 112 sessions had absorbed a label, stranding 314
      turns, **55 of them credited to the wrong person**. Fixed in 0.4.7; the
      only case left is inside a scan. The cut was tried against all 5,154
      distinct titles first — every tail it carves off is a genuine label.
      Second: the footnote pointing at the appendix read as speech — 809 turns
      that were nothing else, and 340 more with its words dropped mid sentence.
      Fixed in 0.4.8 by cutting the phrase like a header. A positional rule was
      tried first and rejected: it cut real debate, because a superscript
      reference can begin a line too.
- [x] A third, milder case: the chair's surname stayed in the speech instead of
      joining the label ("Sr. Presidente" + ". (Gioja). — …"), so 27 turns
      recorded the chair as person-unstated where the page names them.
- [x] Verdicts kept as evidence in
      `reference/verification/blind_read_50.csv`.
- [x] The audit now also checks for the appendix-pointer footnote, so this class
      stays measured instead of being fixed and forgotten.
- [ ] Still worth doing by hand: a blind machine read is a second machine
      reading, independent of the parser's code path but not of machine
      reading itself. `--sample N` regenerates the review sheet
      (`data/processed/senado/review_sheet.csv`) for a human pass.

## Later

- Caucus (bloque) mapping for departed senators (historic roster only has
  the ticket they were elected on) — needed before per-bloc claims harden.
  The analysis now shows why: the provincial-alliance share of floor speech
  falls from ~40% to ~13% after 2019 without senators changing sides.
- Cámara de Diputados (second chamber)
- Formal writeup / dataset publication (corpus is citable via SOURCES.md)
- Optional: the 217 remaining unresolved blocks are invited outside speakers
  at public hearings. Typing them would need the transcripts' own
  introductions of each guest; worth it only if guest speech is ever a
  research target.

## Explicitly not building

Packaging/PyPI, docs site, utils wrappers, test-file mirror, separate
analysis modules before a notebook needs them. Diputados waits until the
Senate corpus is complete back to 2000.
