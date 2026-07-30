# Data sources, terms, and provenance

## Transcripts (the corpus)

- **Source:** Senado de la Nación Argentina, open-data portal —
  <https://www.senado.gob.ar/micrositios/DatosAbiertos/>, dataset
  "Versiones Taquigráficas" (`ExportarListadoVersionesTac/json`).
- **Holdings:** 559 sessions spanning 2000–2024, retrieved 2025-01 and
  2026-07. Complete from 2004 on — every session the portal lists for those
  years is held. Before that the portal lists the sittings but no longer
  serves most of the files: 34 of 47 held for 2003, 4 of 47 for 2002, 10 of
  83 for 2001, 3 of 75 for 2000. Nothing before 2000 is served at all.
  Per-file sha256, source URL, and timestamps:
  [raw_data_manifest.csv](raw_data_manifest.csv), rebuilt from the files on
  disk by `scripts/make_manifest.py`. Listing snapshots are archived under
  `data/raw/senado/listings/`.

## Roster and authorities (speaker resolution)

- **Senators:** `ExportarListadoSenadores/json` (sitting) and
  `ExportarListadoSenadoresHistorico/json` (one row per mandate), retrieved
  2026-07-21; raw responses archived in [reference/senado/](reference/senado/)
  with fetch metadata in `manifest.json`. Re-fetch with `scripts/fetch_roster.py`.
- **Authorities:** no open-data endpoint exists. Two tables feed the resolver.
  [authorities_manual.csv](reference/senado/authorities_manual.csv) is
  hand-compiled, one row per office-holder with period bounds, evidence notes
  and a source: Senate officers are sourced to the designation passages of the
  held transcripts, and national-executive holders (presidents of the Nation,
  cabinet chiefs) to the sittings where the record names them, with tenure
  bounds cross-checked against official announcements. No row rests on a
  Boletín Oficial decree; where that is the case the evidence note says so.
  [authorities_observed.csv](reference/senado/authorities_observed.csv) is
  machine-derived by `scripts/extract_authorities.py` from each sitting's own
  masthead, which names who presided and who sat at the secretaries' table.
  It gives one row per (sitting, office, person); the resolver folds those
  observations into tenure spans. An observed span is a floor on a tenure,
  never a ceiling — it says only that the person held the office on the days
  the record shows them holding it.

### Party is the ticket, not the bloc

The roster field is "PARTIDO POLITICO O ALIANZA": the party or alliance a
senator was **elected under**, one value per mandate. It is *not* the caucus
(bloque) they sat with, and the two diverge sharply. Radicals elected on
Cambiemos and Juntos por el Cambio tickets from 2015 on carry those labels
and not "Unión Cívica Radical"; provincial alliances that later joined a
national coalition disappear from the labels without their senators moving.
Caucus membership is published only for sitting senators, so it cannot be
reconstructed for the rest of the span. The resolved-speaker table names the
column `party_or_alliance` for this reason, and the resolver prints the
caveat on every run. Any grouping built on it — including the party families
in the analysis notebook — is a grouping of electoral labels.

## Terms of use

The portal publishes **no license or terms page** (checked July 2026; the
datasets are also absent from datos.gob.ar). The governing framework, per the
Senate transparency office, is **Ley 27.275** (with Decretos 206/17 and
780/24): information must be provided in open formats that *"permitan su
reutilización o su redistribución por parte de terceros"* (Art. 1
"Apertura"), free of charge (Art. 1 "Gratuidad"), with active-transparency
publication obliged to remove barriers to reuse (Art. 32). Text:
<https://servicios.infoleg.gob.ar/infolegInternet/anexos/265000-269999/265949/norma.htm>.

When citing the underlying transcripts, cite the Senate as publisher with
the session date and the per-session source URL from the manifest.

## Gold evaluation set

[reference/gold/](reference/gold/) holds 36 stratified page annotations
covering 2003–2024: the original 24 (12 sessions × 2 pages, every year
2020–2024, all major session types and known-hard formats) plus 12 added
when the corpus was extended backwards — two pages from each of the eras
2000–2003, 2004–2006, 2007–2009, 2010–2013, 2014–2016 and 2017–2019, with
the sessions drawn at random and the page taken from the middle of each
document. They were produced by machine-assisted careful reading of the
rendered pages.

They have since been checked back against the source PDFs by
`scripts/check_gold.py`, which re-reads each annotated page and asks whether
every recorded turn really is printed there, in that order, with those
opening words, whether any printed speaker label went unrecorded, and
whether every recorded event appears. All 36 pages pass. One slip surfaced
and was resolved: an annotation quoted a turn's opening words without the
footnote marker the page glues to them, which is right about the turn and
right to leave out. **This is a second machine reading of the same pages,
not an independent human audit** — it catches transcription slips and
omissions, not a shared misreading of what a page means.

Widening the set mattered. On the modern-only pages the parser scored a
perfect 1.00, which turned out to say nothing about the older layouts:
the first run over the added pages scored 0.91 and exposed two real
defects, both fixed in parser 0.4.4 — the punctuation that closes a
speaker label was being prepended to the speaker's first words throughout
the pre-2010 files, and a parenthetical surname was landing in the speech
instead of the label.

## Corpus-wide audit

The gold set answers a narrow question well — did the parser read *these 36
pages* the way a careful reader does — but 36 pages is 0.08% of the 45,200 in
the corpus, drawn from 24 of 559 sittings. `scripts/audit_parse.py` covers the
rest by checking, on every session, things that must never happen. Current
results:

- **Page apparatus inside a speech turn: 1 occurrence** in 155,247 turns (a
  footer line that landed mid-sentence in the 7 May 2014 sitting). Mastheads,
  datelines, attendance rolls, section headers and the appendix-pointer footnote
  are otherwise absent from speech, which is what the positional header and
  footer strips are for.
- **The footnote that points at the appendix: 0 occurrences.** It is printed at
  body size in the body font, below the rule at the foot of the page, so neither
  the size test nor the positional footer strip reached it: 809 turns were
  nothing but that footnote, and its words had been drawn into 340 more, mid
  sentence. Position cannot tell it from speech — a superscript reference can
  begin a line too, and a rule keyed on position cut real debate when tried — so
  parser 0.4.8 keys on the wording, which is boilerplate, and cuts it like a
  header. Removing it also repairs the sentences it had been dropped into.
- **A second speaker's label glued inside a turn: 0**, outside the two scanned
  sittings below. This is the error that matters most — it means a change of
  speaker went unnoticed and one senator was credited with another's words.
  The audit found 71 such cases when it was first written; the parser now
  recovers labels the typesetter set in roman instead of bold, which is what
  had caused them.
- **A speaker label absorbed by the section title above it: 0** (1 left, in a
  scan). A numbered title and the label of whoever speaks under it are set in
  one bold run, and the space between them is often the one the PDF drops at a
  line join — "…bandera nacionalSr. Presidente". Read as one long title, the
  label vanishes, the turn never opens, and the next speaker's words are added
  to the previous speaker's turn. 1,693 titles in 112 sessions carried a label
  this way, stranding 314 turns; in 55 of those the swallowed label belonged to
  a *different* speaker, so words really were credited to the wrong person.
  Parser 0.4.7 cuts the title from the label whether or not a space survives.
  The cut was tried against all 5,154 distinct titles in the corpus first: all
  83 distinct tails it carves off are genuine speaker labels, none a false
  positive.
- **Text written out twice: 0 sessions.** No document yields more text than it
  prints.
- **Blocks not findable in the source PDF: 0.32% on average**, 12 sessions above
  1%, the worst of them the 20 October 2004 file whose mis-mapped symbol font the
  parser deliberately repairs. Elsewhere the figure is under 3%, and those are
  turns that span a seam the parser makes on purpose: it merges a speaker's
  consecutive paragraphs and drops the section heading printed between them.
- **Share of each document's printed text kept:** median 79.5%, quartiles 69%
  and 87%. The rest is dropped by design — contents pages, attendance rolls,
  appendices and inserted documents. The lowest figures are short sittings in
  minority that consist of little but a masthead and a roll.

### Fifty pages read blind

Everything above is the parser checked against itself or against invariants. It
cannot answer the plainest question — is the right person behind the words? —
because a rule can be applied perfectly to the wrong speaker. So the 50 turns
`audit_parse.py --sample 50` draws across the 25 years were read independently:
each page was rendered as an image, handed to an agent that was **never shown
the parser's answer**, and asked only which printed label governs the quoted
words. The two answers were compared afterwards, mechanically.

The readings agree on the speaker in **50 of 50**, the quoted words were found on
the page in all 50, and no reader saw page apparatus inside the paragraph. Two of
the turns begin on one page under a label printed on the page before, and the
reader confirmed the parser carried the speaker across the break correctly. The
comparison is in
[reference/verification/blind_read_50.csv](reference/verification/blind_read_50.csv):
the parser's speaker, the label the reader transcribed from the page, and the
reader's own notes and confidence.

Earlier passes disagreed twice, and the reader was right both times. Those two
disagreements are what exposed the two defects above — the section title that
swallows the label after it, worth 55 misattributed turns corpus-wide, and the
appendix-pointer footnote read as speech, worth 1,149 turns — neither of which
any amount of re-reading the 36 annotated pages would have found.

What this is not: an independent *human* audit. It is a second machine reading,
independent of the parser's code path — it works from the rendered page, not from
the PDF's character stream — but still a machine's reading. A shared misreading
of what a page means remains possible, and the review sheet is regenerated for a
human pass whenever `--sample N` is passed.

### Two sittings are scans, not text

The 21 November 2001 and 29 November 2001 sittings are photographs of the
printed Diario de Sesiones with optical character recognition run over them.
Their text is a guess and reads like one: "CAMARA DE- SEÑÁDORES DE L.A
NÁNCION", "Saeretarios", words run together, hyphens surviving from the line
breaks of the original column. Nothing downstream can repair that. The parser
detects them (a page-sized image behind the characters), records
`scanned_page_share` in `parse_stats.csv`, and prints a warning; the audit
lists them first and excludes them from its counts. **Exclude them from any
text analysis.** An earlier note in this project claimed no file from 2000 on
needed OCR; that was wrong for these two.

### Words run together at line joins

The parser reads characters in the order the PDF stores them, which is
faithful to what was typeset but loses the spaces pdfplumber's page-level
extraction infers from the layout. Where a word was broken across lines or
columns the two halves can end up joined — "reemplazala expresión",
"yplenipotenciario". It affects tokenisation, not attribution, and word counts
in the analysis are therefore very slightly low. Not yet fixed.

### Stenographer notes are events

A note the stenographer prints in parentheses — "(Aplausos.)", "(Risas.)",
"(Lee:)" — is recorded as a typed event, not as words spoken. Nobody utters
"aplausos": the note is the stenographer recording what the chamber did, and
preserving it as an event is what makes it possible to measure the room
around the speech. Some formats italicize only the word and leave the
brackets in the roman text, which used to hide such notes inside the
speaker's turn; the parser now restores the brackets before classifying.
Four gold files that had followed the older reading were updated to match
this convention, and the pages were re-checked against the source to confirm
the notes really are printed there.

One annotated turn is knowingly missed — in the August 2003 impeachment
sitting the secretary's label opens a turn whose entire content is the note
"(Lee:)" before an inserted document, so the parser records the note and no
turn. All such notes live in the JSON files themselves.
