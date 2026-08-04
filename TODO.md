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
- [x] Words run together at line joins ("reemplazala expresión") because the
      parser reads characters in stored order and loses the spaces the layout
      implies. Affected tokenisation and word counts, not attribution.
      **Fixed in 0.4.11** — see Phase 9.

## Phase 7 — read the pages blind (done, August 2026 — parser 0.4.10)

The audit checks that no rule was broken; it cannot tell whether the RIGHT
person is behind the words. So sampled turns were read independently: each page
rendered as an image and given to an agent that was never told the parser's
answer, asked only "who does this page say is speaking here?", and the two
answers compared afterwards. 50 pages first, then 300, then 500, then 998 more,
none of the samples overlapping — 1,798 in all, spread across every year.

- [x] 300 of 300 agree on the speaker; the quoted words were found on the page
      in all 300; no reader saw page apparatus inside the paragraph. Two cases
      the reader marked ambiguous were settled by comparing the printed order
      of labels with the parser's own order, and both confirmed it.
- [x] A further 500, 20 per year, drawn so that none repeats the first 300:
      **497 of 500 agree, and no parser defect was found** — the first round of
      this sample was also its last. The three left over are pages that print the
      quoted phrase twice, so nothing on the page tells the reader which
      occurrence was meant; checked afterwards against the page image, the parser
      is right in all three. That check was not blind and is kept out of the 497,
      recorded in its own column of
      `reference/verification/blind_read_500.csv`.
- [x] A further 998, 40 per year, none repeating the first 800: **993 of 998
      agree, and again no parser defect.** All five left over were checked by hand
      against the page and the parser is right in every one — two are the
      repeated-phrase case; two are readers writing "Sra. Presidenta" where the
      page prints "Sra. Presidente"; one is a reader mistaking which page it had
      been given. Evidence in `reference/verification/blind_read_1000.csv`.
      That makes 1,498 pages drawn since the last parser fix with nothing found.
- [x] A fourth flaw in the method, and the first that is about the reader rather
      than the sheet: **a reader tidies the record without noticing.** Asked to
      transcribe a label exactly, two readers supplied the grammatical agreement
      the edition itself does not make. Every disagreement is therefore settled
      against the page image, never against which answer reads better. A reader
      also denied that a phrase appeared twice on a page that prints it twice —
      which is why that count is taken from the PDF and not from the reader.
- [x] The readers reported page apparatus inside the paragraph 30 times in the
      500-page round and 51 times in the 998-page round. The great majority are
      the stenographer's own parentheses — applause, murmurs, a chamber rising to
      its feet — which the edition prints inside the speech and this corpus keeps
      on purpose. The 16 that name the appendix footnote, the contents link, the
      stenographers' footer, a page number or a raised footnote digit were all
      checked against the output: not one of those turns carries any of it. The
      readers were describing the printed page, not what the parser kept.
- [x] Earlier rounds disagreed, and the reader was right every time. Four
      distinct defects, all fixed:
      **(1)** the section title swallows the speaker label printed after it,
      because the two share one bold run and the PDF drops the space between
      them. 1,693 titles in 112 sessions had absorbed a label, stranding 314
      turns, **55 of them credited to the wrong person**. Fixed in 0.4.7; the
      only case left is inside a scan. The cut was tried against all 5,154
      distinct titles first — every tail it carves off is a genuine label.
      **(2)** the footnote pointing at the appendix read as speech — 809 turns
      that were nothing else, and 340 more with its words dropped mid sentence.
      Fixed in 0.4.8 by cutting the phrase like a header. A positional rule was
      tried first and rejected: it cut real debate, because a superscript
      reference can begin a line too.
      **(3)** the page's own "Pág. N" line, in sessions whose typeface carries
      no character map, survives extraction as an accent and a digit and so
      slipped past the header filter, plus the digital edition's "Volver al
      sumario" link and turns left holding no word at all. Fixed in 0.4.9.
      **(4)** the raised footnote digit stranded at the end of a turn once the
      footnote's words were cut. Fixed in 0.4.10.
- [x] A milder case: the chair's surname stayed in the speech instead of
      joining the label ("Sr. Presidente" + ". (Gioja). — …"), so 27 turns
      recorded the chair as person-unstated where the page names them.
- [x] Three flaws in the review method itself, all fixed, all worth recording
      because they produced false disagreements rather than missing real ones.
      The sheet now says **on which page each turn opens** and the reader gets
      every page from there: a long speech carries no label on its later pages,
      so a reader shown only the quoted page finds no speaker and cannot answer —
      six "disagreements" were only that, and capping the supplied pages at three
      back reproduced the same six in the 500-page round. The sample is drawn by
      the content of each turn instead of by row number, so fixing the parser no
      longer reshuffles it: the old draw moved 279 of 300 rows after one
      unrelated fix and threw away a finished reading round; the new one moved 1.
      And a phrase printed twice on its page is now **counted from the PDF and
      reported apart** instead of being charged to the parser: it happens in 60
      of 500 cases, and in 58 every occurrence is the same speaker anyway.
- [x] Verdicts kept as evidence in `reference/verification/blind_read_1000.csv`,
      `blind_read_500.csv`, `blind_read_300.csv` and `blind_read_50.csv`.
- [x] The audit now also checks for the appendix-pointer footnote, so this class
      stays measured instead of being fixed and forgotten.
- [ ] Still worth doing by hand: a blind machine read is a second machine
      reading, independent of the parser's code path but not of machine
      reading itself. `--sample N` regenerates the review sheet
      (`data/processed/senado/review_sheet.csv`) for a human pass.

## Phase 8 — the caucus, not the ticket (done, August 2026)

Every grouping in the analysis rested on the party a senator was ELECTED under,
because that is the only affiliation the historic roster carries. It is not the
caucus they sat with, and the gap was visibly distorting the results.

- [x] Established that no official source publishes caucus historically: the
      open-data portal has no caucus and no votes dataset; the transcripts
      mention caucuses only inside speech (511 of 559 sessions) and never as a
      roster; the site's grouped-by-caucus listing is current-composition only.
- [x] Found it in the roll-call records instead. Every recorded vote publishes
      the whole chamber, absent members included, with each senator's caucus.
      `fetch_blocs.py` reads one record per sitting date — 320 dates, 2005-2024,
      23,007 readings, 287 senators, 62 caucuses — and archives the raw pages.
      All 283 people the corpus resolves from 2005 on match by name, exactly.
- [x] `map_blocs.py` collapses the readings into 302 caucus spells and files
      each caucus under the analysis's own party families, adding two keywords
      that only bite on caucus names: the PRO (the other half of Cambiemos/JxC,
      which as a ticket appeared as "Cambiemos") and Frente Nacional y Popular
      (the peronist bloc after 2020). Without them 27 senators fall into the
      residual bucket. The federal-peronist splinters are deliberately left in
      that bucket, matching what the ticket-side rules do to their equivalents.
- [x] **The result answers the question that motivated it.** By ticket, the
      chamber looks realigned at a stroke in 2019-2020. By caucus, the step
      disappears: radical/Cambiemos sits at 23-34% throughout instead of jumping
      from 9-25% to 30-39%, and provincial and other alliances end at 20-21%
      instead of 13%. The peronist family, largest in 18 of 21 years by ticket,
      is largest in all twenty caucus-covered years.
- [x] Three limits, measured and written into SOURCES.md rather than smoothed
      over: the caucus name is trustworthy and its **date is not** (of 18
      senators filed under Frente de Todos only 2 carry it from a plausible
      date; the rest carry it back to 2016 or earlier, and it was formed in
      2019); nothing exists before 2005; 2.6% of readings carry no caucus.
- [x] Tried and rejected a correction: dating each caucus by when the chamber
      first names it in debate. It works on distinctive names (La Libertad
      Avanza lands on December 2023) but not on names built from ordinary words
      — "Frente de Todos" matches "frente de todos los argentinos" — and only
      33 of 62 caucuses are ever named as such.
- [x] Corrected a stale claim found on the way: the notebook said the peronist
      family was largest "in every fully held year". It is 18 of 21; the README
      already said so and the notebook did not.
- [x] **Dated the twenty largest caucuses by hand** — 88% of all floor speech —
      in `reference/senado/blocs_manual.csv`, each row carrying its evidence,
      the sitting that attests it, and how far that evidence goes. Reading the
      matches is what the job actually was: the earliest hits for "Frente de
      Todos" turn out to be the Chamber of *Deputies* bloc of the same name, and
      "Convicción Federal" matched an ordinary turn of phrase in 2004.
      Three findings the raw data had buried:
      **(1)** the Senate stores the caucus a senator ENDED each mandate in and
      projects it backwards over the whole term — that is the whole shape of the
      error, not a scatter of mistakes;
      **(2)** Unidad Ciudadana is *two* caucuses (2017–2019, absorbed, re-formed
      May 2022), and treating it as one filed three years of Frente de Todos
      speech under the wrong name;
      **(3)** Frente de Todos ends as a *bloc* in May 2022 but survives as the
      *interbloc* holding both halves, which is why it keeps appearing to 2024.
      Best single piece of evidence: the sitting of 16 Nov 2022, where the
      chamber reads out its own composition bloc by bloc with the numbers.
- [x] `map_blocs.py --no-clip` keeps the uncorrected version available. Spells
      are cut to their caucus's life; where the chamber says what a caucus split
      off from, the front is handed to that predecessor, and where nothing is
      documented it is dropped — 6.4% of floor words end with no caucus.
      The notebook's nearest-spell fallback is now bounded to 180 days, because
      an unbounded one silently refilled the gaps and undid the whole repair.
- [x] **Then the other 42**, so all 62 caucuses are dated: 39 rows at
      `confidence: high`, 19 medium, 4 low. Most are one- or two-member caucuses
      that their members' mandates bound exactly. The new piece of evidence is
      the roll of blocs read into the record on 16 Nov 2022 — Frente Nacional y
      Popular 21, UCR 18, Unidad Ciudadana 14, Frente PRO 9, Cambio Federal 4,
      "y los demás son monobloques" — which dates caucuses named nowhere else
      and, in the negative, places Unidad Federal, Convicción Federal, La
      Libertad Avanza and Provincias Unidas after that date. La Libertad Avanza
      was backdated to Dec 2021 for two members who joined it in 2024; Unidad
      Federal to Dec 2017 for a caucus first named in Feb 2023.
- [x] The repair moves real numbers: the peronist share for 2016–2021 falls from
      62–64% to 52–58% once the backdated caucuses are cut to the years they
      existed. The main finding survives it and gets cleaner — radical/Cambiemos
      flat at 23–37% across the supposed 2019 realignment.
- [x] It also costs coverage, unevenly, and the figure now says so per year:
      6.9% of floor words end with no caucus, but 2017 and 2018 keep only about
      three quarters of theirs. Almost the whole 2016–2019 hole is one thing —
      392,000 words by the sixteen senators whose 2015–2021 mandate the Senate
      files under Frente de Todos. Thirteen were elected on a Frente para la
      Victoria ticket and the rest on peronist provincial ones, so they were
      certainly peronist, but three held monoblocs of their own; assigning them
      all to the peronist bloc would be a guess dressed as a finding, so they
      are left unplaced.

## Phase 9 — put back the spaces the files never stored (done, August 2026 — parser 0.4.11)

The last open defect from Phase 6. The 2003–2009 files end a line without
storing a space, so the parser — which reads characters in the order the file
keeps them — glued the last word of one line to the first of the next.

- [x] The parser now inserts a space wherever the page shows one: a new line, a
      new column, a new page, or a gap inside a line too wide for anything else.
      The threshold is measured rather than chosen: on files that DO print their
      spaces, two letters of one word are never more than 0.07 of the type size
      apart (110,744 pairs, widest 0.071), while a printed space is 0.25 to 0.60
      wide, so 0.15 separates them cleanly. A line ending in a hyphen stays
      joined — it is either a broken word or a file number ("P.E.-86/16").
- [x] 710,039 spaces restored in 481 of 559 sittings. The corpus rises from
      21.07 to 21.48 million words: +4% to +6.5% every year from 2003 to 2009,
      under 0.1% everywhere else, which is exactly the shape of the defect.
      Text the parser cannot attribute to anyone fell from 1,884 rows to 1,207.
- [x] Checked against pdfplumber's own layout-aware page reading: words the
      parser produces that the page reading never produces fell from 3.0% to
      0.06% of tokens. Gold set unchanged (F1 = 1.00, 124 of 125 turns); the
      audit unchanged on every invariant.
- [x] Section numbering now works for 2003–2009, which number sections without
      a full stop and were unreadable while the number was glued to the title:
      443 → 529 sittings carry the section each turn belongs to. A bill number
      left at the head of a line has the same shape, so the parser tells them
      apart by counting — a dotless number opens a section only if it carries
      the count forward (within three, or up to ten to open the sitting). In the
      later files, which number with a full stop, the next section is the
      previous plus one in 284 of 290 cases. One scanned November 2001 sitting
      numbers too erratically to follow and now carries no sections.
- [ ] The section TITLE for those years still stops where the style changes
      ("7 Orden del Día N"), because the "º 522" that follows is set in another
      style. The section number and its turns are right; only the title text is
      cut short.

## Later

- Caucus (bloque) mapping — **done at family level, 2005 onward, all 62
  caucuses dated by hand** (see Phase 8). What is still open: a senator who
  crossed the floor mid-term is invisible, four caucuses rest on the mandate
  calendar alone, 6.9% of floor words end with no caucus (concentrated in
  2016–2019), and 2000–2004 has none at all. Closing those needs a source
  outside the Senate.
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
