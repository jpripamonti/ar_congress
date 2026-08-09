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
- Corpus parsed (parser 0.4.21): 152,553 speaker-attributed speech blocks
  and 31,928 typed stenographer events in 237,316 rows, as per-session
  Parquet under `data/processed/senado/`. One session fails to parse — a
  November 2001 sitting that never reached quorum, so it has no session
  opening to find. Text the parser cannot attribute to a speaker is 1,204
  rows (0.5%), and a handful of sessions account for most of it: sittings
  whose record is mostly an inserted document (two impeachment dossiers, a
  printed bill text, a list of judicial appointments) rather than floor
  debate.
- **The words no longer run together.** The 2003–2009 files end a line without
  storing a space, so the last word of one line used to come out glued to the
  first of the next — "reemplazala expresión". Parser 0.4.11 puts the space
  back wherever the page shows one, using a width measured off the files that
  do print their spaces: 710,039 spaces restored in 481 of the 559 sittings,
  and the corpus rises from 21.07 to 21.48 million words (+2.0% overall, +4%
  to +6.5% in every year from 2003 to 2009, under 0.1% elsewhere). Every word
  count in the analysis was that much low. It also makes those years' section
  numbering readable for the first time: 530 sittings now carry the section
  each turn belongs to, against 443 before.
- **Punctuation belonging to the editorial matter no longer counts as speech.**
  A stenographer's note is printed "— Se vota.", but in many files that opening
  dash is stored at the end of the line above, so the turn before it came out
  ending on a dangling dash: 9,003 turns, 5.9% of the corpus. The mirror case is
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
  asks of all 152,553 turns whether each begins and ends the way speech does —
  turns opening mid-word under a new speaker fall from 44 to 5, and those 5 are
  printed that way.
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
  WordPerfect-era sittings use Symbol and WordPerfect's MathA for ordinary
  typography, so the ordinal of "5° Reunión", the dash after a speaker's label,
  the bullet of a printed list and even the "P" and the "g" of a running head all
  came out as codepoints meaning nothing, sitting inside words and sentences.
  0.4.21 gives each of the fourteen the character the page shows, read from what
  surrounds it rather than from the font's nominal table — these files print an
  ordinal with a nominally Greek codepoint. **No private-use character is left in
  the corpus.** Giving the label dash back also lets repairs that were keyed on it
  see labels they had been blind to, which is why the corpus loses 12 speech
  blocks and 27 rows: merges, and page matter now recognisable as page matter.
- Two layers of verification, because they answer different questions.
  **On a hand-annotated sample** — 36 stratified pages spanning 2003–2024 —
  utterance boundary+attribution F1 = 1.00 (124 of 125 turns), event
  precision 1.00 and recall 0.94, no speech leaking onto contents pages. The
  annotations have themselves been checked back against the source PDFs
  (`scripts/check_gold.py`, 36 of 36 pass) — a second machine reading, not an
  independent human audit. **On all 558 sessions that parse** (`scripts/audit_parse.py`):
  no turn carries a second speaker's label, no label is absorbed by the section
  title above it, one page's footer leaks into speech, no text is written out
  twice, 5 turns of 152,553 open mid-word and every one of them is printed that
  way, and a median 79.2% of each document's printed text is kept (the rest —
  contents pages, attendance rolls, appendices — is dropped by design). Two
  sittings of November 2001 are scans with OCR text and should be excluded from
  any text analysis; the parser flags them. **On 5,413 pages read blind** — every
  page rendered as an image and read by an agent that was never shown the
  parser's answer, then compared — the two agree on who is speaking in
  [300 of 300](reference/verification/blind_read_300.csv),
  [497 of 500](reference/verification/blind_read_500.csv),
  [993 of 998](reference/verification/blind_read_1000.csv),
  [498 of 500](reference/verification/blind_read_500_0411.csv),
  [1,000 of 1,000](reference/verification/blind_read_1000_0412.csv),
  [998 of 1,000](reference/verification/blind_read_1000_0413.csv),
  [1,000 of 1,000](reference/verification/blind_read_1000_0413b.csv) and
  [105 of 115](reference/verification/blind_read_115_0418.csv) on eight
  samples that do not overlap, spread across every year of the span. Every case
  left over was checked afterwards against the page image and the parser is right
  in all of them — pages that print the quoted phrase twice, so the reader could
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
- Speakers resolved to persons: **70% of all speech blocks name a person**,
  with the ticket they were elected on and their province. A further 28% is
  a chamber office speaking under its bare title ("Sr. Presidente", "Sr.
  Secretario", no surname), which is how the transcripts printed it before
  about 2016. **These are deliberately left without a person.** The chair
  changes hands during a sitting and the page does not say who holds it, so
  any name would be a guess; the sitting's own cover page names two or more
  presiding officers in 340 of the 545 sittings whose cover page says who
  presided at all (`scripts/count_presiding.py`). They are marked as
  office-known-person-unstated. Another 1.3% is correctly out of scope —
  parties and witnesses at the impeachment trials, deputies, foreign heads
  of state, officials of other institutions. **Genuine lookup failures are
  down to 0.1%** (218 blocks), nearly all of them invited outside speakers
  at public hearings, named by surname alone.
- **What every column holds and what not to assume about it**:
  [docs/DATA_DICTIONARY.md](docs/DATA_DICTIONARY.md) — written for someone who
  has never seen this project. How a version is cut, checked and cited:
  [docs/RELEASE.md](docs/RELEASE.md).
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
  held 27–46% of floor words to 2016 and 13–15% from 2020, while the
  radical/Cambiemos family went the other way (9–27% before 2019, 30–39%
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
- `reference/verification/` — the eight blind reads: what the parser said, what
  an independent reader saw on the page, and whether they agree. 1,000 pages in
  each of the last three rounds, 500 before them, 998 before that, then 500, 300
  and 50 in the first.
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
