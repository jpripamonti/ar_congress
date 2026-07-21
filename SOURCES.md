# Data sources, terms, and provenance

## Transcripts (the corpus)

- **Source:** Senado de la Nación Argentina, open-data portal —
  <https://www.senado.gob.ar/micrositios/DatosAbiertos/>, dataset
  "Versiones Taquigráficas" (`ExportarListadoVersionesTac/json`).
- **Holdings:** all 90 sessions listed for 2020–2024, retrieved 2025-01-01/02.
  Per-file sha256, source URL, and timestamps: [raw_data_manifest.csv](raw_data_manifest.csv).
  Completeness re-verified against the live listing 2026-07-21 (listed 90 =
  held 90); listing snapshots are archived under `data/raw/senado/listings/`.

## Roster and authorities (speaker resolution)

- **Senators:** `ExportarListadoSenadores/json` (sitting) and
  `ExportarListadoSenadoresHistorico/json` (one row per mandate), retrieved
  2026-07-21; raw responses archived in [reference/senado/](reference/senado/)
  with fetch metadata in `manifest.json`. Re-fetch with `scripts/fetch_roster.py`.
- **Authorities:** no open-data endpoint exists. Hand-compiled table at
  [reference/senado/authorities_manual.csv](reference/senado/authorities_manual.csv):
  Senate officers are sourced to the designation passages of the held session
  transcripts (source URL per row); national-executive tenure dates
  (cabinet chiefs) are from public record and marked *pending
  primary-source verification* in their evidence notes.

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

[reference/gold/](reference/gold/) holds 24 stratified page annotations
(12 sessions × 2 pages; every year 2020–2024, all major session types and
known-hard formats). They were produced by machine-assisted careful reading
of the rendered pages and are **pending owner verification**. Known
convention notes: parenthesized italic applause is an event for the parser;
one annotator recorded it as inline text (documented in the JSON notes).
