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
| `data/processed/senado/blocks/<sitting>.parquet` | a passage of one sitting — a turn of speech, a stenographer's note, a heading, or page matter | 237,343 across 559 files |
| `data/processed/senado/speakers.parquet` | one printed speaker label in one sitting, resolved to a person where possible | one per (sitting, label) pair |
| `data/processed/senado/parse_stats.csv` | one sitting, with 40 counts of what the parser did to it | 559 |

There is one file of passages per sitting rather than one big file, so that a
single sitting can be read without loading the corpus. Concatenating them all is
the normal way to work with it.

## The passages table

**What the passage is**

| Column | Meaning |
| --- | --- |
| `type` | `speech` — words somebody said (152,565). `event` — the stenographer's note about something that happened (31,928). `heading` — a section title. `furniture` — printed page matter kept only for tracing; not speech. `inline_italic` — an italicised fragment that had no turn to belong to. `other` — text the parser could not attribute to anyone (1,204, 0.5%). |
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
| `session_type` | What kind of sitting, as the Senate names it: `ORDINARIA` (159,026 rows), `ESPECIAL` (42,040), `EXTRAORDINARIA` (12,285), `INFORMATIVA ESPECIAL` (7,095 — the cabinet chief's report to the chamber), `TRIBUNAL DE JUICIO POLITICO` (6,792 — impeachment trials, where the speakers are largely not senators), `ASAMBLEA` (5,875 — both chambers together, where the President of the Nation speaks), `PREPARATORIA` (2,357), and five smaller kinds. **Mixing them without thinking will mislead you**: an impeachment trial and an ordinary sitting are not the same kind of speech. |
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
| `party_or_alliance` | **The ticket the senator was ELECTED on, not the caucus they sat with.** The two diverge sharply after 2015. If you want the caucus, use `reference/senado/bloque_por_senador_periodo.csv`, and read the caveats in SOURCES.md first. |
| `province` | The province the senator represents. |
| `match_status` | How the label was resolved. This is the field to filter on, and its values are not interchangeable — see below. |

### What `match_status` means, and why 28% has no name

| Value | Share of speech | What it means |
| --- | --- | --- |
| `matched_senator` | 37.6% | A named senator, resolved against the roster and their mandate dates. |
| `office_only` | 28.1% | **A chamber office speaking under its bare title** — "Sr. Presidente", "Sr. Secretario", with no surname printed. This is how the record was printed before about 2016. **These are deliberately left without a person.** The chair changes hands during a sitting and the page does not say who holds it; the cover names two or more presiding officers in 282 of the 559 sittings. Any name here would be a guess. |
| `matched_senator_chair` | 17.1% | A senator speaking from the chair, where the page names them. |
| `matched_authority` | 15.6% | Someone holding a national or chamber office, resolved against a hand-compiled table of office-holders. |
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
- **All 559 sittings audited against their source files**: no turn carries a
  second speaker's label, no text is written out twice, and every turn is
  checked for beginning and ending the way speech does.
- **5,348 turns read blind** across eight rounds, by a reader that was never
  shown the parser's answer: agreement on who is speaking in all but twelve, and
  all twelve resolved in the parser's favour afterwards — every one of them a
  page that prints the quoted phrase more than once.
