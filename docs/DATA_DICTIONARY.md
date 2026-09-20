# What is in this corpus, column by column

Written for someone who has never seen this project. It says what each field
holds, what its values mean, and — where it matters — what you must not assume
about it. The provenance of every source file is in `raw_data_manifest.csv`,
one row per PDF, and the limits measured on them are summarised in the
[README](../README.md).

The corpus is the stenographic record of the Argentine Senate: what was said on
the floor, who said it, and what the stenographer noted around it. 817 sittings
spanning February 1998 to September 2026, 29.5 million words, of which 25.7
million are attributed speech.

## The three tables

| File | One row is | Rows |
| --- | --- | --- |
| `data/processed/senado/blocks/<sitting>.parquet` | a passage of one sitting — a turn of speech, a stenographer's note, a heading, or page matter | 432,564 across 817 files (one sitting of the 818 attempted fails to parse) |
| `data/processed/senado/speakers.parquet` | one printed speaker label in one sitting, resolved to a person and to the caucus they sat with | one per (sitting, label) pair |
| `data/processed/senado/parse_stats.csv` | one sitting, with 40 counts of what the parser did to it | 818 |
| `reference/senado/bloque_observado.csv` | one day the chamber's composition was actually recorded, for one senator | 24,813 over 357 dates, 2000–2026 |

There is one file of passages per sitting rather than one big file, so that a
single sitting can be read without loading the corpus. Concatenating them all is
the normal way to work with it.

## The passages table

**What the passage is**

| Column | Meaning |
| --- | --- |
| `type` | `speech` — words somebody said (247,471). `event` — the stenographer's note about something that happened (60,905). `heading` — a section title (33,494). `furniture` — printed page matter kept only for tracing; not speech (84,102), which from 0.5.4-html includes the HTML era's attendance roll. `inline_italic` — an italicised fragment that had no turn to belong to (1,169). `other` — text the parser could not attribute to anyone (5,423, 1.25%), most of it matter inserted into the record without being spoken: speeches handed in, and the bills read into it. |
| `text` | The words themselves, as printed. Spelling, punctuation and the edition's own mistakes are preserved: where a page misspells a senator's surname, so does this. |
| `event_type` | Only for notes. `vote` (17,417), `incident` (4,097, disorder in the chamber), `applause` (3,755), `unspecified` (1,721), `laughter` (1,395), `pause` (1,378), `stage` (1,180, someone entering, leaving or taking the chair), `timestamp` (1,012, the clock time the record prints). |
| `seq` | Position within the sitting. Sorting by it gives the order the words were printed in, which is the order they were spoken. |
| `pages` | The printed page or pages the passage came from, as a list. |

**A note printed inside a speaker's paragraph stays inside that speech.**
Which row a stenographer's note lands in is decided by typography, not by
what happened: a note set as its own paragraph becomes an `event`, and a
note printed within a speaker's own paragraph is folded into the words of
that speech. The chamber prints the same act both ways, so the same act
lands in different rows in different sittings.

The largest instance is the cue that marks the secretary reading aloud.
Where the page sets it on its own line under the label, it is an `event`
carrying that label — 237 rows. Where the page sets it inside the label's
paragraph, as the HTML era almost always does, the whole turn is a `speech`
row whose entire text is `(Lee:)` — 5,331 rows, 5,251 of them in the HTML
era. A note that closes a speech behaves the same way: 1,127 turns end with
`(Aplausos.)`, `(Risas.)` or the like inside the speech text.

Together that is 6,458 rows, 2.61% of `speech`, holding 8,494 words nobody
spoke — **0.03% of the 25.4 million words of speech**, small enough to
ignore for most counting. It is not small in one place: **31.6% of the
secretary's 16,859 turns are a speech whose whole content is the word
"Lee"**, so any count of turns or words by the secretary needs them
removed. A regex over `text` removes them; the parser leaves them where the
page puts them, which is the same reason the spelling is left alone.

When two annotators were shown these pages without the parser's answer,
both independently marked `Sr. PROSECRETARIO (Pontaquarto).- (Lee:)` as the
secretary taking the floor. The rows are where readers of the page expect
them to be; it is the word count that needs the care.

**Who said it**

| Column | Meaning |
| --- | --- |
| `speaker_raw` | The label exactly as printed: `Sr. Pichetto`, `Sra. Presidente (Michetti)`, `Varios señores senadores`. Not normalised, because normalising it would hide what the page actually says. Empty for anything that is not speech, with one exception: **332 stenographer's notes carry a label because the page printed one directly above them** and the note is the whole of what that turn holds — "Sr. Secretario (Estrada). — (Lee:)" is one printed line, and the secretary took the floor there. The row stays `event`; the label says who the note is about. Filter on `type == "speech"` for anything counting words said, which is what `speakers.parquet` does. |
| `turn_id` | Groups the passages of one continuous turn. A turn whose only content is a stenographer's note has that note as its one row. A turn interrupted by applause, or split across a page break, keeps one `turn_id` across several rows. **Count turns by this, not by rows.** |

To get from a label to a person, join `speakers.parquet` on
(`session_id`, `speaker_raw`). That table is described below.

**Where it sits in the sitting**

| Column | Meaning |
| --- | --- |
| `chapter`, `chapter_title` | The numbered section of the sitting's agenda the passage falls under, and its title. Present in 781 of the 817 sittings that parse; the rest print no section numbering the parser can read. |
| `session_id` | The sitting: date plus its number within the year, e.g. `2014-05-07_r07`. |
| `session_date` | The date of the sitting, `YYYY-MM-DD`. |
| `session_type` | What kind of sitting, as the Senate names it, by row count: `ORDINARIA` (323,298), `ESPECIAL` (51,573), `EXTRAORDINARIA` (24,395), `ASAMBLEA` (11,249), `TRIBUNAL DE JUICIO POLITICO` (6,940), `INFORMATIVA ESPECIAL` (6,696), `PREPARATORIA` (3,294), `ESPECIAL EXTRAORDINARIA` (2,630), `ORDINARIA CONTINUACIÓN` (1,038), `EN MINORÍA` (807), `REUNIÓN CONJ.AMBAS CÁMARAS` (201), `ESPECIAL EN MINORÍA` (196), `FALTA DE QUORUM` (14). These are the chamber's own labels and they overlap — `EN MINORÍA` and `ESPECIAL EN MINORÍA` name the same thing — so group them before counting. **Mixing them without thinking will mislead you**: an impeachment trial and an ordinary sitting are not the same kind of speech. |
| `sesion`, `reunion` | The Senate's own two numberings of the sitting, as printed on its cover. |

**Where it came from**

| Column | Meaning |
| --- | --- |
| `source_file` | The file it was read from. Called `source_pdf` up to release 0.4.37, when every holding was a PDF. |
| `source_format` | `pdf` or `html` — which of the two the chamber served for that sitting. The HTML export covers most of 1998–2003 and carries no pagination, so `pages` is empty and `size` is null on those rows; do not read an empty `pages` as a parsing failure. |
| `source_sha256` | That file's checksum, so a passage can be traced to the exact bytes it came from. Called `pdf_sha256` up to release 0.4.37. |
| `parser_version` | Which version of the parser produced this row. |
| `font`, `font_style`, `size` | The typeface the passage was printed in. Kept because the parser's decisions rest on it and they should be re-checkable, not because they carry meaning. On HTML rows `font` and `size` are null and `font_style` comes from the markup, which states outright what the PDF side has to infer. |

## The speakers table

One row per printed label per sitting — because the same label means different
people in different sittings, and sometimes within one sitting.

| Column | Meaning |
| --- | --- |
| `speaker_raw` | The label as printed, matching the passages table. |
| `label_clean` | The same label with the honorific and the terminator removed. |
| `n_blocks` | How many passages in that sitting carry this label. |
| `person_id`, `person_name` | The person, where one could be established. Empty otherwise. |
| `role` | The office, for people who speak by office rather than by name — the chair, the secretaries, the cabinet chief, the President of the Nation. Taken verbatim from the record, so the same office appears under several spellings. |
| `elected_ticket` | **The list the senator STOOD ON, not the caucus they sat with.** One value per mandate, taken from the roster. See the two-affiliations note below before using it. |
| `province` | The province the senator represents. |
| `bloc` | **The caucus the senator SAT WITH.** Taken from the nearest day the chamber's composition was actually recorded — see below. |
| `bloc_status` | How far that caucus can be trusted, **judged on the date of the sitting, not on the day the caucus was recorded**: `confirmed` (77.6% of senators' floor passages), `anachronistic` (7.0% — the record names a caucus that did not exist on the day of the sitting), `disputed` (0.8% — two records that could each describe the day name different caucuses, so which one held is not established), `undatable` (0.6% — the caucus has no established start, so nothing can be checked). Empty where there is no caucus at all (14.0%, almost all of it 1998–1999). |
| `bloc_basis` | Where the caucus came from: `roll call` (45.0% of senators' floor passages) or `archived roster` (40.9%, the pre-2005 years). |
| `bloc_observed` | The date the caucus was actually recorded on. |
| `bloc_gap_days` | How many days that is from the sitting. Median 0 — most sittings are themselves roll-call days. Rows further than 200 days from any observation get no caucus. |
| `match_status` | How the label was resolved. This is the field to filter on, and its values are not interchangeable — see below. |
| `tiebreak` | Empty on all but 57 rows. It says what separated two senators the roster left in a tie, and it exists so you can refuse either answer: `masthead` (5 rows, 477 passages) means the sitting's cover page STATES who presided that day; `honorific` (52 rows, 173 passages) means only the courtesy title on the label distinguished them, which is how the chamber writes rather than something it states. Drop `tiebreak == "honorific"` if a courtesy title is not evidence you will accept. |

### Two political affiliations, and they are not the same

`elected_ticket` is the list a senator stood on. `bloc` is the caucus they sat
with once in the chamber. They disagree across most of the corpus, and the
disagreement is not noise:

Measured over the 14.7 million words of floor speech by identified senators
where both affiliations are recorded, and grouping labels into the four party
families the notebook uses:

- The two are written the same way in **9.2%**.
- They are written differently but mean the same political camp in **72.0%** —
  the peronist bloc renaming itself, mostly.
- They fall in different camps in **18.9%**, and this is the part that matters:
  three quarters of it is a senator elected on a **provincial alliance** who sits
  with a **national caucus**. Someone elected for the Frente Jujeño sits with
  the radicals; someone elected for Chubut Somos Todos sits with the Frente de
  Todos. The ticket does not say which side of the chamber they are on. The
  caucus does.
- Genuine floor-crossing between two *named* national camps is **0.31%**.

So: for "which party won this seat", use the ticket. For anything about how the
chamber divided, use the caucus.

### Why some caucuses are marked `anachronistic`

The Senate re-labels its own old roll calls with the caucus a senator joined
later. Frente de Todos, formed in December 2019, is stamped on votes going back
to 2010; Pichetto's whole 2013–2019 term is filed under a caucus he founded in
2019 on leaving. Every reading is checked against the caucus's own dated life
in `reference/senado/blocs_manual.csv`, and the ones that fail are **kept and
marked, never corrected or dropped** — 13.1% of senators' floor passages. Dropping
them would hide how much of the Senate's own record is like this. Filter on
`bloc_status == "confirmed"` for any claim about *when* the chamber realigned.

The check is made twice, and the second time is the one this column reports. A
reading is first checked against the day it was recorded; then, because a
sitting can be up to 200 days from the nearest record, it is checked again
against the day of the sitting. The two answers differ: the roll call of 21
December 2005 rightly reads "PJ Frente para la Victoria", a caucus formed that
month, and the nearest sitting to it is in June, six months before the caucus
existed. Ninety-nine passages used to come out `confirmed` that way.

A second thing the nearest reading cannot settle: where the sitting falls
between two records that name DIFFERENT caucuses, the switch happened
somewhere in between and the record does not say on which side of the sitting.
Taking the nearer of the two projected one reading across a disagreement —
sometimes backwards, onto a day an earlier record contradicts. Those rows read
`disputed`: 29 (sitting, label) pairs, 113 passages, eleven senators. Only a
record that could itself describe the day counts as the other side of a
disagreement — one the source already flagged, or a roll call naming a caucus
that did not exist on the day of the sitting, is not evidence of a switch but
the very thing `anachronistic` marks. Of the 113, the 36 passages that cross a
party family are the ones to care about if the question is which side of the
chamber someone was on: Gerardo Morales between the radicals and the Frente
Cívico Jujeño in 2002-2004, and Luis Falco between the radicals and the
Radical Rionegrino in February 2004.

Only roll-call readings are re-checked. The dates on an archived roster page
are the days the page was **captured**, a floor on the caucus's life rather
than a claim about when it began, so a sitting before the earliest capture is
expected — twenty-two passages, all from the first months of 2000 — and
marking them would report
the gaps in the Internet Archive as a fact about the chamber.

### The chair carries a caucus, and that is a trap

A senator speaking from the chair (`match_status == "matched_senator_chair"`)
gets a caucus like anyone else, because they did belong to one. But what they
are saying is procedural — granting the floor, announcing a count. Reading it
as partisan speech is a mistake the data cannot prevent for you. Exclude the
chair from anything about party positions.

### What `match_status` means, and why 22% has no name

| Value | Share of speech | What it means |
| --- | --- | --- |
| `matched_senator` | 35.6% | A named senator, resolved against the roster and their mandate dates. |
| `matched_senator_chair` | 27.3% | A senator speaking from the chair, where the page names them. Where two senators of the same surname sat at once, the sitting's own cover page decides which of them held the gavel that day. |
| `office_only` | 21.5% | **A chamber office speaking under its bare title** — "Sr. Presidente", "Sr. Secretario", with no surname printed. This is how the record was printed before about 2016. **These are deliberately left without a person.** The chair changes hands during a sitting and the page does not say who holds it; the cover names two or more presiding officers in 522 of the 803 sittings whose cover says who presided. Any name here would be a guess. |
| `matched_authority` | 14.3% | Someone holding a national or chamber office, resolved against a hand-compiled table of office-holders and the office-holders each sitting's cover page names. |
| `out_of_scope` | 0.9% | Correctly not a senator: parties and witnesses at the impeachment trials, deputies, ministers of the national executive, foreign heads of state. |
| `unmatched` | 0.1% | A genuine failure: 276 passages, nearly all invited outside speakers at public hearings, named by surname alone. |
| `collective` | 0.1% | "Varios señores senadores" — the record attributing words to several people at once. |
| `ambiguous` | 0.0% | A surname more than one person could hold on that date, with nothing left to separate them: four senators named Martínez and three named González, all of one gender within each group, and the preparatory sittings where the outgoing and the incoming holder of an office are both in window. 55 passages in all. |

**Where a tie was broken, and how.** Two senators named Sapag sat for Neuquén
together from November 1998 to December 2001, and a label reading "Sapag" and
nothing else names neither. Two things settle it, and they are not equally
strong. For the chair, the sitting's cover page names who held the gavel —
"del señor vicepresidente 2° del H. Senado, don Felipe R. Sapag" — which is
the chamber stating a fact. For an ordinary turn, only the courtesy title is
left: "Sra. Sapag" is Silvia, "Sr. Sapag" is Felipe. Which given names the
chamber writes as "señora" is read off the corpus itself rather than guessed
from the spelling, and the title is used only where every candidate's given
name is settled and the title fits exactly one of them. It is not infallible —
about 1% of courtesy titles in the corpus disagree with the senator the label
resolves to — so every row it decided carries `tiebreak == "honorific"`. On
the 69 Sapag turns where the chair's own words introduce the speaker ("tiene
la palabra la señora senadora Sapag"), that wording agrees with the title in
all 69.

**The trap to avoid**: treating `office_only` as missing data and dropping it
loses 22% of the floor, most of it the chair conducting business. Treating it as
one person is worse. For "who spoke most", exclude the chair entirely — that is
what the analysis in this repository does, and it says so.

## Things you should know before using this

- **The text is what the page prints, not what was said.** A stenographic record
  is edited. Senators correct their own words afterwards.
- **Three held files are scans read by character recognition**, and their text
  is unreliable. The parser flags them; exclude them from any text analysis.
  Two are in the corpus — `2001-11-21_r72` and `2001-11-29_r74` — and the
  third, `1997-12-18_r117`, does not parse at all and contributes no rows.
- **The caucus is observed, never continuous.** It is recorded on 357 days
  from 25 May 2000 to 17 September 2026 — roll-call days from 2005, and sixteen
  archived captures of the Senate's own bloc-roster page before that. Every row
  says which day it used and how far that is from the sitting. A senator who
  changed caucus between two observations changes on the later one, not on the
  day they moved.
- **There is no caucus at all for 1998 and most of 1999.** The bloc-roster page
  is the only record of the chamber's composition before the roll calls begin,
  and the Internet Archive's earliest capture of it is 25 May 2000; nothing
  earlier exists. Reaching back from that capture would cross the renewal of
  December 1998, so those sittings are left without a caucus rather than given
  one by inference. It is 14% of senators' floor passages, and it is not spread
  evenly: filter on `session_date >= "1999-11"` for anything comparing caucuses
  over time.
- **Roughly a fifth of each document is dropped on purpose**: contents pages,
  attendance rolls, appendices and inserted documents that were never spoken.
  The median sitting keeps 82.8% of its printed text, and the two formats
  differ: 79.3% for the PDFs against 91.2% for the HTML export, which has no
  repeated page headers or footers to drop.
- **One sitting fails to parse**: `1997-12-18_r117`, the impeachment tribunal
  of December 1997, a scan whose character recognition leaves no opening the
  parser can find. 818 files are attempted and 817 produce rows.

## How far it has been checked

Three layers, summarised in the [README](../README.md). Each measures a
different thing, and the strongest number rests on the smallest sample.

- **320 turns annotated by hand**, in two sets, and this is the only layer that
  measures whether a turn was found at all.
  **36 PDF pages** spanning 2003–2024: boundary and attribution F1 = 0.996,
  124 of 125 turns and 29 of 31 stenographer's notes. **24 stretches of the
  HTML era** spanning 1998–2003, each about 7,000 characters and cut on the
  source rather than at anything the parser found: F1 = 1.000, 195 of 195
  turns and 62 of 62 notes, under either of the two readers who annotated them
  independently. How far those two agree is reported by `check_gold_html.py`
  before either is believed, and on the committed annotations they agree on
  every one of the 195 turn starts and on all 24 stretches.
  The PDF set is scored twice, on the printed label alone and on the label
  together with the turn's own opening words, because a page where the chair
  speaks four times has four identical labels and counting labels alone cannot
  tell a parser that found those turns from one that found four turns in the
  wrong places. Both scores are the same on it.
  **Read the interval, not the point.** One miss in 320 puts the 95% interval
  on recall at 0.983 to 0.999, those 320 turns are 0.13% of the 247,471 in the
  corpus, and two thirds of the PDF pages are 2020 or later — on the record
  before 2016 the measure rests on twelve pages. Neither set checks the order
  the turns came out in.
- **All 817 parsed sittings audited against their source files**: no page
  apparatus inside a turn and no turn carrying a second speaker's label outside
  the three scans, no sitting whose output is longer than the page it came from,
  160,180 blocks probed for being findable in the file they came from with
  0.006% not located once the scans are set aside and no sitting above 1%, and
  every turn checked for beginning and ending the way speech does — 8 turns of
  247,471 open mid-word and every one of them is printed that way.
- **6,819 turns read blind** across thirteen rounds on 691 sittings, by readers
  that were never shown the parser's answer. Twenty-four disagreed at the time
  of reading and each was then checked against the printed page: **two were
  real defects of the parser**, both since fixed — a centred section number read
  as words the chair said, and a bold label split across three font runs that
  cost four senators their turns — and the other twenty-two were the page
  printing no label at all because the speech began earlier, the sheet sending
  a reader to a different printing of the same stock phrase, or one reader's
  own slip. Every answer is re-asked of the current corpus by the project's own
  release checks, because the rounds were run months and many parser versions
  ago and a repair could quietly move a passage to somebody else: 6,549 still
  resolve to the person the round named, **none resolves to anybody else**, and
  270 cannot be re-asked at all — 264 quote words the page prints under more
  than one name, 3 are notes a repair has since moved out of speech, 2 are all
  an unmapped font left of a passage, and 1 has no words recorded.
  This is the only check in the project whose ground truth was produced without
  sight of the parser, and it measures attribution only: it asks whether a turn
  the parser emitted belongs to the person it names, and can never find a turn
  the parser never emitted. That is what the annotated sets above are for.
