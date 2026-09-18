# ar_congress

Corpus of Argentine Senate stenographic session transcripts ("versiones
taquigráficas"): acquisition, parsing into structured speaker-attributed
text blocks, and analysis. The chamber serves them as PDFs from 2004 on and
as its own HTML export for most of 1998–2003; both are read here.

## Status (September 2026)

- 819 session transcripts held, spanning 1998–2026. Coverage is complete from
  2002 onward — every session the portal lists for those years is held — and
  partial before it: 51 of 73 for 1998, 47 of 74 for 1999, 46 of 75 for 2000,
  44 of 83 for 2001. 1997 contributes a single sitting, an impeachment tribunal
  of 18 December. The portal lists sittings back to 1983, but of the 882 it
  lists before 1998 exactly one is still served; the other 881 answer 404. That
  was established by asking for all 882, not by sampling, so 1998 is the floor
  and there is no point looking again.
- **Two formats, one corpus.** The portal serves the same URL as a PDF for the
  sittings from 2004 on and as the chamber's own HTML export for most of
  1998–2003 (212 of the 214 held come from Corel WordPerfect). The downloader
  used to reject anything that did not begin with `%PDF`, which is why those
  years looked unserved: 211 sittings were being thrown away as they arrived.
  Both formats are kept as served, and every row carries the `source_format`
  it came from.
- **What the record declares about itself.** A sitting's masthead may read
  "VERSIÓN TAQUIGRÁFICA (PROVISIONAL)" — the uncorrected record — and the
  manifest carries that as `provisional`, with three values rather than two:
  309 sittings say they are provisional, 338 say they are not, and 172 make no
  claim, because from 2018 the words leave the masthead altogether. Calling
  that last group final would invent a fact about 134 sittings. Read it from
  the raw file: the parser drops the masthead as page apparatus, so parsed text
  puts every PDF at "not provisional" when 261 of 605 are.
- Corpus parsed: 247,163 speaker-attributed speech blocks and 60,765 typed
  stenographer events in 432,331 rows over 817 sittings, as per-session Parquet
  under `data/processed/senado/`. 25.7 million words of attributed speech, of
  which the HTML era contributes 6.5 million. The PDF side is parser 0.4.37 and
  the HTML side `scripts/parse_html.py` at 0.5.0-html; the two share the speaker
  pattern and the event subtypes, so a passage means the same thing in either.
  Two sittings fail to parse, both because the parser cannot find a session
  opening: the November 2001 sitting that never reached quorum, and the 1997
  impeachment tribunal, which does not open like an ordinary sitting. Text that
  cannot be attributed to a speaker is 0.92% of the corpus, and in the HTML era
  82% of it stands just after a marker of insertion — speeches handed in for the
  record and never delivered.
- **The portal serves one sitting twice.** 29 October 2003 is listed as reunión
  27 and as reunión 28, and both URLs return byte-identical files. It is the
  only such pair in the 819, and until it is resolved that sitting's words are
  counted twice.
- **The words no longer run together.** The 2003–2009 files end a line without
  storing a space, so the last word of one line used to come out glued to the
  first of the next — "reemplazala expresión". Parser 0.4.11 puts the space
  back wherever the page shows one, using a width measured off the files that
  do print their spaces: 670,660 spaces restored in 482 of the 559 sittings,
  and the corpus rises from 21.07 to 21.48 million words (+2.0% overall, +4%
  to +6.5% in every year from 2003 to 2009, under 0.1% elsewhere). Every word
  count in the analysis was that much low. It also makes those years' section
  numbering readable for the first time: the sittings carrying the section each
  turn belongs to went from 443 to 530, and stand at 538 today.
- **Punctuation belonging to the editorial matter no longer counts as speech.**
  A stenographer's note is printed "— Se vota.", but in many files that opening
  dash is stored at the end of the line above, so the turn before it came out
  ending on a dangling dash. It happened to 9,025 of the 26,937 notes that open
  with a dash — one in three. The mirror case is
  a note ending in a colon that opened the next turn instead (29). And where a
  section's number is set in the body face rather than the bold of its title,
  the number stayed on the turn above and the section was lost altogether —
  26 sections recovered. All three were found by readers of the sixth blind
  round and fixed in 0.4.13. The eighth round found the same fault splitting a
  word: an interjected note is set in italics, and in a few files the italic run
  carries a character or two past the closing parenthesis, so the note came out
  "(aplausos), s" and the sentence resumed at "i la Argentina debe ser tomada en
  su totalidad?". 0.4.14 gives those tails back — 5 broken words and 70 marks of
  sentence punctuation, in 75 turns.
- **Names are no longer cut in half.** The same change of face happens inside a
  speaker's own name: the page prints "Sr. Presidente. – Se gira…" but the last
  "e" of "Presidente" is set in roman rather than bold, so the corpus recorded a
  speaker called "Sr. President" and the turn began "e. – Se gira…" — also
  "Sra. Higone" for Higonet and "Sr. God" for Godoy. Two further faults came out
  with it. The terminator that closes a label is written ".-" with a plain
  hyphen from about 2013 on, which the parser's pattern did not accept, so the
  repair that already existed for this had been inert for a decade of sittings.
  And a sentence whose opening letters are set a point larger than the rest was
  dropped as page apparatus: the "T" of "Tiene la palabra…", and in one sitting
  the chair's whole "Por favor, les pido si podemos mantener el s—", leaving the
  turn to begin "ilencio durante la exposición". 0.4.16 repairs all three: 14
  names rejoined, 165 labels split from the speech stuck to them (69 more than
  the dash alone allowed), 82 words made whole again. Found by a new check that
  asks of all 152,549 speech blocks whether each begins and ends the way speech
  does — turns opening mid-word under a new speaker fall from 44 to 5, and those
  5 are printed that way.
- **A note is no longer put in somebody's mouth.** The page prints "— Se practica
  la votación por medios electrónicos."; the block ended after "la" and the rest
  was filed as speech, so the corpus had the chair saying "votación por medios
  electrónicos" out loud, and elsewhere "nacional en el mástil del recinto." —
  the tail of a note describing a senator raising the flag. 0.4.17 takes a tail
  of any length back to its note where the note ends on a letter and the tail
  opens in lower case: 8 of them, against 28,308 complete notes left untouched.
  0.4.18 does the same for an italic run that opens a turn — a newspaper's name
  printed right after the label was being swallowed by the turn above, putting
  one senator's words in another's mouth. Measured across the corpus: 2 cases.
- **Punctuation is no longer left standing on its own.** A word set in italics
  inside a sentence — a foreign word, a newspaper's name, a Latin phrase —
  arrives from the file as a piece of its own, and the comma or full stop that
  closes it is back in the body face, so it arrives as another piece again. Every
  piece was being joined with a space, so the corpus read "del  default . Por ese
  motivo" where the page reads "del default. Por ese motivo". 0.4.19 joins each
  piece the way the page sets it. Of the 4,653 marks that stood apart from their
  word, **3,618 were the parser's own doing and are now joined**; the 1,035 that
  remain are spaces the page itself prints. 0.4.20 extends the same rule to the
  marks the first pass left out — the closing quotation mark, the apostrophe, the
  square bracket — and to the opening side, where a quoted word had come out
  spaced on both sides: `caso " strawberry ",` for a page that prints
  `caso "strawberry",`. Together they stop 3,785 marks of punctuation being
  counted as words by anything that splits on spaces. Found by the ninth blind
  read, and completed by the review of that fix.
- **The characters no font would declare are readable now.** 1,234 characters of
  the corpus sat in the range Unicode reserves for private use, where a glyph
  lands when the file draws it from a font whose encoding it never states. The
  WordPerfect-era sittings draw ordinary typography from Symbol, SymbolMT,
  WordPerfect's MathA and Phonetic, and one sitting from a private slot of Times
  New Roman, so the ordinal of "5° Reunión", the dash after a speaker's label,
  the bullet of a printed list and even the "P" and the "g" of a running head all
  came out as codepoints meaning nothing, sitting inside words and sentences.
  0.4.22 gives thirteen of the fourteen the character its own page shows, read
  off the printed page rather than from the font's nominal table — these files
  print an ordinal with a nominally Greek codepoint. The fourteenth is removed
  instead of translated: it prints an upside-down A in the middle of the word
  "categoría", once, and keeping it would break the word for every reader. Where
  the page shows something the document plainly did not mean, the page still
  wins: one codepoint draws an underscore in two sittings that wanted an ordinal
  in one and an exclamation mark in the other, and it is recorded as the
  underscore it prints. A scan of all 559 source PDFs finds exactly these
  fourteen and no others, so **no private-use character is left in the corpus.**
  Giving the label dash back also lets repairs that were keyed on it see labels
  they had been blind to. The whole of the change is 13 places in two sittings:
  15 lines of page matter the parser
  could not read before — a dateline, a page number — are now recognised and
  dropped, and in ten of those places the dropped line had been splitting a
  senator's turn, so 22 half-turns rejoin into 10. That is 27 rows and 12 speech
  blocks fewer, with the same speaker, the same turn number and the same words on
  both sides of every one of the 13. Nothing else in the corpus moves: 48 other
  sittings have single characters translated inside ordinary speech, which is the
  point of the table, and no sitting anywhere changes a block, a turn number or a
  speaker.
- **A word whose letters are spaced apart is one word again.** A page that spaces
  out a word's letters to draw the eye to it — "T e n e r  c a l i d a d" in the
  President's address of 1 March 2009, "V o t a c i ó n  N o m i n a l" over every
  roll-call table from 2004 on — leaves a gap between every pair of letters as
  wide as the gap that means a missing space, so the corpus held one word per
  letter: 189 such runs in 50 sittings, 13 of them inside speech, and the phrases
  findable by no search. What tells the two apart is that a missing space is one
  wide gap between letters otherwise set tight, while a spaced-out word is a row
  of gaps that all measure alike. 0.4.24 puts no space inside such a row, and
  still puts one where the row is broken by a gap wider than the rest, which is
  where the page separates two words. The change is 115 blocks in 43 sittings —
  97 headings, 9 passages of speech, 9 of page matter — and **in all 115 the
  letters are identical and only the spacing moved**
  ([reference/verification/letter_spacing_0424.csv](reference/verification/letter_spacing_0424.csv)).
  With its heading legible, the masthead of a roll-call table is recognised in
  three sittings where it used to be lost, which is 15 new rows. Every output
  check of the audit is identical, and the gold set scores exactly as before.
  One line needed more than that, and 0.4.26 gave it: a roll-call masthead of 18
  November 2009 is set in a Tahoma whose declared widths belong, for half its
  letters, to the letter beside them, so an evenly spaced line arrives with half
  its gaps measuring nothing and half measuring the spacing, and the row of alike
  gaps breaks into pieces of two and three. A line is now taken as spaced from
  end to end when most of what can be measured says so and the line stores its
  own spaces — which is what makes it safe, since the word boundaries are then
  the file's own. It changes 3 blocks in 2 sittings, both page matter. One last
  heading, of 4 March 2009, still read "V otación Nominal", because the rule that
  keeps the space in front of a spaced-out word had no exception for a page that
  had already stored that space and so put a second one in, one letter inside the
  word; 0.4.27 applies that rule only where nothing is stored at that edge, which
  changes that single block and nothing else in the corpus. Four rows of lone
  letters are left, all a senator's own enumeration, spoken that way and
  correct as printed. Two more looked the same and were not: both files print
  the same resolving clause every decree in the corpus uses — "…D E C R E T A
  :" — spaced out for emphasis exactly like every heading this fix collapses
  elsewhere, but by storing a literal space between each letter rather than by
  widening the gap, a form the classifier could not yet see through. Found by
  a later review (`TODO.md`, Phase 25) and closed by 0.4.32 (`TODO.md`, Phase
  26): the two blocks — `2003-06-25_r13` and `2004-02-24_r43`, both quoted
  decree text — now read "DECRETA," and a corpus-wide scan for the same shape
  finds nothing else of the kind left.
- **What the file draws outside the page is no longer in the corpus.** A PDF can
  place text beyond the edges of its own sheet, where nothing prints and nobody
  reading the record can see it, and the extractor hands it over like any other
  text: 3,246 characters on 264 pages of 49 sittings
  ([reference/verification/offpage_text_0425.csv](reference/verification/offpage_text_0425.csv)).
  Mostly runs of spaces, but two sittings of 2013 draw "◄ Ver el Apéndice." down
  a column to the right of the sheet, one letter under the next, and the sitting
  of 12 September 2024 draws its "Pág. N" 170 points past the right edge on all
  187 pages — which is why that record shows no page number. 0.4.25 keeps a
  character only if some part of it is on the sheet. It removes 13 rows: 9 of
  invisible text, and 4 that had been split around it and are now whole,
  including a turn of 4 September 2013 that was broken in two mid-sentence.
- **The letters the fonts declared wrong are the page's letters again.** The
  WordPerfect-era sittings of 2003–2009 draw their ordinals, quotation marks,
  dashes and question marks with symbol fonts, and those fonts tell the file the
  wrong thing about what they draw. Where the font declares nothing at all, the
  mark arrived as a meaningless token that also carried the name of its own font
  — never the bold of the heading it sat in — so a section title broke in two
  around the ordinal and the half after the break, which starts with the bill's
  number, was thrown away as a bill number out of sequence: **8,523 rows in 64
  sittings carried a title cut off that way**. Where the font declares the wrong
  letter, the damage reached the spoken word: the corpus published "el artículo
  1E del proyecto", "la Ley N1 25.673", "en llamar Aprotocolo facultativo de la
  cedaw@", ")Qué trató el Congreso", and "22/ Reunión - 13/ Sesión ordinaria"
  where the ordinal comes out as a slash. 0.4.28 to 0.4.31 read every one of the
  37 font-and-mark combinations off the printed page, at 500 to 600 dpi, and
  rendered again with a second, independent renderer every one that came out
  blank or boxed. Nothing unreadable is left in the corpus anywhere, and 185 cut
  titles fall to 4. The guard is no longer a hand-written list of font names —
  that list is precisely what had left two of these fonts unexamined. The parser
  now checks each document for itself: a font that draws so much as one
  lower-case letter anywhere in the sitting is setting text, and nothing of its
  is touched. Seven wrong letters are deliberately left and counted, in two
  sittings whose ordinal comes from the same Times New Roman that sets their
  body text, where an "E" or a "1" may be a real letter and a real digit.
  Four cut titles remained after this pass; a later and unrelated fault
  behind two of them is closed by 0.4.33 (`TODO.md`, Phase 27), and the last
  two — a title broken across a page and one broken by a double space
  inside its own text — are closed by 0.4.34 (`TODO.md`, Phase 28).
- **A ring mark that Unicode calls a letter isn't one, and 226 of them were
  missing.** "1º," "2ª": the ordinal ring is sometimes drawn in a slightly
  different style than the number and word around it, which a block-smoothing
  pass exists to repair by welding a lone, differently-styled character back
  into its neighbours — except that pass skips anything it reads as a real
  letter, so as not to swallow a genuine one-letter word, and Unicode counts
  "º" and "ª" as letters even though they read as punctuation everywhere a
  person would read them. The mark's own block was never absorbed, and was
  then read as junk and dropped. A corpus-wide scan for the same shape found
  231 of them; 226, in nine sittings from 2008 to 2023, share their
  neighbour's exact type size and are restored by 0.4.33 — "el artículo 9"
  is "el artículo 9º" again, "Orden del Día N" is "Orden del Día Nº" again.
  One was worse than a missing mark: a stage direction of 6 August 2008 broke
  at the ring and its second half was credited to the previous speaker as if
  he had said it himself; that sitting now reads the stage direction whole,
  with no senator saying words that were never his. Five more marks in four
  more sittings sit next to a neighbour of a different type size and are
  measured but not yet reached
  (`TODO.md`, Phase 27; [reference/verification/ordinal_marks_0433.csv](reference/verification/ordinal_marks_0433.csv)).
- **The last two cut titles were each the edge of a corpus-wide fault, not
  a one-off.** A heading's own double space usually marks where a
  speaker's label or a new appendix item starts, so the parser cuts there
  — but sometimes the two spaces just sit where a line wrapped, mid-citation
  or mid-sentence, and cutting there throws away the rest of the title. A
  full-corpus diff against the pre-fix parser, run after every new rule
  added to tell the two cases apart, found the fault in 94 sittings, not
  one: 660 section titles recovered where none had been found before, 87
  more completed from a bare number to their full title, zero lost. A
  second, separate fault — a section's own number surviving as a
  footnote-sized scrap and then read as a leaked page number and deleted —
  closes the other cut title (13 April 2011) and, in one 2001 sitting,
  recovers 92 sections at once by letting the running section count pick
  back up after two numbers it had lost outright. 0.4.34
  (`TODO.md`, Phase 28; [reference/verification/heading_recovery_0434.csv](reference/verification/heading_recovery_0434.csv)).
- **The stenographers' sign-off is out of the senators' mouths.** Every page of
  the 2013-onward format is signed "Dirección General de Taquígrafos" at the
  foot, and the strip that removes it looked only in the last 70 points of the
  page. Fourteen sittings print it a little higher, where it survived — and
  wherever it sat between the last word of one page and the first of the next,
  it was glued into whatever sentence the page break had interrupted. Sanz, on
  7 May 2014, came out saying it in the middle of a question. The line is now
  cut on its own wording anywhere in the bottom fifth of the page, so the band
  did not have to grow and take real text with it: 1,250 pieces of page
  furniture gone, 753 speech fragments rejoined into the turns they belong to,
  19 stenographer's notes recovered from under it — including the opening of
  the 7 May 2014 sitting — and the only speech the corpus loses is the four
  words the footer had put in Sanz's mouth. The audit had been reporting this
  page on every run and still exiting clean, because its page-apparatus check
  was printed and never counted; it counts now. And a heading with no word in
  it is not a title: seven bold blocks — a space left where a page header was
  cut, three of them OCR noise — were typed as section titles, rows saying a
  section began that cannot say which. 0.4.35 and 0.4.36 (`TODO.md`, Phase 29).
- Two layers of verification, because they answer different questions.
  **On a hand-annotated sample** — 36 stratified pages spanning 2003–2024 —
  utterance boundary+attribution F1 = 0.996 (124 of 125 turns), event
  precision 1.00 and recall 0.935, no speech leaking onto contents pages.
  Scored a second time with each turn's own opening words carried alongside
  its label, so that a label moved onto another speaker's words cannot pass as
  a match on the strength of the name alone, it comes out the same: 124 of
  125. Neither score sees the ORDER of the turns on the page — both compare
  what is there, not where — so a page whose turns came out shuffled would
  still score full marks; that is a gap in the measure, not a claim about the
  corpus. **Read that 0.996 as the small sample it is**: one miss in 125 turns
  puts the 95% interval on recall at 0.956 to 0.999, and the 125 turns come
  from only 24 documents, so errors could arrive in clusters the interval does
  not allow for. The 36 pages cover eight kinds of sitting and thirteen years
  from 2003 to 2024, but two thirds of them are 2020 or later; on the
  pre-2016 record, where the printed conventions are least like today's, it
  rests on twelve pages. The
  annotations have themselves been checked back against the source PDFs
  (`scripts/check_gold.py`, 36 of 36 pass) — a second machine reading, not an
  independent human audit. **On all 558 sessions that parse** (`scripts/audit_parse.py`):
  no turn carries a second speaker's label, no label is absorbed by the section
  title above it, no page apparatus leaks into speech outside the two scans,
  no text is written out twice, every one of 98,601 probed blocks is found in
  the PDF it came from (0.120% not located, and no sitting above 1% once the
  two scans are set aside), 5 turns of 151,761 open mid-word
  and every one of them is printed that way, and a median 79.0% of each
  document's printed text is kept (the rest — contents pages, attendance rolls,
  appendices — is dropped by design). Two
  sittings of November 2001 are scans with OCR text and should be excluded from
  any text analysis; the parser flags them. **On 5,463 turns read blind** — every
  page rendered as an image and read by an agent that was never shown the
  parser's answer, then compared — the two agree on who is speaking in
  [50 of 50](reference/verification/blind_read_50.csv),
  [300 of 300](reference/verification/blind_read_300.csv),
  [497 of 500](reference/verification/blind_read_500.csv),
  [993 of 998](reference/verification/blind_read_1000.csv),
  [498 of 500](reference/verification/blind_read_500_0411.csv),
  [1,000 of 1,000](reference/verification/blind_read_1000_0412.csv),
  [998 of 1,000](reference/verification/blind_read_1000_0413.csv),
  [1,000 of 1,000](reference/verification/blind_read_1000_0413b.csv) and
  [105 of 115](reference/verification/blind_read_115_0418.csv) on nine
  samples that do not overlap, spread across every year of the span. All 5,463
  answers are re-asked of the current corpus by `scripts/check_blind_reads.py`,
  which is what makes them a check rather than a record: 5,416 still resolve to
  the person the round named, 47 cannot be re-asked — 43 quote words the page
  prints under two different names, so the record cannot say which turn the
  reader meant; two quotes are all an unmapped font left of a passage; two are
  notes a repair has since moved out of speech — and none resolves to anybody
  else. Every case left over from the
  rounds themselves was checked afterwards against the page image and the
  parser is right in all of them — pages that print the quoted phrase twice, so the reader could
  not know which occurrence was meant, and, in the ninth round, ten pages that
  carry no printed label at all — nine because the speech began pages earlier and
  the reader rightly refused to guess a name, one a reader's own slip. **Who is speaking is settled; what the turn
  says is still being corrected.** Earlier rounds exposed four of the defects
  fixed in 0.4.7–0.4.10; the fifth found an editorial note cut off by a change of
  font and left as a two-character turn (0.4.12); the sixth, while agreeing on
  every speaker, still found three pieces of editorial punctuation kept as speech
  (0.4.13); the seventh found nothing to fix; the eighth, agreeing on every
  speaker in turn, found a word broken in half by an interjected note (0.4.14);
  and the ninth found the punctuation left adrift from italicised words
  (0.4.19, completed in 0.4.20).
  Details and figures: [SOURCES.md](SOURCES.md).
- Speakers resolved to persons: **77% of all speech blocks name a person**,
  with the ticket they were elected on and their province. A further 22% is
  a chamber office speaking under its bare title ("Sr. Presidente", "Sr.
  Secretario", no surname), which is how the transcripts printed it before
  about 2016. **These are deliberately left without a person.** The chair
  changes hands during a sitting and the page does not say who holds it, so
  any name would be a guess; the sitting's own cover page names two or more
  presiding officers in 522 of the 803 sittings whose cover page says who
  presided at all (`scripts/count_presiding.py`). They are marked as
  office-known-person-unstated. Another 0.9% is correctly out of scope —
  parties and witnesses at the impeachment trials, deputies, ministers of
  the national executive, foreign heads of state. **Genuine lookup failures
  are 0.2%** (504 blocks): invited outside speakers at public hearings named
  by surname alone, and the two senators named Sapag who sat together from
  1998 to 2001, for whom a label reading "Sapag" and nothing else cannot be
  told apart and is marked ambiguous rather than assigned.
- The two eras resolve alike: **0.24% of the HTML era's speech is unresolved
  against 0.18% of the PDF era's**. Getting there took the sittings' own
  cover pages, which had never been read for 1998–2003 — they name the
  chamber's secretaries, whom the labels cite by surname alone, and they name
  which senator held the gavel, which is the only thing that separates Felipe
  Sapag in the chair from Silvia Sapag on the floor.
- Caucus attached to **86% of senator speech blocks**. What is missing is
  almost all 1998–1999 (19,797 of the 21,812 blocks without one): the Senate's
  bloc-roster page is the only record of the chamber's composition before the
  roll calls begin in 2005, and the Internet Archive's earliest capture of it
  is 25 May 2000. There is no capture before that — checked, not assumed — and
  reaching back from it would cross the December 1998 renewal, which is exactly
  the kind of inference the caucus data exists to avoid.
- **What every column holds and what not to assume about it**:
  [docs/DATA_DICTIONARY.md](docs/DATA_DICTIONARY.md) — written for someone who
  has never seen this project. How a version is cut, checked and cited:
  [docs/RELEASE.md](docs/RELEASE.md).
- Analysis over the whole span: [notebooks/analysis.ipynb](notebooks/analysis.ipynb).
  Roadmap in [TODO.md](TODO.md).

## Results

> These figures and numbers were computed on the 559-sitting corpus of
> 2000–2024, before the HTML holdings of 1998–2003 and the sittings of
> 2025–2026 were added. They have not been recomputed, so read them as the
> state of the analysis at release 0.4.37, not of the corpus as it stands.

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
  radical/Cambiemos family went the other way (9–27% before 2019, 30–39%
  after) — a chamber that looks realigned at a stroke. Group the identical
  speech by caucus and the step disappears: radical/Cambiemos sits at 23–37%
  throughout, and provincial and other alliances end 2022–2024 at 16–20%
  rather than 13%. Senators did not change sides in 2019; the tickets they had
  been elected on consolidated into two national coalitions. All 62 caucuses are
  dated by hand ([blocs_manual.csv](reference/senado/blocs_manual.csv)), each
  against the sitting that attests it, because the Senate records a caucus once
  per mandate and backdates it over the whole term. `bloc_status` says whether
  the caucus existed **on the day of the sitting**, which is not the same
  question as whether it existed on the day it was recorded: a sitting can be
  up to 200 days from the nearest record, and 99 passages used to come out
  `confirmed` because the check had only ever been made at the other end of
  that gap. 0.4.35 re-checks at the sitting's own date. A second reading of
  the same gap is marked too: where the sitting falls between two records that
  could each describe that day and name DIFFERENT caucuses, the switch happened
  somewhere in between and the record does not say on which side, so taking the
  nearer of the two projected one reading across a disagreement. Those 113
  passages — 0.1% of senators' floor passages, of which 36 cross a party family —
  read `disputed` rather than `confirmed`.
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
projected backwards over the whole term, so **3,043 of its 22,213 readings
(13.7%) name a caucus that did not exist on the day of the vote**. All 62
caucuses are dated by hand against the sittings that attest them, every reading
is checked against those dates, and the ones that fail are marked rather than
dropped or repaired. Seven caucuses still have no established start, so nothing
can be checked for them. A senator who crossed the floor between two
observations changes on the later one, not the day they moved.

Before 2005 the roll-call records do not exist at all, and that gap is now
filled from the Senate's own bloc-roster page as the Internet Archive kept it —
1,112 senator-rows over 16 captures from May 2000 to June 2004, every one checked
against the roster's mandate dates. A capture dates the page, not the chamber:
it brackets a change between two dates and never fixes one to the day.

## Layout

- `scripts/download.py` — fetch sessions + metadata sidecars from the Senate
  open-data portal, in whichever of the two formats it serves for the sitting.
- `scripts/provenance.py` — what a held file is: the format served and whether
  the record declares itself provisional, read from the file's own masthead.
- `scripts/mark_provenance.py` — write those two facts into every sidecar,
  including the files fetched before the fields existed.
- `scripts/parse.py` — parse PDFs into per-session Parquet block tables
  (speech turns, typed events, headings), plus per-session logs and a
  `parse_stats.csv` quality table.
- `scripts/parse_html.py` — the same table from the chamber's HTML export,
  which covers most of 1998–2003. A separate reader, because none of the PDF
  pipeline's work applies to markup that states outright what a PDF only
  implies; the speaker pattern and the event subtypes are shared with
  `parse.py` so both eras mean the same thing.
- `scripts/fetch_roster.py` — fetch senator roster datasets into
  `reference/senado/`.
- `scripts/fetch_blocs.py` — read one roll-call record per sitting date back
  to 2005 into `reference/senado/bloques_por_fecha.csv`: which caucus each
  senator sat with, which the roster publishes only for sitting members.
- `scripts/fetch_archived_blocs.py` — recover the pre-2005 years from the
  Senate's own bloc-roster page, long dead, as the Internet Archive kept it:
  1,112 senator-rows over 16 captures, 2000 to 2004.
- `scripts/build_bloc_observations.py` — put both sources in
  `reference/senado/bloque_observado.csv`, one row per day one senator's
  caucus was actually recorded, each marked with how far it can be trusted.
- `scripts/map_blocs.py` — collapse the roll-call readings into per-senator
  caucus spells and file each caucus under the analysis's party families.
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
- `reference/verification/` — the nine blind reads: what the parser said, what
  an independent reader saw on the page, and whether they agree. 1,000 pages in
  each of the last three rounds, 500 before them, 998 before that, then 500, 300
  and 50 in the first.
- `reference/` — versioned reference data: roster snapshots, authorities
  tables, gold evaluation set. Provenance: [SOURCES.md](SOURCES.md).
- `data/` — symlink to the working copy kept outside Git (see
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

On a new machine, re-create the working-data symlink first (see DATA.md).

## Source

Senado de la Nación Argentina, open-data portal
(<https://www.senado.gob.ar/micrositios/DatosAbiertos/>).

## Licence and citation

The code in this repository is MIT ([LICENSE](LICENSE)). The corpus it produces
and the reference tables behind it are CC BY 4.0 — reusable, including
commercially, on condition of attribution — and [LICENSE-DATA](LICENSE-DATA)
lists exactly what that covers. The transcripts themselves are the Senate's:
not relicensed here, not redistributed, and cited separately, by sitting date
and the per-sitting URL in [raw_data_manifest.csv](raw_data_manifest.csv).
[SOURCES.md](SOURCES.md) works through the terms they are published under.

To cite the corpus:

> Ripamonti, J. P. (2026). *Argentine Senate stenographic transcripts, 2000–2024:
> a speaker-attributed corpus* (version 0.4.37) [Data set]. Zenodo.
> <https://doi.org/10.5281/zenodo.22661020>

Version 0.4.37 has its own DOI, above. To cite the corpus rather than one
release of it, use the concept DOI, which always resolves to the latest:
<https://doi.org/10.5281/zenodo.22661019>.

[CITATION.cff](CITATION.cff) carries the same in the form a reference manager
reads. [docs/RELEASE.md](docs/RELEASE.md) says how a version is cut, checked,
and deposited on Zenodo, where the DOI to add to that citation comes from.
