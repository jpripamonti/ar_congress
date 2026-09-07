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
- [ ] **The year 2000 is exhausted.** Its 96 locatable turns have all been read
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
- [ ] **2002 is nearly exhausted too.** It yielded 12 turns of the forty asked
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
- [ ] **The blind read cannot see this class of fault.** That same case 850 was
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
- [ ] **Decide the licence for the derived tables** — CC BY 4.0 is what the
      release document proposes; the code stays MIT.
- [ ] **Mint a DOI.** Zenodo is the fitting home: it versions, it keeps one
      identifier that always points at the latest, and it is where datasets like
      this are cited from. Publishing is the author's call, not the pipeline's.

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
- [ ] **What is left, measured.** Four cut titles in three sittings, each with
      its own cause and none of them a glyph: a title running across a page
      break (13 Apr 2011), a double space inside a heading (2 Nov 2011), and an
      "N" in bold whose "º" is not (3 Sep 2020, twice). Seven wrong letters in
      two sittings, refused by the guard because the font also sets their body
      text. And 47 places where a bullet or tick stands against the next word
      with no space, 43 of them in the two sittings that are scans, where the
      mark is OCR noise rather than a bullet.

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

## Phase 29 — five readers sent at the finished corpus, and what survived checking (September 2026 — parser 0.4.35)

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
- [x] **A gold score that could not tell a right label in the wrong place.**
      `eval_gold.py` compared a multiset of normalized speaker labels per
      page and threw away the opening words the annotation records beside
      each one, so a page where the chair speaks four times could match four
      identical labels in any order. It now scores twice, the second time
      pairing each gold turn with a parser turn on label AND opening words,
      matched by prefix because the annotation writes as many words as it
      took to identify the turn. **The two scores are the same** — 124 of 125
      — so the weaker measure had not been hiding anything, but it could
      have been. F1 is printed to three places: 0.996, not the 1.00 that
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

## Next

- [ ] The parser's only open item is the five ordinal marks Phase 27 found
      but a neighbouring size mismatch keeps out of reach — small and
      recorded rather than guessed at. Whether to mint a DOI is the author's
      call; the licence is settled (CC BY 4.0, `LICENSE-DATA`).

## Explicitly not building

Packaging/PyPI, docs site, utils wrappers, test-file mirror, separate
analysis modules before a notebook needs them. Diputados waits until the
Senate corpus is complete back to 2000.
