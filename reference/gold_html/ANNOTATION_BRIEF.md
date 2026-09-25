You are annotating a stretch of an Argentine Senate stenographic transcript to
build a GOLD SET — the reference other work is scored against. Your output
becomes ground truth, so an error here mismeasures the corpus permanently.
Accuracy matters far more than speed.

Paths below are relative to the repository root.
Stretches: reference/gold_html/stretches/<stretch_id>.html

Each file is a fragment of the chamber's own Corel WordPerfect HTML export.
Read the MARKUP, not a stripped version: the typography is the evidence.
- A speaker's label is printed in bold: `<B>Sr. PRESIDENTE (Menem).-</B>`,
  `<B>Sra. Fernández de Kirchner. -- </B>`. The holder is sometimes outside
  the bold run: `<B>Sr. Presidente </B>(Cafiero)<B>. -- </B>`.
- The typists are inconsistent. You will see `Sr.Presidente` with no space,
  `Sr Sager` with no stop, `SR. PRESIDENTE` shouted, `Sr. GENOUD.` ended on a
  full stop and no dash, `Sr. Salvatori, --` with a comma. All are labels.
- WordPerfect puts each accented letter in a font of its own, so a label can
  be split across runs — `Sr. AVEL` + `Í` + `N.-` is one label.
- An event is a note printed as its OWN paragraph. Because `<P>` is a
  separator that is never closed, "its own paragraph" means a run that opens
  with a fresh `<P>` before the note starts — usually the whole run to the
  next `<P>` is italic and opens with a dash, `<p><i>-La votación resulta
  afirmativa.</i>`. A parenthesised or italicised note with no `<P>` opened in
  front of it belongs to the speech it sits inside and is NOT an event — even
  one that closes a speech, "...señor presidente. (Aplausos.)", and even one
  that recurs twice inside a single running `<P>` of speech: "...que nos
  honra. (<i>Aplausos</i>.) ¡Cafiero no está imputado de nada! ¡Es un hombre
  honorable! <i>(Aplausos.)</i>" is one turn with no events in it, not a turn
  interrupted twice. The corpus merges a note like this back into the speech
  (TODO.md, Phase 2, in the project's repository). Whether the note itself is in `<i>` is not the test —
  some typists forget the italics on a note that still opens its own `<P>`,
  and that is still an event; the `<P>` boundary decides, not the font.
  Typography decides this, not what happened in the room: this is the corpus
  convention and it is what the parser is scored against. If the markup
  around a note is too tangled to tell whether a `<P>` truly opened before
  it, say so in `notes` with what you decided and why. Getting this wrong
  cost six re-emissions in the first round.
- The stenographer's notes are set in italics and usually open with a dash:
  `<I>— Se practica la votación por medios electrónicos.</I>`. Nobody utters
  them. A parenthesised note like `(Aplausos.)` or `(Risas.)` is also an
  event. But `(Lee:)` spoken by a secretary introducing a document is part of
  that secretary's own turn, not a separate event.
- `<P>` is used as a separator and is never closed. Do not rely on nesting.

For EACH stretch assigned to you, write
reference/gold_html/<stretch_id>.<YOURSET>.json with exactly this shape:

{
  "source_file": "<the .html name from stretches.csv for this stretch_id>",
  "stretch_id": "<the id>",
  "annotator": "<YOURSET>",
  "opens_mid_utterance": true|false,
  "utterance_starts": [
    {"speaker_label": "<the label exactly as printed, terminator included>",
     "first_words": "<the first 10-15 words of what they say>"}
  ],
  "events": ["<each stenographer's note, as printed>"],
  "headings": ["<each section title or number printed as a heading>"],
  "furniture_seen": ["<printed matter that is not speech: back-links, footnote
                      pointers, contents entries, sign-offs>"],
  "notes": "<anything a maintainer should know: a botched label, a passage
             that could be read two ways, text you judged to be an inserted
             document rather than floor speech, and WHY you judged it so>"
}

Rules that decide the hard cases:
1. List a turn ONLY if it STARTS inside this stretch. If the stretch opens in
   the middle of somebody's speech, set opens_mid_utterance true and do not
   list that speech as a start.
2. A PRINTED LABEL ALWAYS OPENS A TURN, even where the same person was
   speaking before it and only a note or a heading intervened. A stretch
   where the chair speaks four times holds four entries, with four identical
   labels and four different `first_words`. This is the ordinary shape of a
   vote: `<p><b>Sr. PRESIDENTE (Cafiero).-</b> En consideración en general.`,
   then an unlabelled sentence, then one or more `<p><i>` votación notes, then
   a fresh `<p><b>Sr. PRESIDENTE (Cafiero).-</b> Queda aprobada...` — two
   turns for the chair, not one continuous one. This rule reaches only an
   UNLABELLED paragraph that runs on: that is not a new turn. Where the
   typist re-sets the label, list it. (TODO.md Phase 2, in the repository; the PDF gold set does
   the same.) Getting this wrong cost four re-emissions in the first round.
3. An inserted document — a bill, a letter, a committee report handed in for
   the record — has no speaker. Do not invent one. Say so in notes.
   But a document a secretary READS ALOUD is that secretary's turn.
4. Record the label as the page prints it, including a typist's error. Do not
   tidy it. If the page prints `Sr. PRESIDENTE.-` with no name, write that.
5. Count every turn. The thing this gold set exists to measure is whether any
   turn is MISSING, so a turn you skip because it looked minor is the exact
   failure mode that matters. Short ones — "Pido la palabra.", "Sí." — count.

DO NOT look at anything under data/processed/. That is the output being
measured; reading it would make this annotation worthless. Work only from the
fragment and, if you need the wider context of the sitting, from the raw file
under data/raw/senado/taquigraficas/.

When done, report: how many turns you listed per stretch, and any case where
you were genuinely unsure and what you decided.
