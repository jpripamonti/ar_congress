# What is in this corpus, column by column

Written for someone who has never seen this project. It says what each field
holds, what its values mean, and — where it matters — what you must not assume
about it. The provenance of the underlying files, and every limit measured on
them, is in [SOURCES.md](../SOURCES.md).

The corpus is the stenographic record of the Argentine Senate: what was said on
the floor, who said it, and what the stenographer noted around it. 559 sittings
spanning 2000 to 2024, 21.5 million words.

## The three tables

| File | One row is | Rows |
| --- | --- | --- |
| `data/processed/senado/blocks/<sitting>.parquet` | a passage of one sitting — a turn of speech, a stenographer's note, a heading, or page matter | 237,308 across 558 files (one sitting fails to parse) |
| `data/processed/senado/speakers.parquet` | one printed speaker label in one sitting, resolved to a person and to the caucus they sat with | one per (sitting, label) pair |
| `data/processed/senado/parse_stats.csv` | one sitting, with 40 counts of what the parser did to it | 559 |
| `reference/senado/bloque_observado.csv` | one day the chamber's composition was actually recorded, for one senator | 23,325 over 336 dates, 2000–2024 |

There is one file of passages per sitting rather than one big file, so that a
single sitting can be read without loading the corpus. Concatenating them all is
the normal way to work with it.

## The passages table

**What the passage is**

| Column | Meaning |
| --- | --- |
| `type` | `speech` — words somebody said (152,549). `event` — the stenographer's note about something that happened (31,928). `heading` — a section title. `furniture` — printed page matter kept only for tracing; not speech. `inline_italic` — an italicised fragment that had no turn to belong to. `other` — text the parser could not attribute to anyone (1,204, 0.5%). |
| `text` | The words themselves, as printed. Spelling, punctuation and the edition's own mistakes are preserved: where a page misspells a senator's surname, so does this. |
| `event_type` | Only for notes. `vote` (17,400), `incident` (4,093, disorder in the chamber), `applause` (3,755), `unspecified` (1,723), `laughter` (1,395), `pause` (1,378), `stage` (1,179, someone entering, leaving or taking the chair), `timestamp` (1,005, the clock time the record prints). |
| `seq` | Position within the sitting. Sorting by it gives the order the words were printed in, which is the order they were spoken. |
| `pages` | The printed page or pages the passage came from, as a list. |

**Who said it**

| Column | Meaning |
| --- | --- |
| `speaker_raw` | The label exactly as printed: `Sr. Pichetto`, `Sra. Presidente (Michetti)`, `Varios señores senadores`. Not normalised, because normalising it would hide what the page actually says. Empty for anything that is not speech. |
| `turn_id` | Groups the passages of one continuous turn. A turn interrupted by applause, or split across a page break, keeps one `turn_id` across several rows. **Count turns by this, not by rows.** |

To get from a label to a person, join `speakers.parquet` on
(`session_id`, `speaker_raw`). That table is described below.

**Where it sits in the sitting**

| Column | Meaning |
| --- | --- |
| `chapter`, `chapter_title` | The numbered section of the sitting's agenda the passage falls under, and its title. Present in 530 of the 559 sittings; the rest print no section numbering the parser can read. |
| `session_id` | The sitting: date plus its number within the year, e.g. `2014-05-07_r07`. |
| `session_date` | The date of the sitting, `YYYY-MM-DD`. |
| `session_type` | What kind of sitting, as the Senate names it: `ORDINARIA` (158,994 rows), `ESPECIAL` (42,040), `EXTRAORDINARIA` (12,285), `INFORMATIVA ESPECIAL` (7,095 — the cabinet chief's report to the chamber), `TRIBUNAL DE JUICIO POLITICO` (6,792 — impeachment trials, where the speakers are largely not senators), `ASAMBLEA` (5,875 — both chambers together, where the President of the Nation speaks), `PREPARATORIA` (2,357), and five smaller kinds. **Mixing them without thinking will mislead you**: an impeachment trial and an ordinary sitting are not the same kind of speech. |
| `sesion`, `reunion` | The Senate's own two numberings of the sitting, as printed on its cover. |

**Where it came from**

| Column | Meaning |
| --- | --- |
| `source_pdf` | The file it was read from. |
| `pdf_sha256` | That file's checksum, so a passage can be traced to the exact bytes it came from. |
| `parser_version` | Which version of the parser produced this row. |
| `font`, `font_style`, `size` | The typeface the passage was printed in. Kept because the parser's decisions rest on it and they should be re-checkable, not because they carry meaning. |

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
| `bloc_status` | How far that caucus can be trusted: `confirmed` (83.4% of senators' floor words), `anachronistic` (13.0% — the source names a caucus that did not exist on that date), `undatable` (1.1% — the caucus has no established start, so nothing can be checked). Empty where there is no caucus at all (2.4%). |
| `bloc_basis` | Where the caucus came from: `roll call` (79.9% of senators' floor words) or `archived roster` (17.7%, the pre-2005 years). |
| `bloc_observed` | The date the caucus was actually recorded on. |
| `bloc_gap_days` | How many days that is from the sitting. Median 0 — most sittings are themselves roll-call days. Rows further than 200 days from any observation get no caucus. |
| `match_status` | How the label was resolved. This is the field to filter on, and its values are not interchangeable — see below. |

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
marked, never corrected or dropped** — 13.0% of senators' floor words. Dropping
them would hide how much of the Senate's own record is like this. Filter on
`bloc_status == "confirmed"` for any claim about *when* the chamber realigned.

### The chair carries a caucus, and that is a trap

A senator speaking from the chair (`match_status == "matched_senator_chair"`)
gets a caucus like anyone else, because they did belong to one. But what they
are saying is procedural — granting the floor, announcing a count. Reading it
as partisan speech is a mistake the data cannot prevent for you. Exclude the
chair from anything about party positions.

### What `match_status` means, and why 28% has no name

| Value | Share of speech | What it means |
| --- | --- | --- |
| `matched_senator` | 37.6% | A named senator, resolved against the roster and their mandate dates. |
| `office_only` | 28.1% | **A chamber office speaking under its bare title** — "Sr. Presidente", "Sr. Secretario", with no surname printed. This is how the record was printed before about 2016. **These are deliberately left without a person.** The chair changes hands during a sitting and the page does not say who holds it; the cover names two or more presiding officers in 340 of the 545 sittings whose cover says who presided. Any name here would be a guess. |
| `matched_senator_chair` | 17.1% | A senator speaking from the chair, where the page names them. |
| `matched_authority` | 15.5% | Someone holding a national or chamber office, resolved against a hand-compiled table of office-holders. |
| `out_of_scope` | 1.3% | Correctly not a senator: parties and witnesses at the impeachment trials, deputies, foreign heads of state, officials of other institutions. |
| `unmatched` | 0.1% | A genuine failure: 218 passages, nearly all invited outside speakers at public hearings, named by surname alone. |
| `collective` | 0.1% | "Varios señores senadores" — the record attributing words to several people at once. |
| `ambiguous` | 0.0% | A surname more than one person could hold at that date. |

**The trap to avoid**: treating `office_only` as missing data and dropping it
loses 28% of the floor, most of it the chair conducting business. Treating it as
one person is worse. For "who spoke most", exclude the chair entirely — that is
what the analysis in this repository does, and it says so.

## Things you should know before using this

- **The text is what the page prints, not what was said.** A stenographic record
  is edited. Senators correct their own words afterwards.
- **Two sittings of November 2001 are scans read by character recognition**, and
  their text is unreliable. The parser flags them; exclude them from any text
  analysis. They are `2001-11-21_r72` and `2001-11-29_r74`.
- **The caucus is observed, never continuous.** It is recorded on 336 days
  across 25 years — roll-call days from 2005, and sixteen archived captures of
  the Senate's own bloc-roster page before that. Every row says which day it
  used and how far that is from the sitting. A senator who changed caucus
  between two observations changes on the later one, not on the day they moved.
- **Coverage before 2004 is thin and uneven** — 34 of 47 sittings held for 2003,
  4 of 47 for 2002, 10 of 83 for 2001, 3 of 75 for 2000 — because the Senate's
  portal lists them but no longer serves the files. Year-on-year comparisons
  across that boundary are comparisons of what survives, not of what happened.
- **Roughly a fifth of each document is dropped on purpose**: contents pages,
  attendance rolls, appendices and inserted documents that were never spoken.
  The median sitting keeps 79.2% of its printed text.
- **One sitting fails to parse**: a November 2001 sitting that never reached
  quorum and therefore has no opening for the parser to find.

## How far it has been checked

Three layers, described in full in [SOURCES.md](../SOURCES.md):

- **36 pages annotated by hand**, spanning 2003–2024: boundary and attribution
  score 1.00, 124 of 125 turns.
- **All 558 parsed sittings audited against their source files**: no turn carries a
  second speaker's label, no text is written out twice, and every turn is
  checked for beginning and ending the way speech does.
- **5,463 turns read blind** across nine rounds, by a reader that was never
  shown the parser's answer: agreement on who is speaking in all but twenty-two,
  and all twenty-two resolved in the parser's favour afterwards — pages that print
  the quoted phrase more than once, and pages that print no label at all because
  the speech began earlier.
