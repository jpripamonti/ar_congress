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
The roster publishes caucus only for the 72 sitting senators, never
historically. The resolved-speaker table names the column `elected_ticket`
for this reason, and the resolver prints the caveat on every run. Any grouping
built on it is a grouping of electoral labels.

How far the two actually diverge, measured over the 14.7 million words of floor
speech by identified senators where both are known, grouping labels into the
four party families the notebook uses: the ticket and the caucus are written the
same way in 9.2%; written differently but meaning the same political camp in
72.0%, which is mostly the peronist bloc renaming itself; and falling in
different camps in 18.9%. That last part is the whole value of holding both.
Three quarters of it is a senator elected on a **provincial alliance** sitting
with a **national caucus**: elected for the Frente Jujeño, sits with the
radicals; elected for Chubut Somos Todos, sits with the Frente de Todos. The
ticket does not say which side of the chamber someone is on. Genuine
floor-crossing between two named national camps is 0.31%, so the ticket is not
*wrong* about the peronist/radical divide — it is simply silent about everyone
else.

### Where the caucus does come from, and how far it can be trusted

The Senate's roll-call records fill most of the gap. Every recorded vote
publishes the whole chamber — including the members absent for it — with the
caucus each senator was sitting in, so one record per sitting date is a
complete snapshot of that day's composition. `scripts/fetch_blocs.py` collects
one per date (23,007 readings over 320 sitting dates, 287 senators, 62
caucuses). Neither the caucus nor the votes appear in the open-data portal;
both are read from the site's own roll-call pages, and the raw HTML is archived
so a re-run neither refetches nor depends on the site still answering.

Three limits, all measured:

* **The Senate dates the caucus wrong, in one specific and measurable way.** It
  stores one caucus per MANDATE and stores the one the senator ENDED that
  mandate in, projected backwards over the whole term. Of the 18 senators filed
  under Frente de Todos, only 2 carry it from a plausible date; the other 16
  carry it back to 2016 or earlier, and that caucus was formed in 2019. La
  Libertad Avanza and Convicción Federal show the same shape, and Pichetto's
  entire 2013–2019 mandate is filed under Peronismo Republicano, a bloc he
  founded in 2019 on leaving, while he in fact led the Frente para la Victoria
  bloc throughout. A senator who crossed the floor mid-term therefore shows one
  unbroken spell.

  Checked against the dated caucus lives below, **3,043 of the 22,213 readings
  that name a caucus (13.7%), spread over 311 of the 320 roll calls, name one
  that did not exist on the day of the vote.** Every one is kept and marked
  `acta_anacronica` rather than dropped or repaired: dropping them would hide
  how much of the Senate's own record is like this, and repairing them would
  mean inventing what the senator sat in instead, which no record says.
* **2.6% of readings carry no caucus at all**, and 11 senators have none in any
  record.
* **A caucus with no established start cannot be checked at all** — 1,046
  readings, marked `acta_sin_control`, so they are never mistaken for confirmed.

### Before 2005: the Senate's own page, as the web archive kept it

Roll-call records begin in February 2005, and 12.9% of the corpus's floor
speech is older than that. The Senate itself published a page listing every
senator under their caucus through those years. The page is long dead and the
Senate keeps no archive of it, but the Internet Archive captured it, and
`scripts/fetch_archived_blocs.py` recovers **1,112 senator-rows from 16 captures
running 25 May 2000 to 19 Jun 2004** — which closes the gap almost exactly
against roll-call records starting the following February. All 91 pre-2005
sittings in the corpus fall within six months of a capture, and 79% of their
words within three.

This is the chamber's own statement of its own composition, and it records real
events rather than a frozen list: three new peronist caucuses appear in
December 2001 as the party splinters during the crisis; after the October 2003
election the page files the newly seated senators under a caucus literally
called "No Informado", and the next capture empties that holding bucket into
four real caucuses, which is four caucus changes no other source records.

Two limits, both stated on every row rather than smoothed over:

* **A capture dates the page, not the chamber.** It says what the page said the
  day it was captured. Bracketing a change between two captures is sound;
  dating it to the day is not, and the readings carry a capture date so the
  distance is always visible.
* **The page lags, provably.** Every recovered name was checked against the
  roster's own mandate dates: 1,110 of 1,112 name someone in office that day. The
  two that do not are a senator still listed four days after his term ended and
  another listed a month before his began. Both are kept as printed.

Eighteen caucuses on these pages died before the roll-call records begin and so
have no entry in the dated list below — Frepaso, Cruzada Renovadora de San
Juan, 17 de Octubre, Peronista del Interior and others. They keep the name the
page printed and are marked `foto_bloque_previo`, since there is nothing to
check them against.

### One file holds every observation

`scripts/build_bloc_observations.py` puts both sources in
`reference/senado/bloque_observado.csv`: **23,325 rows, one per day one
senator's caucus was actually recorded**, over 336 dates and 369 senators, each
with the record it came from and how far it can be trusted. It interpolates
nothing and collapses nothing into spells. `resolve_speakers.py` then takes,
for each sitting, the observation nearest that senator — writing the caucus,
its status, its basis, the day it was observed and the distance in days, so any
stricter reading costs one filter. Of the floor speech by identified senators,
83.4% gets a confirmed caucus, 13.0% one marked anachronistic, 1.1% one that
cannot be checked, and 2.4% none at all.

### Dating the caucuses by hand

**All 62 caucuses** are dated one at a time in
[reference/senado/blocs_manual.csv](reference/senado/blocs_manual.csv), each row
naming its evidence, the sitting that attests it, and how far that evidence
goes: 65 rows, because three caucus names cover two separate lives each, of
which 40 carry `confidence: high`, 20 `medium` and 4 `low`. Those dates are
what every roll-call reading is checked against. Every sentence the file quotes
is quoted as the source prints it, accents and capitals included, so it can be
found by searching for it — 33 in the transcripts and 3 in the archived roster.

The evidence is of four kinds, and the file says which was used for each:

* **The Senate's own bloc-roster page, as archived.** For the pre-2005 years
  this is often the only evidence there is, and it is direct: the caucus is
  printed with its members under it. It fixed a start for nine caucuses that
  had none — the Frente Cívico y Social de Catamarca and the Movimiento Popular
  Neuquino back to May 2000, Fuerza Republicana to April 2002, the Radical
  Independiente to August 2002 — and it brackets two formations to within three
  months: Falcó sits under the UCR in the capture of 15 Dec 2003 and under a
  Radical Rionegrino caucus in the next one, and Giustiniani moves out of "No
  Informado" into the Partido Socialista over the same gap.

* **The chamber naming the bloc in debate.** The strongest, because it is dated
  and unambiguous. The preparatory sitting of 27 Nov 2019 has Mayans proposing
  authorities "en nombre del bloque del Frente de Todos" for the term opening on
  10 December. The sitting of 12 May 2022 speaks of "dividiendo el bloque del
  Frente de Todos" and of "el nuevo bloque Unidad Ciudadana" — one sentence
  fixing the end of one caucus and the start of another. The sitting of 16 Nov
  2022 goes further and reads out the whole composition: Frente Nacional y
  Popular 21, UCR 18, Unidad Ciudadana 14 (Di Tullio), Frente PRO 9.
* **The mandate calendar.** Because the Senate keys a caucus to a mandate, a
  single-member caucus is bounded exactly by that member's term: Estenssoro's
  Coalición Cívica and Cabanchik's Proyecto Buenos Aires Federal both run
  10 Dec 2007 to 9 Dec 2013, and the roll-call readings match to the day.
* **The chamber's own roll of blocs.** On 16 Nov 2022 a senator reads the whole
  chamber into the record — Frente Nacional y Popular 21, UCR 18, Unidad
  Ciudadana 14, Frente PRO 9, Cambio Federal 4, "y los demás son monobloques".
  That dates several caucuses which are never named anywhere else, and it works
  in the negative too: any caucus of two or more absent from that roll did not
  exist that day, which is what places Unidad Federal, Convicción Federal, La
  Libertad Avanza and Provincias Unidas after it.
* **Neither.** Some caucus names cannot be searched for at all — "8 de octubre"
  matches the ordinary date, "San Luis" the province, "independencia" ordinary
  speech — and those rows say so and fall back on the mandate calendar.

Read together, the evidence also settled four things the raw data got wrong.
Unidad Ciudadana is **two** caucuses, not one: 2017–2019, absorbed into Frente
de Todos, then re-formed in May 2022 — a single span would have filed three
years of Frente de Todos speech under the wrong name. Frente de Todos ends as a
*bloc* in May 2022 while surviving as the name of the *interbloc* that holds
both halves, which is why the transcripts keep using it to 2024. And the
archived pages show the same two-lives shape twice more: the Movimiento Popular
Fueguino sat in 2000–2001 as well as 2013–2019, and a Liberal de Corrientes
caucus existed in 2002–2003 as well as 2009–2015. Each is now two rows.

**Seven caucuses still have no start date, and the file says what was looked
for.** Producción y Trabajo, Concertación Plural and Partido de la Victoria are
named in the corpus only as parties outside the chamber — the closest miss is
Basualdo saying "pertenezco a un partido que se denomina Producción y Trabajo",
which calls it a party, not a caucus. Federalismo Santafesino appears nowhere
at all, not even in the speeches of the senator the Senate attributes it to.
Puntano Independiente appears nowhere. Trabajo y Dignidad is named in debate in
February 2010, but by its second holder, so that dates her spell and not the
caucus. And Tucumán was searched for under seven phrasings without success: a
committee record of 8 Jul 2009 lists its senator among the "presidentes de
bloque", so she did head a caucus and the record simply never prints its name.
A blank here is the honest answer — an invented start would silence exactly the
misdated readings these dates exist to catch.

Where the chamber says what a caucus split off from, the stretch cut off the
front is handed to that predecessor — Unidad Ciudadana's and Frente Nacional y
Popular's members sat in the Frente de Todos bloc until it was divided, and the
chamber says so on the day. Where nothing is documented the stretch is dropped
rather than guessed, which is why **6.9% of floor words end up with no caucus**
and are left out of the caucus view entirely.

That loss is **not spread evenly**, and the figure says so per year. 2017 and
2018 keep about three quarters of their floor words, 2005 keeps 72%, while most
years keep over 98%. Almost all of the 2016–2019 hole is one thing: 392,000
words by the sixteen senators whose 2015–2021 mandate the Senate files under
Frente de Todos, a caucus formed in 2019. Thirteen of the sixteen were elected
on a Frente para la Victoria ticket and the other three on peronist provincial
ones, so they were certainly peronist — but three of them held monoblocs of
their own, so assigning them all to the peronist bloc would be a guess dressed
as a finding. They are left unplaced, and those years are to be read as resting
on less evidence rather than as movement.

The repair moves real numbers. The peronist share for 2016–2021 falls from
62–64% to 51–56% once the caucuses the Senate had carried backwards are cut to
the years they existed — the raw data had invented a bump.

One correction was tried and rejected: dating every caucus automatically by
when the chamber first names it. It recovers the distinctive names (La Libertad
Avanza lands on December 2023, correctly) but fails on names built from ordinary
words — "Frente de Todos" matches "frente de todos los argentinos", and its
earliest hits turn out to be the Chamber of *Deputies* bloc of the same name —
and only 33 of the 62 caucuses are ever named as such. Reading the matches by
hand is what separates those cases, which is why the table is hand-made.

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
pages* the way a careful reader does — but 36 pages is 0.08% of the 45,687 in
the corpus, drawn from 24 of 559 sittings. `scripts/audit_parse.py` covers the
rest by checking, on every session, things that must never happen. Current
results:

- **Page apparatus inside a speech turn: 1 occurrence** in 152,550 speech blocks (a
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
- **Other printed apparatus that reached the body text, all now 0**: the page
  dateline in a sitting whose font has no character map, where "Pág. 5" survives
  as little more than its accent and its digit and the strip that looks for the
  printed dateline cannot see it; the digital edition's link back to the contents
  page, glued onto the end of 255 turns; the footnote's own raised number, left
  stranded at the end of 469 turns once its text was cut; and 48 turns that
  carried no word at all, just a stray "." or "—" the style grouping left behind.
  Each is counted in its own column of `parse_stats.csv`, so the figures above
  can be recomputed from the run rather than taken on faith.
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
- **Blocks not findable in the source PDF: 0.422% on average**, 29 sessions above
  1%, the worst of them the 20 October 2004 file whose mis-mapped symbol font the
  parser deliberately repairs. This figure went UP as the parser improved, and
  the reason is worth stating plainly: where a footnote had been dropped into the
  middle of a sentence, removing it joins "…el proyecto de ley." to "Se
  comunicará…", which reads as printed but is no longer a literal stretch of the
  page. The check measures faithfulness to the character stream, and a repair is
  by definition a departure from it. The rest are turns that span a seam the
  parser makes on purpose: it merges a speaker's consecutive paragraphs and drops
  the section heading printed between them. Sessions with very few probed blocks
  (a short sitting in minority may have twenty) turn one miss into several
  percent.
- **Share of each document's printed text kept:** median 79.2%, quartiles 69%
  and 87%. The rest is dropped by design — contents pages, attendance rolls,
  appendices and inserted documents. The lowest figures are short sittings in
  minority that consist of little but a masthead and a roll.
- **Letter-spaced typography is read as separate words: 177 runs in 45
  sittings, 9 of them inside speech.** Where a page sets a phrase with wide
  spacing between its letters for emphasis — the printed page really does show
  "T e n e r  c a l i d a d" in the President's opening address of 1 March 2009 —
  the rule that restores the spaces the file never stored cannot tell that
  spacing from a space between words, and records each letter as its own word.
  The gaps sit just above the threshold (about 0.18 of the type size against a
  cut-off of 0.15, where a real printed space is 0.25 to 0.60), which is why the
  rule takes them. It inflates the word count by 2,852 words in 21.48 million,
  0.013%, and makes those phrases unfindable by any search. Ninety-seven runs are
  in headings and 71 in page matter; the nine inside speech are listed with their
  sitting, page and speaker in
  [reference/verification/letter_spacing_0423.csv](reference/verification/letter_spacing_0423.csv).
  Not repaired yet: the rule that would have to change inserts 710,040 spaces
  across the corpus, and it is not worth touching without its own verification
  pass. Found by a review asked to hunt for repairs justified by meaning rather
  than by the page.
- **Turns that do not begin or end the way speech does: 5 open mid-word under a
  new speaker**, and all 5 are printed that way — the record really does write
  "Sr. Presidente (Pinedo).- informo a la Cámara…". This check was added last and
  is the only one that looks at the FIRST and last characters of a turn rather
  than inside it, which is where every text fault found so far has lived. It
  began at 44 and the difference was faults of one family, all repaired in
  0.4.15–0.4.23 and described below. It also reports two counts kept as
  observations rather than faults: 71 turns of three characters or fewer (a
  senator answering "20." or the chair "E") and 131 that end on a dash or comma,
  most of them in the 2003 impeachment sittings, where a turn interrupted by a
  page break comes out as two rows instead of one.

### The name cut in half

The audit's shape check found what eight rounds of blind reading had not. A
label is printed "Sr. Presidente. – Se gira a la Comisión…" and the closing "e"
of "Presidente" is set in the roman face rather than the bold, so the style
grouping ends the label one letter early: the corpus recorded a speaker called
**"Sr. President"** and the turn opened "e. – Se gira…". The same happened to
real names — "Sra. Higone" for Higonet, "Sr. God" for Godoy, where the face
changes twice inside one surname and the name arrives in three pieces. Parser
0.4.15 takes the letters back, but only where the bold block reads as a label
and carries no terminator of its own, the block below opens in lower case, and
its terminator arrives within thirty characters: 14 names.

Two further faults surfaced with it, both larger than the first.

* **The terminator is a plain hyphen from about 2013 on.** The pattern that
  finds the ".—" closing a label accepted every kind of dash except the ordinary
  hyphen, and the later files write "Sr. Godoy.-". Every repair keyed on that
  pattern was therefore silently inert for a decade of sittings — including the
  one that separates a label from the speech bolted onto it by a bold run left
  open. Accepting the hyphen took that repair from 96 to **165** labels.
* **A sentence set a point larger was thrown away.** Blocks whose type size
  differs from the body's are page apparatus — footnotes, plates, attendance
  lists — and are dropped, but the typesetter sometimes sets the opening of a
  sentence a point larger than the rest, and it went with them: the "T" of
  "Tiene la palabra el señor senador Rodríguez Saá", and in the 31 July 2013
  sitting the chair's entire "Por favor, les pido si podemos mantener el s",
  leaving the turn to read "ilencio durante la exposición. Les agradezco." The
  evidence that the two belong together is that the break falls INSIDE a word —
  the block above ends on a letter, the block below opens on a lower-case one,
  and nothing that is really apparatus ends that way. **82 words** made whole
  again in 34 sittings.

### The note that was put in somebody's mouth

Chasing the same edge in the other direction turned up one more. Parser 0.4.12
gives a cut-off scrap back to the note it was cut from, but only a scrap: twelve
characters at most. Some tails are longer. The page prints "— Se practica la
votación por medios electrónicos."; the block ended after "la", and the rest was
filed as SPEECH, so the corpus had the chair saying "votación por medios
electrónicos" out loud. Another had him saying "nacional en el mástil del
recinto." — the tail of a note describing a senator raising the flag.

0.4.17 takes back a tail of any length where the note ends on a LETTER and the
tail opens in lower case, which is a sentence continuing and not how a turn
begins. The letter is what makes it safe: a note ending in "…" or ")" is one
interjected in the middle of somebody's sentence, and what follows really is
that person resuming — 28,308 complete notes and 1,529 unfinished ones followed
by speech in upper case are left untouched. **8 tails**, with no case where the
test was wrong.

One more of the same shape, found by eye and then measured. An italic run that
OPENS a turn — a newspaper's name printed right after the label, "Sr. Jefe de
Gabinete de Ministros. – *La Nación* es un diario opositor…" — was absorbed into
the turn above, so one senator's words were filed under another's name. Italics
inside a sentence do belong to the turn they interrupt, which is why they are
absorbed at all; the exception is the run whose next block belongs to somebody
else and continues in lower case, which shows the run opens that sentence rather
than closing the one before. **2 cases in the whole corpus** — worth repairing
because it is a wrong attribution, worth stating because the family is that
small.

The same edge also explains what a page break does NOT do. When an intervention
crosses to the next page, the running head stands between its halves and the
speech comes out as two rows — 1,503 of them. All are filed under one turn, so
nobody is misattributed: 919 break cleanly, 580 keep the space that separates
the words, and 4 want a space the file never stored. It looked like the largest
remaining fault and it is not a fault at all.

One thing this says about the blind reads is worth recording. Case 850 of the
seventh round had the parser answering "Sr. Presidente (Pinedo).- C" where the
reader had written "Sr. Presidente (Pinedo).-", and the comparison scored it as
agreement, because it compares the words of a label and ignores a stray
character. The reader was right and the parser was wrong, and the test could not
see it. Reading pages blind answers who is speaking; it does not police the
shape of what is recorded, and the two need separate checks.

### Fifty-three hundred pages read blind

Everything above is the parser checked against itself or against invariants. It
cannot answer the plainest question — is the right person behind the words? —
because a rule can be applied perfectly to the wrong speaker. So turns drawn
across the 25 years were read independently: each page was rendered as an image,
handed to a reader that was **never shown the parser's answer**, and asked only
which printed label governs the quoted words. The two answers were compared
afterwards, mechanically.

It has been done nine times, on nine samples that do not overlap. The first
eight were drawn turn by turn; the ninth, page by page.

* **300 turns.** Agreement on the speaker in **300 of 300**, no disagreement, the
  quoted words found on the page in all 300. Two could only be confirmed by
  position — the same stock words are spoken by two senators on one page, and
  what the reader could verify is that both labels are printed, in the order the
  parser records them.
  ([reference/verification/blind_read_300.csv](reference/verification/blind_read_300.csv))
* **500 further turns**, 20 per year, none of them among the first 300.
  Agreement on the speaker in **497 of 500**, and this time the reading was right
  first time: it exposed no parser defect at all. The three left over are all
  cases where the reader could not know which occurrence was meant, and all three
  were then checked by hand against the page image, where the parser proves right:
  in two, the quoted phrase is printed twice on the same page under two different
  labels, and the reader reported the first; in one, the reader gave a surname
  that appears nowhere on the page.
  ([reference/verification/blind_read_500.csv](reference/verification/blind_read_500.csv))
* **998 further turns**, 40 per year, none of them among the first 800. Agreement
  on the speaker in **993 of 998**, and again no parser defect. Of the five left
  over, checked by hand against the page afterwards, the parser proves right in
  all five: two are the repeated-phrase case again; in two the page prints
  "Sra. Presidente" and the reader wrote "Presidenta", adding an ending the
  edition does not use — those two sittings print the masculine form 154 and 145
  times; and in one the label stands on the very page supplied, which the reader
  mistook for a different page.
  ([reference/verification/blind_read_1000.csv](reference/verification/blind_read_1000.csv))
* **500 further turns**, 20 per year, none of them among the first 1,848, drawn
  after the corpus was re-parsed with the spaces restored — so this round reads
  parser 0.4.11's output rather than its predecessor's. Agreement on the speaker
  in **498 of 500**, no disagreement. The two left over are the repeated-phrase
  case once more, and both were checked by hand afterwards: page 61 of the
  28 Nov 2001 sitting prints "Pido la palabra." twice, under Sr. Ulloa and under
  Sr. Villaverde, and the parser records both turns, one under each; page 143 of
  the 29 Nov 2017 sitting does the same with "¿Quiénes se abstienen?".
  ([reference/verification/blind_read_500_0411.csv](reference/verification/blind_read_500_0411.csv))
* **1,000 further turns**, 40 per year, none of them among the first 2,348.
  Agreement on the speaker in **1,000 of 1,000** — the first round with no case
  left over at all, and none needing an after-the-fact check. Every one of the
  116 turns whose quoted phrase the page prints more than once agreed as well.
  ([reference/verification/blind_read_1000_0412.csv](reference/verification/blind_read_1000_0412.csv))
* **1,000 further turns**, 40 per year, none of them among the first 3,348, read
  after those three punctuation repairs. Agreement on the speaker in
  **998 of 1,000**, no disagreement, and **no parser defect of any kind** — the
  first round that turned up nothing at all to fix. The two left over are the
  repeated-phrase case: page 13 of the 12 Jul 2017 sitting prints "¿Por qué se
  cambió el orden?" four times under three different labels, and the parser
  records all four turns, one under each. This round the year 2000 could not
  fill its share of forty: its 96 locatable turns had all been read already, so
  the shortfall went to the years that had turns to spare.
  ([reference/verification/blind_read_1000_0413.csv](reference/verification/blind_read_1000_0413.csv))
* **1,000 further turns**, 40 per year, none of them among the first 4,348.
  Agreement on the speaker in **1,000 of 1,000** — the second round with nothing
  left over, and this time the largest sample yet in which every single case was
  settled by the blind read alone. All 128 turns whose quoted phrase the page
  prints more than once agreed as well. It did, however, find a defect in the
  text, described below. Two years could not fill their share of forty: the year
  2000 has no unread turn left at all, and 2002 yielded 12, so their shortfall
  went to the years with turns to spare.
  ([reference/verification/blind_read_1000_0413b.csv](reference/verification/blind_read_1000_0413b.csv))
* **115 further pages**, 5 per year, none of them among the first 5,298 and none
  on a page any earlier round had been given. Agreement on the speaker in
  **105 of 115**. Nine of the ten left over are of a kind the earlier rounds did
  not throw up: the reader was given the opening of a block that continues a
  speech begun pages earlier, so no label is printed anywhere on the page and the
  reader refused, rightly, to supply a name. All nine were checked afterwards —
  the parser's speaker is the one who opened that turn, and on the two longest
  runs the intervening pages were read to confirm no label was skipped in
  between. The tenth is a reader's own slip: the phrase is on the page, three
  labels down. The round found the spacing defect described below. Two years could fill
  nothing at all: 2000 has no unread turn left, and 2002 none on an unread page.
  ([reference/verification/blind_read_115_0418.csv](reference/verification/blind_read_115_0418.csv))

**The ninth round found the punctuation of a sentence standing on its own.** A
reader was given a turn whose recorded text read "…la salida del  default . Por
ese motivo…" and reported that the page prints "default." with nothing between
the word and the stop. It does. A word set in italics inside a sentence — a
foreign word, a newspaper's name, a Latin phrase — reaches the parser as a piece
of its own, because the change of face ends the piece before it; the comma or
full stop that closes the word is back in the body face, so it reaches the parser
as yet another piece. Every piece was being joined to the turn with a space,
which put a space on both sides of the italicised word. Parser 0.4.19 joins each
piece the way the page sets it — no space where the piece opens with punctuation
that never takes one, and none where the text already ends in one. Of the 4,653
marks that stood apart from their word (2,547 commas, 1,646 full stops, and the
rest colons, semicolons, question and exclamation marks and closing parentheses),
**3,618 were the parser's own doing and are now joined**. The 1,035 that remain
are the page's own spacing: an em dash closing a parenthetical, an ellipsis, an
apostrophe opening a decade ("los años ’90"), and the odd space the typist left
before a stop.

**0.4.20 finishes it, on both sides.** The review of that fix found it had been
written for the marks the example happened to contain. The closing quotation
mark, the apostrophe and the square bracket were left out, so the corpus still
read "Ministerio de Economía ”, el Dr." where the page prints no space; 138 of
those. And the rule only ever guarded the closing side, so a word set between
quotation marks came out spaced away from both of them — "caso " strawberry ","
for a page that prints "caso "strawberry","". The same test now runs against the
opening marks as well. Between them the two versions stop 3,785 marks of
punctuation being counted as words by anything that splits on spaces.

**Fourteen characters the fonts never declared are now readable.** Chasing one of
those quotations found 1,234 characters sitting in Unicode's private-use range,
where a glyph lands when the file uses a font whose encoding it never states.
They are not exotic: the WordPerfect-era sittings draw ordinary typography from
Symbol, SymbolMT, WordPerfect's MathA and Phonetic, and one sitting from a
private slot of Times New Roman, so the ordinal of "5° Reunión", the dash after
a speaker's label, the bullet of a printed list and even the "P" and the "g" of a
running head all arrived as codepoints with no meaning. Left in, they sat inside
words and sentences — "bloque unipersonal el bloque Misiones". 0.4.22 gives
thirteen of the fourteen the character its own page shows, settled by looking at
the printed page rather than by the font's nominal table, since these files use a
nominally Greek codepoint to print an ordinal.

**Where a page is itself broken, and what is done about it.** Reading these
codepoints turned up three sittings whose PAGE is wrong, not just whose file is —
checked by rendering the page at 600 dpi with two independent renderers. The rule
that came out of it has three cases, and the third was learnt the hard way.

*The glyph is clear: transcribe it.* That is almost all of them.

*The page is broken but every occurrence means the same thing: reconstruct it,
and say so here.* Two sittings, of 2004 and 2007, print "59E aniversario" and
"Acta NE 5", because the ordinal is drawn from a font that puts a capital E where
another font puts the ring. All 100 occurrences are ordinals, so the corpus
writes the ordinal. A third sitting, of 20 October 2004, prints its dashes and
quotation marks as the letters C, A and @ — "Sra. Avelín. C ...porque hay un
fiscal" is what is on the paper — because a font used for nothing but punctuation
carries a broken character map. The corpus writes the dash, because otherwise a
speaker's name cannot be told from their words and the sitting loses its speakers
altogether. Both are reconstructions of a broken document, not transcriptions of
it, and reading them literally does more damage than the fault: read as a letter,
the E splits the notes it sits in and invents twenty-five turns nobody spoke.

*The page is broken and the occurrences mean different things: transcribe it,
because no reconstruction can be right.* One codepoint is drawn as an underscore
and stands for a different character in each of the two sittings that use it:
"192_aniversario" wants an ordinal, and "¡Sí, juro_" — five of the twenty-three
senators sworn in on 26 November 2009, the other eighteen printing normally —
wants an exclamation mark. It is recorded as the underscore it prints. This was
caught in review, by rendering the page and looking at it, after 0.4.21 had read
the codepoint as an ordinal from its context alone and put a degree sign into
those five oaths. The same fault turned up a second time in the repair that reads
the broken punctuation font: it was turning the raised reference number of a
footnote into an ordinal in two other sittings, because the number and the
ordinal are the same character there. They are set at different sizes, and 0.4.23
makes the substitution only at body size.

Nothing in the range is mapped on faith, and the weaker readings say so. Nine
rest on dozens to hundreds of occurrences. Five are thin, and each was read off
its printed page: the ellipsis that ends a trailing-off turn (8 occurrences in
two sittings); a parenthetical dash drawn from a private slot of Times New Roman
(9, one sitting); the underscore described above (10, two sittings); a hard
space WordPerfect draws as a raised dot, "son las reglas·del juego" (once);
and the one character the parser removes instead of
translating — a Symbol codepoint that prints an upside-down A in the middle of
"categoría", once, in the sitting of 20 October 2004, where keeping it would
break the word for every reader. Two of the fourteen, the "P" and the "g", never
reach the text at all: they appear only in the running head, and are read so that
the header strip can recognise a running head as one. A scan of all 559 source
PDFs closes the list — 2,676 occurrences of exactly these fourteen codepoints and
no others, of which 1,234 reached the text. The other 1,442 sit in matter the
parser drops or absorbs before it writes anything: 1,136 of them in the running
head, 137 in the label dash itself, which is consumed when a speaker's label is
split from the words after it, and 169 elsewhere. Anything not on the list is
still treated as unmapped
([reference/verification/unmapped_glyphs_0422.csv](reference/verification/unmapped_glyphs_0422.csv),
one row per codepoint with its font, its count and a line of its printed context).

Restoring the label dash lets the existing repairs see labels they had been blind
to. The whole of the change is 13 places in two sittings. Fifteen lines of page
matter the parser could not read before — a dateline, a page number — are now
legible as page matter and dropped. In ten of those places the dropped line had
been splitting a senator's turn in two, so 22 half-turns rejoin into 10; the other
three drop a line and join nothing. That is where the corpus loses 12 speech
blocks and 27 rows. All 13 places carry the same speaker, the same turn number
and the same words on both sides, listed case by case with their pages in
[reference/verification/glyph_map_diff_0421.csv](reference/verification/glyph_map_diff_0421.csv).
No block, turn number or speaker changes anywhere else; 48 further sittings have
single characters translated inside ordinary speech, which is what the table is
for, and 508 are unchanged to the character. Verified after re-parsing:
gold F1 1.00 (124/125),
annotations 36/36, 5 turns opening mid-word, and no private-use character left
anywhere in the corpus.

**The eighth round found a word broken in half.** One reader was given a turn
whose recorded text began "i la Argentina debe ser tomada en su totalidad?" and
reported that the page shows the running head cutting through the paragraph. The
page in fact prints "…de allí trasladarnos a otra parte del país (aplausos), si
la Argentina debe ser tomada en su totalidad?" — the note is interjected in the
middle of the sentence, and in a few files the italic run it is set in carries
one or two characters past the closing parenthesis. The note came out as
"(aplausos), s" and the sentence resumed at "i la Argentina", a word split in
two. Parser 0.4.14 gives the tail back to the speaker: 5,191 parenthesised notes
end cleanly; 5 held letters the sentence continues, and 70 held a comma,
semicolon or dash closing the clause the note interrupted. A colon does not
count as a tail — 13 notes end in one, and there it is the note's own,
introducing the matter quoted below. 75 turns changed in 41 sittings.

**The sixth round found three defects, because agreeing on the speaker is not
the same as agreeing on the text.** Readers are asked to say whether anything
that is not speech appears inside the paragraph they are reading, and 24 of the
1,000 said yes. Most were footnote markers and stage directions that sit on the
printed page but never entered the output. Three were real, and all three are the
same kind of mistake: a mark of punctuation belonging to the editorial matter
around a turn, stored on the wrong side of the boundary and kept as if it were
part of what someone said. Parser 0.4.13 gives each back:

* **The dash that introduces a note stayed on the turn above it.** A note is
  printed "— Se vota."; in many files that dash is stored at the end of the line
  before it, so the turn it follows appeared to end on a dangling dash. The dash
  is stored where it belongs 17,912 times and left behind 9,025 — one note in
  three — and in only 8 of those does the note carry a dash of its own, which is
  what shows the stray one is the same dash rather than a second.
* **The colon that closes a note opened the next turn.** "…cuyos textos se
  incluyen en el Apéndice, son los siguientes:" lost its colon to the block
  below, which then began ": Denominación de un puente carretero…". Taken back
  only where the note stops mid-phrase with no closing punctuation of its own:
  29 cases. Where the note is already complete — "(Risas.)" followed by a turn
  that starts with a colon — the colon is left alone, because nothing there
  shows it is not part of what follows. That leaves 17 such cases untouched, on
  purpose.
* **A section's number was left on the turn above it, and the section was
  lost.** In some sittings the number is set in the body face rather than the
  bold of its title, so the style grouping ends the block at the number: the
  turn above ends "…todos los asuntos. 5." and the title "Renuncia presentada
  por el señor senador Claudio Javier Poggi" is left with no number, which means
  it is not read as a section at all and everything under it stays filed under
  section 4. The number is taken back only onto a title of four words or more
  that is not a speaker's label, and only where it continues the section count.
  26 sections were recovered, and one more sitting now carries sections: 530.

The fifth round had found a fourth defect of the same family, fixed before this
one was drawn. One case sent the reader a "turn" whose whole text was "E 13",
and the reader answered that this is not speech at all: it is the tail of the
note "El resultado de la votación surge del Acta N° 13", cut off because the
degree sign comes from another font, and left as a two-character turn credited
to whoever had spoken last. Parser 0.4.12 gives such a scrap back to the note it
was cut from, but only where the note stops mid-phrase AND the scrap cannot be
read as speech — nothing but an ordinal marker and its number, or a fragment
opening in lower case. That matters, because the same position also holds
genuine short turns: of the 102 blocks that follow an unfinished note, 81 are
scraps ("E", "E 13", "z.", "of Mostyn.", "9 y 20:") and the rest are real speech
("Ausente.", "Gracias.", "¡Rojo!"), which the rule leaves alone. Every scrap it
joins is listed in the session's log, so the judgement can be re-read rather
than trusted.

Those after-the-fact checks were made by looking at the page, so they are **not**
blind, and they are kept out of the agreement counts rather than folded into
them. Each is recorded in its file's own column so the reasoning can be
re-examined.

The repeated-phrase problem is measured rather than argued about: for each
sampled turn, the quoted phrase is counted in the page's printed text. It appears
more than once in 60 of the first 500, 139 of the 998, 58 of the 500 after that,
116 and 126 of the two 1,000-turn rounds after those, and **128 of the latest
1,000** — the chamber's stock
formulas recur — and in all but two of each round the reader still landed on the
parser's answer, because every occurrence belongs to the same speaker. The count
is taken from the PDF precisely because the reader's own judgement is not
reliable here: in one case a reader stated the phrase appeared only once on a
page that prints it twice.

Reaching the first 300 took four rounds, and every disagreement along the way was
the parser's fault, not the reader's. Between them they exposed the title that
swallows the label after it (55 turns credited to the wrong person), the
appendix-pointer footnote read as speech (1,149 turns), the page dateline set in
glyphs the font cannot map, the contents-page link glued onto the end of a turn,
and the footnote's raised number left stranded once its text was cut. None of
these could have been found by re-reading the 36 annotated pages. The 500 and the
998 that followed found nothing further — 1,498 pages drawn with nothing to
report — the 500 read after the space fix turned up the cut-off note above, the
1,000 after that agreed on every speaker while still turning up three pieces of
editorial punctuation kept as speech, the 1,000 after that turned up nothing at
all, the 1,000 after that turned up the broken word above, and the 115 read page
by page turned up the spacing defect above.

That is the point of running it again, and the two things it measures have come
apart. **Who is speaking is settled**: 5,463 turns read blind across nine
rounds, agreement in all but twenty-two, and every one of those twenty-two
resolved in the parser's favour by hand — pages that print the quoted phrase more
than once, and pages that print no label at all because the speech began earlier.
The ninth round is the first drawn page by page rather than turn by turn, which
is why that second kind appears in it and in none before. **What the turn says is still being corrected**,
in smaller and smaller pieces — a dash, a colon, a section number, and now two
letters — found only because readers are asked to report anything on the page
that is not speech, and to answer even when the speaker is not in doubt. All 27
reports of apparatus in the latest round were checked against the output and all
27 had stayed on the page where they belong. The broken word came to light a
different way: the phrase the reader was asked to find began "i la Argentina",
and no page prints that. What each round tests is not only the reader's answer
but the question put to them.

Two things the seventh round confirmed rather than corrected are worth recording,
because both look like errors and are not. A page of May 2010 interleaves
"(Aplausos)" between the items of a list a senator is reading out, so her turn
comes out as fragments each opening with a comma — which is what the page shows.
And a page of October 2022 misspells a surname as "Sr. Rodíguez Saá", missing an
r, which the parser copies as printed and the resolver still matches to the right
person.

Four things about the method are worth stating, because all four were wrong at
first and each produced false disagreements rather than hiding real ones:

* **The sheet has to say where the turn opens**, and the reader has to be given
  every page from there. A turn can begin many pages before the words quoted from
  it — a president addressing the Legislative Assembly speaks for twenty pages
  without the label being reprinted — and a reader given only the quoted page
  finds no speaker at all and cannot answer. Six early "disagreements" in the
  first round were this; capping the supplied pages at three back reproduced the
  same six in the second.
* **The sample must not be drawn by row number.** Each turn is now selected on a
  hash of its own content, so a parser change that adds or removes unrelated
  rows no longer redraws the whole sheet and throws away the reading already
  done on it. Under the old row-number draw, one fix moved 279 of 300 rows;
  under the new one, the same kind of fix moved 1.
* **A phrase that repeats on its page cannot be scored.** The reader is asked to
  find words and report the label above them; when the same words are printed
  twice under different labels, nothing on the page says which was meant. Those
  are now counted from the PDF and reported apart, instead of being charged to
  the parser or waved through on the reader's say-so.
* **A reader will tidy the record without noticing.** Asked to transcribe a label
  exactly, two readers wrote "Sra. Presidenta" where the page prints "Sra.
  Presidente" — the grammatical agreement the edition itself does not make. Every
  disagreement therefore has to be settled against the page image, never against
  which of the two answers reads better.

What this is not: an independent *human* audit. It is a second machine reading,
independent of the parser's code path — it works from the rendered page, not from
the PDF's character stream — but still a machine's reading. A shared misreading
of what a page means remains possible, and the review sheet is regenerated for a
human pass whenever `--sample N` is passed. What eighteen hundred pages do settle
is the size of the doubt: with no confirmed error, the share of turns credited to
the wrong person is under 0.2%.

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

### Words that used to run together at line joins (fixed in 0.4.11)

The parser reads characters in the order the file stores them, which is
faithful to what was typeset but carries no line breaks. The 2003–2009 files
end a line without storing a space, so the last word of one line and the first
of the next came out joined — "reemplazala expresión", "yplenipotenciario". It
never affected who was credited with the words, but it broke them into the
wrong tokens, and every word count was low.

Parser 0.4.11 puts the space back wherever the page shows one: a new line, a
new column, a new page, or a gap inside a line wide enough that only a space
explains it. "Wide enough" is measured, not guessed. On the files that DO print
their spaces, two letters of the same word are never more than 0.07 of the type
size apart (110,744 pairs measured, widest 0.071) while a printed space is 0.25
to 0.60 wide, so the threshold sits at 0.15 with clear air on both sides. A
line ending in a hyphen is left joined, because there the two halves belong
together — either a word broken across the line or a file number like
"P.E.-86/16".

That restored **710,039 spaces in 481 of the 559 sittings** and raised the
corpus from 21.07 to 21.48 million words (+2.0%): +4% to +6.5% in every year
from 2003 to 2009, and under 0.1% everywhere else, which is the shape the
defect had. Checked against pdfplumber's own layout-aware page reading over a
sample of pages, words that exist in the parser's output but not in the page's
own reading fell from 3.0% to 0.06%. Nothing that had already been verified
moved: the gold set scores exactly as before (F1 = 1.00 on 124 of 125 turns),
the audit is unchanged on every invariant, and all 1,848 answers recorded in
the four blind reads still stand in the new parse, checked row by row.

Two things followed from it, both checked. **Section numbering now works for
2003–2009**: those sittings number their sections without a full stop ("2
Izamiento de la bandera"), which was unreadable while the number was glued to
the title, so 87 more sittings (443 → 529) now carry the section each turn
belongs to. And because a bill number left at the head of a line has exactly
the same shape ("Orden del Día N° / 522 Obras de los bajos…"), the parser now
tells them apart by counting: sections run 1, 2, 3 in order, so a dotless
number opens a section only where it carries the count forward — within three
of the section before it, or up to ten to open the sitting. Bill numbers run in
the hundreds and never qualify. In the later files, which number with a full
stop and cannot be confused, the next section is the previous one plus one in
284 of 290 cases, which is what the rule rests on. One sitting of November 2001
— a scan — numbers too erratically to be followed and now carries no sections
at all.

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
