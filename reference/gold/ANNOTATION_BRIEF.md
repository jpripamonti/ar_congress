# Annotating a printed page of the Diario de Sesiones

You are annotating pages of an Argentine Senate stenographic transcript to
build a GOLD SET — the reference the parser is scored against. Your output
becomes ground truth, so an error here mismeasures the corpus permanently.
Accuracy matters far more than speed.

Paths below are relative to the repository root.
Pages: `reference/gold/pages/<page_id>.png`
Index: `reference/gold/pages.csv`

## Read the image. Nothing else.

Open the `.png` with the Read tool and annotate what you see printed on it.

**Do not open the PDF, do not extract its text, and do not look at anything
under `data/processed/`.** That directory is the parser's output — the thing
being measured. Reading it, or reading text extracted by the same library the
parser uses, would make this gold set agree with the parser by construction,
including where the parser is wrong. The page image is what the chamber
printed, and it is the only evidence you are allowed.

If a page is genuinely illegible, say so in `notes` and annotate what you can.

## What the page looks like

The Diario is set in a serif face, one column, with the speech justified.

- **A speaker's label is bold and ends in a dash**: `Sr. Presidente (Zamora).-`,
  `Sra. Fellner.-`, `Sr. Pichetto. —`. The surname in parentheses is the person
  holding the office that day.
- **The terminator varies by era and by printer.** You will see a hyphen
  (`.-`), an en dash (`. –`) and an em dash (`. —`), sometimes with a space
  before and sometimes not. All are labels.
- **The holder is sometimes set in a different weight** from the office —
  bold `Sr. Presidente`, roman `(Pampuro)`, bold `. –`. It is still one label.
- **Before roughly 2016 the chair is usually printed with no surname at all**:
  `Sr. PRESIDENTE.-`. Record it exactly like that. Do not supply a name.
- **The stenographer's notes are italic and usually open with a dash**:
  `— La votación resulta afirmativa.`, `— Ocupa la Presidencia el señor
  presidente provisional del H. Senado, senador D. Federico Pinedo.` Nobody
  utters them.
- **Section headings are centred and bold**, often a number on its own line
  above a title: `35` / `Orden del Día N° 25` / `Incremento de partidas
  presupuestarias`.
- **The running header** across the top — date, kind of sitting, page number —
  is page furniture, as is the footer (`Dirección General de Taquígrafos`), the
  year motto some years print above it, footnote lines (`5 Ver el Apéndice.`)
  and contents links (`(volver)`, `Orden del Día Nº 24` set as a blue
  underlined link).

## What to write

For EACH page assigned to you, write
`reference/gold/gold_<page_id>.<YOURSET>.json` with exactly this shape:

```json
{
  "pdf": "<the source_file from pages.csv for this page_id>",
  "page": <the page number, an integer>,
  "page_id": "<the page_id>",
  "annotator": "<YOURSET>",
  "opens_mid_utterance": true,
  "utterance_starts": [
    {"speaker_label": "<the label exactly as printed, terminator included>",
     "first_words": "<the first 10-15 words of what they say>"}
  ],
  "events": ["<each stenographer's note, as printed>"],
  "headings": ["<each section title or number printed as a heading>"],
  "furniture_seen": ["<printed matter that is not speech: the dateline, the
                      motto, footnote lines, contents links, the footer>"],
  "notes": "<anything a maintainer should know: a botched label, a passage
             that could be read two ways, text you judged to be an inserted
             document rather than floor speech, and WHY you judged it so>"
}
```

## The rules that decide the hard cases

1. **List a turn ONLY if it STARTS on this page.** If the page opens in the
   middle of somebody's speech, set `opens_mid_utterance` true and do not list
   that speech as a start. A turn that starts here and runs onto the next page
   is still a start, and belongs in the list.
2. **A PRINTED LABEL ALWAYS OPENS A TURN**, even where the same person was
   speaking before it and only a note or a heading intervened. A page where
   the chair speaks four times has four entries, with four identical labels and
   four different `first_words`. This rule reaches only an UNLABELLED paragraph
   that runs on: that is not a new turn.
3. **An inserted document has no speaker.** A bill, a letter, a committee
   report printed into the record was never spoken. Do not invent a speaker for
   it; say in `notes` that you judged it inserted, and why. But a document a
   secretary READS ALOUD is that secretary's turn — `Sr. SECRETARIO
   (Oyarzún).- (Lee:)` is the secretary taking the floor, and the note
   `(Lee:)` printed inside that same paragraph is part of that turn, not a
   separate event.
4. **A parenthesised note inside somebody's paragraph belongs to that speech.**
   `...señor presidente. (Aplausos.)` closing a speech is NOT an event; it is
   the end of that turn's words. A note is an event only when it stands as its
   own paragraph. This is the corpus convention and it is what the parser is
   scored against.
5. **Record the label as the page prints it**, including a typist's error.
   Do not tidy it, do not correct the spelling, do not expand an abbreviation.
6. **Footnote markers are glued to the words.** The page prints `Aprobado.5`
   and `pertinentes.6`. The digit is a footnote pointer, not part of the
   sentence. Leave it out of `first_words` and list the footnote line under
   `furniture_seen`.
7. **Count every turn.** What this gold set exists to measure is whether any
   turn is MISSING, so a turn you skip because it looked minor is the exact
   failure mode that matters. Short ones — `Pido la palabra.`, `Sí.`,
   `(Lee:)` — count.
8. **A page can hold no speech at all.** A contents page, an attendance roll,
   a page of appendix: `utterance_starts` is then empty, and that is a real and
   useful annotation. Say in `notes` what the page is, so a maintainer knows
   that anything the parser attributes to a speaker there is a false positive.

## When you are done

Report, per page: how many turns you listed, how many events, and any case
where you were genuinely unsure and what you decided. Flag anything about the
page that looked damaged or strange — a previous round found a real defect
because a reader mentioned something that looked like a typesetting accident.
