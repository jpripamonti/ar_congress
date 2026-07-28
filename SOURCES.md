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
