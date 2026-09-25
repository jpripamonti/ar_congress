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
      (218 blocks), and persons named rose from 63% to 70%. The residue is
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
none of the samples overlapping — 1,848 in all, spread across every year.

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
- [x] Still worth doing by hand: a blind machine read is a second machine
      reading, independent of the parser's code path but not of machine
      reading itself. `--sample N` regenerates the review sheet
      (`data/processed/senado/review_sheet.csv`) for a human pass.
      23 September 2026, asked to do it in the owner's place: 29 turns drawn
      fresh (`--sample 50 --sample-seed human20260923`, one a year, 1998-2026),
      the parser's answer hidden, and each PDF page read as a rendered IMAGE,
      not as extracted text — the HTML ones in the file itself. 29 of 29 agree,
      including "Afirmativo." 6th of 182 on its page and "Pido la palabra." 1st
      of 14, found by the words printed before them. Evidence in
      `reference/verification/page_image_read_29_20260923.csv`. Left open: it
      was still a model reading, the same kind of evidence as the blind
      rounds, not the human pass this item asks for.
      24 September 2026, the human pass: the owner checked the same 29 against
      the page images (each PDF page rendered with the parser's phrase
      highlighted, the HTML ones as excerpts of the file) and marked all 29 as
      agreeing. Verdicts and timestamps are in the same CSV
      (`correct? (y/n)`, `human_checked_at`).

## Phase 8 — the caucus, not the ticket (done, August 2026)

Every grouping in the analysis rested on the party a senator was ELECTED under,
because that is the only affiliation the historic roster carries. It is not the
caucus they sat with, and the gap was visibly distorting the results.

- [x] Established that no official source publishes caucus historically: the
      open-data portal has no caucus and no votes dataset; the transcripts
      mention caucuses only inside speech (503 of the 558 sessions that parse)
      and never as a roster; the site's grouped-by-caucus listing is current-composition only.
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
      `confidence: high`, 19 medium, 4 low (40, 20 and 4 today, after Phase 16
      added a row and split another). Most are one- or two-member caucuses
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
      Text the parser cannot attribute to anyone fell from 1,884 rows to 1,207
      (1,204 today, after later repairs).
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
- [x] The section TITLE for those years stopped where the style changes
      ("7 Orden del Día N"), because the "º 522" that follows is set in another
      style. The section number and its turns were right; only the title text was
      cut short. **Closed in 0.4.28** — see Phase 23. What is left is one sitting
      whose ordinal is not in the file at all.

## Phase 10 — read 500 more, against the new parse (done, August 2026 — parser 0.4.12)

The space fix changed the output, so the reading was run again on it: 500 turns,
20 per year, none of them among the 1,798 read before, drawn after the re-parse.
The exclusion compares texts with the spacing removed, or the 2003-2009 pages
already read would have looked new.

- [x] **498 of 500 agree on the speaker, no disagreement.** The two left over are
      the repeated-phrase case again, both settled by hand afterwards: the page
      prints the quoted words twice under two labels and the parser records both
      turns, one under each. Evidence in
      `reference/verification/blind_read_500_0411.csv`.
- [x] **A defect, the first in three rounds, and one only a reader finds.** A
      sampled "turn" whose whole text was "E 13" is not speech: it is the tail of
      the note "El resultado de la votación surge del Acta N° 13", cut off because
      the degree sign comes from another font, left as a two-character turn
      credited to the last speaker. Parser 0.4.12 gives the scrap back to its
      note.
- [x] The rule is narrow on purpose. The same position also holds genuine short
      turns, so a scrap is reattached only where the note stops mid-phrase AND the
      scrap cannot be read as speech — nothing but an ordinal marker and its
      number, or a fragment opening in lower case. Of the 102 blocks that follow
      an unfinished note, 81 are scraps ("E", "E 13", "z.", "of Mostyn.") and the
      rest are real speech ("Ausente.", "Gracias.", "¡Rojo!"), untouched. Every
      scrap joined is listed in the session's log.
- [x] One instruction was added to the reading brief, against the reader bias the
      last round exposed: copy the ending exactly even where it reads as a
      mistake, because the record prints "Sra. Presidente". No reader tidied a
      label this round.
- [x] Nothing else moved: gold set unchanged (F1 = 1.00, 124 of 125 turns), audit
      unchanged on every invariant, and all 2,348 answers recorded across the five
      blind reads still stand under 0.4.12, checked row by row.
- [x] The mis-mapped degree sign — the notes read "Acta NE 13" rather than
      "Acta N° 13" in those 2004-2005 sittings. **Closed by the glyph work of
      0.4.21/0.4.22 without anyone noticing**; not one is left in the corpus,
      confirmed by counting in Phase 23.

## Phase 11 — read 1,000 more (done, August 2026 — parser 0.4.13)

A thousand turns, 40 per year, none of them among the 2,348 read before. The
year 2000 holds only three sittings and cannot fill its share, so its shortfall
was spread over the years that had turns to spare rather than leaving the round
short of the thousand.

- [x] **1,000 of 1,000 agree on the speaker.** No disagreement, and for the first
      time nothing left over needing a check by hand. All 116 turns whose quoted
      phrase the page prints more than once agreed too. Evidence in
      `reference/verification/blind_read_1000_0412.csv`.
- [x] **Three defects even so, all in the text rather than the speaker.** Readers
      are asked to report anything inside the paragraph that is not speech;
      24 of the 1,000 did, and three of those were real:
      - The dash that introduces a stenographer's note ("— Se vota.") is stored
        at the end of the line above in many files, so the turn before it ended
        on a dangling dash — 9,025 of the 26,937 notes that open with a dash, one
        in three. The dash is stored where it belongs 17,912 times; in only 8 of
        the 9,025 does the note carry a dash of its own, which is what shows
        the stray one is the same dash.
      - A note ending in a colon ("…son los siguientes:") lost it to the block
        below, which then opened ": Denominación de un puente carretero…". Taken
        back in 29 cases, only where the note stops mid-phrase. Where the note is
        already complete ("(Risas.)") the colon is left where it is — 17 such
        cases, untouched on purpose.
      - A section's number set in the body face rather than the bold of its title
        stayed on the turn above, so the title carried no number, was not read as
        a section, and everything under it stayed filed under the section before.
        26 sections recovered; 530 sittings now carry sections. The number is
        taken back only onto a title of four words or more that is not a
        speaker's label, and only where it continues the count — the first draft
        stole vote-record numbers ("Acta N° 1.") onto speaker labels and invented
        thirteen sections in one sitting.
- [x] Nothing verified moved: gold set unchanged (F1 = 1.00, 124 of 125 turns),
      audit unchanged on every invariant (0.424% of blocks not located, median
      coverage 79.2%, no text written out twice), and all 3,348 answers recorded
      across the six blind reads still stand under 0.4.13, checked row by row —
      no speaker changed anywhere. The only four turns that no longer exist are
      the note scraps Phase 10 correctly returned to their notes.

## Phase 12 — read 1,000 more, after the punctuation repairs (done, August 2026 — parser 0.4.13)

- [x] **998 of 1,000 agree on the speaker, no disagreement, and no defect of any
      kind** — the first round that turned up nothing at all to fix. The two left
      over are the repeated-phrase case: page 13 of the 12 Jul 2017 sitting
      prints "¿Por qué se cambió el orden?" four times under three different
      labels, and the parser records all four turns, one under each. Evidence in
      `reference/verification/blind_read_1000_0413.csv`.
- [x] 29 readers reported apparatus inside the paragraph they were reading —
      footnote markers, applause, "(Lee:)" — and in every case it had stayed on
      the page and never entered the output. Checked one by one.
- [x] Two things confirmed rather than corrected, both of which look like errors:
      a May 2010 page interleaves "(Aplausos)" between the items of a list a
      senator is reading out, so her turn comes out as fragments each opening
      with a comma, which is what the page shows; and an October 2022 page
      misspells a surname as "Sr. Rodíguez Saá", which the parser copies as
      printed and the resolver still matches to the right person.
- [x] (noted, closed 23 September 2026: a fact about the sample, not work) **The year 2000 is exhausted.** Its 96 locatable turns have all been read
      across the seven rounds, so this round covered 24 years, not 25, and its
      share of forty went to the years with turns to spare. Any further round has
      the same floor: three sittings is all that is held for that year.

## Phase 13 — read 1,000 more, and find a word broken in half (done, August 2026 — parser 0.4.14)

- [x] **1,000 of 1,000 agree on the speaker**, nothing left over at all — the
      largest sample yet settled entirely by the blind read, with no
      after-the-fact check needed. All 128 turns whose quoted phrase the page
      prints more than once agreed as well. Evidence in
      `reference/verification/blind_read_1000_0413b.csv`.
- [x] 27 readers reported apparatus inside the paragraph; all 27 checked against
      the output and all 27 had stayed on the page.
- [x] **One text defect, found through the question rather than the answer.** A
      reader was asked to locate "i la Argentina debe ser tomada en su
      totalidad?", which no page prints. The page has "…de allí trasladarnos a
      otra parte del país (aplausos), si la Argentina…": the note is interjected
      mid-sentence, and in a few files the italic run it is set in carries a
      character or two past the closing parenthesis, so the note kept ", s" and
      the sentence resumed at "i la Argentina". 0.4.14 gives the tail back — 5
      broken words and 70 marks of sentence punctuation, 75 turns in 41
      sittings. A colon is never taken: 13 notes end in one and it is the note's
      own, introducing the matter quoted below.
- [x] Nothing verified regressed after the re-parse: gold F1 = 1.00 (124 of 125),
      the annotations still check out against the PDFs (36 of 36), the audit is
      unchanged on every invariant (0.424% of blocks not located, median coverage
      79.2%, no text written out twice, one footer leak), and all **5,348 answers
      recorded across the eight blind reads still stand — no speaker changed
      anywhere and no turn went missing**.
- [x] (noted, closed 23 September 2026: a fact about the sample, not work) **2002 is nearly exhausted too.** It yielded 12 turns of the forty asked
      for, on top of the year 2000 yielding none. Four sittings is all that is
      held for 2002, so future rounds keep drawing more heavily on the years
      after 2004.

## Phase 14 — ask every turn whether it looks like speech (done, August 2026 — parser 0.4.16)

- [x] **A new check in `audit_parse.py` that reads the first and last characters
      of all 152,574 turns**, which nothing else did: every text fault found so
      far has lived at the edge of a block, and the conservation check probes
      only from ten characters in. Reports turns opening mid-word under a new
      speaker, turns of three characters or fewer, and turns ending on a dash or
      comma.
- [x] **Speaker names cut in half — 14 repaired.** The closing letter of the name
      is set in the roman face rather than the bold, so the corpus held speakers
      called "Sr. President", "Sra. Higone", "Sr. God". Taken back only where the
      bold block reads as a label with no terminator, the block below opens in
      lower case, and its terminator arrives within thirty characters.
- [x] **The terminator is a plain hyphen from about 2013 on**, and the pattern
      did not accept it, so the repair that separates a label from speech bolted
      onto it had been inert for a decade: 96 → 165 labels.
- [x] **82 words made whole in 34 sittings.** A sentence whose opening is set a
      point larger than the body was dropped as page apparatus — the "T" of
      "Tiene la palabra…", and once the chair's whole "Por favor, les pido si
      podemos mantener el s", leaving the turn as "ilencio durante la
      exposición". The rule fires only where the break falls inside a word.
- [x] Turns opening mid-word under a new speaker fall from 44 to 5, and all 5 are
      printed that way. Nothing verified regressed: gold F1 = 1.00 (124/125),
      annotations 36/36, and 5,347 of the 5,348 blind-read answers unchanged —
      the one that moved is case 850 of the seventh round, whose parser answer
      was the truncated "Sr. Presidente (Pinedo).- C" and is now the whole label.
- [x] **The blind read cannot see this class of fault** — so the ninth round was
      drawn page by page instead of turn by turn, and the readers were asked to
      report anything on the page that looked broken as well as who was speaking.
      That is what surfaced the spacing defect: the reader was not comparing a
      label, they were reading a sentence.
- [x] (closed 23 September 2026: `audit_parse.py` check 6c now reads every label for
      a stray parenthesis, text after it, or a terminator left on) **The blind read cannot see this class of fault.** That same case 850 was
      scored as agreement, because the comparison ignores a stray character in a
      label. Reading pages blind answers who is speaking; the shape of what is
      recorded needs its own check.
- [x] **A turn interrupted by a page break comes out as two rows — measured, and
      not a fault.** 1,503 of them, all filed under one turn, so nobody is
      misattributed: 919 break cleanly, 580 keep the space that separates the
      words, and 4 want a space the file never stored. It looked like the
      largest thing left and it was nothing.
- [x] **8 note tails taken out of somebody's mouth (0.4.17).** Chasing that same
      edge found the real fault: 0.4.12 gives a cut-off scrap back to its note
      but only up to twelve characters, and longer tails stayed filed as speech —
      the chair "saying" *votación por medios electrónicos* and *nacional en el
      mástil del recinto*. Now taken back at any length where the note ends on a
      letter and the tail opens in lower case; 28,308 complete notes and 1,529
      unfinished ones followed by upper case are untouched. A note ending in "…"
      or ")" is excluded, and so is one whose closing parenthesis already has a
      letter or two after it — that is the italic-overrun fault, repaired later
      in the run, and feeding it more of the sentence undid the earlier repair.
      The blind-read re-check caught that collision on the first pass.
- [x] **An italic run opening a turn landing on the turn above — measured and
      repaired (0.4.18).** The 7 May 2014 sitting prints "Sr. Jefe de Gabinete de
      Ministros. – La Nación es un diario opositor…" and the newspaper's name was
      filed at the end of the previous senator's turn. Handed forward where the
      next block belongs to somebody else and continues in lower case. **2 cases
      in the whole corpus** — a wrong attribution, and a very small family.

## Phase 16 — the caucus, dated and marked (August 2026)

How other corpora do this was surveyed first: the unit is the turn everywhere,
party membership is timestamped rather than fixed to a person in every project
with a stated rationale, unresolvable speakers are omitted and the non-match
rate published, and the chair is recognised but left deliberately thin. This
phase brings the caucus up to that standard.

- [x] **Split the two affiliations.** `party_or_alliance` became
      `elected_ticket` — the list a senator stood on — and `bloc` is new: the
      caucus they sat with. Measured over the 14.7M words where both are known,
      they are written the same way in 9.2%, differ in wording but not in
      political camp in 72.0%, and fall in different camps in 18.9% — of which
      98% is a provincially-elected senator sitting with a national caucus, the
      thing the ticket alone cannot tell you. Genuine floor-crossing between two
      named national camps is 0.31%.
- [x] **Recover 2000–2004 from the web archive.** The Senate's own bloc-roster
      page, long dead: 1,112 senator-rows over 16 captures, May 2000 to June 2004,
      by `scripts/fetch_archived_blocs.py`. All 91 pre-2005 sittings fall within
      six months of a capture. 1,110 of the 1,112 name someone in office that day;
      the two that do not are the page lagging the chamber and are kept as
      printed. The pages are broken HTML in three specific ways, each handled by
      name rather than by loosening the parse.
- [x] **Date eleven more caucuses, and say what was searched for the rest.**
      Ten start dates now rest on the archived pages or on the chamber naming
      the caucus in debate, each with the verbatim sentence. Two caucus names
      turned out to cover two separate lives, which makes three in the file
      counting Unidad Ciudadana, dated earlier. Seven still have no start, and the
      file now records what was looked for — Tucumán's senator is listed among
      the "presidentes de bloque" in 2009, so she headed a caucus the record
      never names.
- [x] **Mark the misdated readings instead of hiding them.** 3,043 of the 22,213
      roll-call readings that name a caucus (13.7%), over 311 of 320 roll calls,
      name one that did not exist that day. Every one is kept and marked. 1,046
      more cannot be checked at all and are marked differently.
- [x] **One observation file.** `bloque_observado.csv`: 23,325 rows, one per day
      one senator's caucus was actually recorded, 336 dates, 369 senators. No
      interpolation, no spells. The resolver takes the nearest observation and
      writes the distance in days beside it.
- [x] **Re-verify.** Gold F1 1.00 (124/125), annotations 36/36, audit invariants
      unchanged (152,565 turns, 1,204 unattributed, 5 opening mid-word). The
      passage files were never rewritten, so the eight blind reads stand.

## Phase 15 — make the corpus citable (in progress, August 2026)

- [x] `docs/DATA_DICTIONARY.md` — what every column holds, what the values mean,
      and the three traps: `office_only` is 28% of the floor and is deliberately
      nameless, `elected_ticket` is the ticket and not the caucus, and turns
      must be counted by `turn_id` rather than by rows.
- [x] `docs/RELEASE.md` — what a release bundle contains, the checks that must
      pass before one goes out, how versions are cut, and how the transcripts
      and this corpus are cited separately.
- [x] **Decide the licence for the derived tables** — settled: CC BY 4.0 for the
      corpus and the reference tables, MIT for the code, with the split and the
      exact list of what each side covers in `LICENSE-DATA`.
- [x] **Mint a DOI.** Published on Zenodo, 8 September 2026:
      10.5281/zenodo.22661019 is the concept DOI and 10.5281/zenodo.22661020 is
      version 0.4.37. The deposit is the dataset, the pipeline that makes it and
      what a stranger needs to use and cite it; the repository's working records
      stay here.

## Later

- Caucus (bloque) mapping — **done, 2000–2024** (see Phase 16). What is still
  open: seven caucuses have no established start, so their readings can never
  be checked; a senator who changed caucus between two observations changes on
  the later one rather than the day they moved; and 2.4% of identified
  senators' floor words get no caucus at all. Two leads were checked and came
  up empty — Wikidata holds the field for dated caucus membership but leaves it
  blank for Argentine senators of this period, and the cross-national
  legislator databases either omit Argentina or record the electoral party
  rather than the caucus.
- Cámara de Diputados (second chamber)
- Formal writeup / dataset publication (corpus is citable via SOURCES.md)
- Optional: the 218 remaining unresolved blocks are invited outside speakers
  at public hearings. Typing them would need the transcripts' own
  introductions of each guest; worth it only if guest speech is ever a
  research target.

## Phase 17 — eleven readers sent to look for trouble (August 2026)

Nine of the fifteen phases before this one were checked only by the person who
wrote them. This one was not: a ninth blind read of 115 pages drawn page by page,
three independent audits of the caucus work of Phase 16, and two passes
recomputing every number in the documents against the files on disk.

- [x] **Ninth blind read: 105 of 115 agree on the speaker (parser 0.4.18).** The
      sample is drawn page by page rather than turn by turn — 5 pages a year,
      none of them on a page any earlier round used. Ten pages carry no printed
      label because the speech began pages earlier, and every reader refused to
      guess; all ten were checked by hand and the parser's speaker is the one who
      opened that turn. On the two longest runs the intervening pages were read
      to confirm no label was skipped. One of the ten was a reader's own slip.
      Evidence in `reference/verification/blind_read_115_0418.csv`.
- [x] **The punctuation of a sentence was standing on its own (0.4.19).** An
      italicised word inside a sentence reaches the parser as its own piece and
      the mark that closes it as another, and every piece was joined with a
      space: "del  default . Por ese motivo" for a page that reads "del default.
      Por ese motivo". Of the 4,653 marks that stood apart from their word, 3,618
      were the parser's doing and are now joined; the 1,035 that remain are the
      page's own spacing. Nothing verified regressed: gold F1 1.00 (124/125),
      annotations 36/36, and the eight earlier blind reads still stand — no
      speaker changed.
- [x] **The archived roster carried a dead address on all of its rows.** The
      offline path of `fetch_archived_blocs.py` wrote the literal word "(cached)"
      where the address goes, so every row pointed at
      `…/20000525090352id_/(cached)`. Each capture now keeps the address it came
      from beside it, and the offline path stops rather than inventing one. The
      re-run also found the archive now serves three captures with rosters on them
      that it did not before, and a fourth that is a "página en construcción" with
      nobody on it: **1,112 senator-rows over 16 captures**, up from 905 over 13.
- [x] **A caucus that lived twice was given one life.** Unidad Ciudadana sat
      2017–2019, was absorbed, and formed again when the Frente de Todos bloc
      split on 12 May 2022. `build_bloc_observations.py` folded the two into one
      span running from the first start to the first close, so **163 readings
      from May 2022 on were marked as naming a caucus that did not exist** —
      including the sitting that attests it. `map_blocs.py` had this right
      already. Misdated readings fall from 3,206 to 3,043.
- [x] **A quoted sentence that was cut in the middle of a word.** The evidence for
      Unidad Ciudadana's second life quoted "el nuevo bloque unidad ciudadana";
      the page reads "la presidenta **del** nuevo bloque Unidad Ciudadana", and
      the quote began after the "d". It matched as a search string, which is why
      it survived. Corrected, along with the note's claim that the chamber
      "called" the caucus that.
- [x] **Numbers recomputed against the files.** Corrected: unattributed text
      1,207 → 1,204; unresolved blocks 217 → 218; roll calls carrying a misdated
      reading 262 of 320 → 311 of 320; the first-phase blind-read total 1,798 →
      1,848 (50+300+500+998, an arithmetic slip the rest of the document had
      already corrected); sessions where someone says "bloque" on the floor 511
      of 559 → 503 of 558; the radical/Cambiemos share before 2019 9–25% → 9–27%
      and the provincial share to 2016 30–46% → 27–46% (2004 broke both ceilings);
      four repair counters in SOURCES.md that later re-parses had nudged.
- [x] **One claim could not be reproduced and has been replaced.** "The cover page
      names two or more presiding officers in 282 of the 559 sessions" could not
      be rebuilt from anything in the repository — three attempts landed between
      30 and 266. `scripts/count_presiding.py` now counts it in the open: **266 of
      the 526 sittings whose cover page says who presided**, with 33 saying
      nothing.
- [x] **Every quotation in `blocs_manual.csv` now reads as the record prints it.**
      All of them had been captured through an accent-stripping, lower-casing
      search, and what was pasted back was the search string rather than the
      sentence it found — "desde el bloque del Frente Civico Jujeno" for a page
      that prints "Jujeño". Nothing was wrong in substance, but a quotation that
      cannot be found by quoting it is not evidence a reader can check, and one
      of them had been cut in the middle of a word. 17 rewritten against the
      transcripts and 3 against the archived roster; the remaining two are single
      words the notes discuss rather than quote. **All 27 now appear verbatim in
      the source they cite**, 24 in the transcripts and 3 in the roster.

## Phase 18 — seven readers sent after the repairs themselves (August 2026)

Phase 17 fixed three faults and rewrote a great deal of prose. None of that had
been checked by anyone but its author, so seven readers were sent after it, each
told to assume the repair was wrong until it had been proved right. Four of the
seven found something.

- [x] **The spacing repair had been written for its own example (0.4.20).** It
      covered the marks that happened to appear in the case that found it and
      left out the closing quotation mark, the apostrophe and the square bracket
      — 138 of those still stood apart from their word. It also guarded only the
      closing side, so a word between quotation marks came out spaced away from
      both: "caso " strawberry "," for a page that prints them tight. Both sides
      are now tested. Re-verified after re-parsing: gold F1 1.00 (124/125),
      annotations 36/36, corpus totals unchanged.
- [x] **The presiding-officer count was blind to a change of format.** The Senate
      replaced the cover-page sentence with a list of offices around mid-2020, so
      `count_presiding.py` read five officers as one, or as none, for every
      sitting after that; three narrower faults cost it one officer per page
      elsewhere, including a role pattern that could never match the masculine
      "presidente". Rewritten to read both formats and checked against eight
      cover pages verified by hand: **340 of 545**, not 266 of 526, and 14
      sittings say nothing rather than 33.
- [x] **Two quotations had never been rewritten at all** — including the one used
      as the example of the fault, the Frente Cívico Jujeño. The extraction that
      found the quotations broke on a note containing an English possessive
      ("the Senate's own page"), which threw its quote-pairing out by one and hid
      every quotation in such a note. Found again with a rule that survives a
      stray apostrophe, and corrected, along with a quotation attributed to the
      sitting of 21 Dec 2005 that is in the one of the 22nd.
- [x] **Four numbers had been left behind in corners the edit never reached**:
      the caucus-confidence shares in SOURCES.md, the count of audited sittings
      (559, when one does not parse and 558 are checked), and two sentences about
      the blind read. Also corrected: three captures with rosters on them
      appeared, not four — the fourth is a "página en construcción" with nobody
      on it — and nine of the ninth round's ten open cases are unlabelled pages,
      the tenth being a reader's own slip.
- [x] **1,234 characters of the corpus were glyphs no font could map (0.4.21,
      corrected in 0.4.22).**
      They sat in the private-use range, where a glyph lands when the file draws
      it from a font whose encoding it never declares, and they landed inside
      words and sentences — "bloque unipersonal el bloque Misiones". Fourteen
      codepoints account for all of them, and none is exotic: the WordPerfect-era
      sittings print ordinary typography from Symbol, SymbolMT, MathA and
      Phonetic, and one sitting from a private slot of Times New Roman, so the
      ordinal of "5° Reunión", the dash after a speaker's label, a list's bullet
      and even the "P" and "g" of a running head arrived meaningless. Thirteen are
      now given the character their own page shows, settled by what surrounds them
      rather than by the font's nominal table — these files use a nominally Greek
      codepoint for an ordinal. The fourteenth is removed instead: it prints an
      upside-down A inside the word "categoría", once, and keeping it would break
      the word. Five of the fourteen rest on ten occurrences or fewer and are
      flagged as the weaker readings; two others, the "P" and the "g", never reach
      the text at all and are read only so the header strip can recognise a
      running head. A scan of all 559 source PDFs closes the list at exactly these
      fourteen, 2,676 occurrences, of which 1,234 reached the text.
      **Nothing in the private-use range is left in the corpus.** Restoring the
      label dash lets repairs keyed on it see labels they had been blind to. The
      whole change is 13 places in two sittings: 15 lines of page matter are read
      and dropped, and in ten of those places the dropped line had been splitting
      a turn, so 22 half-turns rejoin into 10 — 27 rows and 12 speech blocks
      fewer, same speaker, same turn and same words on both sides of all 13
      (`reference/verification/glyph_map_diff_0421.csv`); no block, turn number or
      speaker changes anywhere else. Gold F1 1.00 (124/125), annotations 36/36,
      5 turns opening mid-word. Found while checking a quotation.
- [x] **One of those fourteen was read from its context and not from its page,
      and it put a degree sign into five senators' oaths (0.4.22).** The
      codepoint appears in two sittings. In one it sits in "192 aniversario",
      where an ordinal is the obvious reading, and that is how 0.4.21 read it —
      from the sentence, without looking at the page. In the other it closes
      "¡Sí, juro", where the obvious reading is an exclamation mark; that sitting
      was never examined. So the corpus published "¡Sí, juro°" for five of the
      twenty-three senators sworn in on 26 November 2009. Rendered at 600 dpi the
      page draws an underscore in both places, and 0.4.22 records the underscore:
      no single substitution is right in both, and inventing one would put on the
      page something the page does not show. Found by a reviewer asked to check
      each of the fourteen against its printed page — the check the fix itself
      claimed to have done, and had not done for this one.

## Phase 19 — a spaced-out word is one word again (August 2026 — parser 0.4.24)

- [x] **Letter-spaced typography no longer comes out one word per letter.**
      189 runs in 50 sittings, 13 of them inside attributed speech, cost 2,697
      words counted that the page prints as far fewer. The premise this task
      rested on was half wrong: the files store the spaces of such a phrase
      themselves, so the word boundary never had to be guessed from the widths.
      A gap is letter spacing where four or more gaps in a row measure alike —
      none more than a fifth from the row's own measure — and what they separate
      is letters or figures rather than the row of dots of a contents line,
      which is spaced identically and means the opposite. The one gap that
      breaks the pattern by being wider is still read as a space, which is what
      saves the space in front of a word set so wide that its own gaps are as
      wide as one ("Buenos Aires. Esos expedientes", not "Aires.Esos"). The
      measured range is 0.15 to 0.94 of the type size; the first cut at this
      stopped at 0.48 and missed the widest of them.
- [x] **Verified.** 115 blocks changed in 43 sittings, and in all 115 the letters
      are identical and only the spacing moved; 15 rows are new, all of them a
      roll-call masthead recognised now that its heading is legible
      (`reference/verification/letter_spacing_0424.csv`). Spaces restored fall
      from 710,040 to 670,660, the 39,380 difference being the gaps now read as
      letter spacing. The audit's whole output side is byte-identical, gold F1
      1.00 (124/125), annotations 36/36, 152,550 speech blocks, 1,204 rows
      unattributed, 5 turns opening mid-word.

## Phase 20 — text drawn outside the page (August 2026 — parser 0.4.25)

- [x] **What a file draws beyond the edges of its own sheet is no longer in the
      corpus.** 3,246 characters on 264 pages of 49 sittings, mostly runs of
      spaces. Two cases are not: two sittings of 2013 draw "◄ Ver el Apéndice."
      down a column to the right of the page, one letter under the next, which is
      where three of the lone-letter runs came from; and the sitting of 12
      September 2024 draws its "Pág. N" 170 points past the right edge on all 187
      pages, which is why that record shows no page number. A character is kept
      if any part of its box is on the sheet, so one straddling an edge survives.
- [x] **Verified, and the 2024 sitting is why it needed verifying.** The header
      strip finds the running head by looking for "Pág. N", so that sitting loses
      the marker: it strips 189 pages instead of 192 and its output is identical
      block for block, the repeated-line rule catching the rest. Corpus-wide the
      change is 13 rows fewer — 9 of invisible text, and 4 rows that had been
      split around it and are now whole, including a turn of 4 September 2013
      broken in two mid-sentence. The only text lost anywhere is two "(cid:9)"
      in the two sittings that are scans. Gold F1 1.00 (124/125), annotations
      36/36, the audit identical on every count but the one turn that rejoined
      (152,549 speech blocks), 1,204 unattributed, 5 turns opening mid-word.

## Phase 21 — the line whose own widths are wrong (August 2026 — parser 0.4.26)

- [x] **The last of the letter-spacing fault is closed.** A roll-call masthead of
      18 November 2009 is set in a Tahoma whose declared widths belong, for about
      half its letters, to the letter beside them, so an evenly spaced line
      arrives with 33 of its 78 gaps measuring nothing and 35 measuring the 0.15
      of the spacing, and the row of alike gaps breaks into pieces of two and
      three. A line is now taken as spaced end to end when the middle of its gaps
      is wider than a space, at least eight measure alike, those are two fifths
      of the line or more, and the line stores its own spaces — the last
      condition being what makes suppressing every gap safe, since the word
      boundaries are then the file's own.
- [x] **Verified.** 3 blocks in 2 sittings, all page matter, all of them spacing
      only: the masthead, and a heading of 7 November 2007 twice ("NACIONES U
      NIDAS"). No row, turn, speaker or section moves anywhere; the audit's output
      side is byte-identical; gold F1 1.00 (124/125); annotations 36/36. **The 6
      runs of lone letters left in the corpus are all correct as printed** — four
      enumerations a senator spoke, two files that store a space between every
      letter of "D E C R E T A".

## Phase 22 — the space the file had already stored (August 2026 — parser 0.4.27)

- [x] **The last spaced-out heading reads as one word.** Where a word is spaced
      out so widely that its own gaps are as wide as a space, the space in front
      of it measures no wider than they do; 0.4.24 kept it by reading the
      character before the word, and that rule had no exception for a page that
      had already stored a space there, so it put a second one in, one letter
      inside the word. It now applies only where nothing is stored at that edge:
      a space already in the file is not a space that is missing.
- [x] **Verified.** One block, one sitting, page matter, spacing only — the
      heading of 4 March 2009, now "Votación Nominal" for "V otación Nominal".
      Every other row of the corpus is byte-identical; the audit's output side is
      unchanged on every count (152,549 speech blocks, 1,204 unattributed, 5
      turns opening mid-word, 130 ending on a dash or comma); gold F1 1.00
      (124/125); annotations 36/36.

## Phase 23 — the letters the fonts declared wrong (August 2026 — parser 0.4.28 to 0.4.30)

Two items were still marked open in the phases above, below the "Next" line
that claimed nothing was outstanding. One had closed itself; the other was
much larger than its note said, and pulling it turned up a third fault that
had reached the spoken word.

- [x] **The mis-mapped degree sign of 2004–2005 is gone** — the notes that read
      "Acta NE 13" now read "Acta N° 13", and there is not one left in the
      corpus. Closed by the glyph work of 0.4.21/0.4.22 without anyone noticing;
      confirmed by counting.
- [x] **The section titles cut short were not a title problem.** 8,523 rows in
      64 sittings carried "10 Orden del Día N" for a page printing "10 Orden del
      Día N° 248 Día Internacional de la Juventud". The ordinal comes from a
      WordPerfect font that declares no character map, so it arrives as a
      meaningless token carrying the name of ITS font — never the bold of the
      heading — and the title breaks in two around it. The half after the break
      opens with the bill's number and was thrown away as a bill number out of
      sequence. 0.4.28 reads the 24 font-and-glyph combinations off the printed
      page at 600 dpi (each blank or boxed one rendered again with a second,
      independent renderer), and gives a mark read this way the weight and size
      of the word beside it, which is what puts the heading back together.
      Ten occurrences, in four font-and-glyph combinations, are dropped rather
      than translated: the file has no glyph to draw and
      both renderers print an empty box, and what the page fails to print is not
      a character this corpus can supply.
- [x] **The repair introduced a fault and it was caught before release.** The
      double space that separates a heading from the label after it is where the
      LINE ended, and the line can end inside the label — "…Armas Convencionales
      Sr." then "Presidente. — Corresponde considerar…". Cutting there left half
      a label behind and 49 turns of four 2003 sittings became nobody's. Those
      halves are now rejoined first.
- [x] **The third fault, and the one that reached the spoken word (0.4.29,
      0.4.30).** The same fonts declare the WRONG letter for the ordinal, the
      quotation marks, the dashes and the question marks, so the extraction
      hands back a plain, legible, incorrect character and nothing downstream
      can tell. The corpus published "el artículo 1E del proyecto", "la Ley N1
      25.673", "en llamar Aprotocolo facultativo de la cedaw@", ")Qué trató el
      Congreso" — about 3,700 characters across 163 sittings, most of it inside
      debate. All fourteen readings taken from the printed page at 500 dpi. The
      guard is measured rather than assumed: these two fonts draw 2 and 14
      distinct characters in the whole corpus and never carry running text, so
      there is no word for a substitution to break. One rule came with it —
      these files paint a mark several times over itself to make it heavier (the
      dash of a speaker's label is four glyphs stacked within a tenth of a point),
      so a repetition standing exactly where the mark before it stands is read
      once.
      The two fonts sit on opposite sides of the line between transcription and
      reconstruction, and both are declared in SOURCES.md: the typographic-symbol
      font is drawn correctly on the page, so reading it recovers what the page
      shows; WP-MathA is not — the page itself prints "artículo 1E" — so putting
      the ordinal back reconstructs a document broken in print, the same decision
      already made for the 2004 Courier file.
- [x] **Verified.** 164 sittings change, 394 untouched, nothing lost: the 3,820
      "words" that disappear are the broken forms themselves (1E, NE, 2E, N1),
      and the 72 speech blocks that disappear are two-character scraps ("E 1",
      "E 4") that were the tails of "Artículo 1°" standing as turns credited to a
      senator. Unattributed text 1,204 → 1,121 rows; turns of three characters or
      fewer 71 → 46; gold F1 1.00 (124/125); annotations 36/36; no turn carries
      another speaker's label; the 5 opening mid-word are printed that way.
- [x] **What was thought to be left.** 185 titles still cut, 181 of them in the
      sitting of 17 September 2003 "where the ordinal is not in the file in any
      form"; and 21 wrong letters in three sittings. **Both claims were wrong,
      and Phase 24 says how** — the ordinal is in that file, drawn as a slash,
      and fourteen of the twenty-one letters were safe to read after all.

## Phase 24 — five readers sent to break Phase 23 (August 2026 — parser 0.4.31)

Phase 23 was checked only by its author, so five readers were sent after it,
each with a different angle and each told to assume the repair was wrong until
proved right. Four of the five found something, and one of the findings undid
the phase's main excuse.

- [x] **Seven wrong claims of the author's, each verified before being changed.**
      The README said two sittings were left untouched where there are three;
      three event-subtype counts in the data dictionary were stale; the row loss
      in the two 2001 scans was eight rows and not two (the diff method used to
      count it aligns rows, so a row that changed at all was counted as changed
      rather than gone); the mathematical font was said to draw "nothing but an
      E and a space" when it draws five things; and Tahoma was named as one of
      the fonts that break the ordinal when Tahoma sets running text in those
      same sittings — 96 distinct characters, close to a million of them.
- [x] **The phase's main excuse was false, and the fix was one line.** Phase 23
      said the 181 cut titles of 17 September 2003 could not be repaired because
      the ordinal "is not in the file in any form". It is: the file draws it as
      an ASCII slash from a font whose name carries a hyphen, and the page
      prints "22° Reunión - 13° Sesión ordinaria". The font draws two characters
      in the whole corpus — that slash and an apostrophe — so reading it cannot
      break a real one. **185 cut titles fall to 4**, and 225 rows that held
      nothing but a lone slash rejoin the words they belong to.
- [x] **Fourteen of the twenty-one wrong letters left were safe after all.**
      They come from SimSun, a Chinese text font one 2005 sitting borrows for
      the ordinal, and it draws exactly two characters in that whole sitting —
      the same safety signature already accepted for the other fonts. Seven
      remain, in two sittings whose ordinal comes from the Times New Roman that
      also sets their body text; those are refused, and counted.
- [x] **The guard stopped being a hand-written list of font names.** That list is
      exactly what had left both of the fonts above unexamined, and no amount of
      careful reading of its output could have found them. The parser now checks
      each document for itself: a font that draws so much as one lower-case
      letter anywhere in the sitting is setting text, and nothing of its is
      touched.
- [x] **A landmine defused.** The map of unmapped glyphs was keyed on the raw
      font name while its sibling map normalised the name first, and five
      sittings spell that font with a hyphen. Nothing turned on it today — those
      five declare their characters properly — but it is the very fault the map
      exists to repair, waiting for the file that would trip it.
- [x] **The transcription/reconstruction line was drawn in the wrong place, and
      is now measured.** Phase 23 said reading the mathematical font's ordinal
      was reconstruction everywhere. It depends on the file, and the split is
      clean: where the file does not embed the font — **152 sittings, 3,006
      occurrences** — nothing on the page is the file's own, every reader
      substitutes and each one draws a capital E, and putting the ordinal back
      is reconstruction; where the file does embed it — **6 sittings, 223
      occurrences** — the page prints the ring and reading it is transcription.
- [x] **What the readers checked and found sound**, each on its own evidence:
      that no real speech text was lost anywhere (a reader rebuilt the previous
      corpus from its own code and compared 58 sittings word by word); that the
      style inheritance cannot take the weight of the wrong run; that the
      stacked-glyph rule drops nothing but genuine over-painting (3 drops in
      3,707 matches, all four copies of one dash); that the letter-spacing
      indices stay aligned; that the label rejoin never glues two headings (all
      11,078 titles checked); and that no unrelated font collides with a map key.
- [x] **Re-measured from scratch.** The 0.4.27 corpus was rebuilt from that
      version's own code and the whole journey measured against it with a method
      that counts a vanished row as vanished: 198 sittings change, 360 are
      untouched, and of the 5,812 word-forms that disappear only 146 are
      ordinary words, every one of them a half that now forms a single word.
      Gold F1 1.00 (124/125), annotations 36/36, no turn carrying another
      speaker's label, unattributed text 1,204 → 1,121 rows.
- [x] (closed 23 September 2026, left as measured) **What is left, measured.** Four cut titles in three sittings, each with
      its own cause and none of them a glyph: a title running across a page
      break (13 Apr 2011), a double space inside a heading (2 Nov 2011), and an
      "N" in bold whose "º" is not (3 Sep 2020, twice). Seven wrong letters in
      two sittings, refused by the guard because the font also sets their body
      text. And 47 places where a bullet or tick stands against the next word
      with no space, 43 of them in the two sittings that are scans, where the
      mark is OCR noise rather than a bullet.
      Closed without a change. The seven letters are refused by design (the
      font also sets body text) and the 43 marks are the scans'. Of the cut
      titles, 3 September 2020 now reads whole; the other two, "…N° 068/11,
      N°" across a page break and "S.-1.911/11 y otros", are chapter titles,
      not speech, and a rule for each would buy a cosmetic fix at the price of
      a new way to glue two headings together.

## Phase 25 — five readers sent to check Phases 19-22 (August 2026)

Phases 19 through 22 — the letter-spacing collapse, the off-page filter, the
Tahoma width fix, the stored-space edge case — had each been checked only by
whoever wrote it. Five readers were sent after them: one hunting false
positives and negatives in the letter-spacing classifier, one attacking the
off-page filter from both directions, one re-measuring every numeric claim of
the four phases at their exact historical commits, one checking Phases 23 and
24 hadn't quietly broken either fix, and one chasing a specific hypothesis
about the font-safety guard.

- [x] **A real gap in the letter-spacing classifier, and it is not only
      dormant.** The classifier reasons about the gap between two glyphs; where
      a page spaces a word's letters apart by storing a real space
      **character** between each one, instead of just pushing the glyphs
      further apart, the check that tells letter spacing from a missing space
      is never reached at all — it returns immediately whenever either side of
      a gap already is a space. Found live in the "Votación Nominal" masthead
      of one 2005 sitting and, complete, in the "AUTORIDADES" cover heading of
      all 13 sittings the corpus holds from 2024, apparently a different export
      tool starting that year — but neither survives into what ships: the 2005
      masthead is stripped as a repeating page header, the 2024 heading is cut
      with the rest of the cover page before the session opens.
- [x] **Phase 21 was wrong about "D E C R E T A," and the corpus has shipped it
      broken since.** Phase 21 said the six remaining runs of lone letters were
      "all correct as printed," four of them a senator's own enumeration and
      two a file that stores a space between every letter of "D E C R E T A."
      Rendering both pages shows the same resolving clause every decree in the
      corpus prints — "EL PRESIDENTE DEL H. SENADO DE LA NACIÓN, D E C R E T A
      :" — spaced out for emphasis exactly like every heading Phase 19 was
      built to fix, and Phase 19's own pre-fix scan had already logged it that
      way (`letter_spacing_0423.csv`, "as the page reads: DECRETA"). It is the
      same fault Phase 19 closed, arriving by the stored-space route this
      round's reading found, and it was never checked against the page before
      being called correct. Confirmed as the *only* two blocks left of this
      kind anywhere: a scan of the pattern across all 558 published sessions
      finds exactly these two and nothing else.
      `2003-06-25_r13`, page 3, and `2004-02-24_r43`, page 3, both quoted decree
      text, not attributed speech.
- [x] **A landmine in the font-safety guard, defused.** The check that decides
      whether a symbol font is setting real words scanned every character on
      the page before the filter that drops text drawn off the sheet ever ran,
      so an invisible lower-case letter in one of those fonts could in
      principle poison the guard for the whole document. Checked directly
      against all 559 source files: it never has — every lower-case letter
      those fonts draw is either printed on the page or the font never
      appears. Moved the scan to run after the off-page filter. Confirmed
      inert on the current corpus by reprocessing a sitting that uses one of
      the guarded fonts and diffing the output byte for byte.
- [x] **The off-page filter held, over the whole corpus, not a sample.** Zero
      of the corpus's 45,687 pages are rotated, and the character coordinates
      would stay correct even if one were — checked by reading pdfplumber's
      own rotation transform and by building three synthetic rotated PDFs and
      running the real filter against them. No page's crop box differs from
      its media box, which closes the other way a page could hide printed text
      from the filter. The headline count — 3,246 characters on 264 pages of
      49 sittings — reproduces exactly from the raw files, and the 30
      characters dropped closest to a page edge are all blank space or a
      zero-width tab, never ink.
- [x] **No regression from Phases 23 and 24.** 30 fixes sampled across both —
      15 letter-spacing collapses, 15 off-page drops, 30 different sittings
      from 2001 to 2023 — all still hold exactly as the verification records
      describe, checked against the rendered page and not only the record.
- [x] **Most of the four phases' own numbers re-measured exact; one will not
      reproduce.** Running each historical parser version at its own commit
      reproduced, to the exact figure: 670,660 spaces restored against 39,380
      now read as letter spacing (Phase 19); 3,246 off-page characters on 264
      pages of 49 sittings (Phase 20); the two Tahoma blocks of Phase 21 and
      the one stored-space block of Phase 22, each on the sitting named. Phase
      19's own opening count will not reproduce: "189 runs in 50 sittings, 13
      inside speech, 2,697 words." A fresh count against the real parser,
      corpus-wide, finds letter-spacing activity in 156 sittings, not 50; the
      file already on record from the commit before the fix counts a related
      pass at 177 runs in 45 sittings. Neither the code that produced 189/50
      nor the one that produced 177/45 was kept, and the two commits already
      disagree with each other by these numbers — two informal measurements of
      the problem's scope taken while the fix was being built, not a claim
      about what the corpus holds. What the corpus holds — 115 blocks changed
      in 43 sittings — was checked against the file the corpus actually
      publishes, and it reproduces exactly.

## Phase 26 — a stored space read as letter spacing too (August 2026 — parser 0.4.32)

- [x] **The letter-spacing fix now sees the form Phase 19 could not.** A word
      set apart by widening the gap between its letters is one thing; a word
      set apart by storing a literal space character between each letter is
      another, and the first fix only ever measured the gap, which does not
      exist where a space glyph fills it. What still marks such a run as one
      word's own letters, not a run of short words, is that a real word
      capitalises only once — all its letters alike, or one capital and the
      rest lower, exactly as spelt — while a run of Spanish's own one-letter
      words (a, o, y, u, e) or single-digit numbers never keeps one case for
      four letters running. A run glued to the letter before or after it is
      refused before its case is even read, so the tail of an acronym can
      never be mistaken for the head of a spelled-out word.
- [x] **Measured over the whole corpus three times, because the first two
      rules were each wrong in a different way.** A first version, run over
      all 559 source files, collapsed 153 runs: sixteen were true headings —
      the two decree closings and the fourteen cover pages — and 137 shared
      the same false shape, an acronym's own last letter sitting right before
      "y a" or "o a," which is how spoken Spanish constantly runs one word
      into the next ("la AFIP y a los propios empleados" read as "AFIPYALOS").
      The rule had no notion of where a word starts, so it began counting
      wherever a capital happened to sit. It also missed one heading
      entirely — "Votación Nominal," six pages of one roll-call masthead —
      because it required a single capital for the whole run, and that
      heading is two words, each capitalised on its own. Fixing the word
      boundary and letting a run hold more than one word found all 22 true
      headings and cut the false matches to one: "O.D. N° 560" printed with
      its periods missing as "O d D N.I. 560," two abbreviations short of a
      word each, joined only because the length was checked for the whole
      run and not for each word in it. A third pass, checking each word's own
      length, found exactly the 22 genuine headings and nothing else.
- [x] **Only the two already-broken blocks change in what ships.** Of the 22
      runs, 20 sit in text that something else in the pipeline already cuts
      before publication — the masthead as a repeating page header, the
      cover-page headings as front matter — exactly as Phase 25 found. The
      two decree closings do not, and now read "DECRETA" in the published
      corpus for the first time.
- [x] **Verified.** Full corpus reprocessed at 0.4.32 (559 sittings, the one
      known no-quorum failure of November 2001 unaffected). Gold F1 1.00
      (124/125), annotations 36/36, both unchanged from 0.4.31. The audit's
      every named count — 1,121 unattributed rows, 5 turns opening mid-word,
      0 turns carrying a second speaker's label, 0 sessions written out
      twice — is unchanged, and none of the 17 affected sittings appears in
      any of its flagged lists. A corpus-wide scan for the same shape of
      run — four or more single characters joined by real spaces — finds the
      62 genuine short-word runs the rule was built to leave alone (spoken
      enumerations, lettered subsections, arithmetic) untouched, and the two
      "D E C R E T A" rows gone.
      (`reference/verification/stored_space_letter_spacing_0432.csv`)

## Phase 27 — a letter that isn't one, and the merge it defeated (August 2026 — parser 0.4.33)

Two of the four cut titles Phase 24 left open — both in one 2020 sitting,
both reading "…Orden del Día N" and stopping there — turned out to share a
single, narrow cause worth reading more than the titles alone.

- [x] **The ring after an "N" breaks a heading that never meant to break.**
      "Orden del Día Nº 117/20" prints its "N" and its "117/20" in the same
      bold as the rest of the heading, but the ring mark between them — "º" —
      comes out of the file in plain roman. That flip is exactly the fault a
      block-smoothing pass already exists to repair: a single character set
      in a different style than its neighbours is folded back into them,
      because on the page it is never a heading, a sentence, or a word of its
      own — it is one mark, sitting inside whichever word or number surrounds
      it. That pass excludes anything it reads as a real letter, so as not to
      absorb a genuine one-letter word standing alone. "º" is not a real
      letter by that test, but Unicode disagrees: it is coded as one (the
      same is true of "ª"), even though it reads exactly like the punctuation
      it is — "1º," "2ª" — everywhere a person would read it. The exclusion
      let every one of these marks slip past the pass meant to catch it, so
      the heading stayed broken at the "N" and the ring, wherever it landed,
      was read as its own island and thrown out as junk.
- [x] **The same fault is not two titles, it is 226 marks in nine sittings.**
      A corpus-wide scan for the same shape — a lone "º" or "ª," in a
      different style than both neighbours, sitting where an ordinal reads —
      found 231 of them. 226 share their neighbour's exact type size and are
      picked up by the fix: two in the 2020 sitting's own titles, and 224
      more scattered through ordinary speech and stage directions in eight
      other sittings from 2008 to 2023 — "el artículo 9" restored to "el
      artículo 9º," "Orden del Día N" restored to "Orden del Día Nº," a
      dozen years of senators reading article numbers and order-of-business
      numbers aloud, each missing its mark until now.
- [x] **One of the 226 was not a dropped character, it was a stolen line.**
      In the sitting of 6 August 2008, the stage direction "— Ocupa la
      Presidencia la señora vicepresidenta 2º del H. Senado, senadora
      Liliana T. Negre de Alonso." broke at the ring exactly like the
      titles did — but stage directions sit between speakers, not inside one
      person's own speech, so the second half of the line did not simply
      vanish. It landed as an orphaned turn, credited to whichever senator
      happened to be speaking just before, sandwiched between two of his own
      real remarks: senator Marín's turn read as if he had said "2º del H.
      Senado, senadora Liliana T. Negre de Alonso." himself. The fix makes
      this one whole stage direction again, and the misattributed row is
      gone.
- [x] **What is left, measured.** Five more marks of the same shape, in four
      more sittings — 2012-10-25, 2013-10-09, 2018-11-14, 28-09-2023 — sit
      next to a neighbour of a slightly different type size, so the same
      smoothing pass still will not reach them; widening the pass to ignore
      size too risks welding unrelated text together, and nothing here
      justifies that risk yet. The other two cut titles Phase 24 left open —
      one heading broken across a page (13 April 2011) and one broken by a
      double space that happens to sit inside the heading's own text
      (2 November 2011) — are a different fault and untouched by this one.
- [x] **Verified.** Full corpus reprocessed at 0.4.33 (559 sittings, the one
      known no-quorum failure of November 2001 unaffected). Gold F1 1.00
      (124/125), annotations 36/36, unchanged from 0.4.32. The audit's every
      named count — 1,121 unattributed rows, 5 turns opening mid-word, 0
      turns carrying a second speaker's label, 0 sessions written out twice
      — is unchanged, and none of the nine affected sittings appears as an
      outlier in the audit's source-fidelity check.
      (`reference/verification/ordinal_marks_0433.csv`)

## Phase 28 — the last two cut titles, and the fault behind both of them (August 2026 — parser 0.4.34)

The two cut titles Phase 24 counted and Phase 27 left standing — a title
broken across a page (13 April 2011) and a title broken by a double space
inside its own text (2 November 2011) — turned out not to be two odd cases.
Each was the visible edge of a fault reaching back across the whole
2000–2013 portion of the corpus.

- [x] **13 April 2011 was three faults stacked, not one.** The section's own
      number sits on the line above its title, in the body face rather than
      the title's bold, so the style grouping splits them — a shape Phase 13
      already recovers by reading a trailing "N." off the block above and
      splicing it onto the title below. Here the number was never adjacent:
      a footnote marker's own tiny scrap of text sat between the number and
      the title, one block further down than the recovery step looked. And
      the 2000–2013 layouts print that number without its full stop, which
      the recovery step required. And the page-apparatus cleanup that
      strips leaked page numbers read the now-unclaimed number as exactly
      that — a leaked page number — and deleted it before the recovery step
      ever ran. Fixing all three (looking past a footnote-sized scrap to the
      block under it, trusting a dotless number exactly as far as
      `continues_the_count` already trusts a dotless heading, and leaving a
      bare number standing when an unnumbered bold heading follows it) gives
      chapter 32 of that sitting its number back.
- [x] **2 November 2011 was one occurrence of a corpus-wide fault, not a
      one-off.** A heading's own two spaces are read as a printed line
      break — because that is what usually separates a heading from the
      speaker's label or appendix item glued to its own end — and the text
      is cut there. Here the two spaces sat inside one continuous bold run
      with nothing on either side that was a label or a new item; the title
      was simply the page's own line wrap, and cutting there threw its
      second half away. A full-corpus scan for the same shape — not a
      sample, all 559 sittings, read by diffing every recovered section
      against what the pre-session parser produced for the same file — found
      it was not one sitting, or one shape of double space either.
- [x] **The double space is not one shape, it turned out to be five, and
      each was found by the same full-corpus diff coming back with a new
      kind of wrong answer.** A part that opens in lower case is a wrapped
      sentence, not a new unit ("...Fortín histórico Huitrú" / "y Estancia
      Villaverde..."). A part that is nothing but the section's own leading
      number belongs to the title that follows it, never stands alone
      ("21" / "Subsidio para..."). A part that is the number plus a bare
      citation — a roman numeral or a bill reference code — is not yet the
      title it introduces ("67 II" of "II Foro Internacional...", "9
      S.-272/09" of "USO EFICIENTE DE LA ENERGÍA"). A part that opens with a
      bill's own citation is completing the word before it, not starting
      something new ("17 ACUERDO" / "P.E.- 22/12 EMBAJADOR..."). And the
      same shape recurs with the citation spelled "O.D. N° 812/12." instead
      of a bare dash-and-number, caught only on a second look at a title
      that had already been flagged short but not yet checked against the
      page ("13 ACUERDO" / "O.D. N° 812/12. PROCURADOR GENERAL DE LA
      NACIÓN"). Each rule was checked against the full corpus before the
      next was added, precisely because the first four each looked complete
      until the next sitting proved otherwise.
- [x] **What changed, measured against the pre-session parser on all 559
      sittings, twice — once to confirm the fifth rule was needed, once
      after adding it:** 660 section titles recovered where the parser
      previously found nothing, 87 more completed from a bare number to
      their full title, across 94 sittings. Zero sections present before and
      missing after, in either pass. Every title under two words among the
      recovered and completed ones — 17 of them, from "Manifestaciones" and
      "Juramentos" to "APÉNDICE" — was read against its own printed page and
      is the section's whole and genuine title, not a truncation. One
      sitting shows the scale a few small breaks can reach: in
      **2001-07-18**, a handful of section numbers — 6 and 9 among them —
      were lost outright, their own number set in the body face and
      dropped the same way chapter 32 of 13 April 2011 was; a numbered
      heading is only trusted as continuing the count when it lands within
      three of the last one recognized, so each loss left the running count
      too far behind to trust the genuine, undamaged headings that followed.
      Closing both faults together recovers chapter 6 and every one from 9
      through 99 — 92 sections in one sitting, every title built only from
      characters the file already carried, none of them invented.
- [x] **Verified.** Full corpus reprocessed at 0.4.34 (559 sittings; the one
      known no-quorum failure of November 2001 unaffected). Gold F1 1.00
      (124/125), annotations 36/36, both unchanged from 0.4.33. The audit's
      every named count holds or improves — unattributed rows 1,121 → 1,109,
      5 turns opening mid-word, 0 turns carrying a second speaker's label, 0
      sessions written out twice, all unchanged — and none of the 94
      affected sittings appears as a new outlier in the audit's
      source-fidelity check.
      (`reference/verification/heading_recovery_0434.csv`)

## Phase 29 — five readers sent at the finished corpus, and what survived checking (September 2026 — parser 0.4.35 and 0.4.36)

A review of the release candidate raised five defects. Each was re-derived
from the data before anything was changed, and each was real; two were
mis-measured, and one of those turned out to be a sixth of what was there.

- [x] **The stenographers' sign-off, inside a senator's question.** Every page
      of the 2013-onward format is signed "Dirección General de Taquígrafos"
      at the foot, and `strip_page_footers` looked only in the last 70 points
      of the page. Fourteen sittings set it a few points higher, where it
      survived the strip; a backstop then typed it as furniture wherever it
      formed a block of its own, which is why only the cases where it was
      glued mid-sentence ever showed. The review found one — Sanz, 7 May
      2014, "Usted habló del grupo Clarín; Dirección General de Taquígrafos
      ¿cuál más…?" — and a corpus-wide scan found six: that one and five
      stenographer's notes, two of them cut in half by it. The line is now
      matched on its own wording and cut anywhere in the bottom fifth of the
      page, so the band did not have to grow and take real text with it.
- [x] **What the repair moved, measured on all 559 sittings.** 233,415 rows
      against 235,402: 1,250 pieces of page furniture gone; 753 speech
      fragments rejoined into the turns they belong to (turn count and speaker
      count unchanged, so nothing was re-attributed); 19 stenographer's notes
      recovered from under the footer, including the opening event of the
      7 May 2014 sitting and the two notes it had cut in half; the section each
      turn belongs to now readable in 538 sittings against 530. **No speech
      lost**: per-sitting speech word counts are identical across all 558
      parsed sittings but one, and that one loses exactly the four words of the
      footer. Fourteen sittings changed at all. The two headings
      that disappear are single letters off an appendix signature block.
- [x] **The audit had been reporting it every run and still exiting clean.**
      `check_output_only` printed the page-apparatus count and returned only
      the glued-label count, so the one leaked footer never reached the exit
      status. It is counted now. All seven apparatus patterns report 0
      outside the two OCR scans.
- [x] **A caucus confirmed for the day it was recorded, not the day of the
      sitting.** `bloc_on` takes the observation nearest the sitting — up to
      200 days away — and passed its `fiabilidad` through untouched. The
      reading is checked against the caucus's dated life on the day of the
      VOTE, so the roll call of 21 Dec 2005 rightly reads "PJ Frente para la
      Victoria", a caucus formed that month; carried back to the nearest
      sitting in June it says a caucus that did not yet exist, and said it
      under `confirmed`. 73 (sitting, label) pairs, 99 passages. The check is
      now made again against the sitting's own date, which is what the column
      has always claimed to report. Roll-call readings only: an archived
      roster page's dates are the days it was CAPTURED, a floor on the
      caucus's life and not a claim about its start, so the 6 pre-2005 pairs
      below their caucus's earliest capture are left as they are — marking
      them would report gaps in the Internet Archive as facts about the
      chamber. `confirmed` falls from 83.4% to 83.3% of senators' floor words.
- [x] **The speakers table was a parser version behind.** 35 (sitting, label)
      pairs whose `n_blocks` no longer matched the passages — 152,466 stored
      against 152,514 present. Nothing missing and nothing extra, only counts
      left over from before Phases 26-28; regenerating it closes all 35. Now
      0 mismatches, and the release checklist runs `resolve_speakers.py`
      after every parse for exactly this reason.
- [x] **A gold score that could not tell a right label on the wrong words.**
      `eval_gold.py` compared a multiset of normalized speaker labels per
      page and threw away the opening words the annotation records beside
      each one, so two labels swapped between two turns left the multiset
      untouched and scored full marks. It now scores twice, the second time
      pairing each gold turn with a parser turn on label AND opening words,
      matched by prefix because the annotation writes as many words as it
      took to identify the turn. Swapping one pair of labels on each of the
      23 annotated pages that have two differently-named turns, as a test,
      leaves the old score exactly where it started, 124 of 125, and takes the
      new one to 79. **The two scores are the same on the real corpus** — 124 of 125 —
      so the weaker measure had not been hiding anything, but it could have
      been.
      What the second score does NOT add is any sense of position: both
      compare bags of turns, so four turns by the same chair coming out in
      the wrong order would still score full marks. An earlier version of
      this entry and of the README claimed otherwise. F1 is printed to three places: 0.996, not the 1.00 that
      `:.2f` had been rounding it to, and the docs now say 0.996.
- [x] **Documentation and licence.** `docs/DATA_DICTIONARY.md` still declared
      237,308 rows against 235,402 present, and stale type and event-type
      counts; all now regenerated at 0.4.35. The derived tables' licence had
      stood as a recommendation inside `docs/RELEASE.md` since Phase 15 —
      "CC BY 4.0 is the fitting choice and is what the release should state"
      — and is now declared in `LICENSE-DATA`, which every release carries.
- [x] **What the review got wrong, recorded so it is not re-litigated.** The
      footer count was 1, not 6. The gold evaluator compares label STRINGS as
      a multiset, not "quantities of labels per page" — order and opening
      words are what it misses, not the names. And one session,
      **2014-03-12**, now appears in the audit's source-fidelity check at
      10% (2 of 20 blocks): both are turns the footer used to split, whose
      three probe windows all straddle the join now that they are one block.
      Every half was read against the printed page and is there, in order,
      with only the footnote markers and the footer between them. It is the
      probe's known blind spot on short blocks with legitimate joins, not
      text from nowhere.
- [x] **A heading with no word in it, found in the review's own evidence and
      not in its report.** Four rows typed `heading` whose whole text is a
      space: the whitespace sweep runs before the heading passes, and those
      passes then make a bold space — left where a page header was cut — into
      a section title, a row that says a section began and cannot say which.
      The sweep is repeated at the end of the pipeline, where headings are
      already typed, and takes seven: the four plus three in **2001-11-29_r74**,
      one of the two OCR scans, that carry no alphanumeric character at all.
      Nothing else moves: 233,408 rows against 233,415, the difference is the
      seven. 0.4.36.
- [x] **One drift the review did not find.** The README put provincial and
      other alliances at "27-46% of floor words to 2016" by ticket; the
      notebook it cites has printed 30-46% since it was last run, and prints
      it still. Corrected. Everything else in Results was re-derived and
      holds, including the incident rate — 12.33 per 10,000 floor words in
      2023, against 0.96 through the 2000s. The committed notebook had also
      been a corpus behind (237,343 rows in its own output against the
      237,308 the dictionary declared and the 235,402 present), which is the
      same staleness as the speakers table and has the same fix: re-execute
      it in the release run, which the checklist already requires.

## Phase 30 — the blind reads re-asked, by something other than hand (September 2026)

The release checklist has required since Phase 15 that every answer recorded
in the blind reads still resolve to the same speaker in the re-parsed corpus.
Nothing implemented it: the nine rounds were run by hand, months and a dozen
parser versions ago, and the requirement had never been anything but a
sentence in a document. Two corpus changes in one day — 753 speech fragments
rejoined into their turns — is exactly the situation it exists for.

- [x] **`scripts/check_blind_reads.py`.** Re-asks all 5,463 records across 506
      sittings: is the passage the reader quoted still attributed to the person
      the parser named at the time? **5,459 hold, none resolves to anybody
      else.** The 4 that cannot be re-asked are recorded as such: two quotes
      are the three characters an unmapped font left of a passage ("E 26"),
      which nothing can locate; two are notes a repair has since moved out of
      speech — "— Se practica la votación por medios electrónicos.", which the
      corpus once had the chair saying out loud.
- [x] **The check had to be built to survive the project's own repairs.** The
      quoted words are a snapshot of what the parser held on the day of each
      round, and the rounds are what prompted the repairs that followed: a
      record from before 0.4.22 quotes "artículo 3(cid:47)", one from before
      0.4.33 quotes "artículo 7E" for the same ordinal, ones from before 0.4.16
      carry a letter cut off the front of the speech ("C En consideración...")
      or a section number glued to the end. A naive re-check reports 21 of
      those as failures, which would be reporting progress as damage. So the
      known artefacts are cut out, the longest surviving fragment becomes the
      key, and it is looked up in three windows so that whatever a repair took
      off either end does not defeat it.
- [x] **And to handle the short turns, which are not damage at all.** 96
      records quote a whole one-word turn — "Sí.", "Aprobado.", "Afirmativo.",
      "¡Sí, juro!" — and the chamber says those on every other page, so the
      words alone cannot pin the turn down. Matched as the whole turn on the
      page the round wrote down, which is exact: 94 of the 96 resolve, and the
      two that do not are the "E 26" fragments.
- [x] **The check can fail, which was tested rather than assumed.** On 40
      records of one sitting: as shipped, 40 hold; with every label in the
      sitting replaced, 40 report CHANGED; **with every label shifted by one
      position** — the subtlest realistic regression, each turn credited to its
      neighbour — 40 report CHANGED; with speech removed entirely, 36 report
      the passage missing. A check that cannot fail is not a check.
- [x] **The count of rounds was wrong in two places.** README and RELEASE.md
      both said eight blind reads and 5,413 pages; there are nine and 5,463
      turns. The missing one is `blind_read_50.csv`, the first round of all,
      50 of 50 in agreement. The data dictionary had it right.

## Phase 31 — the audit's own blind spot (September 2026)

The source-fidelity check looks a block up by three 40-character windows taken
from inside it, and had been reporting about 470 blocks as text found nowhere
in the PDF they came from. The figure had been going UP as the parser improved,
and the project had written that down as the price of repairing text. It was
the check.

- [x] **Why three windows can all miss.** A block carries cuts of its own, most
      often the footnote marker taken out of the middle of a sentence — which is
      why "…el proyecto de ley.3 Se comunicará…" comes out joined, reading as
      printed but no longer a literal stretch of the page. Where the pieces on
      either side of such a cut are each shorter than 40 characters — 38 and 25,
      in **2014-03-12**, the sitting that made this visible at 10% of its blocks
      — no window of that size can sit inside one, however the three are placed.
      All three straddle the cut. A block that fails is now looked up again by
      shorter windows swept across it, which lands one inside a piece.
      **0.422% unlocated becomes 0.009%, and 40 sittings above 1% become none.**
- [x] ~~**Verified as a fallback and not a loosening.**~~ **It was a
      loosening**, and Phase 32 replaced it. The reasoning here — that the
      rescued blocks rebuild from the source in two pieces — was a check on the
      blocks that happened to pass, not on what the test would let through. See
      Phase 32.

## Phase 32 — the second round, and the two checks that were not checking (September 2026)

Five more readers sent at Phase 29-31's own work, with the standing brief to
refute rather than confirm. Three of the five landed something real, and two of
those were faults in the verification rather than in the corpus — the worse
kind, because a check that passes wrongly is invisible.

- [x] **The audit's second chance was a hole, not a fallback.** A block the
      three 40-character windows could not find was accepted if any ONE
      24-character window of it appeared anywhere in the PDF. Measured against
      the corpus: genuine text checked against the WRONG sitting passed that
      test **28% of the time** (2.8% under the strict probe alone), and a
      genuine opening of **24 characters vouched for an invented tail of any
      length** — the anchor needed had fallen from about 50 characters to 24.
      Replaced by asking whether the WHOLE block can be rebuilt from the
      source, walking it from the start and each time taking the longest
      stretch still printed at or after where the last one was found. It
      separates: 98.4% of the blocks the long windows miss rebuild inside the
      eight runs allowed, most in two, while a genuine opening with an invented
      tail never does — 0 of 572. **The corpus passes the honest test
      everywhere** — 0.009% unlocated becomes 0.120%, still no sitting above 1%
      outside the two scans. A side effect worth recording: because each run
      must be found after the last one ENDS, the rebuild also notices a block
      whose own sentences came out shuffled, which no window test could —
      shuffling every turn of three or more sentences in 258 sittings, 12,987
      of them, 98.8% rebuild in their printed order and 3.6% shuffled, almost
      all of that the three-sentence turns (15.9%, against 1 in 7,463 for turns
      of six or more).
- [x] **And the first version of that walk did not do what its own docstring
      said.** It set the next run's starting point to where the last run
      BEGAN, not where it ended, so a run could be found inside the one before
      it and the ordering barely bound anything. Measured with the bug in
      place, 44.6% of shuffled turns still rebuilt; with the next run required
      to start after the last one ends, 3.6% do. It changes nothing about
      which blocks the corpus reports — the rate is 0.120% either way — and
      everything about what the test would let through.
- [x] **What the rebuild is honest about rather than good at.** Given the
      WRONG sitting's text it rejects 99.6% of blocks of 150 flattened
      characters or more, and accepts 46% of shorter ones — which is correct,
      not a failure: a short block holds a standing formula of the chamber and
      those words really are printed in the other sitting. And a few genuine
      blocks are reported as text from nowhere. Two of 243 in the sample just
      need more than the eight runs allowed; raising the cap to sixteen
      recovers those and takes the shuffle residue from 3.6% to 7.0%, so the
      cap stays at eight — a block wrongly shown to a human costs less than an
      order fault passing unseen. Others no cap recovers: page 76 of
      **2005-11-23** prints "Sí, menos los artículos 4E, 5E, 6E y 7E", each E
      an unmappable ordinal mark, and the corpus rightly stores "4°, 5°, 6° y
      7°" — the comparison key drops the degree sign and keeps the E, so one
      side reads "456y7" and the other "4e5e6ey7e". That needs a run per digit,
      and the walk takes the longest stretch available at each step rather than
      the one leaving the rest reachable, so it strands itself. Recorded, not
      fixed: it is a handful of blocks on a review list.
- [x] **The blind-read re-check could say "holds" of a passage that had
      moved.** It collected every block on the page that any window of the
      quoted words touched, pooled their labels, and asked only whether the
      recorded name was somewhere in the pool — so a coincidental match further
      down the page masked a genuine reattribution. **136 of the 5,090 records
      the window lookup settles** were decided by a pool reaching more than one
      speaker. Each record is now settled against the ONE turn that best
      carries the words — the whole quote first, then the number of windows —
      and where several turns carry it equally well, **every one of them must
      carry the recorded name.** Asking for one match was still a hole: where a
      page prints the same formula twice and only one of the two is
      reattributed, the untouched twin answered for it. Control on all 380
      records whose words more than one turn prints, reattributing one of the
      tied turns: **the old rule noticed 6, this one notices all 380.** Where
      the tied turns already carry different names the reader recorded one of
      them and the record does not say which — 43 records, now reported as
      unaskable rather than as holding. The corpus is unchanged: 5,416 hold,
      0 changed.
- [x] **The caucus was projected across disagreements.** `bloc_on` takes the
      observation nearest the sitting, and where the sitting falls BETWEEN two
      records naming different caucuses the switch happened somewhere in
      between — the record does not say on which side. Taking the nearer of the
      two carried one reading across the disagreement, sometimes backwards onto
      a day an earlier record contradicts. Those rows now read `disputed`:
      **29 (sitting, label) pairs, 113 passages, eleven senators**, of which
      **36 passages cross a party family** — Morales between the radicals and
      the Frente Cívico Jujeño in 2002-2004, Falco between the radicals and the
      Radical Rionegrino in February 2004.
- [x] **The first version of that rule disputed 2,049 passages, and was wrong
      about 1,936 of them.** It treated ANY record within 200 days as evidence
      of a switch, including records the pipeline had already flagged. The
      largest cluster — 1,816 passages, 88% of the whole set — disputed
      "JUSTICIALISTA" for sittings of August to October 2004 against a roll
      call of 3 February 2005 reading "PJ Frente para la Victoria". All 21 of
      that day's readings are recorded `acta_anacronica`, and `blocs_manual.csv`
      dates that caucus from 10 December 2005: it is not a competing account of
      2004, it is the back-labelling that `anachronistic` exists to mark, and
      the check simply failed to re-apply its own neighbouring test. One more
      row disputed a caucus against itself in different capitalisation. Only a
      record that could itself describe the day now counts as the other side of
      a disagreement, and the caucus names are compared normalised. `confirmed`
      goes back to 83.2%.
- [x] **The gold annotations were being checked more weakly than claimed.**
      `check_gold.py` verifies that each annotated turn's opening words really
      are printed under that speaker's label on that page — except it looked
      the label and the words up as two independent searches, so the words only
      had to appear SOMEWHERE at or after the label. Moving one turn's words
      onto another speaker's label on each of the 23 usable annotated pages,
      **the old check caught 0 of 23 and the fixed one catches 23 of 23** —
      and this is precisely the error the gold set exists to rule out. It also
      mispaired 10 of the 125 real turns, on pages where one label repeats:
      it took the first "Sr. Presidente" on the page and words printed up to
      514 characters further down, and in one case words printed 333 characters
      BEFORE the label it credited them to. The words must now start where the
      label ends, and all 36 pages still pass.
- [x] **What the new gold score does and does not do, corrected.** Phase 30
      claimed that carrying each turn's opening words alongside its label stops
      four turns by the same chair matching in the wrong places. It does not:
      both scores compare bags of turns and neither sees position, so a page
      whose turns came out shuffled still scores full marks. What it does catch
      is a label moved onto another speaker's words — swapping one pair of
      labels on each of the 23 annotated pages that have two differently-named
      turns leaves the old score at a perfect **125 of 125** and takes the new
      one to **79**. The claim in README and TODO is now what the measure
      actually does.
- [x] **Documentation caught up with the data.** `session_type`'s seven row
      counts in the dictionary no longer summed to the corpus's own total;
      `unmatched` was 218 where it is 215; median coverage 79.2% where it is
      79.0%; the three largest `match_status` shares off by up to two tenths
      of a point;
      "twelve passages, all from 2000-2004" for the archived-roster rows before
      the earliest capture, where it is 22 passages and all of them from the
      first months of 2000. In SOURCES, the caucus shares, and the claim that
      **most years keep over 98%** of their floor words in the caucus view —
      only **seven of the twenty** do, and 2006, 2007, 2019 and 2022 sit well
      below without being mentioned. The 0.4.11 entry's 710,039 spaces and its
      "F1 = 1.00" are left standing as what was measured then, with a note that
      Phase 19 put the count at 670,660 and the F1 is 0.996.
- [x] **The gold pairing could undercount, and the score was reported without
      its uncertainty.** `opening_overlap` paired each annotated turn with a
      parser turn greedily, longest annotation first. That loses a match where
      one speaker has two turns whose openings run together and then part —
      "Señor presidente: el proyecto a…" and "…el proyecto b…" — and the parser
      has a turn shorter than both, which opens either: the first annotation
      takes it and the second finds nothing left, scoring 1 where 2 was
      available. Replaced by a full pairing that re-routes an earlier choice.
      **The 36 pages score the same either way, 124 of 125**, so this is about
      what the measure would do on a differently shaped page. Reported with
      the sample now: one miss in 125 turns is a 95% interval on recall of
      0.956 to 0.999, the 125 turns come from only 24 documents, and 24 of the
      36 pages are 2020 or later — the pre-2016 record rests on twelve pages.

- [x] **A third round, on the second round's own work.** The rebuild's position
      bug, the caucus rule disputing against records already flagged, the
      annotation check that never checked adjacency, and the count of records
      the old pooled lookup decided on more than one name all came out of it
      and are above. Four more corrections it found in the prose: the caucus
      shares are of PASSAGES and were labelled "floor words" — counted by words
      anachronistic is 12.1%, not 13.1%; README dropped the "once the two scans
      are set aside" qualifier from the sitting-above-1% claim, which is
      literally false without it; the swapped-label demonstration leaves the
      old score at its baseline 124 of 125, not at a perfect 125 (a multiset of
      labels cannot beat the baseline by permuting, which is the point); and
      two of the three `match_status` shares moved by two tenths, not one. The
      0.4.11 and Phase 19 entries also disagree by one about how many spaces
      0.4.11 restored, 710,039 against 710,040, and neither is recomputable —
      both are left as measured and the clash is noted where it matters.

- [x] **What this round got wrong, recorded so it is not re-litigated.** One
      reader put the ticket-versus-caucus split at 22.3%/68.5% against the
      published 18.9%/72.0%, using a coarser classifier of its own and saying
      so; reconstructed with the notebook's own `family()` the published
      figures reproduce to a tenth of a point. Another reported the masthead
      leaking into speech in two scanned sittings, 11 rows and 2 — it is 5 rows
      in one of them and none at all in the other, and the audit already prints
      and excludes them by design.
      And the count of sittings whose text the footer fix touches is 14 as
      claimed at the block level, though 19 differ at the character level, four
      of them on front matter that is discarded anyway and one a separate
      footnote bug the restructuring fixed in passing.

## Phase 33 — the secretary took the floor and the record did not say so (September 2026 — parser 0.4.37)

The page prints "Sr. Secretario (Estrada). — (Lee:)" as one line: the secretary
was given the floor and the stenographer wrote down that he read. The
parenthetical is the stenographer's note, not words spoken, so the parser types
it as an event and events carry no speaker — but the label was consumed the way
every printed label is, and the turn it opened held nothing but that note. The
label was therefore written nowhere at all.

- [x] **265 printed speaker labels opened a turn with no row of its own.** Every
      one of them is a label whose turn holds only a note. The note now carries
      the label the page printed above it: **331 event rows gain a
      `speaker_raw`**, and the labels left unwritten fall from 265 to 91. Types
      are untouched — 233,408 rows, 151,761 speech, 31,955 events, the same
      three numbers as 0.4.36 — and `speakers.parquet` is unchanged, because
      `resolve_speakers.py` reads speech rows only.
- [x] **The rule is adjacency, not resemblance.** Only the block directly after
      a consumed label is attributed, so a note further down a turn stays
      anonymous. That matters: "— La votación resulta afirmativa" is about the
      chamber, not about whoever spoke last, and only the four notes that a
      label directly precedes could be read otherwise.
- [x] **A lone full stop was eating the connection.** The secretary's label
      arrives as three pieces in the 2000-2013 formats — bold "Sr. Secretario",
      normal "(Oyarzún)", bold "." — and the shard-of-a-label rule discards the
      third without emitting it. The first attempt cleared its "a label was
      just printed" mark on that shard and attributed 162 notes instead of 331;
      carrying the mark through the shard, as the rule already carries the
      running speaker through it, is what the fix turned on.
- [x] **What this does NOT do.** The gold set still scores 124 of 125, because
      `eval_gold.py` counts speech turns and this turn's one row is an event.
      The annotation calls the secretary's label a turn and the corpus now
      records it, but not as speech, and the two will keep disagreeing until
      somebody decides whether a turn holding only a note is a turn. That is a
      definitional question, not a defect, and it is written here rather than
      settled by moving 331 rows into `speech`.
- [x] **One thing found on the way, not fixed.** 36 of the newly attributed
      notes read "-Okay", and the page shows "Sra. Presidente.- Okay." — the
      chair really said it, and the typesetter set it in italics, which is the
      only thing that makes the parser call a line a stenographer's note. The
      attribution is now right; the type is arguably not. It is 36 rows across
      four sittings of 2016 and would need a rule that can tell an italicised
      word said aloud from an italicised note, which nothing in the file's own
      styling supports.

## Next

- [x] **0.4.37 is cut and deposited.** Notes in `docs/releases/0.4.37.md`,
      bundle built by `scripts/make_release.py` and checksummed beside the data,
      tag `v0.4.37`, published on Zenodo under 10.5281/zenodo.22661019.
- [x] (done, Phase 40) **At least 42 passages are real floor speech that lost its label.** They
      sit in the 1,109 rows the parser gives no speaker, which is otherwise
      inserted documents and scan damage: 362 rows are the two November 2001
      scans, 321 are three sittings whose record is mostly a list of judicial
      appointments or a decree text, and 155 of the remaining 426 are a word or
      less (a stray full stop, a single letter, an orphan "(Guinle)", a
      contents-page "Volver"). The 42 are not any of that. They read
      "Señor presidente: voy a ser muy breve porque hemos acordado que sea el
      presidente de nue…", "Pido la palabra.", "Quiero manifestar mi más hondo
      pesar por la lamentable desaparición física de Su Santida…". The count
      comes from matching how a turn opens, so it is a floor, not a total; the
      65 rows over 50 words outside the five known sittings are worth reading
      before deciding. Worth a look because these are senators speaking with no
      name on them, unlike everything else in that number.
- [x] (closed, 23 September 2026) **They were read, and it is one fault.** The entry above was written at
      0.4.37 against the 559-sitting PDF corpus; on the same PDF-only universe
      today the unattributed rows are 948, not 1,109, and the long rows
      outside the five known sittings are 45, not 65. All 45 were read against
      the printed page. **23 of them are real floor speech that lost its
      label, across 16 sittings.** The other 22 are correctly unattributed:
      21 are insertions, where a senator hands in a written text instead of
      speaking and the record prints it under "PARA INSERTAR" or "SOLICITADA
      POR", and one is a roster of appointments.
      The 23 are one fault with three faces, and the fault is that A BOLD RUN
      IS READ AS A SECTION HEADING, WHICH ENDS THE TURN. Either the label is
      printed but does not match the pattern (`S. ALASINO.—` for Sr., a bare
      surname `Negre de Alonso`, `S r a . Corregido.—` with the letters spaced
      apart, or a label whose first letter was pulled onto the tail of the
      previous sentence: `r. Pichetto.—`, `ra. Di Perna.—`,
      `r. Petcoff Naidenoff.—`); or the title and the surname fall in
      different style runs; or the bold run is not a label at all — a
      decorative drop cap, an emphasised word inside a spoken list, an
      expediente number — and it breaks the turn anyway.
      The worst case, verified here row by row: 2014-10-29_r18 pages 34-39.
      Row 157 is the chair saying "Muchas gracias, senador Fernández. Senadora
      Montero, tiene la palabra." Row 158 is `Sra.- ` alone, typed as a
      heading. Row 159 is `Montero.-Gracias, señor presidente...` — **3,591
      words, the largest orphaned block in the corpus**, her whole budget
      speech, with no speaker on it while the row above it names her.
      **Two more of the same family, from the HTML era**, found by the new
      split-bold-label check and verified row by row: `2002-08-01_r17` seq
      1631 prints `Sr. Presidented (Maqueda). -- Pasamos a considerar los
      órdenes del día...` — a stray "d" welded to "Presidente" — and
      `2003-02-27_r01` seq 151 prints `Sr. Presidente (Gioja), -- Corresponde
      elegir al vicepresidente 2...` with a comma where the full stop goes.
      Both land as `other` with no speaker, and both are the chair. Out of
      14,443 labels of that shape only these two fail, so the pattern is
      sound and it is the printing that defeats it — same as `S. ALASINO.—`
      and `r. Pichetto.—` above.
      The 42 was a floor because it matched how a turn OPENS and these open
      mid-sentence. The 152 rows of 2 to 50 words were not read and almost
      certainly hold more of the same: the entry above quotes "Pido la
      palabra." as an example, and that is three words.
      Closed 23 September 2026 (parser 0.5.5). Montero and most of the 23 had
      already been fixed by `repair_damaged_labels`; the two HTML cases too.
      What was left, measured on the PDF sittings outside the five known
      ones: 10 long rows (6 of them real speech) and 96 of 2 to 50 words, all
      read. Five causes, each fixed where the page shows it:
      (1) the lookup of how a person is called elsewhere in the sitting read
      "Sra. Avelín" as "Sr" + "a. Avelín", so it never found a woman — the
      repair then refused, for want of an honorific, every woman's label it
      met; (2) office and holder in three runs, "Sr, Presidente" / "(Pampuro)"
      / ". —", or welded behind a pointer, "Orden del Día Nº 357 Presidente" /
      "(Guinle)" / ". —"; (3) a bold drop cap, "N" / "acional", and a bold
      "Nº" before its number; (4) "Sr. Moliné O" / "'" / "Connor. —", the
      apostrophe in another font; (5) "Sra. Presidenta (" / "Fernández de
      Kirchner" / ").-", all three bold. A first draft of (3) joined a bold
      "a" to "contramano" in a 2001 scan: a one-letter word (a, e, o, u, y) is
      no longer read as a drop cap. Full re-parse against the previous output:
      21 sittings change, `other` rows 818 → 740 on the PDF side, 1,355 words
      gain a speaker, and no word moves from one speaker to another; the
      speakers table gains one label (Pampuro, resolved) and changes no
      attribution or caucus. Gold 310 of 310 unchanged. Left: "Sra Colombo.-"
      welded into a chapter title with no full stop (2004-09-15, "Pido la
      palabra."), and the two remaining rows of 2003-11-04 and 2016-11-23.
- [x] (re-measured and closed 23 September 2026, parser 0.5.6 — see Phase 41) The parser's open items are the five ordinal marks Phase 27 found but a
      neighbouring size mismatch keeps out of reach, and the 91 printed labels
      that still leave no row of their own. The secretary reading a document
      into the record was the bulk of that second number and 0.4.37 settled it
      (Phase 33): a note directly under a printed label now carries it, 331
      event rows gained a speaker, and the labels written nowhere fell from 265
      to 91. What is left of that case is definitional rather than a defect —
      `eval_gold.py` counts speech turns and this turn's one row is a note, so
      the gold set stays at 124 of 125 until somebody decides whether a turn
      holding only a stenographer's note is a turn.

## Phase 34 — the HTML era (September 2026)

The portal serves the same URL as a PDF or as the chamber's HTML export
depending on the sitting's age, and the downloader had been rejecting
everything that was not a PDF. Fixing that added 211 sittings of 1998-2003,
29 of 2025-2026 and the one served sitting of 1997: 559 holdings become 819,
and 21.5 million words of attributed speech become 25.7.

- [x] Accept both formats, keep each as served, record `format` per sitting
- [x] Census all 882 listed sittings before 1998: 881 are gone, one survives
- [x] Record `provisional` from the masthead, with `unstated` as a third value
- [x] `parse_html.py`: 214 files, no errors, 6.5M words of attributed speech
- [x] Rename `source_pdf`/`pdf_sha256` to `source_file`/`source_sha256`, add
      `source_format`, and re-parse every PDF so the corpus has one schema
- [x] Resolve speakers over the whole corpus: 23,711 label-sessions across
      816 sittings, 488 people. The roster reaches 1998 fine; what was missing
      was the sittings' own cover pages, which had never been read for
      1998-2003 and which name the chamber's secretaries and whoever held the
      gavel. Unresolved speech is 0.24% in the HTML era against 0.18% in the
      PDF era.
- [x] Separate the two senators named Sapag. The cover page settles the chair;
      the courtesy title settles the rest, with which given names the chamber
      writes as "señora" read off the corpus rather than guessed from the
      spelling. Every row a tiebreak decided says which one it was, in a new
      `tiebreak` column, because the title is how the chamber writes and not
      something it states. On the 69 Sapag turns the chair introduces by name,
      its wording agrees with the title in all 69.
- [x] No caucus for 1998 and most of 1999 — 19,797 senator speech blocks. The
      Internet Archive has no capture of the Senate's bloc-roster page before
      25 May 2000 (checked, not assumed: its CDX index holds no bloc page at
      all for the domain before then), and reaching back from that capture
      would cross the December 1998 renewal. Needs a different source — the
      chamber's printed roster, a library holding, or the transcripts' own
      mentions of who spoke for which bloc.
      Closed by the chair-call source in `scripts/extract_chair_caucus.py`;
      the exhaustive result and its checks are recorded below.
      PARTLY CLOSED, 21 September 2026. The same site ran one page per
      senator, and the Archive holds 58 of them from 2 February 1998, each
      printing "Bloque: …" (scripts/fetch_archived_profiles.py ->
      reference/senado/bloque_por_ficha.csv, every row with the address of
      its capture). The 1997 captures print "Partido: …" instead and are not
      used: a party is not a caucus. One page lagged the chamber (Vaca, gone
      20 January 1998) and is kept as printed, as the roster page's two are.
      Result: 5,932 blocks gain a caucus, every one previously empty and every
      one between 25 February and 19 August 1998; nothing else in the speaker
      table moved. 13,935 remain, August 1998 to November 1999, beyond 200
      days from both sources and mostly after the December 1998 renewal.
      Deliberately not done: carrying a senator's caucus across the gap
      because it reads the same in February 1998 and May 2000 — that is an
      inference, and the observations table exists not to make one.
      CLOSED, 22 September 2026, from the transcripts. A Codex agent searched
      the window and found the chair naming the caucus of the senator it gave
      the floor to ("…senador por Mendoza del bloque de la Unión Cívica
      Radical. Sr. GENOUD.-"); it reported 38 such calls, and an exhaustive
      scan of the same wording found 157 before May 2000.
      scripts/extract_chair_caucus.py keeps 153: a call counts only where the
      province the chair names is the speaker's own (four refused — the chair
      called one senator and another spoke), the chair's wordings are mapped
      by hand to the names the caucus data uses, and "bloque de la Alianza"
      is refused (ten calls): a coalition of two caucuses that sat apart.
      Every row carries the transcript's address and the chair's words
      verbatim. Where a call and an archived page fall within 200 days of each
      other they agree 66 times out of 66. Result: senator speech with a
      caucus 89.7% -> 98.0%, 12,874 blocks gained, no caucus that existed
      changed and no disputed reading added. 1,061 blocks of 1998-1999 remain
      without one — senators the chair never introduced by caucus.
- [x] (done, 22 September 2026) The senators' own floor statements of their
      caucus, 1998 to May 2000. Two Codex (Terra) agents searched: one the
      Internet Archive's every capture of the Senate's site 1997-2000 (846
      addresses; nothing new — committee lists, a bloc page naming caucuses
      but no members, officers with party initials), the other the
      transcripts, which found 15 statements. A pattern search of my own over
      every 1998-2000 speech by the 58 senators then without a caucus found
      74 passages, and read one by one, 32 say plainly which caucus a named
      senator sat with (scripts/extract_declared_caucus.py, which also says
      what was refused: "el bloque de la mayoría", "mi bloque", "bloque de la
      Alianza" — the coalition — and "bloque peronista", which does not say
      which Peronist caucus). None disagrees with another source within 400
      days. 275 blocks gained, none changed; 786 of 1998-1999 remain.
- [x] (done, 23 September 2026) Carry a caucus across a gap where the same
      senator is recorded in it on both sides, inside one mandate. Measured
      first: of 550,000+ roll-call pairs 400-2,200 days apart showing a
      senator in the same caucus, none has another caucus in between; of the
      archived roster pages' 1,591 such pairs, 2 do. 392 blocks of 23
      senators, all 1998-1999, spans 407-843 days (median 659), marked
      `bloc_status = "bracketed"` with a new `bloc_span_days` column; none
      changed an existing caucus. 394 blocks of 1998-1999 remain, mostly
      senators with an observation on one side only (Avelín, 131).
      CORRECTED the same day: the roll-call half of that measurement says
      nothing. The Senate re-labels old roll calls with a senator's later
      caucus, so they show a change inside 2 of 338 mandates where the
      roster pages show one inside 17 of 176. The rule rests on the roster
      pages' 2 of 1,591 alone, and the docs now say so.
- [x] (done, 23 September 2026) The chair's calls without the word
      "bloque". The first reading kept only "del bloque …" with no comma
      before it and missed "por San Juan, del bloque …", "de la Unión Cívica
      Radical", "del Partido Cruzada Renovadora", "ha pedido la palabra".
      153 calls become 311, none lost; each of the 158 new ones checked
      against the same senator's other readings within a year first: 153
      agree, none disagrees, 5 have nothing near. 194 blocks gained (Avelín
      131, Molinari Romero 32, Bauzá 15, Villarroel 9, Raijer 4, Ortega 3),
      190 bracketed blocks now rest on a call instead, nothing changed.
      Coverage 98.6%; 200 blocks of 1998-1999 remain.
- [x] (refused, 23 September 2026) Two ways to fill those 200, measured and
      not taken. Carrying a caucus from one side only, within a mandate: on
      the 2000-2004 roster pages 5% of such carries 200+ days long land on a
      different caucus, 7-10% beyond 600 days. Bracketing across a
      re-election (Tell, Sager, Costanzo): 21 testable pairs, and in 2 the
      senator changed caucus exactly as the new mandate began. Rivas and
      Ludueña have no reading at all.
- [x] (done, 23 September 2026) Checked the corpus against the official
      counts per caucus (scripts/check_bloc_counts.py, counts copied by hand
      from the HCDN document below). 2002: every caucus matches, once Mera,
      sworn in on 5 March, is allowed for. 1999: the corpus never puts more
      senators in a caucus than the chamber counted; the 11 senators it leaves
      without a caucus fill exactly the shortfalls, with one exception below.
      Two real disagreements, both left as they are:
      - Santa Cruz. The document has a one-senator "PCIA STA CRUZ-PJ" on 1
        March 1999 and 1 March 2000. The corpus puts both Santa Cruz
        Peronists, Varizat and Arnold, in JUSTICIALISTA: the chair calls each
        "del bloque justicialista" in June 1999, and the archived roster page
        of 25 May 2000 lists both there. The dates differ by three months, so
        the two need not contradict, but nothing says who sat apart.
      - Morales, 2004. The document counts two in the Frente Cívico Jujeño on
        1 March 2004; the archived roster page of 24 March lists Morales back
        in the UCR. The corpus already marks his caucus there `disputed`.
- [x] (done, 23 September 2026) Deduce a caucus from the official count
      where it leaves one answer (scripts/deduce_bloc_from_counts.py). On 1
      March 1999 the 11 senators without a caucus fill the 11 places the
      count leaves: Almirón the Fuerza Republicana seat, Romero the Fueguino,
      Silvia Sapag the Neuquino, Gagliardi and Massaccesi the two Radical,
      six Peronists the six Peronist (JUSTICIALISTA and the Santa Cruz one
      counted together; none of the six is from Santa Cruz). Marked
      `deduced`, used only where no reading is within 200 days, within 200
      days of the count and inside the same mandate — so Tell's and
      Costanzo's 1998 blocks, in the mandate before, stay empty. 99 blocks
      gained, nothing else moved; 97 of 1998-1999 left.
- [x] (closed, 23 September 2026) A web search (Sonnet agent) found no per-senator
      caucus for the 200 blocks, but one whole-chamber source: the Chamber of
      Deputies' "Composición del H. Senado por bloque y género", counts per
      caucus on 1 March of each renewal year, 1984-2024 —
      https://www2.hcdn.gob.ar/export/hcdn/secparl/dgral_info_parlamentaria/dip/archivos/SenadoresporBloqueGenero-_Cantidades.pdf
      No names, but on 1 March 1999 it lists a one-senator caucus "PCIA STA
      CRUZ-PJ" beside JUSTICIALISTA (33). Santa Cruz's Peronist senators then
      were Varizat (the chair calls him "bloque Justicialista" on 16 June
      1999) and Arnold, so one of them sat apart — which is why Varizat's
      1998 blocks must not be filled with JUSTICIALISTA by default. Two uses
      worth doing: identify who sat in that caucus, and check the counts of
      1 March 1996, 1999 and 2000 against the caucuses the corpus assigns on
      those days. Searched without result: Wikipedia (no 1995-2001 senator
      list), Wikidata, Página/12 and Río Negro archives, Directorio
      Legislativo (unreachable), La Nación, Clarín (blocked to the tool).
      Two more independent Sonnet searches the same day, one of official
      documents (other HCDN files, Senate decrees, Boletín Oficial, Congress
      guides, Directorio Legislativo via archive.org) and one of provincial
      press and academic work, found no per-senator caucus and no named
      whole-chamber list for 1996-2000. What they did find: two floor
      statements of Oyarzún in our own transcripts that the hand search had
      missed (now in extract_declared_caucus.py, +4 blocks, 196 left), and a
      Perfil retrospective saying Cristina Fernández de Kirchner, expelled from
      the Justicialista caucus in May 1997, "formó su propio bloque, 'PJ Santa
      Cruz'" — the likely origin of the 1999 one-senator caucus, though
      nothing found says who held it in 1999. Next step if anyone pursues
      it: each provincial paper's own archive, searched through its own
      interface, which general web search does not reach.
      A last round the same day, three Haiku agents searching each of the 17
      senators still missing (97 blocks) by exact full name, found nothing
      usable: every "finding" was a caucus guessed from a vote, an attendance
      list or a party, mostly from transcripts already in the corpus, with no
      quote naming a caucus; one was wrong (Reutemann put in "the Alianza").
      Not passed on to verification, since there was no quote to verify.
      Three Sonnet agents then tried what general search misses (provincial
      papers, archive.org, Google Books, academic repositories): nothing for
      1998-1999. Two real notes of November 2000 name Varizat (Ámbito,
      16 Nov 2000, "subloque 17 de octubre") and Carbonell (Revista Mercado,
      15 Nov 2000) inside the Justicialista caucus — agreeing with the roster
      pages the corpus already uses for those dates, and too far from the
      missing blocks to fill them. Río Negro's 1998 site has only three
      homepage captures on archive.org. What is left needs each provincial
      paper's own archive search, by hand.
      Closed here: the 97 blocks stay without a caucus, as marked.
- [x] (done, 22 September 2026) Three sittings of 2003 label the chair "Sr.
      Presidente (Maqueda)" after Maqueda left the Senate for the Supreme
      Court on 27 December 2002. It is 13 blocks, not 15, all routine agenda
      items ("Corresponde considerar el dictamen…", "En consideración…")
      re-used from a template that still carried his name. A chair or officer
      label whose name nobody held any seat or office under on the day, while
      someone had before, is now read as the bare office (`office_only`), the
      same as "Sr. Presidente": the label says the chair spoke and no more.
      The full scan let through two more of the kind and nothing else —
      "Sr. Presidente (Losada)" in 2008-12-17_r23 and "Sr. Secretario
      (Estrada)" in 2017-11-01_r14 — once a first draft, which also caught
      names still in office, was tightened: "Sr. Presidente (Oyarzún)" in
      2001, the sitting's own secretary, stays unmatched as a misprint, and
      "Sra. Presidente (Villarroel)" of 2025-05-07 is Villarruel misspelt and
      is now a recorded variant. Unmatched passages 190 → 174.
- [x] (done, 21 September 2026) 39 sittings of 2024-2026 have no readable
      masthead: the cover page changed again and `extract_authorities.py`
      does not follow it. It was 40, from 13 December 2023 on. The new cover
      is not a masthead in another layout but a different statement: an
      "A U T O R I D A D E S" list of who HOLDS each office, every
      vice-president included and vacant posts marked, where the masthead
      said who PRESIDED that sitting. It is read now, into a new `basis`
      column (`roster` against `masthead`), and resolve_speakers takes roster
      rows for tenure and never for who held the gavel — reading them that way
      would hand a same-surname chair to a vice-president who was not in it.
      "It costs nothing today" was not quite true: three officers the curated
      table does not have — Fitzgerald, Viramonte Olmos, Finochietto — had
      labels going unresolved, and now resolve from the cover. Adding the
      roster also exposed that the curated row only won over a cover-page row
      for labels naming the office; a bare surname with both records valid on
      the day was left unresolved (Tunessi, 20 December 2019). Fixed on the
      day, not across spans: a first attempt dropped the cover record wherever
      the two overlapped, and since the curated Tunessi covers weeks where the
      covers show four years, it lost 73 of his labels. Net: 4 labels
      resolved, none lost, unresolved 124 to 120. Six sittings still have no
      cover read, each for its own reason — the image-only 1997 tribunal, the
      two joint sittings of both chambers, the November 2001 scan and two
      tribunal sittings of November 2003.
- [x] (decided 23 September 2026: left out, by the project owner's call) One sitting does not parse: the 1997 impeachment tribunal
      (1997-12-18_r117, 117th reunión, 21st sitting as tribunal, the trial of
      judge Francisco Miguel Ángel Trovato). The reason recorded here before —
      that it does not open like an ordinary sitting — was wrong. Looked at
      21 September 2026: the file is a photocopy saved as eight page images
      with NO text layer, zero characters on every page. "no_opening_found" is
      simply the parser finding nothing to read.
      The pages are legible, two columns, bold labels and italic notes. OCR
      works tolerably — tesseract with only its English model reads the
      columns in order and keeps "Sr. Villarroel. — Pido la palabra.", though
      it mangles accents ("sefiores"); the Spanish model is not installed.
      What OCR cannot give back is bold and italic, which is how the PDF
      parser tells a label and a note from speech, so it would need a
      text-only reader of its own, and the result would carry the same
      scanned-session flag as the two 2001 scans. Left out for now: eight
      pages, the only 1997 sitting held, the rest of the corpus 1998-2026.
      Reopen if a year-1997 sitting is ever wanted.
- [x] 29 October 2003 is served twice, as reunión 27 and reunión 28, byte for
      byte identical. The document decides it: its masthead reads "28°
      Reunión - 6° Sesión en tribunal", so reunión 27's slot returns the wrong
      document. Parsed once, under reunión 28;
      `reference/senado/superseded_sources.csv` records the decision, and both
      files stay on disk and in the manifest. What the portal serves is a fact
      about the portal, and the ordinary sitting of that day is simply not
      held.
- [x] Re-run the analysis and the figures over all 817 sittings. The notebook
      now takes the caucus from `speakers.parquet` rather than the older spell
      table, which is what let the caucus panel start in 2000 instead of 2005,
      and it keeps the readings the Senate mis-dates after checking what they
      get wrong: the name, not the family (1.4% cross one). Dropping them
      would have cost 40% of 2018-2019 and biased the panel against the
      peronist family, which is the one the Senate back-labels.
- [x] Put the HTML era through the audit. `audit_parse.py` opened every source
      with pdfplumber, so the conservation and coverage checks had never seen
      these 214 files. They pass: not one of 54,829 probed blocks is missing
      from the file it came from, against 0.008% on the PDF side, and the HTML
      keeps a median 91.2% of what it prints against 79.3%. The three turns it
      reports as opening mid-word were each read back against the file and the
      page prints them that way — one of them because the chamber's own typist
      dropped the opening words of a sentence.
- [x] The audit found its own bug first. Two files declare utf-8 and were being
      read as iso-8859-1, which turned "VERSIÓN TAQUIGRÁFICA" into mojibake:
      the audit called a third of their text foreign, and the same assumption
      in two other scripts left those sittings declaring no provisional status
      and naming no officers. One decoder now honours the declared charset and
      the parser, the provenance and the audit all use it.
- [x] The audit also found a sitting parsing to seven rows of debris and no
      speech at all. Where a file sets the opening dash in roman with the page
      number before it, the front-matter cut ran past the opening and matched
      the CLOSING event, taking the sitting's only speech with it. Measured over
      all 605 held PDFs, recognising it moves the cut in 123: 115 gain the
      opening event, 7 recover real content the old cut threw away — 22 March
      2006 was losing two whole sections — and the no-quorum sitting of 29
      November 2001 goes from not parsing to parsing. Parser 0.4.38.
- [x] A blind read of the HTML era, the tenth round and the first on these
      files: 60 passages, five readers, each given the file and the words and
      never the parser's answer. 48 name the same speaker. 11 the readers
      refused to pin down and were right to — see the next item. The one
      disagreement was theirs and it was correct, and it found a real defect.
- [x] A centred section number and an `<h1>` title were being read as words the
      chair said. The HTML reader recognised a heading only by the `<center>`
      tag, and a later exporter carries the same thing in CSS — the same shape
      as the CSS-bold labels already handled. 117 rows of one sitting's agenda
      were credited to Gioja as speech. Fixed in 0.5.1-html, with centring read
      as a property of the paragraph and cleared at each break: as a nesting
      depth it never comes back down, because these files use `<p>` as a
      separator and never close it, and every later paragraph then reads as a
      heading. 18 of the 214 files can be touched by the rule at all; after it,
      no section title anywhere in the corpus is emitted as speech.
- [x] The review sheet could not be answered for half its rows. With no page to
      offer, turns opening alike in the same sitting hashed alike, so 60 rows
      held 47 distinct passages — one sentence nine times over — and the reader
      could not tell which occurrence was meant anyway. The draw now keys on the
      passage's own text AND which occurrence of it this is, and the sheet says
      "3 of 41" where the words repeat. 60 rows are now 60 distinct passages.
- [x] A second, larger HTML round: 300 fresh passages over 131 sittings, read
      by twenty readers, none overlapping the first 60. 297 name the same
      speaker. Two disagreements were the sheet miscounting — it numbers turns
      whose WHOLE text matches, a reader counts the words as printed, and the
      two diverge where the phrase also sits inside a longer turn; both were
      verified against the file and the parser was right. The third was real.
- [x] WordPerfect sets each accented letter in a font of its own, so a bold
      label split into three runs — "Sr. AVEL", "Í", "N.-" — and the parser read
      only the first, which matches nothing. In the sitting of 13 May 1998 every
      senator with an accent in their name lost their turns: two were swallowed
      into the chair's and three dropped outright. Runs are now merged by style
      rather than by tag. Across the 214 files this touches 17 sittings, +32
      turns, +993 words, and four speaker labels that had never appeared; the
      parser's sequence of that sitting's fourteen "Pido la palabra." now
      matches the blind reader's, name for name. 0.5.2-html.
- [x] The review sheet's `which_occurrence` counted turns whose whole text
      matches; a reader counts printed occurrences. Thirteen of the twenty
      readers of the 500-passage round reported the gap without being asked,
      and it accounts for all seven of that round's disagreements. It now
      counts occurrences of the quoted words in the source file, which
      reproduces four readers' own counts exactly — 78 "(Lee:)" where the
      sheet said 76, 25 "En consecuencia, pasa al Archivo." where it said 20.
      Only for HTML: a PDF row carries the page number, which is how a reader
      finds the passage there.
- [x] (closed 23 September 2026: the sheet now carries `printed_just_before`, the
      last 15 words printed ahead of the passage) The label a reader is shown is sometimes too short to be an answerable
      question — "(Lee:)", "Pido la palabra." Now that the occurrence count is
      right the reader can still be sent to the right passage, but a sheet
      that quoted more would not depend on the count at all.
## Phase 35 — the labels the parser was not reading (September 2026 — parsers 0.4.40 and 0.5.4-html)

- [x] Widen the speaker pattern to the honorific as the typists spell it.
      The pattern demanded "Sr." with a stop and one space, and the HTML era
      also prints "Sr.Presidente" with no space, "Sr Sager" with no stop,
      "Sr- Usandizaga" with a hyphen for it, "Sr. .Pichetto" with two, and
      "SR. PRESIDENTE" and "VARIOS SEÑORES SENADORES" shouted. The case is now
      free and the separator loose, but a letter must follow, which is what
      keeps an ordinary word beginning "Sr" out. Checked against every label
      in the corpus: one was lost and it was a mangling ("Sr. .Pichetto"),
      recovered by allowing the doubled stop. 0.4.39.
- [x] Read the labels the HTML splitter was throwing away. Four mechanics,
      each measured on all 214 files before and after: a bold run that stops
      inside the holder's name ("Sr. PRESIDENTE (Cafiero" + ").- La
      Presidencia"); a terminator that does not end the run, because the first
      character of the speech is bold along with it ("Sr. YOMA.- ¿"); a label
      the typist ended on a full stop and no dash at all ("Sr. GENOUD. Si no
      le daban mandato"); and a label set in the body face, which 42
      paragraphs are. The loose paths are fenced: the in-run cut needs a
      label-shaped prefix, the bare stop needs a name of one or two words and
      a new sentence after it and never a colon — a colon after an office is
      how an inserted letter greets its addressee — and the body-face path
      needs an explicit dash. Against the previous parser: 317 labels gained,
      0 lost, 11 changed and every one of the eleven cleaner than before
      ("Sr. PRESIDENTE.- (Losada)" is now "Sr. PRESIDENTE (Losada)").
      0.5.3-html.
- [x] Read the files in windows-1252, which is what a browser does with a
      declaration of iso-8859-1 and what the exporter meant. 40 of the 212
      files that declare it put bytes in the range latin-1 leaves as control
      codes: 252 curly quotes, 46 dashes, 12 ellipses. The dashes were the
      cost — the em dash that ends a speaker's label, so the label had no
      terminator and the sitting lost the speaker.
- [x] File the attendance roll as furniture. The PDF side never sees it, cut
      with the front matter; the HTML export prints it inside the document,
      where nothing marked it off, so 624 senators' names sat in the corpus as
      text attributed to nobody. Recognised by its own shape: a shouted
      heading, then "SURNAME, Given" one to a line. 3 of the 624 are left, and
      they stand outside any roll.
- [x] File the printed apparatus that was still unattributed: the footnote
      pointing at the appendix, the stenographers' office sign-off, and the
      bare "Volver" back-link on each appended roll-call plate. No block of
      the last shape is speech anywhere in the corpus, in either format.
- [x] Together: text the parser cannot attribute to anyone fell from 1.52% of
      the corpus to 1.25%, speech turns rose 247,130 → 247,469, and all 5,823
      records of the eleven earlier blind rounds still resolve to the person
      the round named. The gold set is unchanged at F1 0.996.

## Phase 36 — a gold set for the HTML era, and what it cost to build (September 2026 — parser 0.5.5-html)

- [x] The 36 gold pages were all PDF pages — they are keyed by page number and
      the HTML export has none — so 214 sittings, 85,684 turns and 5.9 million
      words had never had turn recall or event recall measured. A blind read
      cannot supply it: it samples turns that exist and never asks whether one
      is missing. The unit is a stretch instead, ~7,000 characters cut on the
      source by offset, drawn by `scripts/draw_gold_html.py`, four per year
      across 1998-2003. Cut on the source deliberately: cutting at a heading
      the parser found would hand the annotators only what it already reads
      well.
- [x] Two readers annotated all 24 stretches independently.
      `scripts/check_gold_html.py` reports the agreement before either is
      believed: 99.2% of turn starts, 22 of 24 stretches identical,
      `opens_mid_utterance` the same everywhere. The two disagreements were
      the same question, and both readers had already named it.
- [x] Settle it: a printed label opens a turn, and rule 2 of the brief reaches
      only an unlabelled paragraph that runs on. Not chosen by preference —
      the convention is in Phase 2 above, the PDF gold set does the same
      (`gold_2004-04-28_p24.json` lists four separate chair starts across two
      electronic votes), and the parser gives 497 turn ids to 497 labelled
      rows of one sitting. Four annotations were re-emitted under it.
- [x] The defect the set was built to find: 18 November 1998 prints
      `Orden del Día N° 1230Sr. PRESIDENTE.-` inside one centred bold run with
      no space between the document's title and the chair's label. The title
      made the paragraph a heading and the label was never reached, so the
      turn was lost. Both readers flagged it before it was scored. Exactly two
      paragraphs in the 214 files are botched this way, one centred and one
      not; the split fires only where a label is welded to a document pointer
      with no space. 0.5.5-html.
- [x] The other defect was the brief's, not the parser's: it called a
      parenthesised note an event without saying where it has to sit, so 15
      inline notes were recorded as events that the parser had correctly kept
      inside a speaker's turn. Event recall read 0.803 and was measuring the
      brief. Corrected, and the six affected annotations re-emitted.
- [x] Against the settled set: boundary and attribution P=1.000 R=1.000
      F1=1.000 on all 195 annotated turns, events P=1.000 R=1.000 on 62,
      identical under either reader.
- [x] Decide what a note closing a speaker's paragraph is. The convention
      names two positions, standalone and inline, and the page uses a third:
      "...seguimos siendo pobres, señor presidente. (Aplausos.)" — speech
      before it, nothing after, inside the paragraph. It is treated as inline
      today, which makes "Aplausos" a word the senator spoke. An annotator
      raised it; applause closing a speech is probably the commonest note in
      the corpus, so the count it affects is not small.
      Settled as rule 4 of `reference/gold/ANNOTATION_BRIEF.md`: a
      parenthesised note inside the speaker's paragraph belongs to the turn.
- [x] Fix the annotation brief before the next set is drawn: say that an event
      stands as its own paragraph, and that a printed label always opens a
      turn. Both cost a re-emission this round. Both rules went in with the
      set itself (a94c38a) and this entry outlived them. They are now keyed to
      the markup rather than asserted about "paragraphs", which mean nothing
      obvious in a WordPerfect export: `<P>` is a separator that is never
      closed (2,013 of them in 2000-08-23_r46, none closed), so an event is a
      note with a fresh `<P>` opened in front of it. The italics are not the
      test — 2000-08-23_r46 prints two `(Aplausos.)` inside one running `<P>`
      of speech, one italicising the word and the other the whole
      parenthesis, and neither is an event.

## Phase 37 — where the dropped text goes (September 2026)

- [x] 52 sittings of real length keep under 60% of their printed text, and
      nobody had ever looked at what the other 40% is. It is not lost debate:
      **91.8% of those 785,705 words are an appendix or an insertion**. The
      worst, 20 April 2005 at 14%, is an impeachment tribunal that closes on
      page 13 of 74 — "queda levantada la sesión", 23:37, the stenographers'
      sign-off — with the Orden del Día 1755 appended behind it. 27 November
      2003 closes at row 66 of 693 with 88,861 words of appendix after it.
- [x] (closed 23 September 2026 — see Phase 41) The residue is 64,592 words, of which 36,851 are in two of the three OCR
      scans, where the fault is the scan. That leaves ~27,700 words across 50
      sittings, and the rule that explained the rest is a keyword heuristic,
      so that figure is a ceiling rather than a measurement. Worth one pass.
- [x] (done, Phase 40) **A SITTING HOLDS THE WRONG DOCUMENT. 2014-09-03_r13.** The special
      sitting of 3 and 4 September 2014 on the debt swap and the RUFO clause
      prints 264,787 words; the corpus holds 118,986. **The first 214 pages of
      floor debate are absent** — pages 9, 60, 120 and 180 were probed on
      their body text and none is in the corpus, while 223, 224 and 300 are.
      Worse than the absence: the parser began reading at page 224, where a
      COMMITTEE MEETING OF 19 AUGUST is appended, and the first row of the
      corpus for this sitting reads "a las 17 y 18 del martes 19 de agosto de
      2014". So a large part of what ships under this session_id is a
      different document of a different date, with its participants counted
      among the sitting's 58 speakers.
      **Not a late start.** 37 of 514 PDF sittings begin after page 10 and
      almost all are legitimate: 2010-04-28_r07 begins at PDF page 96, which
      carries the printed header "Pág. 9" — 95 pages of contents and Orden del
      Día listings precede the sitting's own first page, and the parser starts
      exactly where it opens. 2019-07-17_r07 is the same. Both were reported
      to this project as lost floor speech and neither is. **The symptom to
      scan for is not a late start but a parsed date that disagrees with the
      sitting's own date**. That check is now written and run
      (`scratchpad/date_mismatch.py`): it reads the date out of the opening
      stage note, "a las 15 y 33 del miercoles 28 de abril de 2010", and
      compares it with the sitting's own. **Six hits corpus-wide, and only one
      is a defect**: 2014-09-03_r13 above. Of the other five, two are the
      chamber's own typing — 2008-09-03_r14 and 2012-08-15_r12 each open with
      the year one short of the masthead's ("3 de septiembre de 2007" under a
      masthead reading 2008; "15 de agosto de 2011" under 2012), and the
      parser preserves the error, which is right — and three are off by a
      single day because the sitting ran past midnight (2003-11-27_r38,
      2004-11-10_r32, 2018-06-27_r08). Six alerts, one defect, every false
      positive explainable. **Move it into `scripts/audit_parse.py` as a
      standing check**: it would have caught 2014-09-03_r13 with nobody
      reading a page.
      Scan of first/last page per sitting: `scratchpad/late_start.csv`.
      Found while checking a claim of ~217,000 lost words. That figure does
      not survive: half of it was 2010-04-28_r07's front matter. The confirmed
      loss is ~145,800 words in this one sitting, which is still five times
      the ceiling recorded above for all fifty.

## Phase 38 — a second blind round, and the sheet it broke (September 2026)

- [x] 498 HTML passages drawn fresh (28 overlap the first round of 500) and
      read by twenty readers who saw the page and never the parser's answer.
      **497 confirm the parser. The one disagreement is the reader's**: at
      h203 the page prints `Sr. Pardo. --` directly above the passage and the
      reader read up past it to the chair's previous label. Evidence in
      `reference/verification/blind_read_500_html_r2.csv`.
- [x] The round's ten apparent disagreements were all the sheet, not the
      parser, and they exposed two faults in how a passage is numbered.
      **A string count is not a block count**: a sitting prints its contents
      list before the debate, so the first "Tiene la palabra el señor senador
      por San Juan." in the file is a line of the summary and not a turn.
      **And a folded quote matches inside longer words**: "Sí." folds to
      "si." and was found inside "así.", sending a reader to the tail of
      somebody else's sentence. Blocks are now placed by walking the file, and
      a match buried inside a word is not counted. Every one of the 498 rows
      now lands on the block whose speaker it prints; ten did not before.
- [x] `--sample-seed` on the audit, so a second round draws passages the first
      did not see instead of redrawing the ones already answered.
- [x] `scripts/show_passage.py` — opens an HTML transcript at a passage for a
      reader, marking the bold runs, since these files have no page numbers.
- [x] (closed 23 September 2026: the check exists — `audit_parse.py`'s "HTML split
      labels" section finds 14,443 labels of this shape and verifies each one's
      attribution) Nineteen of twenty readers reported the same thing unprompted: the bold
      run that should wrap a speaker's label instead opens at the section
      heading above it and closes partway through the name, so the label is
      not a bold run of its own. The parser reads these correctly — that is
      what the round measured — but no check states that it does, and the
      readers are describing the single commonest shape in the era.
## Phase 39 — 36 more gold pages, and the note the parser swallows (September 2026)

- [x] 36 pages drawn from 1998-2015 by `scripts/draw_gold.py`, two a year, by
      page so the sample's boundaries are the document's and not the parser's,
      and rendered to images so no annotator ever sees extracted text. Page
      images are dropped by the parser's own `page_is_scanned`, page by page
      and not sitting by sitting.
- [x] Each read twice by annotators who never saw each other. The two readings
      agree on all 195 turn starts and all 36 pages
      (`scripts/check_gold_pages.py`). Turn recall holds: 318 of 320, F1 0.997,
      identical under either reading. The pre-2016 sample goes from 8 pages and
      50 turns to 44 pages and 195.
- [x] **"— El texto es el siguiente:" is sometimes an event and sometimes part
      of the chair's words.** The page prints it on its own indented italic
      line before an inserted document; the parser folds it into the end of the
      preceding speech turn. Corpus-wide it is an `event` 3,503 times and glued
      to a speech turn 4,162 times, plus 359 mid-turn, across 242 sittings.
      Both annotators independently called it an event on 2003-05-28 p28, and
      the printed page agrees with them. **Before changing anything, check the
      LAYOUT of the 4,162, not the text**: the corpus convention is that
      typography decides, so a note genuinely printed inside the paragraph is
      correctly folded and only the ones set on their own line are wrong. A
      keyword count cannot tell those apart — that is the same mistake the
      residue figure makes. Touching this is a parser change and a version
      bump.
      Closed in parser 0.5.0 (Phase 40, Q1): the opening dash is read where
      the file stores it, at the end of the run above, so the italic line
      after it is classified as the note it is.
- [x] (Q1 and Q2 done, Phase 40; Q3 still open) **Measured by layout, September 2026. The three event questions below
      are one decision, and it is not a judgement call.** All 184 PDFs that
      print "— El texto es el siguiente:" were scanned by printed line,
      indent and font, nine pages were read as images, and the two known
      failure modes of the line test (two-column OCR, and the sitting whose em
      dash extracts as "C") were found and corrected that way.
      **Q1.** The phrase appears 8,026 times in 242 sittings. Of the 4,165
      folded into a speech turn, **4,164 are printed on their own line**. The
      decisive measure is not the line but the indent: the folded ones sit 123
      points right of the body margin and the ones already called events sit
      at 122 — same indent, same italic face, same furniture, opposite
      treatment. Only four occurrences corpus-wide are genuinely printed
      inside a paragraph. The cause is not the phrase: the note's opening em
      dash is stored at the end of the roman run above it, so the italic block
      starts at "El" and the dash test in `classify_blocks` fails. In 4,500 of
      4,509 the character before the phrase IS that dash. So key any fix on
      the dash, not on the words — tried on 20 sittings of 2003-2006 that rule
      fires 201 times, 182 on this phrase and **19 on other notes lost the
      same way** ("Se llama para formar quórum.", "Así se hace."), and leaves
      every dashless italic run alone ("default", "ad referéndum", "shock").
      Cost: ~4,500 new event rows, ~27,000 words leave attributed speech
      (0.10%), turn counts and the 0.997 turn F1 untouched because `turn_id`
      advances only on a printed label. `parse_html.py` needs nothing.
      **Q2.** 60,905 event rows hold 68,211 printed note lines; 6,447 rows
      hold more than one and hide 7,306 lines. It is purely a PDF artefact —
      the HTML half is 26,179 rows to 26,179 lines, exactly one to one.
      **Verified here: the pair "La votación resulta afirmativa." / "En
      particular es igualmente afirmativa." is welded into one row 4,713 times
      in the PDF era and zero times in the HTML era.** The corpus contradicts
      itself, so this is not a free choice between two conventions. It also
      mis-files subtypes: 1,527 merged rows swallow a line of a different
      subtype, including 429 pauses filed under `vote` and 295 timestamps that
      disappear.
      **Event recall under each unit**, identical under either reading: as
      shipped 0.705, by printed line 0.905, by note 0.883. Do not decide on
      those numbers — 0.905 against 0.883 decides nothing. Decide on the fact
      that the HTML half already uses the printed line 26,179 times out of
      26,179. **And the cleanest result: under the printed-line unit all nine
      remaining misses are Q1. Fix Q1 and Q2 together and the gold set reads
      95 of 95, recall 1.000.** All thirteen false positives are Q3.
      **Q3 is a different kind of problem: the two halves already answer it,
      and they answer it oppositely.** 7,998 notes sit inside attributed
      speech, 10,772 words, 0.042% of the 25.7 million — but 7,865 of them are
      HTML and only 133 are PDF. The PDF parser makes a paragraph-closing note
      an event because the italic run breaks the block; the HTML parser folds
      it into the speech because the paragraph is the block. The dictionary's
      rule is implemented in one half and contradicted in the other, and the
      dictionary blames the chamber for what is the parser's doing. So the
      question is not "what should the third position be" but "why do the two
      formats disagree", and either answer costs a parser change. Lifting the
      note out in the HTML era is the smaller one, matches what the gold
      annotators read off the page, takes event precision from 0.869 to about
      1.000, and removes the wart where 31.6% of the secretary's turns are a
      speech whose entire content is the word "Lee".
      Nothing here is done. All three are parser changes and version bumps,
      and Q3 needs the convention settled before any code moves.

- [x] (done, Phase 40 — the unit is the printed line) The parser emits one `event` row where the page prints two note lines
      ("— La votación resulta afirmativa." / "— En particular es igualmente
      afirmativa."). No text is lost and no speech is affected, but event
      counts are not comparable with a reader's, and it is most of the gap
      between event recall 0.705 and the 0.935 the old 36 pages showed. Decide
      whether the unit is the printed line or the note, and say so in the data
      dictionary either way.
- [x] Annotators flagged printing defects worth their own scan: the ordinal
      sign printed as a capital E, a page number set in Greek glyphs, a
      missing Orden del Día number, an uncleared yellow highlight. **All four
      are scanned. None of them damages the corpus.**
      The ordinal and the Greek page number are settled above. The other two:
      **The missing Orden del Día number** is real and is the ONLY occurrence
      in all 605 PDFs. The annotator had the number wrong, which the corpus
      settles: chapter 34 is "Orden del Día N° 23", chapter 35 is
      "Orden del Día N°" and nothing, chapter 36 is "N° 25". **The missing one
      is 24**, and chapter 35's own body cites "Orden del Día Nº 24" twice —
      the 25 the annotator named is the next section, correctly numbered.
      Harmless today: the section's sequence number 35 is intact and delimits
      its blocks, `chapter_title` is documented as free text, and nothing in
      the repo parses a number back out of it. A reader matching this section
      to its committee report would have to take the number from the body one
      line down.
      Everything else the raw-text scan turned up was a false positive,
      each confirmed by rendering: 2001-era two-column pages where
      `extract_text()` interleaves the columns, alternate spellings that do
      carry a number ("No. 732", "Nro. 108", "Número 148/12"), and headings
      whose number is simply printed on the next page.
      **The yellow highlight** is a drawn rectangle, not a PDF annotation —
      pdfplumber exposes no Highlight objects in these files. Four sittings
      carry one: 2008-11-25 p3 and 2009-03-01 p3 both behind the same roster
      line "*RIVAS, Jorge – no incorporado", and 2022-10-27 p56 and
      2022-06-30 p86 behind a senator's speech. A fifth candidate,
      2022-03-17 p186, renders with no visible yellow at all — the rect sits
      behind an opaque bar chart — and was excluded. Cosmetic everywhere:
      `parse.py` reads characters and never `page.rects` or colour, the two
      roster pages are cut as front matter and never reach the blocks, and
      the two speech pages parse with their text intact.
- [x] The ordinal-as-E is already repaired and was reported here as a finding
      by mistake: `parse.py` maps ("WPMathA", "E") to the degree sign and
      documents its 3,229 occurrences, so the corpus reads "artículo 5°". The
      residue is 26 rows carrying 36 marks (some rows hold two, "incisos 1E y
      3E"), and it is concentrated in three sittings rather than scattered:
      1999-05-05_r15 has 15 rows, 1998-05-06_r13 has 9, 2001-03-23_r12 has 2.
      Recounted row by row against the corpus, so the 26 is a count and not
      an estimate; two regex hits are excluded as genuine text, an
      engineering group code "G2E" and a YouTube id.
      Of the 11 HTML rows only 9 carry a font signal — the broken E is an
      isolated `Courier New` run glued to a digit, against a body with no font
      wrapper. The 2 rows in 2001-03-23_r12 have none: "artículo 1E de la ley
      24.452" sits in the same `Arial` run as a correctly drawn "artículo 8°"
      a few words earlier in that paragraph. So the font machinery reaches 9
      of 26; the other 17 are as unrecoverable as the PDF cases and should be
      left alone, which is this project's existing stance on a character the
      source never drew unambiguously.
- [x] **The audit's apparatus check is keyed on a string a symbol font
      defeats.** It matches the literal `P[áa]g\.\s*\d+`
      (`scripts/audit_parse.py:81`). Scanning all 605 PDFs by FONT instead of
      by text found **628 pages in 19 sittings whose running header is set in a
      symbol face**, where the letters extract into the private use area at
      U+F000 + the ASCII code and that pattern can match nothing. None of the
      628 leaked into the corpus — but the check did not establish that; the
      repeated-header rule did, and it never looks at the text. The check
      passes for a reason other than the one it states, which is the failure
      mode this project has already written down. Re-key it on position and
      repetition across pages. The 19 sittings run 1998 to 2022 and are not a
      handful of stray pages: 2008-10-01 has 112 such pages, 2004-08-11 has 85,
      2008-08-06 has 76, 1998-04-01 has 65.
      Closed in `scripts/audit_parse.py`, section "RUNNING HEADERS": it scans
      the top strip by position and requires repetition across the document.
- [x] `86°°` — a doubled ordinal sign in 12 rows across 5 sittings
      (2003-12-17_r41, 2004-10-20_r30, 2005-06-01_r15, 2006-11-01_r26,
      2007-04-11_r04). Not a repair artifact: the PDF holds two consecutive
      U+F0B0 Symbol glyphs at x0=223.25 and x0=228.05, 4.8pt apart, so two
      glyphs printed side by side, and a rendered crop confirms the page reads
      "el 86°° aniversario del grito de Córdoba". The typesetter keyed it
      twice and the parser preserves it, which is correct — the corpus keeps
      the edition's errors the way it keeps a misspelled surname.
- [x] (done, Phase 40) **THE HEADER RULE DELETES REAL SPEECH. Verified in the shipped corpus.**
      Page 31 of 2003-07-23_r15 prints 2,119 characters and the corpus holds
      1,246 — **41% of the page is gone, and it is the chair speaking**:
      "Sr. Presidente (Gioja). — En consideración.", "— En consecuencia, pasa
      al Archivo.", "— Queda aprobada la declaración.", three Orden del Día
      headings and the text of an Auditoría General report. 9,254 characters
      in that sitting (`header_chars_removed` in parse_stats).
      The mechanism: that document has NO running header on any page, but the
      detector works by repetition rather than by words, so ordinary
      procedural phrasing recurring five or more times at a matching height
      is taken for a header and removed. The rule that survives a symbol font
      and a Greek page number (see above) fails the opposite way here.
      **Scope, stated honestly.** Two sittings confirmed: this one, losing
      speech, and 2004-10-20_r30, where six pages of 103 lose
      "— El texto es el siguiente:" as if it were a header. Of the seven
      all-Helvetica 2003 sittings only this one removes anything at all — the
      other six are at zero, so it is not a property of that cluster but of
      sittings where no header AND repeating pagination coincide. A signature
      of nonzero removal with a header found on under 80% of pages, 8 pages or
      more, gives **27 candidates**, unverified; one checked turned out to be
      a legitimate second banner, so the list is candidates and not defects.
      Corpus-wide 4,216,547 characters are removed as header across 573
      sittings, median 5,074, and the overwhelming bulk of that is correct.
      **The opposite failure, same rule.** It needs a line repeated five times
      before it will call anything a header, so a sitting under five pages can
      never have one detected, real or not. 23 such sittings, mostly
      EN MINORÍA quorum failures. Three ship the header as a row —
      1998-06-17_r25, 1998-07-22_r30, 1998-12-08_r69, the last carrying
      "8 de diciembre de 1998 Versión provisional - sesión ordinaria" on page
      4. All three landed as `furniture`, so no turn was corrupted; they are a
      leak, not damage.
      Both modes are confirmed against rendered pages and the shipped parquet,
      not inferred. Fixing this is a parser change and a version bump, and the
      27 candidates want a pass before anyone decides what the fix is.
- [x] Two sittings are said to be set in a sans-serif face with no header,
      footer or page number (1998-07-23 p7, 2003-07-23 p74). Scanned all 605
      PDFs, 48,815 pages, reusing the parser's own `extract_all_characters`,
      `strip_page_headers` and `strip_page_footers` rather than a
      reimplementation. **One of the two reports was wrong**: 1998-07-23 p7
      (Mandela addressing the joint session) is sans-serif, but it does carry
      a running header and page number — an italic banner over a rule, on
      every content page — which the repeat detector catches correctly. Only
      2003-07-23 p74 is genuinely bare. The properties do not travel together
      and are counted apart: sans-serif body 14,404 pages in 306 sittings
      (31%, almost all the 2020-2026 Arial format and the WordPerfect-era
      Helvetica substitution); no header found 2,763 pages (5.7%), but 484 of
      the 515 sittings touched have exactly one such page, which is the cover
      and is by design; no page number 2,942 (6.0%); no footer 21,400 (44%),
      expected because only the 2024 format ever had one. All three absent on
      a sans-serif page: 439 pages in 64 sittings, of which 38 are a lone
      cover. The real multi-page shape is 26 sittings, and the mid-document
      stretches in 2005-2009 are appended annexes, correctly tagged furniture.
      Scan at `scratchpad/furniture_scan.csv`.
- [x] (superseded) Two sittings are set in a sans-serif face with no header, footer or page
      number at all (1998-07-23 p7, 2003-07-23 p74), which looks typeset from a
      different source. Worth knowing how many sittings are like that before
      trusting any rule that keys on the running header.
- [x] `check_gold_pages.py` and `check_gold_html.py` report 100% agreement
      between two readings, but both readings are the same model working from
      the same brief. That is weaker evidence than two people, and the write-up
      should say so rather than quoting the number bare. It also probably
      explains the entry below.
      CLOSED by 430f6d1: README and the data dictionary now say both readings
      are one model on one brief, and that agreement between them checks the
      brief, not the reading.

- [x] The HTML gold set's inter-annotator figure does not reproduce. a94c38a
      records 99.2% of turn starts and 22 of the 24 stretches identical;
      `check_gold_html.py` on the annotations committed in that same commit
      prints 195 of 195 and 24 of 24, and neither the annotations nor the
      checker have been touched since. Either the message was written from a
      run before the set was finalised, or the two readings were reconciled
      before committing — which would mean the set is not two independent
      readings and the claim has to be weakened. The docs now quote only what
      the committed files reproduce. Settle which it was before the next
      release quotes either number.
      SETTLED (23 September 2026): the readings were revised before
      committing. The record of the session that built the set holds the
      first run of check_gold_html.py, at 21:46 on 19 September: every stretch
      identical except 1998-08-05_r31 (1 turn start shared of 1 and 2) and
      2000-06-07_r22 (20 shared of 22 and 20) — the 99.2% and 22 of 24 the
      commit quotes. The annotators who had read the re-set label the other
      way were then told to re-emit, the brief's event rule was corrected, and
      the same checker printed 195 of 195 right after the push. So the commit
      message quotes the independent state and the files hold the reconciled
      one. 430f6d1 already words the docs that way; no number changes.
- [x] `¿` is stored as `)` where the export switched font: 147 of them, plus
      16 `¡` stored as `(`. Found by a reader who took it for encoding
      damage. Needs a full scan before any repair: the rule has to tell these
      from a real parenthesis, and only a corpus-wide count can show it does.
      CLOSED in 0.5.8-html and 0.5.3. The raw scan verified all 147/16 HTML
      font runs and 9/4 PDF glyphs; the output changes exactly 156 `)` to `¿`
      and 20 `(` to `¡`, with 180,463,050 characters, 150,591,419 non-space
      characters and all 439,735 row types unchanged. Four question-opening
      `)` and zero exclamation-opening `(` remain: all four are literal
      ordinary-font source typos with no recoverable font signal. Both gold
      evaluations remain at P=R=F1=1.000 for turns and P=R=1.000 for events.


- [x] Group the chamber's own `session_type` labels before counting: `EN
      MINORÍA` and `ESPECIAL EN MINORÍA` name the same thing. Done as a
      `session_kind` column beside the raw label, never in place of it, from a
      mapping in `reference/senado/session_type_map.csv` that carries the
      reasoning for each of the 13 labels and flags the four folded in by
      judgment rather than identity. Verified over all 817 files: every row
      has the column and no label went unmapped. Parsers 0.4.41 and
      0.5.6-html.
- [x] `session_kind` holds two dimensions in one column, and something should
      eventually separate them. `ordinaria` / `extraordinaria` / `especial`
      say how a sitting was called and in what period; `en_minoria` and
      `sin_quorum` say whether it had a quorum. A sitting held in minority is
      also ordinary or special, and one column cannot say both — so counting
      `ordinaria` today silently excludes the 34 sittings that were ordinary
      AND short of quorum. The mapping's own notes already say this ("not a
      convocation type: the chamber's own label for a sitting that failed to
      reach quorum") and then group it in the same column anyway. The
      dictionary warns about it. Two columns would be the honest shape, but
      the chamber gives one label per sitting, so the second would have to be
      inferred, and that needs evidence rather than a default.
      DONE (23 September 2026, parsers 0.5.4 and 0.5.9-html): two new
      columns beside it, `convened_as` and `quorum_failed`; `session_kind`
      unchanged. `quorum_failed` is the label alone (35 sittings — the 34
      above was a miscount). `convened_as` for those 35 comes from the
      sitting itself, quoted in reference/senado/session_convened_as.csv:
      6 by label, 1 by cover, 3 by the words spoken; 25 stay empty. Covers
      were read for all 35 and say only "Sesión en minoría". The running
      header "sesión ordinaria" is a template and is contradicted by the
      text on 8 December 1998, so it is not used.

## Phase 40 — four fixes, and the two they exposed (September 2026 — parsers 0.5.0 and 0.5.7-html)

- The sitting that held the wrong document is fixed. The body size is no
  longer the most frequent size: every candidate is tried and the one whose
  opening line comes earliest in the file wins. 2014-09-03_r13 goes from
  118,986 words to 251,293 and opens on 3 September, not 19 August. Of 605
  PDFs only 4 change their cut point and the other three all gain.

- A file that prints its sitting twice now keeps the first copy. It fires on
  exactly one file of 605. The first version of this cut compared the opening
  line alone, and where the opening is a speaker's label — which recurs in
  the same document — it cut the preparatory sitting of 29 November 2001 in
  half and took the swearing-in of senator Maqueda with it. It now asks for a
  genuine opening event at both ends and for a line of at least 40 characters.

- Exposed by that work: a sitting's body size can wobble by a fraction of a
  point. Sizes within 0.5 of it now count as body. Only 4 sittings hold more
  than 500 words there, and all 4 recover speech — 2001-11-21_r72 from 9,159
  to 17,164 attributed words. The tolerance is deliberately kept out of the
  front-matter cut, where it changed which size was chosen as the body at all.

- The header rule no longer deletes speech. A repeating line is confirmed as
  a running header only if it opens the page on at least 80% of its
  appearances. Position consistency, the first hypothesis, does not separate
  them: real headers drift up to 31 points, and the false ones in
  2003-07-23_r15 are perfectly consistent because the page is set solid. All
  three defects are repaired, including one found in the course of checking
  (2006-12-20_r32, an insertion caption). 30 sittings change, none removes
  more than before.

- Q1 and Q2 are answered, and the unit is the printed line. A block that
  reads like a sentence and follows a run ending on a dash is a note, because
  the dash is stored at the end of the run above; and a block is split
  wherever a sentence ends and a dash opens the next, which is how two notes
  in the same italic run arrive welded. Event rows go 60,905 to 74,186. On
  the gold set events reach P=0.877 R=0.979, and both remaining misses are on
  the one page annotated off an appended committee meeting.

- 97 PDF passages of floor speech had lost their speaker to a damaged label,
  not the 23 first reported — those were only the ones leaving a long orphan
  paragraph. A new repair pass takes 66 and widening the collective form
  takes 31. All 97 read against the page: no genuine section heading is
  swallowed. Nine are left as headings because the page gives no honorific to
  settle who speaks (Connor seven times, Avelín, Di Tullio). The HTML side
  gains 12 labels the same way.

- Found in passing and fixed: NOTE_TAIL_RE was bound twice at module level,
  so reattach_note_tails had been matching ordinal scraps against a pattern
  for parenthesis tails; and write_stats keeps a fixed column list that
  silently dropped any new counter, which is why the two new stats were
  computed and thrown away.

- [x] (done, 21 September 2026) **Gold page 295 of 2014-09-03_r13 was annotated on the wrong document.**
      It was drawn before the fix above, from the committee meeting of 19
      August that the file appends and the corpus no longer attributes to that
      sitting. It now accounts for all 12 missed turns and both missed events
      in the PDF gold set: excluding it, turns are 308 of 310 and events 93 of
      93. Leaving it in puts a ceiling of 0.963 on recall that no correct
      parser can pass, and hides any real regression underneath it. Proposed:
      draw and annotate a replacement page from the same sitting, and keep
      this one out of the scored set with a note saying why, rather than
      delete it. Done: both readings and the page image are in
      reference/gold/retired/ with the reason, and the replacement is page 72,
      drawn by the same seeded rule from the 214 eligible pages of the floor
      debate and read independently twice. Both readings agree exactly — no
      label, no note, no heading, one speech running through the page — and
      the corpus covers it with a single turn by senator Godoy spanning pages
      71 to 74. The set loses 10 annotated turns and gains a page that can
      only catch a false positive: the honest cost of the draw landing on a
      continuation page, and not a reason to draw again.

- [x] (done, 21 September 2026) The gold-score prose in README.md and DATA_DICTIONARY.md still quoted
      the older 125-turn figures (F1 = 0.996). It should be rewritten once the
      page above is settled, since that decision changes the numbers.

- **How often does a PDF insert a committee meeting behind the sitting?
  Once.** The question was asked because 2014-09-03_r13 was not supposed to
  be a one-off. Two scans failed first, in opposite directions, and neither
  number should be quoted: looking for the heading at the top of a page found
  64 files and missed 2014 itself, where the announcement sits in the body
  under the sitting's own running header; looking for the phrase anywhere on
  the page found 38, most of them a senator talking about a committee
  transcript mid-debate. In the largest of those, 2006-07-12_r16, the line is
  a senator saying she consulted it, and the chamber is still sitting on that
  page and every page after.

  What separates an insertion from a mention is that an insertion announces
  the meeting the way the record opens any sitting, with the hour and the
  date: "...a las 17 y 18 del martes 19 de agosto de 2014:". Asking for the
  announcement and a dated opening in the same sentence returns exactly one
  file of 605, the 2014 one, where the corpus now holds 0 speech rows behind
  page 224. All 37 the rule dropped were read: every one is a senator
  speaking about a transcript, not a document being reproduced.

  The rule only sees files that use this wording at all. The standing backstop
  for the rest is the opening-date check in the audit, which is what would
  have caught 2014 and today flags two sittings, both a year out because of a
  misprinted date rather than a wrong document.

- **The gold set contradicts itself about the note at the end of a sentence,
  and that is the real finding of the 0.877 event precision.** The parser was
  reading "(Aplausos.)" as an event wherever it appeared, including at the end
  of a speaker's own sentence — "…Dios y la Patria os lo demanden.
  (Aplausos.)", the fragment sitting at x=425 in the middle of the printed
  line. Measured against the page, 3,610 of the 5,370 bare parenthesised event
  rows sit inside a line rather than opening one. 0.5.1 reads them as part of
  the speech, which is the convention the annotation brief states as rule 4 in
  those words.

  Event precision goes 0.877 to 0.988 and recall 1.000 to 0.892. The ten
  newly missed events are all the same shape and all from the older
  single-reading pages (2020-03-01 p12 and p22, 2021-02-24 p56, 2022-06-30
  p101); every one was checked on the printed page and sits mid-line. The
  pages with two readings say the opposite: on 2005-11-29_r39 p5 both
  annotators wrote, separately, that none of the seven "(Aplausos.)" is an
  event, citing the convention.

  So the drop in recall measures the contradiction, not the parser. Done, 21
  September 2026: the four pages were re-read blind from their images, each
  by an annotator not shown the old file. All four agreed with the original
  on every turn, label and heading, and all four placed each of the ten notes
  inside a paragraph. The ten events were removed with the reason written into
  each file; the re-readings are kept in reference/gold/rereadings/. Gold
  events now read P=0.988 R=1.000 (83 of 83).

- [x] (done, 0.5.2) **The secretary's "(Lee:)" is filed as an event, against rule 3 of the
      brief.** "Sr. Secretario (Oyarzún).- (Lee:)" is the secretary taking
      the floor; the note in his own paragraph is his turn. 256 of the 259
      "(Lee...)" event rows in the PDFs carry the secretary's label that
      opened them. It is the last extra event in the gold set AND one of its
      two missed turns (2001-11-14_r71 p5), so fixing it moves both. It is
      older than 0.5.1 and a different mechanism:
      reassign_hyphens_to_italic_blocks moves the LABEL's terminating dash
      into the italic block, so the note opens with a dash and the leading-dash
      test makes it an event before any position test is reached. Fixing it
      means telling a label's terminator from a note's opening dash where the
      dash is moved, not in classify_blocks.
      Done otherwise than planned: the dash does not come from the pass that
      moves hyphens, because the holder "(Oyarzún).—" is set in roman and the
      terminator is an em dash. What decides it is whether a complete label is
      the last thing printed before the bracket; the note is then carried to
      identify_speakers flagged and handed to the label's turn. 266 notes move
      to the secretary's speech, the PDF half now files them as the HTML half
      does, and the gold reads 310 of 310 turns and 82 of 82 events. One more
      July-convention annotation (2003-08-20 p3, counting "(Lee:)" as both the
      turn's words and an event) was corrected after a blind re-reading. Five
      "(Lee:)" stay events on purpose: the italic run also carries the start
      of what was read ("(Lee:) “"), and splitting it risks the text.

- [x] (closed, 21 September 2026) Q3, the note that closes a speaker's
      paragraph, where the two halves of the corpus answered oppositely —
      7,865 of the 7,998 were HTML and 133 PDF.
      The convention was already settled, as rule 4 of the annotation brief:
      a note inside somebody's paragraph belongs to their speech. The HTML
      half followed it; the PDF half did not, and 0.5.1 brought it into line.
      Checked from the other side against the raw HTML, splitting on every
      block-level tag and not only <p>: the sources hold 2,064 applause,
      laughter and "manifestaciones" notes, the parsed corpus holds the same
      2,064, and only 2 are printed as a paragraph of their own — both parsed
      as events. 1,821 sit in speech, 233 inside longer notes that are their
      own italic paragraph ("-Puestos de pie los presentes… (Aplausos.)"),
      7 in inserted speeches, 3 in section titles. So the HTML parser is right,
      and the gap against the PDF half — 791 applause notes on their own row —
      is how the two eras were printed: the 1998-2003 WordPerfect exports
      almost never set applause as a paragraph of its own. Nothing to change.

## Phase 41 — the labels that led nowhere, and the rest of the list (23 September 2026 — parser 0.5.6)

- [x] **Printed labels that open a turn with no row: 43 → 19** (the "91" of
      0.4.37, re-measured on today's corpus as turn numbers that leave no row).
      Read one by one. 6 are the November 2001 scan. Most of the rest are the
      secretary's label followed by the document he reads, which the page
      sets as a heading or an inserted text — whether that document is his
      turn is the definitional question left open above, not a defect.
- [x] **A quoted hearing put one man's questions in another's mouth.** On 27
      November 2003 a senator quotes, in italics, Badeni questioning
      Magariños: "Sr. Magariños. — No." / "Sr. Badeni. — ¿Se le permitió…?".
      The question after each label was typed as an italic fragment with no
      turn, and glued onto the answer above it — 154 words of Badeni's under
      Magariños, 18 of the chair's, 11 of Falú's. Italics printed straight
      after a label now belong to that label: they open its speech when the
      speech goes on, and otherwise stand as its note, as every other line of
      that exchange does. Corpus-wide the same rule moves "(Lee:)" from the
      chair who asked for the reading to the secretary whose label it is
      printed under, and an italic "Okay" back to the presiding
      officer who said it. A first draft carried the label's own italic ". —"
      into the speech (". — Senadora Latorre: sírvase…"); it is punctuation
      and is now dropped, which also takes ". —" off the end of 17 notes and
      votes it used to be glued to.
- [x] **A note welded below a label's note no longer inherits the label.**
      "Sr. Secretario (Estrada). — (Lee:)" / "— El texto es el siguiente:"
      split into two rows, and both carried the secretary. Only the first is
      his. 
- [x] **The chair's closing parenthesis was left in the speech** — "Sra.
      Presidente (Villarruel" / ").- Sí, senador Mayans." — in 23 labels of
      2014-2025, and five labels kept a comma for their full stop ("Sr.
      Menem,"). Both repaired: 28 labels become the clean label of the same
      person, and the five comma labels, which resolved to nobody, now
      resolve (unmatched 114 → 109). An italic "(Estrada)" after "Sr.
      Secretario" is read into the label — only after an office, since after
      a senator an italic parenthesis is a stage note ("(de pie)"), which a
      first draft wrongly read as part of the name.
- [x] **Measured against 0.5.5**, by speaker, over every row that carries one:
      57 PDF sittings change; the only words that move between named people
      are the ones above, each read in the row diff; `speakers.parquet`
      changes no attribution and no caucus. Gold 310/310 and events 82/82;
      blind reads unchanged (6,529 hold, the same 2 CHANGED in the 2014
      sitting that held the wrong document); audit unchanged on every
      invariant, turns ending on a dash or comma 65 → 55.
- [x] **New audit check 6c: labels carrying a character no label should.** The
      blind read forgives a stray character in a label, so this reads them.
      4 remain, all printed that way: three HTML typos of 1998-1999 ("Sr.
      PRESIDENTE ((Ulloa)", "Sr. PRESIDENTE (Menem) (Menem)", "Sr. PRESIDENTE
      Menem)") and one PDF "Sr. Presidente)" of 2005.
- [x] **The dropped-text residue has no lost debate in it.** Every page of the
      90 low-coverage PDF sittings was checked against the output: each page
      before the sitting's close that is missing is a cover, an attendance
      roll or a contents page, and every body page that looks partly kept was
      read line by line — what is "missing" is the lines that open with a
      speaker's label, which the corpus keeps in `speaker_raw` and not in the
      text, and the running headers.
- [x] **The review sheet quotes what is printed just before the passage**, so
      a three-word turn is found by reading, not by counting occurrences.

## Phase 42 — cutting 0.5.7 (24 September 2026; first cut as 0.5.6, never published)

- [x] **The whole checklist re-run on the build that ships**: `parse.py
      --force` (605 PDFs, the 1997 tribunal the one failure),
      `parse_html.py --force` (213, none), the caucus chain, gold 310/310 and
      82/82, HTML gold 195/195 on both readings, 108/108 annotations against
      their pages, blind reads 6,529 hold and 0 changed, the notebook
      re-executed and its four figures regenerated.
- [x] **The two blind-read records that still failed were the check, not the
      corpus.** Both were read on pages of the committee meeting appended to
      2014-09-03_r13, which the parser now files as furniture. The check found
      no speech with the words on their page and went on to search the whole
      sitting, where a single 24-character window of one of them sits in
      another senator's speech — and reported a reattribution. It now asks
      first whether something else on the SAME page holds the whole quote, and
      calls that "moved out of speech". Measured against the previous run over
      all 6,819 records: those two change and nothing else. It cannot hide a
      real reattribution, because a reattributed passage is still speech and is
      found on its page before this branch is reached.
- [x] **A label that lost its opening parenthesis was credited to the wrong
      man.** "Sr. PRESIDENTE Menem)" (20 May 1998) was cleaned to "Sr.
      PRESIDENTE Menem", read as the office, and given to Ruckauf, who held it;
      Menem held the chair. `clean_label` now puts a name after the office
      back inside the parenthesis it lost, collapses "((" and a holder printed
      twice ("(Menem) (Menem)"), and strips a closing parenthesis only when
      nothing precedes it but the office. Over all 23,961 labels it changes
      exactly four: that one, now Menem; "(Menem) (Menem)" of 23 September
      1998 and "Presidente  Menem)" of the November 2001 scan, both unmatched
      and now Menem; and "((Ulloa)", already right. Found by reading the four
      odd labels the audit lists before writing that they resolve correctly.
- [x] **The bundle carries what the pipeline has grown**: `parse_html.py`,
      the caucus scripts, the HTML gold set and the archived senators' pages.
      `docs/DEPOSIT_README.md` rewritten for 0.5.6 — it describes a release,
      so it changes when one is cut. `docs/RELEASE.md`'s table of what ships
      had described the 0.4.37 bundle before it was cut down to the dataset;
      it now matches `make_release.py`.
- [x] **The ticket-versus-caucus split in the data dictionary was the PDF
      era's.** Recomputed over the whole corpus with the same definition
      (the 0.4.37 figure reproduces on the PDF years alone, 14.85 million
      words, 0.31%): 20.5 million words, 19.6% written the same, 63.4% the
      same camp, 17.0% different camps, 0.38% floor-crossing.

- [x] **The audit's split-label check failed on a typo the parser had
      repaired.** "Sr. Presidented (Maqueda)" (1 August 2002) is attributed
      to Maqueda, but the check compared the printed label with the parsed one
      letter for letter. It now reads a misspelt office word on both sides the
      way speaker resolution does (`fix_role_typos`) — both, because the
      parser repairs some ("Presidented") and keeps others as printed
      ("Secreetario", "Preisdente"), and a first version that repaired only the
      printed side broke those two. 14,443 of 14,443 attributed; the audit
      goes from 15 things to look at to 14, every one printed that way. The
      repair only accepts a word of eight letters or more very close to an
      office name, so it cannot turn one office into another or touch a name.
- [x] **Two annotation briefs carried a personal path** ("Repo:
      /Users/…"), and both ship. Now "relative to the repository root".
- [x] **Bundle built and verified**: 1,469 files, 129 MB, 96 MB packed,
      sha256 25909a27…; clean extraction, every checksum passes, no personal
      path, every script imports, the README's loading example gives 439,692
      rows and 245,725 speech passages over 817 sittings.
      Rebuilt as 0.5.7 after the review round: same size, sha256 345297c8…;
      the same checks on a clean extraction give 439,686 rows and 245,722
      speech passages over 817 sittings. The full audit is unchanged: 14
      things to look at, all printed that way, no page dateline in speech.
- [x] **A review round by five independent agents found four more things,
      each checked against the page**, so the cut became 0.5.7 (PDF parser
      0.5.7, HTML 0.5.10-html). 38 speech rows of 2002-04-11_r05 carried
      "Pág.. N", a dateline printed with two stops; the pattern now takes one
      or more, and the audit looks for it. Six rows with no visible text are
      dropped: three HTML speech rows of 1999-06-16_r25 and three PDF
      whitespace rows. `download.py --from-manifest` fetches each source
      the manifest lists and checks its hash, tested on two real files.
      `LICENSE-DATA`, the data dictionary and the rebuild section of the
      deposit README corrected where the reviewers found them wrong or thin.
      Two claims discarded after checking: a "Presidenta stored as
      Presidente" (the page prints "Sra. Presidente") and "pages off by two",
      which was the dictionary's definition of `pages`, not the data.
      The full re-parse against the previous build: those 44 rows changed and
      nothing else; 65 rows still hold "Pág. N", all bibliographic citations
      or contents entries, none in speech. Gold, HTML gold, annotations
      and blind reads re-run: unchanged.
- [x] **Review again on the latest Opus.** Review agents run on the latest
      Opus by default, not Sonnet; the Sonnet round's findings stand. Done:
      Phase 43, which is why 0.5.7 was not published either.

## Phase 43 — what the Opus review of 0.5.7 found, and 0.5.8 (24–25 September 2026)

Three reviewers on the latest Opus read the built 0.5.7 bundle: who said
what against the pages, every figure in the shipped documents, and the bundle
as a stranger gets it. Each finding was checked on the page and scoped by a
full-corpus scan before it was changed; every parser change was measured by
re-parsing all 818 files and classifying every changed stretch against
0.5.7 by the rule that explains it (716 appendix, 684 document note, 65
small type, 34 HTML, 3 placeholders; the 17 left over were document-note
lists further than three rows from their note, and seven director
signatures, all read by eye). PDF parser 0.5.8, HTML 0.5.11-html.

- [x] **Debate set a point off the body went out as furniture** (2006–2014):
      83 labels in 13 sittings, the words after them to the previous speaker.
      `restore_small_set_debate` reads a run of blocks half a point to a point
      off the body as body when it holds a bold label, inside the debate
      (before the last closing formula, strict or loose, or the last
      body-size label), and never in the scans. 14 sittings, 328 blocks;
      2011-03-30 p. 9 read on the page. The no-quorum sitting of 10 November
      2010, whose body size is misread as 11, gets its minority speeches back.
      Also: the director's signature is furniture wherever it stands.
- [x] **HTML labels the typist broke** (`broken_label`,
      `split_embedded_labels`, centred labels): 34 changed stretches, every one
      read in the source. Genoud's 1,415 words of 11 August 1999 are his.
      "Sr. Varios señores senadores" is one label, not split at its own stop.
- [x] **Foreign heads of state** out of scope: any republic but Argentina.
      Four labels change, no other.
- [x] **Everything after the director's sign-off under the last close is
      appendix**: 12 files, 326 speech rows, 56,897 words — committee
      meetings bound into 2005-04-06, 2005-05-18 (176 turns) and 2005-08-10,
      the 2003 tribunal's annex, and the handed-in speeches of 2005–2007.
- [x] **Text after "— El texto es el siguiente:" and "…cuyos textos se
      incluyen en el Apéndice, son los siguientes:" is nobody's**: the turn
      ends at the note, as the HTML half always had it. 2001–2019, about
      300,000 words out of speech. Where the chair's next words follow with
      no label reprinted (2008-11-20) they are now `other`, where they had
      been the secretary's.
- [x] **Senators chairing since 2020 keep their senator id and caucus**:
      213 labels, 9,256 passages, nine senators; nothing else changes.
- [x] Typesetter placeholders ("AQUI INCLUIR…", "(INCORPORAR DECRETO)") are
      furniture; "Sra Colombo.-" glued to a heading (2004-09-15) is cut off
      it; "Sr.0 Presidente (Losada)" reads as Losada.
- [x] The blind-read check: a passage printed twice on its page, once in a
      turn and once in a list now out of speech, is "printed under more than
      one name", not a reattribution. One record changes. 6,518 hold, none
      resolves to anyone else.
- [x] Checks on the build: gold 310/310 and 82/82, HTML gold 195/195 on
      both readings, 108/108 annotations, 24/24 stretches agree; audit: 0
      page apparatus in speech outside the scans, 0 second labels, 0 of 817
      longer than their source, 14,443 of 14,443 HTML split labels, 14
      things to look at, all printed that way. The seven official-count
      differences are unchanged. Three declared-caucus entries re-pointed
      to their rows' new positions.
- [x] Scripts: the twelve with no options answer `--help` instead of
      running; `extract_authorities`, `extract_chair_caucus`,
      `make_manifest` and the audit's source checks stop on a partial set of
      sources; the caucus extractors take each sitting's URL from the
      manifest, so `--from-manifest` downloads rebuild them exactly;
      `extract_authorities` sorts deterministically; the archive records no
      owner; notebook dependencies are a group of their own.
- [x] Licence: CC BY 4.0 covers what the project adds; the text column, the
      page images, the HTML fragments, the Senate's roster and the archived
      pages are the Senate's (Ley 11.723 art. 27 noted). The list of sitting
      senators with their contact details no longer ships. The owner agreed
      (25 September 2026), and that the repository goes public with the data.
- [x] The documents said the gold sets were annotated "by hand"; they say
      now that a language model annotated them and no person checked them.
- [x] **A body-size label with its words set off the body** (4 September
      2013, 21 December 2016): a run with a word in it, led by a label right
      above it, is restored too; split words are rejoined first, so a letter
      set in another size no longer comes out as "s ilencio". Seven sittings
      change, each read. Found by listing the turns that leave no row: 21
      became 19.
- [x] Figures in the documents recomputed for 0.5.8 by one Opus agent
      (`.agent/scratch/doc_figures/figures.py`, re-runnable), each definition
      first checked to reproduce the 0.5.7 figure on the 0.5.7 bundle; its
      changes read and the headline figures recomputed independently. The
      unresolved labels and the turns with no row were re-described from the
      rows themselves. Gold, blind reads and audit re-run on the final build
      (audit: 13 things to look at, all printed that way).
- [x] Bundle 0.5.8 built and verified on a clean extraction: 1,468 files,
      96 MB packed, sha256 3342de8c…; checksums, no personal path, every
      script answers `--help`, the loading example gives 440,447 rows and
      244,805 speech passages over 817 sittings; the archive records no owner.
- [x] **Second Opus round on 0.5.8** (three reviewers: attribution, figures,
      the bundle as a stranger). Each finding checked on the page or in the
      markup, each rule measured by a full re-parse against the previous
      build, every changed stretch classified and the unexplained ones read:
  - Notes introducing a document in any wording ("…son los siguientes:",
    "…es el siguiente:", with a colon, a full stop or a bracket after, or
    welded to the document's first words) end the turn: 88 rows, ~68,000
    words of 2019–2025 lists were the chair's or the secretary's.
  - HTML italic paragraphs are notes only when they read as notes (a dash
    or bracket, the chamber's stage language, a vote or applause); quoted
    passages and lists of titles stay in the speaker's turn (Gómez Diez
    2002, Avelín 1998, Yoma 1998, Bioy Casares's and Luna's homages).
  - HTML labels the typist misspelt or left without the honorific ("S r.",
    "S.", "PRESIDENTE (Cafiero).-", "DEL PIERO.-", an unclosed "(Maqueda"),
    a holder in roman after a bold office, a label with no terminator but
    a holder in parentheses, a turn whose paragraph carries a back-link;
    resolution reads a missing honorific as "Sr.". 11 new labels, all to
    the right person.
  - PDF office labels set in roman ("Sr. Secretario (Estrada) Se
    registraron…", "Sra. Presidente.- Aprobados.").
  - A note whose italic run overran the next word's first letter no longer
    takes the rest of the speech with it (Fuentes 2018, 1,559 words; four
    presidents' addresses); a one-letter word keeps its space ("y el que"),
    half a word does not ("si", "es").
  - Bracketed notes printed mid-sentence rejoin the speech (78 in 46
    sittings, mostly assemblies); label punctuation stripped from 158 turn
    starts; roman notes under a note, a note's comma-ended second line and
    the director's name over the signature filed as what they are; debate
    set off the body that continues an open sentence restored, a word the
    size change split rejoined.
  - Misspelt chair labels since 2020 resolve to the senator: the senator is
    found by the office-holder's full name, whole words, chair only (four
    labels of Ledesma Abdala; a first attempt matched "Arce" inside
    "Marcelo" and was caught by the comparison).
  - Documents: annotation independence per batch, the person check as a
    plausibility check, provisional records, the manifest's columns, the
    audit as a list, which gold pages ship an image, figures recomputed,
    the Results section from a re-run of the notebook. Bundle: only the
    archived captures a table cites (the 1997 senators' pages with personal
    details stay out), the caucus-periods table rebuilt to 2026, an offline
    rebuild no longer restamps the manifest.
  - Checks on the build: gold 310/310 and 82/82, HTML 195/195, 108/108,
    blind reads none reattributed, audit 13 things to look at.
- [x] Figures recomputed on the final build (the Opus figures agent again,
      headline figures recomputed independently); bundle rebuilt and verified
      on a clean extraction: 1,250 files, 96 MB packed, sha256 75564da1…;
      checksums, no personal path, the loading example gives 440,347 rows and
      244,662 speech passages, an offline caucus rebuild leaves every
      checksum intact.
- [x] A last Opus review of the final bundle (three agents: attribution,
      figures, bundle). The figures and bundle findings were fixed in
      0254168. Of the eleven attribution findings, the four systematic ones
      are fixed, each measured by a full reparse against the build before:
  - HTML: the speaker goes on after a note, as on the PDF side, unless the
    note introduces a text or says one is read out (Cafiero 2000, 789 words);
    a roman sentence and its italic note in one paragraph are split
    (Rodríguez Saá's default announcement, 2001, and the nine paragraphs
    after it); a speaker resumes in body type after an insertion set small
    (Melgarejo 1999); the director's name over the signature is page matter
    (90 sittings); a note welded to the work plan it introduces is cut
    from it (2001).
  - PDF and HTML: about 120 notes printed in roman inside a speech are
    notes of their own; a note that announces a list ends the turn there,
    including one split onto two page-matter rows (15 August 2012) or set in
    roman mid-row (16 November 2022); the chair taking the floor back after
    such a list is the chair again (20 April 2005). Scans are left alone.
  - 48 italic words under a label are speech, not labelled notes (37 of
    them Michetti's "Okay"); 40 labelled notes remain, 29 of them "(Lee:)".
  - Left as known issues: a bold word mid-paragraph read as a heading
    (Perceval 2006, six such cases spoken), italic titles in a sentence filed
    as notes (about 22), a "Dr." label (2003), the chair after a list where
    the note came under the secretary (2008-11-20), tiny page-matter rows
    inside turns.
  - Build: 440,443 rows, 244,684 speech passages, 6,392 unattributed
    (1.45%); speakers table unchanged; gold 310/310 and 82/82, HTML 195/195,
    108/108, blind reads none reattributed, audit 13 things to look at.
    Bundle rebuilt and verified on a clean extraction: 1,250 files, 95 MB
    packed, sha256 6815859c…; checksums, no personal path, loading example.
- [x] Version DOI reserved on Zenodo, 10.5281/zenodo.22959187, and put in
      the five documents that carry the citation.
- [x] An independent review before the deposit (two Opus agents: the bundle
      as a stranger gets it, and 80 passages read against the sources, none
      wrong). Fixed: two earlier debates reprinted as insertions and counted
      as that day's speech (2000-02-23, 2001-08-08; 61 passages, listed in
      `reference/senado/inserted_debates.csv`); two chair replies welded into
      the turn before in the HTML (1998-05-13, 2003-06-11), and the audit's
      glued-label check, which did not know the HTML's double hyphen; edge
      spaces stripped from every text; "369 of the 665" cover pages is 397;
      senators-elect, inserted matter in notes and page matter, and "most of
      1998-2003" documented. Build: 440,445 rows, 244,625 speech passages,
      gold 310/310, 82/82, HTML 195/195; blind reads none reattributed (304
      cannot be re-asked); audit 12 to
      look at. A third Opus agent checking those fixes found a third reprint
      (Menem's speech of 25 October 2000 reprinted on 15 November) and the
      notes inside reprints still counted as that day's events; both fixed,
      and the chair's label of 11 June 2003 kept as printed. Build: 440,445
      rows, 244,624 speech passages, 69,290 notes, 6,461 unattributed
      (1.47%); gold unchanged; blind reads none reattributed; audit 13 to look
      at. Bundle: 1,251 files, 95 MB, sha256 2562fe3e….
- [ ] **For the owner**: make the GitHub repository public (the bundle links
      to it and cites it as evidence), then tag v0.5.8, upload the bundle and
      its .sha256 to the Zenodo draft, and publish.

## Explicitly not building

Packaging/PyPI, docs site, utils wrappers, test-file mirror, separate
analysis modules before a notebook needs them. Diputados waits until the
Senate corpus is complete back to 2000.
