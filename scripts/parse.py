"""Parse Argentine Senate stenographic transcript PDFs (versiones
taquigraficas) into per-session block tables.

v0.3.0 pipeline (empirically recalibrated against the stratified profile of
the corpus — see git history for the v0.2.0 heuristics it replaces):

1. Extract characters with pdfplumber (text, font, size, page, y-position),
   putting back the spaces the file never stored: the 2003-2009 formats end
   a line without one, so the words either side of a line join used to come
   out glued together (space_is_missing) — except where the page has spaced
   a word's own letters apart for emphasis, which measures the same and is
   not a space (letter_spacing_gaps).
2. Strip page headers POSITIONALLY: every page format 2020-2024 carries a
   dateline containing "Pág. N" near the top (even the 2024 ArialNarrow
   variant); all characters at or above that line are furniture.
3. Classify font style from the subset-prefix-stripped family name.
4. Calibrate body size per document (modal size of normal-style chars —
   12.0 in every format sampled, but computed, not assumed).
5. Group characters into blocks on (font family, style, size) change —
   family in the key stops Times-Roman headings fusing with Helvetica
   speaker labels.
6. Cut front matter at the first opening event (dash-initial italic at
   body size) or first speaker label; fall back to the old bold "1."
   sumario marker. The 2024 "ÍNDICE" format has no bold marker at all.
7. Classify blocks: furniture (non-body sizes: appendix, footnotes,
   attendance lists), events (italic body-size, dash-initial or
   parenthesized or event-verb) with subtypes, inline italics (merged
   back into the surrounding speech instead of splitting turns),
   chapter headings, speaker labels (GATED on ^Sr./Sra. — other bold
   blocks become typed headings and reset the speaker instead of
   becoming phantom speakers), speech, and unattributed "other".
8. Consolidate consecutive same-speaker speech into turns; events and
   headings break turns, inline italics are absorbed.

Output per session: data/processed/senado/blocks/{session_id}.parquet,
a log under logs/, and a merged parse_stats.csv row.

Heuristics are calibrated against pdfplumber 0.11.5 (see pyproject.toml).
"""

import argparse
import contextlib
import hashlib
import json
import re
import sys
import time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pdfplumber

PARSER_VERSION = "0.4.30"

REPO_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = REPO_ROOT / "data" / "raw" / "senado" / "taquigraficas"
OUT_DIR = REPO_ROOT / "data" / "processed" / "senado"
MANIFEST_PATH = REPO_ROOT / "raw_data_manifest.csv"

SUBSET_RE = re.compile(r"^[A-Z]{6}\+")          # PDF font-subset prefixes: ABCDEF+ArialMT
PAG_LINE_RE = re.compile(r"Pág\.\s*\d+")         # page-header dateline invariant
SPEAKER_RE = re.compile(
    r"^(?:(?:Sr|Sra|Srta|Sres)\.\s"                             # Sr. Mayans / Sra. Presidenta (…)
    r"|(?:Varios señores|Varias señoras|Un señor|Una señora) senador)"  # anonymous/collective speakers
)
# "1. Título" (2014+) or dotless "1 TÍTULO" (2000–2013 layouts)
CHAPTER_RE = re.compile(r"^\d+(?:\.\s?\S|\s+[A-ZÁÉÍÓÚÜÑ])")
EVENT_DASH_RE = re.compile(r"^[–—−-]")
# Some sittings draw the dash from a symbol font with no Unicode mapping, so
# it extracts as a private-use codepoint. No claim is made about what such a
# codepoint means elsewhere in the text — only that, printed between a
# speaker's name and their words, it is the label's terminator.
PUA = r"-"

# Fourteen of those codepoints are not a mystery: they are ordinary characters
# drawn from Symbol, SymbolMT, WordPerfect's MathA and Phonetic, and one private
# slot of Times New Roman, whose encodings the file never declares. A scan of all
# 559 source PDFs finds exactly these fourteen and no others — 2,676 occurrences,
# of which 1,234 reach the text. The rest are in matter the parser drops or
# absorbs before writing anything: chiefly the running head, and the label dash
# itself, which is consumed when a speaker's label is split from their words.
# Each is settled by what its own page shows rather than by the font's nominal
# table: the WordPerfect-era files use these fonts for ordinary typography, so
# a codepoint that is nominally a Greek letter prints as an ordinal. Left in,
# they land inside words and sentences: "5 Reunion",
# "59 aniversario", "bloque unipersonal el bloque Misiones".
# Anything else in the range is still left alone and still treated as unmapped.
GLYPH_MEANING = {
    "\uf0b0": "\u00b0",   # Symbol B0, the ordinal: "5° Reunión", "1° de enero"
    "\uf045": "\u00b0",   # 45, the same ordinal, from two fonts that draw it
                          # differently: MathA prints the ring ("N° 2"), Symbol
                          # prints a capital E, so two sittings of 2004 and 2007
                          # show "59E aniversario" and "Acta NE 5" on the page.
                          # Reconstructed rather than transcribed, because every
                          # one of the 100 occurrences is an ordinal; reading the
                          # E as an E splits the notes it sits in and invents
                          # turns nobody spoke. Declared in SOURCES.md.
    "\uf05f": "_",        # Symbol 5F, which the page draws as an underscore
                          # and which stands for a different character in each of
                          # its two sittings: "192_aniversario" wants an ordinal,
                          # "¡Sí, juro_" wants an exclamation mark. Read as the
                          # underscore it prints, because no single substitution
                          # is right in both places and the page is the record.
                          # 10 occurrences, 2008 and 2009
    "\uf02d": "\u2013",   # Symbol 2D, the dash that opens a parenthetical
    "\uf8e7": "\u2014",   # SymbolMT F8E7, the dash after a speaker's label
    "\ue83a": "\u2014",   # a private slot of Times New Roman: a parenthetical
                          # dash, 9 occurrences in the sitting of 15 Dec 2010
    "\uf0bc": "\u2026",   # Symbol BC, the ellipsis ending a trailing-off turn.
                          # Thin evidence: 8 occurrences over two sittings
    "\uf0b7": "\u2022",   # Symbol B7, the bullet of a printed list
    "\uf02e": ".",        # Symbol 2E, the stop of "Pág. 5" in the running head
                          # of thirteen sittings, 2002-2009
    "\uf020": " ",        # Symbol 20, the space beside it, in those thirteen and
                          # one more where WordPerfect's Phonetic font draws it
    "\uf041": " ",        # MathA 41, drawn as a raised dot — WordPerfect's own
                          # mark for a hard space: "son las reglas·del juego".
                          # One occurrence, read off its page (26 Mar 2009)
    "\uf022": "",         # Symbol 22, drawn as an upside-down A in the middle of
                          # "categorí∀a" (20 Oct 2004). The only one dropped
                          # instead of translated: it is the page's own accident,
                          # and keeping it breaks the word for every reader
    "\uf050": "P",        # Symbol 50 and 67, the two letters five sittings of
    "\uf067": "g",        # 2002-2005 draw from the symbol font in "Pág.".
                          # Neither ever reaches the text: reading them is what
                          # lets the header strip see a running head as one
}


# The other half of the same fault. Where a font declares no mapping at all,
# the extraction hands back the literal token "(cid:47)" instead of a
# codepoint, so these never went through the map above and stayed in the text.
# They are worse than ugly: the token carries the name of ITS font, which is
# never the bold of the heading it sits in, so a section title breaks in two
# around it and the half after the break is read as a bill number and dropped —
# "10 Orden del Día N" for a page that prints "10 Orden del Día N° 248 Día
# Internacional de la Juventud". 8,523 rows of 64 sittings carried a title cut
# off that way.
#
# Every reading below was taken from the printed page at 600 dpi, one
# occurrence of each rendered and looked at, and every one that came out blank
# or boxed was rendered a second time with an independent renderer before being
# decided. Keyed on the font by name, because the same number means different
# things in different fonts.
CID_MEANING = {
    # the ordinal ring: "1° de marzo", "13° Reunión", "artículo 4°", "Ley N°
    # 26.075". 1,249 occurrences, 2003-2008, and the whole of the cut-title
    # fault
    ("WPMultinationalARoman", 47): "°",
    ("WPMultinationalARoman,Italic", 47): "°",
    ("WPMultinationalAHelve", 47): "°",
    ("WPMultinationalAHelve,Italic", 47): "°",
    ("Symbol", 176): "°",
    # the apostrophe: "años'30", "Moliné O'Connor". 155 occurrences. The page
    # draws the straight tick this typeface uses for it, and the rest of the
    # corpus spells that name the same way 296 times
    ("WPMultinationalARoman", 39): "'",
    ("WPMultinationalARoman,Italic", 39): "'",
    ("WPMultinationalAHelve", 39): "'",
    ("WPMultinationalAHelve,Italic", 39): "'",
    # the bullet of a printed list, round in one font and square in the other
    ("Symbol", 183): "•",
    ("WPMathA", 67): "•",
    ("Wingdings", 167): "▪",
    ("Wingdings-Regular", 131): "▪",
    # the tick of the cover-page form that says what kind of sitting it was:
    # "Secreta -- Pública ✓ Ej. de Acuerdos". One sitting of 2006 also uses it
    # as a list bullet
    ("Wingdings-Regular", 57): "✓",
    ("Wingdings", 252): "✓",
    # the tab of the two 2001 sittings that are scans, standing between the
    # running head and what is printed to its right. Nothing is drawn and the
    # character has no width; what it does is separate, so it is read as the
    # space it separates with. 366 occurrences, both of them scans
    ("Times-Roman", 9): " ",
    ("Times-Bold", 9): " ",
    ("Times-Italic", 9): " ",
    ("Helvetica", 9): " ",
    ("Helvetica-Oblique", 9): " ",
    # dropped, not translated: the file has no glyph to draw. Two renderers
    # print the empty box of a missing character ("artículo 3□ de la Ley",
    # "1□ Congreso"), or nothing at all — the 2014 one has no width either.
    # What the page itself fails to print is not a character this corpus can
    # supply
    ("TimesNewRoman", 31): "",
    ("WPTypographicSymbols", 31): "",
    ("TimesNewRoman", 16): "",
    ("Calibri", 2): "",
}
CID_NUM_RE = re.compile(r"^\(cid:(\d+)\)$")


# The third face of the same fault, and the one that reached the spoken word.
# These WordPerfect fonts DO declare a mapping — it is simply the wrong one, so
# the extraction hands back a plain, legible, incorrect letter and nothing
# downstream can tell it is wrong. The corpus carried "el artículo 1E del
# proyecto", "la Ley N1 25.673", "en llamar Aprotocolo facultativo@", ")Qué
# trató el Congreso" — 3,600 characters of it, inside 144 sittings of debate.
#
# Every reading was checked against the printed page at 500 dpi. Two different
# situations, both kept here and told apart in SOURCES.md:
#
#   The typographic-symbol font is drawn CORRECTLY on the page — it really
#   prints the quotation marks, the inverted question mark, the dash — so
#   reading it is recovering what the page shows, nothing more.
#
#   WP-MathA is NOT. The page itself prints "artículo 1E", the capital E is on
#   the paper, and every one of its 3,229 occurrences stands where an ordinal
#   belongs. Putting the ordinal back is reconstructing a document broken in
#   print, the same decision this parser already made for the 2004 Courier
#   file, and it is declared as such rather than passed off as transcription.
SYMBOL_FONT_LETTERS = {
    ("WPMathA", "E"): "\u00b0",          # "artículo 1E" for "artículo 1°"
    ("WPTypographicSymbols", "A"): "\u201c",   # opening quotation
    ("WPTypographicSymbols", "@"): "\u201d",   # closing quotation
    ("WPTypographicSymbols", ")"): "\u00bf",   # inverted question mark
    ("WPTypographicSymbols", "1"): "\u00ba",   # the ordinal of "Ley Nº 25.673"
    ("WPTypographicSymbols", "0"): "\u00aa",   # its feminine, "la 28ª sesión"
    ("WPTypographicSymbols", "B"): "\u2013",   # "Un alumno – un profesor"
    ("WPTypographicSymbols", "S"): "\u2013",   # the dash opening a listed item
    ("WPTypographicSymbols", "C"): "\u2014",   # the dash of a speaker's label
    ("WPTypographicSymbols", "("): "\u00a1",   # inverted exclamation mark
    ("WPTypographicSymbols", "Y"): "\u2026",   # the ellipsis of a trailing quotation
    ("WPTypographicSymbols", "="): "\u2019",   # the apostrophe of "del '80"
    ("WingdingsRegular", "!"): "\u25aa",      # the square bullet of a list
    ("WPTypographicSymbols", "<"): "\u2018",   # opening single quotation
    ("WPTypographicSymbols", ">"): "\u2019",   # its closing half
}
# the same font is named four ways across the files — with a hyphen, with a
# space, without either, and its italic under a name of its own — and none of
# that changes what it draws
SYMBOL_FONT_ALIAS = re.compile(r"[\s-]|,(?:Italic|Bold|BoldItalic|Oblique)$")



# 2000–2013 layouts split the chair label across styles:
#   bold "Sr. Presidente" + normal "(Pampuro)" + bold ". –"
# The shards need reassembly (identify_speakers) instead of the bold
# punctuation becoming a heading that resets the running speaker.
BOLD_JUNK_RE = re.compile(r'^[\s.:;,\-–—−…"“”«»ºª°()]+$')
PAREN_ONLY_RE = re.compile(r"^\([^()]{1,60}\)$")
# "(Estrada). — Por Secretaría…": the parenthetical belongs to the label,
# the terminator is punctuation, and only what follows is speech.
# The chair's surname opens the roman run that follows the bold "Sr. Presidente",
# sometimes behind the label's own period — ". (Gioja). — Indudablemente…". Leave
# that period in place and the surname stays in the speech, so the page names the
# chair and the record still says the person is unstated.
PAREN_HEAD_RE = re.compile(r"^[\s.]*(\([^()]{1,60}\))\s*\.?\s*[–—−-]?\s*")
# a turn's first words are printed after the label's ". —" terminator
TURN_LEAD_RE = re.compile(rf"^\s*\.?\s*[–—−\-{PUA}]\s*")
LABEL_CLOSED_RE = re.compile(r"[–—−(]")  # label already carries its own paren/terminator
# A numbered section title and the label of whoever speaks under it are set in
# the same bold run, and the space between them is often the one the PDF drops
# at a line join ("…bandera nacionalSr. Presidente"). Cut on either, and cap
# the tail so a title that merely names a person cannot be mistaken for one.
LABEL_SPLIT_RE = re.compile(r"\s?(?=(?:Sr|Sra|Srta|Sres)\.\s)")  # fused "TÍTULO Sr. X" headings
MAX_LABEL_TAIL = 70
# 2006-2009 files drop the space at line joins ("…Fiscalía N°3Sr. Presidente"),
# so the label can be glued straight onto the heading with no separator.
FUSED_LABEL_RE = re.compile(r"\s?(?=(?:Sr|Sra|Srta|Sres)\.\s)")
LABEL_FRAGMENT_RE = re.compile(r"^[.\s]*(?:Sr|Sra|Srta|Sres)$")  # shattered label: reset, not heading
# a heading that ends on the opening word of a label — the line broke there
LABEL_OPENER_TAIL_RE = re.compile(r"(?:^|\s)(?:Sr|Sra|Srta|Sres)\.$")
LEAD_JUNK_RE = re.compile(r'^[\s.:;,\-–—−…"“”«»]+')  # bold-glued tail of the previous sentence
PAREN_LABEL_RE = re.compile(r"^\(([^()]{1,60})\)[\s.\-–—−:]*$")  # bare "(Rojkés de Alperovich).-" chair label
DGT_RE = re.compile(r"^Dirección General de Taquígrafos\b")
# The footnote that points at the appendix is printed at body size, below the
# rule at the foot of the page, so neither the size test nor the positional
# footer strip catches it and it reads as something a senator said. Its own
# raised marker sometimes comes along. Position cannot separate a footnote from
# speech here — a superscript reference can start a line too — so this is keyed
# on the wording, which is boilerplate.
# Capitalised as printed. It carries no content of its own — it says only "see
# the appendix" — so it is cut like a header or footer rather than kept as a row.
FOOTNOTE_TEXT_RE = re.compile(r"\s*(?:\d{1,3}\s*)?Ver el Ap[eé]ndice\.?\s*")
# the digital edition's link back to the contents page, printed after a turn
SUMARIO_RE = re.compile(r"\s*\[\s*Volver al sumario\s*\]\s*", re.I)
# characters from a font with no Unicode map land in the private-use area
CID_UNMAPPED_RE = re.compile(r"[-]")
# what is left of the "Pág. N" dateline once the unmapped letters are dropped
PAGENUM_ONLY_RE = re.compile(r"^\s*[áa]?\s*\d{1,4}\s*$")
WORD_CHAR_RE = re.compile(r"[0-9A-Za-zÁÉÍÓÚÜÑáéíóúüñ]")
# the footnote's raised marker, or the number of the next section heading, left
# stranded at the very end of a turn. A number somebody actually spoke is inside
# the sentence, before its full stop, so it cannot match.
TRAILING_MARKER_RE = re.compile(r"([.!?])\s*\d{1,3}\s*$")
CID_RE = re.compile(r"\(cid:\d+\)")  # glyphs the PDF font maps to nothing
# A speaker label ends at ". —"; anything printed after it is already the
# first words of the turn, bolded by accident ("Sr. Mayans. – ¡").
# The terminator is a dash of some kind, and from about 2013 the files set it
# as a plain hyphen ("Sr. Godoy.-") rather than the en or em dash the earlier
# ones use. Leaving the hyphen out meant every repair keyed on this pattern was
# silently inert for a decade of sittings.
LABEL_TERM_RE = re.compile(rf"\.\s*[–—−─\-{PUA}]\s*")
# A complete printed label — title, name, terminator — found inside a roman
# paragraph, where the typesetter forgot to set it in bold.
INLINE_LABEL_RE = re.compile(
    rf"(?:Sr|Sra|Srta)\.\s*[A-ZÁÉÍÓÚÑ][^.]{{1,45}}?\s*\.\s*[–—−─{PUA}]\s"
)
SENTENCE_END = set('.!?:"”’\')]')
COURIER_RE = re.compile(r"courier", re.I)

# Ordered: first match wins. Applied lowercased.
EVENT_SUBTYPES = [
    ("timestamp", re.compile(r"^[–—-]?\s*(?:a las|son las)\s+\d"
                             r"|^[–—-]?\s*en (?:la ciudad aut|buenos aires)")),
    ("vote", re.compile(r"votaci[oó]n|se vota|resulta[n]?\s+(?:aprobad|rechazad)|afirmativ|negativ|unanimidad|asentimiento")),
    ("pause", re.compile(r"luego de (?:unos )?instantes|cuarto intermedio|se reanuda")),
    ("applause", re.compile(r"aplausos")),
    ("laughter", re.compile(r"risas")),
    # Disorder in the chamber, however the stenographer words it. Senators
    # talking over each other is the commonest form by far and used to fall
    # through untyped, which undercounted every incident rate; the remote
    # sittings of 2020-2021 add their own kind of disorder, a connection
    # that drops out mid-speech.
    ("incident", re.compile(r"manifestaciones|interrupci|abucheo|cánticos|murmullos"
                            r"|contenido no inteligible|fuera del alcance del micrófono"
                            r"|hablan a la vez|dialogan|interferencias"
                            r"|no se alcanza[n]? a (?:percibir|o[ií]r|escuchar)"
                            r"|se interrumpe la (?:transmisi|conexi)")),
    ("stage", re.compile(r"ocupa la presidencia|ingresa|se retira|izamiento|entonaci|himno"
                         r"|arrían|puestos de pie")),
]

STATS_COLUMNS = [
    "session_id",
    "file_name",
    "characters_extracted",
    "scanned_page_share",
    "header_chars_removed",
    "footer_chars_removed",
    "body_size",
    "blocks_generated",
    "micro_islands_merged",
    "marker_mode",
    "blocks_after_marker",
    "empty_blocks_removed",
    "chapters_detected",
    "title_labels_cut",
    "fused_labels_split",
    "inline_labels_recovered",
    "split_words_rejoined",
    "labels_rejoined",
    "label_spillover_split",
    "apparatus_text_cut",
    "contents_links_cut",
    "footnote_markers_cut",
    "wordless_turns_dropped",
    "events_tagged",
    "note_tails_reattached",
    "note_dashes_returned",
    "note_colons_returned",
    "note_tails_returned",
    "inline_merged",
    "italics_handed_forward",
    "appendix_demoted",
    "speech_blocks",
    "heading_blocks",
    "furniture_blocks",
    "other_blocks",
    "rows_written",
    "duration_s",
    "parser_version",
    "parsed_at",
    "error",
]


# ---------------------------------------------------------------------------
# Character extraction and page-level cleanup
# ---------------------------------------------------------------------------

def extract_all_characters(pdf_path, max_pages=None):
    """Extract every character with font family, style, size, page, and y.

    Returns (chars, page_heights) — heights feed the footer strip.
    """
    chars = []
    page_heights = {}
    scanned_pages = 0
    restored = 0
    suppressed = 0
    off_page = 0
    cids_read = 0
    letters_read = 0
    stacked = 0
    with pdfplumber.open(pdf_path) as pdf:
        pages = pdf.pages if max_pages is None else pdf.pages[:max_pages]
        prev_raw = prev_out = None
        for i, page in enumerate(pages):
            page_heights[i + 1] = page.height
            if page_is_scanned(page):
                scanned_pages += 1
            page_chars = [c for c in page.chars if on_the_page(c, page)]
            off_page += len(page.chars) - len(page_chars)
            tracked = letter_spacing_gaps(page_chars)
            for j, c in enumerate(page_chars):
                family = SUBSET_RE.sub("", c["fontname"])
                low = family.lower()
                if "bold" in low:
                    style = "bold"
                elif "italic" in low or "oblique" in low:
                    style = "italic"
                else:
                    style = "normal"
                if prev_raw is not None and space_is_missing(prev_raw, c, i + 1):
                    if j in tracked:
                        # the page spaces this word's own letters apart for
                        # emphasis; the gap is not a space (letter_spacing_gaps)
                        suppressed += 1
                    else:
                        # the gap belongs to the line that is ending, so it is
                        # cut or kept with it when headers and footers go
                        chars.append(dict(prev_out, text=" "))
                        restored += 1
                text = GLYPH_MEANING.get(c["text"], c["text"])
                size = round(c["size"], 1)
                letter = SYMBOL_FONT_LETTERS.get(
                    (SYMBOL_FONT_ALIAS.sub("", family), text))
                if letter is not None:
                    # These files paint one mark several times over itself to
                    # make it heavier: the dash of "Sr. Gómez Diez. —" is four
                    # glyphs stacked at the same place on the line. Read one
                    # per place, or the label comes out with four dashes.
                    if (prev_raw is not None and prev_raw["text"] == c["text"]
                            and abs(prev_raw["x0"] - c["x0"]) < 1
                            and prev_raw["page"] == i + 1):
                        prev_raw = dict(c, page=i + 1)
                        stacked += 1
                        continue
                    text = letter
                    if (prev_out is not None and prev_out["page"] == i + 1
                            and abs(prev_out["top"] - c["top"]) < 3):
                        style, size = prev_out["font_style"], prev_out["size"]
                    letters_read += 1
                cid = CID_NUM_RE.match(text)
                if cid:
                    read = CID_MEANING.get((family, int(cid.group(1))))
                    if read is not None:
                        text = read
                        # and it stops standing apart from the line it is in.
                        # A font brought in for one mark of punctuation
                        # declares a weight and a size of its own, and the
                        # grouping reads those as a change of style: an
                        # ordinal set this way cuts its own heading in half.
                        # The mark belongs to the word beside it, so it is
                        # given that word's weight and size — never across a
                        # line, where there is no word beside it.
                        if (prev_out is not None and prev_out["page"] == i + 1
                                and abs(prev_out["top"] - c["top"]) < 3):
                            style, size = prev_out["font_style"], prev_out["size"]
                        cids_read += 1
                if text == "":
                    continue
                out = {
                    "text": text,
                    "font": family,
                    "font_style": style,
                    "size": size,
                    "page": i + 1,
                    "top": c["top"],
                }
                chars.append(out)
                prev_raw, prev_out = dict(c, page=i + 1), out
    remapped = repair_symbol_font(chars)
    scanned_share = scanned_pages / max(len(pages), 1)
    print(f"Extracción completa. Se extrajeron {len(chars)} caracteres en total.")
    if restored:
        print(f"Se repusieron {restored} espacios que el archivo no guarda "
              f"pero la página muestra.")
    if suppressed:
        print(f"No se repusieron {suppressed} huecos que son el espaciado de "
              f"letras de una palabra destacada, no un espacio.")
    if off_page:
        print(f"Se descartaron {off_page} caracteres que el archivo dibuja "
              f"fuera de la hoja, donde la página no imprime nada.")
    if remapped:
        print(f"Se repararon {remapped} caracteres de una fuente de símbolos mal mapeada.")
    if cids_read:
        print(f"Se leyeron {cids_read} glifos que la fuente no declara, "
              f"según lo que imprime la página.")
    if letters_read:
        print(f"Se corrigieron {letters_read} caracteres que una fuente de "
              f"símbolos declara como otra letra.")
    if stacked:
        print(f"Se descartaron {stacked} repeticiones de un mismo signo "
              f"dibujado varias veces en el mismo lugar.")
    if scanned_share:
        print(f"=== Advertencia: {scanned_share:.0%} de las páginas son imágenes "
              f"escaneadas; el texto proviene de OCR y no es fiable ===")
    return chars, page_heights, scanned_share


# A gap this wide, measured against the type size, is a space the file does not
# store. Both bounds were measured on files that DO print their spaces: two
# letters of one word are never more than 0.07 apart, and a printed space is
# 0.25 to 0.60 wide, so anything above 0.15 is a space and nothing below it is.
GAP_IS_A_SPACE = 0.15


def space_is_missing(prev, cur, page):
    """Does the page show a space here that the file does not store?

    The parser reads characters in the order the file keeps them, which is
    faithful to what was typeset but carries no line breaks: where the older
    formats end a line without storing a space, the last word of one line and
    the first of the next come out joined ("reemplazala expresión"). The same
    happens across a wide gap inside a line, which is how a page header runs
    into the text below it.

    A line ending in a hyphen is left joined: it is either a word broken across
    the line or a file number ("P.E.-86/16"), and in both the two halves belong
    together.
    """
    if prev["text"].isspace() or cur["text"].isspace():
        return False
    size = max(prev["size"], cur["size"], 1)
    if prev["page"] != page:
        return True
    if abs(cur["top"] - prev["top"]) > 0.5 * size:      # a new line, or a new column
        return prev["text"] != "-"
    return (cur["x0"] - prev["x1"]) > GAP_IS_A_SPACE * size


# A word set with its letters spaced apart for emphasis — "T e n e r  c a l i d a d"
# in the President's address of 1 March 2009, "V o t a c i ó n  N o m i n a l"
# over every roll-call table from 2004 on. The gap between two of its letters is
# wider than GAP_IS_A_SPACE, so the rule above used to read every one of them as
# a space and hand out one word per letter. What tells the two apart is that the
# gaps of a spaced-out word all measure the same, and a missing space is one wide
# gap between two runs of letters set tight. Where the page really does put a
# space inside such a word, it is visible either as a space the file stores or as
# the one gap noticeably wider than the rest — and that gap is still read as a
# space. Measured over all 559 files: a spaced-out word's gaps run from 0.15 to
# 0.94 of the type size — one word of the address of 23 June 2004 is set at 0.9 —
# and inside one word they never vary by more than a fifteenth of themselves.
LETTER_SPACING_CEIL = 1.00      # wider than this is layout, not a spaced word
LETTER_SPACING_TOLERANCE = 0.20  # gaps this close to their run's own gap are alike
LETTER_SPACING_MIN_GAPS = 4     # five characters in a row, at least
LETTER_SPACING_MIN_ALPHA = 0.5  # a word or a file number ("S-4188/08"), not the
                                # row of dots of a contents line, which is spaced
                                # exactly the same way and means the opposite


def letter_spacing_gaps(page_chars):
    """Which gaps on this page are a word's letter spacing rather than a space?

    Returns the indices whose gap to the character before them is the extra
    space a typesetter puts between the letters of a word to draw the eye to
    it. Everything else — including the one wider gap that separates two such
    words — is left to space_is_missing, which is what puts the space back.
    """
    spaced = set()
    gaps = [None]                # gaps[j]: the gap before character j, or None
    for j in range(1, len(page_chars)):
        prev, cur = page_chars[j - 1], page_chars[j]
        size = max(prev["size"], cur["size"], 1)
        if abs(cur["top"] - prev["top"]) > 0.5 * size:      # a new line
            gaps.append(None)
            continue
        gaps.append((cur["x0"] - prev["x1"]) / size)

    run = []
    line = []
    for j in range(1, len(gaps) + 1):
        gap = gaps[j] if j < len(gaps) else None
        if gap is None:                                  # the line ends here
            spaced.update(letter_spaced_run(run, gaps, page_chars))
            spaced.update(letter_spaced_line(line, gaps, page_chars))
            run, line = [], []
            continue
        line.append(j)
        if GAP_IS_A_SPACE <= gap <= LETTER_SPACING_CEIL:
            run.append(j)
        else:
            spaced.update(letter_spaced_run(run, gaps, page_chars))
            run = []
    return spaced


# The rule above reads the gaps between one character's box and the next one's,
# and that is not always what the typesetter set. One roll-call masthead of 18
# November 2009 is set in a Tahoma the file describes badly: the width it gives
# some letters is the width of the letter beside them, so the same evenly spaced
# line arrives with some pairs touching and others twice as far apart as they
# are printed, and the row of alike gaps breaks into pieces too short to
# recognise. Read as a whole line the spacing is still plain — most of its gaps
# do measure alike — so a line whose gaps are mostly one width, wider than a
# space, is set with letter spacing from end to end, and none of them is a space.
# This is only allowed where the line stores its own spaces, so that reading it
# this way cannot glue two words together; where it does not, the rule above
# still decides gap by gap.
LETTER_SPACED_LINE_SHARE = 0.4    # in that Tahoma, half the pairs measure as
                                  # touching, so "most" cannot be the test
LETTER_SPACED_LINE_MIN_ALIKE = 8  # a spaced line, not a chance pair of gaps


def letter_spaced_line(line, gaps, page_chars):
    """Every gap of a line set with letter spacing from one end to the other."""
    if len(line) < LETTER_SPACING_MIN_GAPS:
        return ()
    widths = sorted(gaps[j] for j in line)
    typical = widths[len(widths) // 2]
    if not GAP_IS_A_SPACE <= typical <= LETTER_SPACING_CEIL:
        return ()
    alike = [j for j in line
             if abs(gaps[j] - typical) <= LETTER_SPACING_TOLERANCE * typical]
    if (len(alike) < LETTER_SPACED_LINE_MIN_ALIKE
            or len(alike) < LETTER_SPACED_LINE_SHARE * len(line)):
        return ()
    text = "".join(c["text"] for c in page_chars[line[0] - 1:line[-1] + 1])
    if sum(c.isalnum() for c in text) < LETTER_SPACING_MIN_ALPHA * max(len(text), 1):
        return ()
    if not any(c.isspace() for c in text):
        return ()
    return line


def letter_spaced_run(run, gaps, page_chars):
    """The gaps of one candidate run that are letter spacing, if it is a word."""
    if len(run) < LETTER_SPACING_MIN_GAPS:
        return ()
    widths = sorted(gaps[j] for j in run)
    typical = widths[len(widths) // 2]
    alike = [j for j in run
             if abs(gaps[j] - typical) <= LETTER_SPACING_TOLERANCE * typical]
    if len(alike) < LETTER_SPACING_MIN_GAPS or len(alike) < 0.7 * len(run):
        return ()
    text = "".join(c["text"] for c in page_chars[run[0] - 1:run[-1] + 1])
    if sum(c.isalnum() for c in text) < LETTER_SPACING_MIN_ALPHA * max(len(text), 1):
        return ()
    # Where the spaced word is set so wide that its own gaps are as wide as a
    # space, the space in front of it measures no more than they do and would be
    # swallowed with them ("…Aires.Esos expedientes"). It is still visible: the
    # character before the word is set tight against the one before it, so it
    # belongs to a word set normally, and the gap between the two is a space.
    # The same at the far end, where the spaced word runs back into normal text.
    # "Set tight" means what the rest of the page does — a gap of about nothing —
    # not merely narrower than a space: inside a spaced word one pair of letters
    # can fall just under the threshold and end the run without ending the word.
    # None of this applies where the file already stores a space of its own at
    # that end of the word: nothing is missing there, and putting a second one
    # back cuts the word open at its first letter ("V otación Nominal").
    def is_tight(gap):
        return gap is not None and gap < GAP_IS_A_SPACE and gap < 0.5 * typical

    def stored_space(j):
        return 0 <= j < len(page_chars) and page_chars[j]["text"].isspace()

    edges = []
    if is_tight(gaps[run[0] - 1]) and not stored_space(run[0] - 2):
        edges.append(run[0])
    if (run[-1] + 1 < len(gaps) and is_tight(gaps[run[-1] + 1])
            and not stored_space(run[-1] + 1)):
        edges.append(run[-1])
    return [j for j in alike if j not in edges]


# A PDF can place text beyond the edges of its own sheet, where nothing prints
# and nobody can read it, and the extractor still hands it over. Two sittings of
# 2013 draw "◄ Ver el Apéndice." down a column to the right of the page — one
# letter under the next, all at x = 602.8 on a sheet 595.2 wide — so it arrived
# as a row of lone letters; the sitting of 12 September 2024 draws its "Pág. N"
# 170 points past the edge on all 187 pages, which is why that record shows no
# page number when you look at it. Across the corpus it is 3,246 characters on
# 264 pages of 49 sittings, most of them runs of spaces. A character that
# straddles an edge is kept: part of it does print.
def on_the_page(char, page):
    """Is this character inside the sheet the page is printed on?"""
    left, top, right, bottom = page.bbox
    return (char["x1"] > left and char["x0"] < right
            and char["bottom"] > top and char["top"] < bottom)


def page_is_scanned(page):
    """Is this page a picture of a page rather than a page?

    Almost every transcript is born-digital, and its characters are the
    characters the typesetter set. A few are scans of the printed Diario de
    Sesiones with optical character recognition run over them, and there the
    "text" is a guess: words run together, letters swap, hyphens survive from
    the line breaks of the original column. Nothing downstream can repair
    that, so it has to be visible. A scanned page is an image that covers
    essentially the whole sheet.
    """
    area = (page.width or 1) * (page.height or 1)
    covered = sum(max(i["x1"] - i["x0"], 0) * max(i["bottom"] - i["top"], 0)
                  for i in page.images)
    return covered > 0.6 * area


# What the mis-mapped symbol font actually draws. Every mapping was read off
# the 2004-10-20 file's own contexts, and each is unambiguous there: "C"
# appears only as the label terminator and event dash, "1" only after "N",
# "(" and ")" only at the start of a word, "8" only after an already-accented
# vowel (a leftover the accent had consumed, so it is dropped).
SYMBOL_FONT_MAP = {"C": "—", "A": "“", "@": "”", ")": "¿", "(": "¡",
                   "1": "°", "8": ""}


def repair_symbol_font(chars):
    """Undo a broken character map in a font used only for punctuation.

    The 2004-10-20 file draws its dashes, quotes and inverted question
    marks in a subsetted Courier whose character map is wrong, so an em
    dash extracts as a literal "C" ("Sr. Presidente. C La sesión está
    abierta"). That swallows the turn's opening words into the speaker
    label and leaves the chair unidentifiable.

    What the page shows, not just what the file stores. Rendered, the page
    really does print "Sra. Avelin. C ...porque hay un fiscal" — the letter
    is on the paper, checked with two independent renderers. So this is a
    reconstruction of a document broken in print, not a recovery of what the
    page shows, and it is declared as such in SOURCES.md. It is made anyway
    because without it the label and the words after it cannot be told apart
    and the whole sitting loses its speakers.

    Other sittings do set real text in Courier — an inserted document in a
    typewriter face — and must not be touched. The two uses are told apart
    by run length: a font standing in for punctuation never draws more than
    a couple of characters in a row, while body text runs for hundreds.

    One entry needs a second guard. "1" stands in for the ordinal of "Orden
    del Dia N 1284", but the same font also sets the raised reference number
    of a footnote, and turning THAT into an ordinal writes a degree sign into
    two other sittings. The two are the same character at different sizes:
    the ordinal is set at body size, the reference number smaller. So the
    substitution is made only at body size.
    """
    idx = [i for i, c in enumerate(chars) if COURIER_RE.search(c["font"])]
    if not idx:
        return 0
    longest = run = 0
    for a, b in zip(idx, idx[1:]):
        run = run + 1 if b == a + 1 and chars[b]["text"].strip() else 0
        longest = max(longest, run)
    if longest > 3:
        return 0                      # the font is carrying words, not symbols
    body = Counter(c["size"] for c in chars).most_common(1)[0][0]
    fixed = 0
    for i in idx:
        repl = SYMBOL_FONT_MAP.get(chars[i]["text"])
        if repl is None:
            continue
        if chars[i]["text"] == "1" and chars[i]["size"] < body - 0.5:
            continue                  # a raised footnote number, not an ordinal
        chars[i]["text"] = repl
        fixed += 1
    return fixed


def strip_page_headers(chars):
    """Drop every char at or above the per-page "Pág. N" dateline.

    The dateline (with the motto above it, where present) is the one
    running-header invariant across all 2020-2024 formats. Pages without
    a dateline (cover, plates) are left untouched — the front-matter cut
    handles those at block level.

    Appended plates (roll-call tallies, inserted documents) carry their own
    running header instead of the dateline, so a second pass cuts any line
    that repeats near the top of five or more pages AT THE SAME HEIGHT.
    Fixed position is what separates a running header from a stock phrase
    like "El texto es el siguiente:", which recurs but floats down the page.
    """
    # line assembly per page, top band only
    lines = {}
    for c in chars:
        if c["top"] < 200:
            lines.setdefault((c["page"], round(c["top"] / 3)), []).append(c)

    per_page = {}
    for (page, _), line_chars in sorted(lines.items()):
        text = "".join(ch["text"] for ch in line_chars)  # extraction order = reading order
        if text.strip():  # blank spacer lines must not use up the first-3 window
            per_page.setdefault(page, []).append((text, line_chars))

    cutoffs = {}
    for page, page_lines in per_page.items():
        for text, line_chars in page_lines:
            if PAG_LINE_RE.search(text):
                cutoffs[page] = max(ch["top"] for ch in line_chars) + 0.5
                break

    repeats = Counter()
    for page_lines in per_page.values():
        for text, line_chars in page_lines:
            key = re.sub(r"[\d\s]+", " ", text).strip()
            if len(key) >= 20:
                repeats[(key, round(line_chars[0]["top"] / 5))] += 1
    running = {k for k, n in repeats.items() if n >= 5}
    # (text, height) rather than text alone: a running header sits at a fixed
    # height on every page, while a recurring stock phrase drifts.

    for page, page_lines in per_page.items():
        for text, line_chars in page_lines:
            key = re.sub(r"[\d\s]+", " ", text).strip()
            if (key, round(line_chars[0]["top"] / 5)) in running:
                bottom = max(ch["top"] for ch in line_chars) + 0.5
                cutoffs[page] = max(cutoffs.get(page, 0), bottom)

    kept = [c for c in chars if not (c["page"] in cutoffs and c["top"] <= cutoffs[c["page"]])]
    removed = len(chars) - len(kept)
    print(f"Encabezados de página eliminados: {removed} caracteres en {len(cutoffs)} páginas.")
    return kept, removed


def strip_page_footers(chars, page_heights):
    """Drop the per-page "Dirección General de Taquígrafos" footer.

    The 2024 format signs every page at the bottom (mixed styles: bold
    "Taquígrafos" next to normal text), which otherwise becomes a
    speaker-resetting heading on every page. Only lines in the bottom
    band that actually mention Taquígrafos trigger a cut, so pages
    without the footer are untouched.

    A bottom-band line carrying no letters at all is a bare page number
    ("- 1 -", "2") — the way the appended roll-call plates number their
    own pages — and is cut on the same terms.
    """
    lines = {}
    for c in chars:
        h = page_heights.get(c["page"], 842)
        if c["top"] > h - 70:
            lines.setdefault((c["page"], round(c["top"] / 3)), []).append(c)

    cutoffs = {}
    for (page, _), line_chars in sorted(lines.items()):
        text = "".join(ch["text"] for ch in line_chars)
        page_number = text.strip() and not any(ch.isalpha() for ch in text)
        if page_number or "Taquígrafo" in text or "Direcci" in text:
            y = min(ch["top"] for ch in line_chars) - 0.5
            cutoffs[page] = min(cutoffs.get(page, y), y)

    kept = [c for c in chars if not (c["page"] in cutoffs and c["top"] >= cutoffs[c["page"]])]
    removed = len(chars) - len(kept)
    print(f"Pies de página eliminados: {removed} caracteres en {len(cutoffs)} páginas.")
    return kept, removed


def body_size_candidates(chars):
    """Candidate body sizes, most frequent normal-style size first.

    Usually the modal size IS the body — but short Asambleas are dominated
    by 10 pt attendance lists, so the caller tries candidates in order
    until one yields a session opening.
    """
    counts = Counter(c["size"] for c in chars if c["font_style"] == "normal")
    if not counts:
        return [12.0]
    total = sum(counts.values())
    cands = [s for s, n in counts.most_common(3) if n >= 0.05 * total]
    print(f"Candidatos a tamaño de cuerpo: {cands}")
    return cands or [counts.most_common(1)[0][0]]


# ---------------------------------------------------------------------------
# Block construction
# ---------------------------------------------------------------------------

def group_characters_into_text_blocks(chars):
    """Group consecutive chars into blocks; break on (style, size) change.

    Font family is recorded but deliberately NOT in the break key: the
    ilovepdf-recompressed files rewrite fonts mid-heading ("1." and its
    title land in different families), which fragments chapter headings.
    Heading/label fusion across families is handled by the double-space
    split in assign_chapter_to_blocks instead.
    """
    blocks = []
    cur = None
    for c in chars:
        if cur is None:
            cur = {"text": c["text"], "font": c["font"], "font_style": c["font_style"],
                   "size": c["size"], "pages": [c["page"]]}
            continue
        if (cur["font_style"], cur["size"]) != (c["font_style"], c["size"]):
            blocks.append(cur)
            cur = {"text": c["text"], "font": c["font"], "font_style": c["font_style"],
                   "size": c["size"], "pages": [c["page"]]}
        else:
            cur["text"] += c["text"]
            if c["page"] not in cur["pages"]:
                cur["pages"].append(c["page"])
    if cur is not None:
        blocks.append(cur)
    print(f"Agrupamiento completo. Se generaron {len(blocks)} bloques de texto.")
    return reassign_parens_to_italic_blocks(reassign_hyphens_to_italic_blocks(blocks))


def reassign_hyphens_to_italic_blocks(blocks):
    """Mueve los guiones finales al inicio del siguiente bloque cursivo."""
    for i in range(len(blocks) - 1):
        cur, nxt = blocks[i], blocks[i + 1]
        if cur["text"].strip().endswith("-") and nxt["font_style"] == "italic":
            cur["text"] = cur["text"].strip().rstrip("-")
            nxt["text"] = "-" + nxt["text"].strip()
    return blocks


def reassign_parens_to_italic_blocks(blocks):
    """Give a parenthesized stenographer note back its brackets.

    Some formats italicize only the word and leave the brackets in the
    surrounding roman text, so the run splits as "…demanden. (" + "Aplausos"
    + ".) Invito al señor senador…". The middle block is then a lone
    italicized word, which the classifier reads as emphasis inside speech
    and merges back into the turn — and the applause is never recorded.
    Moving the brackets into the italic block restores the note.
    """
    moved = 0
    for i in range(1, len(blocks) - 1):
        prev, cur, nxt = blocks[i - 1], blocks[i], blocks[i + 1]
        text = cur["text"].strip()
        if cur["font_style"] != "italic" or not text:
            continue
        lead = re.match(r"^[\s.]+(?=\()", cur["text"])
        if lead and text.endswith(")"):
            # the italic run swallowed the full stop that ends the previous
            # sentence ("Patria" + ". (Aplausos.)"): give it back, so what
            # remains is the note alone
            prev["text"] = prev["text"].rstrip() + lead.group(0).strip()
            cur["text"] = cur["text"][lead.end():]
            text = cur["text"].strip()
            moved += 1
        if text.startswith("("):
            continue
        # Either bracket may have stayed in the roman text, or both.
        take_open = "(" not in text and prev["text"].rstrip().endswith("(")
        close = re.match(r"\s*\.?\s*\)", nxt["text"]) if ")" not in text else None
        if not take_open:
            continue
        if not (close or text.endswith(")")):
            continue
        prev["text"] = prev["text"].rstrip()[:-1]
        cur["text"] = "(" + text + (close.group(0).strip() if close else "")
        if close:
            nxt["text"] = nxt["text"][close.end():]
        moved += 1
    if moved:
        print(f"Paréntesis devueltos a {moved} notas del taquígrafo.")
    return blocks


def smooth_micro_islands(blocks):
    """Weld letterless micro-blocks back into their neighbors.

    2000–2013 PDFs flip style on single characters ("29º", stray dots),
    splitting one sentence into three blocks; a bold island then acts as a
    phantom heading that resets speaker attribution. A lone space between
    two bold runs does the same damage — it is what breaks "Sr." away from
    "Presidente" in the 2006–2009 files. Absorb the island into the
    preceding block and, when the following block resumes the preceding
    block's style, rejoin that continuation too.
    """
    out = []
    merged = 0
    resume_key = None
    for b in blocks:
        t = b["text"].strip()
        if out and b["text"] and len(t) <= 2 and not any(ch.isalpha() for ch in t) \
                and b["size"] == out[-1]["size"]:
            out[-1]["text"] += b["text"]
            out[-1]["pages"] = sorted(set(out[-1]["pages"]) | set(b["pages"]))
            resume_key = (out[-1]["font_style"], out[-1]["size"])
            merged += 1
            continue
        if resume_key is not None and (b["font_style"], b["size"]) == resume_key:
            out[-1]["text"] += b["text"]
            out[-1]["pages"] = sorted(set(out[-1]["pages"]) | set(b["pages"]))
            resume_key = None
            continue
        resume_key = None
        out.append(b)
    if merged:
        print(f"Suavizado: {merged} micro-islas de estilo fusionadas.")
    return out, merged


def cut_front_matter(blocks, body_size):
    """Start the session at the first opening event or speaker label.

    Sessions open with a dash-initial italic event ("–A las 15:02 ...",
    "–En la Ciudad Autónoma ...") or directly with a chair label. This is
    format-independent and also skips the sumario/índice listing, whose
    chapter titles are re-detected from the body headings. Falls back to
    the v0.2 bold "1." marker; returns ([], "none") when nothing matches.
    """
    for i, b in enumerate(blocks):
        t = b["text"].strip()
        if b["size"] != body_size:
            continue
        if b["font_style"] == "italic" and EVENT_DASH_RE.match(t):
            return blocks[i:], "opening_event"
        if b["font_style"] == "bold" and SPEAKER_RE.match(t):
            return blocks[i:], "first_speaker"
    for i, b in enumerate(blocks):
        if b["font_style"] == "bold" and b["size"] == body_size and b["text"].strip().startswith("1."):
            return blocks[i:], "numbered_marker"
    print("=== Advertencia: no se encontró el inicio de la sesión ===")
    return [], "none"


def cut_apparatus_text(blocks):
    """Cut printed apparatus out of the middle of a speech turn.

    Three kinds reach the body text because they are set in the body font at
    body size, so neither the size test nor the positional strips see them, and
    the grouping pass draws them into whichever speaker's block sits next to
    them in the stored character order:

    * the footnote pointing at the appendix ("…los residuos Ver el Apéndice. de
      desecho…"),
    * the contents-page link the digital edition prints after a turn
      ("Queda aprobado el plan de labor.[ Volver al sumario]"),
    * the page dateline in a sitting whose font has no character map, where
      "Pág. 5" extracts with only the accent and the digit intact and the strip
      that keys on the printed dateline therefore cannot find it.

    Removing them also repairs the sentence they had been dropped into.
    """
    cut = 0
    for b in blocks:
        text, n = FOOTNOTE_TEXT_RE.subn(" ", b["text"])
        cut += n
        if PAGENUM_ONLY_RE.match(CID_UNMAPPED_RE.sub("", text)):
            text, cut = "", cut + 1
        if text != b["text"]:
            b["text"] = re.sub(r"\s{2,}", " ", text)
    if cut:
        print(f"Aparato de página removido del texto: {cut} fragmentos.")
    return blocks, cut


def clean_final_speech(blocks):
    """Last pass over the settled turns: cut the contents link, drop empty ones.

    The contents-page link arrives split across two style runs — the bracket
    ends one block and "Volver al sumario]" is the next — so it can only be cut
    once the italic fragments have been merged back into the speech they
    interrupt, which is here. Turns left carrying no word at all ("." or "—" or
    "(") are shards of the style grouping, not utterances, and go with it.
    Nothing here can change who is credited with what: the speakers are already
    settled, so this only removes printed apparatus and empty rows.
    """
    links = markers = 0
    for b in blocks:
        text, n = SUMARIO_RE.subn(" ", b["text"])
        if n:
            text = re.sub(r"\s{2,}", " ", text).strip()
            links += n
        if b.get("type") == "speech":
            # a bare number left at the very end of a turn is the footnote
            # marker whose text was cut, or the number of the section heading
            # printed next — never a figure anybody spoke
            text, m = TRAILING_MARKER_RE.subn(r"\1", text)
            markers += m
        if text != b["text"]:
            b["text"] = text
    kept = [b for b in blocks
            if b.get("type") != "speech" or WORD_CHAR_RE.search(b["text"])]
    dropped = len(blocks) - len(kept)
    if links or markers or dropped:
        print(f"Enlaces al sumario removidos: {links}. "
              f"Marcadores de nota al pie sueltos removidos: {markers}. "
              f"Turnos sin ninguna palabra descartados: {dropped}.")
    return kept, links, markers, dropped


def remove_empty_blocks(blocks):
    """Drop blocks that are empty, whitespace, or only unmapped glyphs.

    Fonts without a Unicode mapping extract as literal "(cid:47)" tokens.
    Where that is ALL a block contains it is a decorative bullet, so the
    block is dropped; a block that mixes them with real words is kept,
    glyphs and all, so the extraction loss stays visible in the text.
    """
    kept = [b for b in blocks if CID_RE.sub("", b["text"]).strip()]
    removed = len(blocks) - len(kept)
    print(f"Se eliminaron {removed} bloques vacíos. Quedan {len(kept)} bloques.")
    return kept, removed


# ---------------------------------------------------------------------------
# Block classification
# ---------------------------------------------------------------------------

def classify_event(text):
    """Subtype an event text; first matching pattern wins."""
    low = text.lower()
    for subtype, pattern in EVENT_SUBTYPES:
        if pattern.search(low):
            return subtype
    return "unspecified"


def rejoin_split_word(blocks, body_size):
    """Rescue the words that a change of type size cut off mid-word.

    Blocks whose size differs from the body's are page apparatus — footnotes,
    plates, attendance lists — and are dropped. But the typesetter sometimes
    sets the opening of a sentence a point larger than the rest of it, and then
    the opening is dropped with them: the "T" of "Tiene la palabra el señor
    senador Rodríguez Saá" disappears and the turn begins "iene la palabra";
    the chair's "Por favor, les pido si podemos mantener el s" goes and the turn
    begins "ilencio durante la exposición".

    The evidence that the two belong together is that the break falls INSIDE a
    word: the block above ends on a letter and the block below opens on a lower
    case one, with no space between them. Nothing that is really apparatus ends
    that way. Any label terminator carried at the front of the rescued piece is
    dropped, since it belongs to the label and not to the sentence.
    """
    out, rejoined = [], 0
    for i, b in enumerate(blocks):
        t = b["text"].strip()
        nxt = blocks[i + 1] if i + 1 < len(blocks) else None
        if (t and b["size"] != body_size and t[-1:].isalpha()
                and b.get("type") is None
                and nxt is not None and nxt.get("type") is None
                and nxt["size"] == body_size and nxt["font_style"] != "bold"
                and nxt["text"].lstrip()[:1].islower()):
            piece = re.sub(r"^\s*\.?\s*[–—−─-]\s*", "", t)
            if piece and piece[-1:].isalpha():
                nxt["text"] = piece + nxt["text"].lstrip()
                rejoined += 1
                continue
        out.append(b)
    if rejoined:
        print(f"Palabras partidas por un cambio de cuerpo reunidas: {rejoined}.")
    return out, rejoined


def classify_blocks(blocks, body_size):
    """Assign preliminary types: furniture, event (+subtype), inline.

    Bold blocks are left for the chapter/speaker passes; normal body-size
    blocks are speech candidates resolved in identify_speakers.
    """
    events = 0
    for b in blocks:
        t = b["text"].strip()
        if DGT_RE.match(t):
            b["type"] = "furniture"      # "Dirección General de Taquígrafos" backstop
            continue
        if b["size"] != body_size:
            b["type"] = "furniture"      # appendix, footnotes, attendance lists, plates
            continue
        if b["font_style"] == "italic":
            # verb-pattern path requires sentence shape, so a lone italicized
            # word like "votación" stays inline instead of becoming an event
            sentence_like = t[:1].isupper() and (len(t) > 15 or t.endswith("."))
            if EVENT_DASH_RE.match(t) or t.startswith("(") or \
                    (sentence_like and classify_event(t) != "unspecified"):
                b["type"] = "event"
                b["event_type"] = classify_event(t)
                events += 1
            else:
                b["type"] = "inline"     # italicized fragment inside speech
    print(f"Clasificación: {events} eventos etiquetados.")
    return blocks, events


# What is left of an editorial note when the typesetter's ordinal marker comes
# from another font: "…surge del Acta N" + "E 13", where the E is a degree sign
# the font maps wrong. Digits, the marker, and the words that join two of them
# ("y", "a") are all that may appear.
NOTE_TAIL_RE = re.compile(r"^[Eº°\d][\dEº°.,;:\s]*(?:\s(?:y|a)\s[\dEº°.,;:\s]*)*[.\s—–-]*$")


def reattach_note_tails(blocks):
    """Give a cut-off scrap back to the editorial note it was cut from.

    A note such as "— El resultado de la votación surge del Acta N° 13" sets its
    degree sign in a different font, so the style grouping ends the block at the
    "N" and the rest — "E 13" — becomes a two-character turn credited to whoever
    spoke last. The same happens to a name split across fonts ("Lord Williams" +
    "of Mostyn.").

    A scrap qualifies only where the note before it stops mid-phrase, with no
    full stop, and where the scrap itself cannot be speech: nothing but the
    marker and its number, or a fragment opening in lower case. Short real turns
    that happen to follow a note — "Gracias.", "Ausente.", "¡Rojo!" — are
    untouched, which is why the test is on the shape of the scrap and not on its
    length alone.

    The tail is not always short. "— Se practica la votación por medios
    electrónicos." breaks after "la", and the rest was credited to the chair as
    if he had said "votación por medios electrónicos" out loud; another left him
    saying "nacional en el mástil del recinto." So a tail of any length is taken
    back where the note ends on a LETTER and the tail opens in lower case — a
    sentence continuing, which is not how a turn begins. The letter is what
    makes it safe: a note ending in "…" or ")" is one interjected in the middle
    of somebody's sentence, and what follows really is that person resuming.
    8 such tails in the corpus, with no case where the test is wrong.
    """
    out, scraps = [], []
    for b in blocks:
        prev = out[-1] if out else None
        t = b["text"].strip()
        if not (prev is not None and prev.get("type") == "event"
                and b.get("type") is None and t
                and not re.search(r"[.!?)]$", prev["text"].strip())):
            out.append(b)
            continue
        note = prev["text"].strip()
        is_scrap = len(t) <= 12 and (NOTE_TAIL_RE.match(t) or t[:1].islower())
        # a note whose closing parenthesis is followed by a letter or two is the
        # other fault entirely — the italic run overrunning into the sentence,
        # repaired further down — so it must not be fed more of that sentence
        is_sentence = (note[-1:].isalpha() and t[:1].islower()
                       and not NOTE_TAIL_RE.search(note))
        if is_scrap or is_sentence:
            prev["text"] = prev["text"].rstrip() + (" " if is_sentence else "") + t
            prev["pages"] = sorted(set(prev["pages"]) | set(b["pages"]))
            scraps.append(t if len(t) <= 40 else t[:40] + "…")
            continue
        out.append(b)
    if scraps:
        # listed, not just counted: every one of them should be unreadable as
        # speech, and that is checkable only if the log says what they were
        print(f"Restos de notas devueltos a su nota: {len(scraps)} — "
              + ", ".join(repr(s) for s in scraps))
    return out, len(scraps)


TRAILING_DASH_RE = re.compile(r"\s*[—–-]\s*$")
LEADING_DASH_RE = re.compile(r"^\s*[—–-]")
LEADING_COLON_RE = re.compile(r"^\s*:\s")
NOTE_TAIL_RE = re.compile(r"\)([^)]{1,12})$")


def return_stage_direction_punctuation(blocks):
    """Give an editorial note back the punctuation printed as part of it.

    A note is introduced by a dash — "— Se vota." — but in many files that dash
    is stored at the end of the line above, so it comes out stuck to the end of
    the turn before it, which then appears to finish on a dangling dash. The
    dash is stored where it belongs 17,912 times and left behind 9,025; in only
    8 of those does the note carry a dash of its own, and that is what shows the
    stray one is the same dash rather than a second.

    The mirror case is a note that ends in a colon — "…cuyos textos se incluyen
    en el Apéndice, son los siguientes:" — whose colon is stored with the block
    below and opens the next turn. It is taken back only where the note stops
    mid-phrase, with no closing punctuation of its own. Where the note is
    already complete ("(Risas.)") the colon is left alone: nothing there shows
    it is not part of what follows.

    A third case runs the other way. An interjected note is set in italics, and
    in a few files the italic run carries a character or two past the closing
    parenthesis, so the note ends "(aplausos), s" and the sentence resumes at
    "i la Argentina debe ser tomada en su totalidad?" — a word broken in half.
    5,191 parenthesised notes end cleanly; 5 hold letters the sentence
    continues, and 70 hold a comma, semicolon or dash closing the clause the
    note interrupted. Those go back to the speech. A colon does not: 13 notes
    end in one and it is the note's own, introducing the matter quoted below.
    """
    dashes = colons = tails = 0
    for i, b in enumerate(blocks[:-1]):
        nxt = blocks[i + 1]
        if (b.get("type") is None and nxt.get("type") == "event"
                and TRAILING_DASH_RE.search(b["text"])
                and not LEADING_DASH_RE.match(nxt["text"])):
            b["text"] = TRAILING_DASH_RE.sub(" ", b["text"])
            nxt["text"] = "— " + nxt["text"].lstrip()
            dashes += 1
    for i, b in enumerate(blocks):
        prev = blocks[i - 1] if i else None
        if (i and b.get("type") is None and prev.get("type") == "event"
                and LEADING_COLON_RE.match(b["text"])
                and not re.search(r"[.!?)]$", prev["text"].strip())):
            b["text"] = LEADING_COLON_RE.sub("", b["text"], count=1)
            prev["text"] = prev["text"].rstrip() + ": "
            colons += 1
    for i, b in enumerate(blocks[:-1]):
        nxt = blocks[i + 1]
        if b.get("type") != "event" or nxt.get("type") is not None:
            continue
        m = NOTE_TAIL_RE.search(b["text"].rstrip())
        if not m:
            continue
        tail = m.group(1)
        stripped = tail.strip()
        letters = re.search(r"[^\W\d_]", stripped, re.UNICODE)
        resumes = nxt["text"].lstrip()[:1].islower()
        if not stripped or stripped == "." or ":" in stripped:
            continue
        if not ((letters and resumes) or re.fullmatch(r"[,;—–]+", stripped)):
            continue
        b["text"] = b["text"].rstrip()[: m.start(1)]
        # a tail ending in a letter is half of a word: join it with no space
        rest = nxt["text"].lstrip() if stripped[-1:].isalpha() else nxt["text"]
        nxt["text"] = stripped + rest
        tails += 1
    if dashes or colons or tails:
        print(f"Puntuación devuelta a la nota que la lleva impresa: "
              f"{dashes} rayas de apertura, {colons} dos puntos de cierre; "
              f"{tails} arranques de frase devueltos al orador.")
    return blocks, dashes, colons, tails


DOTTED_CHAPTER_RE = re.compile(r"^\d+\.")


def continues_the_count(text, current):
    """Is this numbered title the next section, or a bill number?

    A title numbered with a full stop ("7. Homenaje") is unambiguous and is
    always taken. A dotless one is taken only where its number carries the
    count forward, or opens the sitting — otherwise it is the number of a bill
    left at the head of a line by the line break above it.

    Forward by up to three rather than by exactly one, because a section whose
    number is swallowed by the title above it would otherwise break the count
    for the rest of the sitting. Bill numbers run in the hundreds and are never
    within three of the section being read.

    The count may open at anything up to ten, not at 1 alone: the first section
    of a sitting is sometimes swallowed the same way, and the numbering then
    starts at 2 or 3. Ten is still far below any bill number.
    """
    if DOTTED_CHAPTER_RE.match(text):
        return True
    num = int(re.match(r"\d+", text).group())
    if current is None:
        return num <= 10
    return 0 < num - int(current) <= 3


def assign_chapter_to_blocks(blocks, body_size):
    """Detect bold body-size "N. Título" headings; assign chapters to blocks.

    A numbered title and the label of whoever speaks under it share one bold
    run, so the label has to be cut off and re-emitted as its own block. Miss
    that cut and the label vanishes into the title: the turn never opens, the
    next speaker's words are added to the previous speaker's turn, and the
    stranded "(Surname)" half of the label is left sitting in the speech.

    The 2000–2013 layouts number their sections without a full stop ("2
    Izamiento de la bandera"), which is also the shape of a bill number left at
    the head of a line ("Orden del Día N° / 522 Obras de los bajos..."). The
    two are told apart by counting: sections run 1, 2, 3 in order — in the
    later files, which number with a full stop and cannot be confused, the next
    section is the previous one plus one in 284 of 290 cases — while a bill
    number is whatever the bill happens to be. So a dotless heading opens a
    section only where it continues the count.
    """
    chapters = {}
    current = None
    out = []
    label_cuts = 0
    out_of_sequence = 0
    numbers_recovered = 0
    for b in blocks:
        t = LEAD_JUNK_RE.sub("", b["text"].strip())
        bold_title = (b.get("type") is None and b["font_style"] == "bold"
                      and b["size"] == body_size)
        if (bold_title and not t[:1].isdigit() and out
                and not SPEAKER_RE.match(t) and len(t.split()) >= 4):
            # the section's own number is sometimes set in the body face rather
            # than the bold of its title, so the style grouping leaves it on the
            # end of the turn above and the section is lost. Take it back only
            # where it continues the count, so a figure that merely happens to
            # end a sentence is not read as a section number — and never onto a
            # speaker's label, which is bold too and follows the same notes.
            stray = re.search(r"(?:^|\s)(\d{1,3}\.)\s*$", out[-1]["text"])
            if stray and continues_the_count(stray.group(1), current):
                out[-1]["text"] = out[-1]["text"][:stray.start(1)].rstrip() + " "
                t = f"{stray.group(1)} {t}"
                b["text"] = t
                numbers_recovered += 1
        numbered = bold_title and CHAPTER_RE.match(t)
        if numbered and not continues_the_count(t, current):
            out_of_sequence += 1                 # a bill number, not a section
        elif numbered:
            # split fused "N. Título  Sra. Presidenta..." blocks on double spaces
            parts = [p.strip() for p in t.split("  ") if p.strip()] if "  " in t else [t]
            # that double space is where the line ended, and the line can end
            # in the MIDDLE of the label — "…Armas Convencionales Sr." then
            # "Presidente. — Corresponde considerar…". Cutting there leaves half
            # a label behind, so the chair opens no turn and everything said
            # under the heading is recorded as nobody's. Put those halves back
            # together before anything else looks at them.
            rejoined = []
            for p in parts:
                if rejoined and LABEL_OPENER_TAIL_RE.search(rejoined[-1]):
                    rejoined[-1] = f"{rejoined[-1]} {p}"
                else:
                    rejoined.append(p)
            parts = rejoined
            # 2000–2013 fuses with single spaces: cut a trailing speaker label
            # off each part so it can open its own turn downstream
            fission = []
            for p in parts:
                last = None
                for last in LABEL_SPLIT_RE.finditer(p):
                    pass
                tail = p[last.end():] if last else ""
                if (last and SPEAKER_RE.match(tail) and p[:last.start()].strip()
                        and len(tail.strip()) <= MAX_LABEL_TAIL):
                    fission += [p[:last.start()].strip(), tail.strip()]
                    label_cuts += 1
                else:
                    fission.append(p)
            parts = [p for p in fission if p]
            num = re.match(r"\d+", parts[0]).group()
            chapters[num] = parts[0]
            current = num
            for extra in parts[1:]:
                nb = {"text": extra, "font": b.get("font"), "font_style": b["font_style"],
                      "size": b["size"], "pages": b["pages"], "capítulo": current}
                out.append(nb)
            continue
        b["capítulo"] = current
        out.append(b)
    print(f"Asignación de capítulos completa. Se detectaron {len(chapters)} capítulos; "
          f"{label_cuts} etiquetas de orador separadas del título.")
    if out_of_sequence:
        print(f"Títulos numerados descartados por no seguir la numeración: {out_of_sequence}.")
    if numbers_recovered:
        print(f"Números de sección recuperados del bloque anterior: {numbers_recovered}.")
    return out, chapters, label_cuts


def split_fused_labels(blocks, body_size):
    """Split a bold heading that has a speaker label glued onto its end.

    The 2000-2009 layouts run an unnumbered section title straight into the
    chair's label in one bold run — "…Comodoro Rivadavia, Chubut Sr.
    Presidente" — separated by a single space. The chapter pass only splits
    numbered titles, so without this the whole run reads as a heading, the
    running speaker is dropped, and the paragraphs that follow are orphaned.
    Blocks that already START with a label are left alone: there the label
    is the block, and a later "Sr." belongs to the quoted text.
    """
    out = []
    split = 0
    for b in blocks:
        t = b["text"].strip()
        if (b.get("type") is None and b["font_style"] == "bold"
                and b["size"] == body_size and not SPEAKER_RE.match(t)):
            last = None
            for m in FUSED_LABEL_RE.finditer(t):
                if m.start() > 0:
                    last = m
            if last:
                head, tail = t[:last.start()].strip(), t[last.end():].strip()
                if head and tail:
                    out.append({**b, "text": head})
                    b = {**b, "text": tail}
                    split += 1
        out.append(b)
    print(f"Encabezados fusionados con etiqueta separados: {split}.")
    return out, split


def split_inline_labels(blocks, body_size):
    """Recover a speaker label that was set in roman instead of bold.

    Every format marks a change of speaker by printing the label in bold, and
    the label pass is gated on that. But the typesetter sometimes forgets, and
    then the label runs on inside the previous speaker's paragraph with no
    space around it — "…en general.Sr. Secretario (Estrada). — Se deja
    constancia…". Read that way, one senator is credited with the next
    speaker's words, which is the worst error this parser can make and the
    one a page-sample check is least likely to see.

    A label is recognised here only where the printed convention is complete:
    the title, a name, the ". —" terminator, and a sentence that has just
    ended (or the start of the block). What is found is re-emitted as a bold
    block so the ordinary label machinery handles it from there.
    """
    out = []
    found = 0
    for b in blocks:
        if (b.get("type") is not None or b["font_style"] != "normal"
                or b["size"] != body_size):
            out.append(b)
            continue
        text = b["text"]
        pieces, last = [], 0
        for m in INLINE_LABEL_RE.finditer(text):
            before = text[:m.start()].rstrip()
            if before and before[-1] not in SENTENCE_END:
                continue                     # mid-sentence mention, not a label
            pieces.append((m.start(), m.end(), m.group(0).strip()))
        if not pieces:
            out.append(b)
            continue
        for start, end, label in pieces:
            head = text[last:start]
            if head.strip():
                out.append({**b, "text": head})
            out.append({**b, "text": label, "font_style": "bold"})
            last = end
            found += 1
        tail = text[last:]
        if tail.strip():
            out.append({**b, "text": tail})
    if found:
        print(f"Etiquetas en redonda recuperadas: {found}.")
    return out, found


def reclaim_truncated_label(blocks, body_size):
    """Give the label back its last letters when the bold stops short of them.

    The mirror of the case below. The page prints "Sr. Presidente. – Se gira a
    la Comisión…", but the closing "e" of "Presidente" is set in the roman face
    rather than the bold, so the style grouping ends the label at "Sr.
    President" and the turn opens "e. – Se gira…". The speaker recorded is then
    a word cut in half — "Sr. President", "Sra. Higone", "Sr. Pre" — which
    matches no person, and the words that finish the name are read as speech.

    Taken back only where every one of these holds: the bold block reads as a
    label but carries no terminator of its own, the block after it is ordinary
    text, it begins in lower case (so it continues a word rather than opening a
    sentence), and its terminator arrives within the first 30 characters. A turn
    that legitimately resumes in lower case — an answer echoing the question —
    has no terminator ahead of it and is left alone.
    """
    out, taken = [], 0
    skip = 0
    for idx, b in enumerate(blocks):
        if skip:
            skip -= 1
            continue
        t = b["text"].strip()
        if not (b.get("type") is None and b["font_style"] == "bold"
                and b["size"] == body_size and SPEAKER_RE.match(t)
                and not LABEL_TERM_RE.search(t)):
            out.append(b)
            continue
        # the face can change more than once inside one name — "Sr. God" /
        # "o" / "y.-" is three blocks — so the rest of the label is gathered
        # from as many as it takes, within a budget of 30 characters
        run, chars = [], ""
        for nxt in blocks[idx + 1:idx + 5]:
            if nxt.get("type") is not None or nxt["size"] != body_size:
                break
            piece = nxt["text"].lstrip() if not run else nxt["text"]
            if not run and not piece[:1].islower():
                break
            run.append(nxt)
            chars += piece
            if len(chars) > 30 or LABEL_TERM_RE.search(chars[:30]):
                break
        m = LABEL_TERM_RE.search(chars[:30]) if chars else None
        if m and "." not in chars[:m.start()]:
            b = {**b, "text": t + chars[:m.end()]}
            rest = chars[m.end():]
            last = run[-1]
            last["text"] = rest
            last["font_style"] = "normal"
            skip = len(run)              # the ones wholly absorbed disappear
            out.append(b)
            out.append(last)
            taken += 1
            continue
        out.append(b)
    if taken:
        print(f"Etiquetas cortadas a mitad de palabra reunidas: {taken}.")
    return out, taken


def split_label_spillover(blocks, body_size):
    """Give the turn back its first words when they were bolded with the label.

    Some sittings carry the opening punctuation of the speech inside the
    bold run that holds the label — "Sr. Mayans. – ¡" — because the
    typesetter never closed the bold before "¡Sí!". Read whole, the label
    becomes a speaker of its own and never matches a person. The label
    ends at its ". —" terminator by convention, so whatever follows is
    speech: it is split off into a normal-style block of its own and
    picked up as the first words of the turn.
    """
    out = []
    split = 0
    for idx, b in enumerate(blocks):
        t = b["text"].strip()
        if (b.get("type") is None and b["font_style"] == "bold"
                and b["size"] == body_size and SPEAKER_RE.match(t)):
            m = LABEL_TERM_RE.search(t)
            if m and (spill := t[m.end():].strip()):
                nxt = blocks[idx + 1] if idx + 1 < len(blocks) else None
                out.append({**b, "text": t[:m.end()]})
                # left standing alone, a spill of one or two characters is read
                # as page furniture further down and the turn loses its first
                # letter — "T" dropped and the turn opening "iene la palabra".
                # So the face of the block below does not decide this: only
                # that it is ordinary text and not a label of its own.
                if (nxt is not None and nxt.get("type") is None
                        and nxt["size"] == body_size
                        and not SPEAKER_RE.match(nxt["text"].strip())):
                    # the spill opens the very next sentence ("¡" + "Sí!"):
                    # rejoin without a separator, the typesetter had none
                    nxt["text"] = spill + nxt["text"].lstrip()
                    b = None
                else:
                    b = {**b, "text": spill, "font_style": "normal"}
                split += 1
        if b is not None:
            out.append(b)
    print(f"Etiquetas con texto hablado adherido separadas: {split}.")
    return out, split


def identify_speakers(blocks, body_size):
    """Attribute speech to speakers; gate labels on ^Sr./Sra. patterns.

    Bold body-size blocks that are NOT speaker labels become typed
    headings and RESET the current speaker (they mark section changes:
    INSERCIONES, Actas, signature) instead of becoming phantom speakers.
    """
    annotated = []
    current = None
    turn_id = 0
    open_turn = None   # turn whose first speech block has already been seen
    speech = 0
    paren_labels = {}  # "(Name)" seen inside a full label -> that full label
    i = 0
    while i < len(blocks):
        b = blocks[i]
        i += 1
        t = b["text"].strip()
        if b.get("type") in ("furniture", "event", "inline"):
            annotated.append(b)
            continue
        if b["font_style"] == "bold" and b["size"] == body_size:
            if BOLD_JUNK_RE.match(t):
                continue             # punctuation shard of a split label — not a
                                     # heading; must not reset the running speaker
            t = LEAD_JUNK_RE.sub("", t)  # previous sentence's bold-glued period
            if SPEAKER_RE.match(t):
                label = t
                # 2000–2013 chair labels: the parenthetical is a separate
                # normal-style block ("Sr. Presidente" + "(Pampuro)") — absorb
                # it into the label it belongs to
                if not LABEL_CLOSED_RE.search(t) and i < len(blocks):
                    nxt = blocks[i]
                    if (nxt.get("type") is None and nxt["font_style"] == "normal"
                            and nxt["size"] == body_size
                            and (m := PAREN_HEAD_RE.match(nxt["text"]))):
                        label = f"{t} {m.group(1)}"
                        rest = nxt["text"][m.end():]
                        if rest.strip():
                            nxt["text"] = rest
                        else:
                            i += 1  # the block was only the parenthetical
                elif t.endswith("(") and i < len(blocks):
                    # reversed shatter: bold "Sr. Presidente (" + normal
                    # "Pampuro). – speech…" — pull the name into the label
                    nxt = blocks[i]
                    if (nxt.get("type") is None and nxt["font_style"] == "normal"
                            and nxt["size"] == body_size):
                        m = re.match(r"\s*([^()]{1,60}\))", nxt["text"])
                        if m:
                            label = t + m.group(1)
                            rest = LEAD_JUNK_RE.sub("", nxt["text"][m.end():].lstrip())
                            if rest:
                                nxt["text"] = rest
                            else:
                                i += 1  # nothing left of that block
                        elif (i + 1 < len(blocks)
                                and re.fullmatch(r"[^()]{1,60}", nxt["text"].strip())
                                and blocks[i + 1]["font_style"] == "bold"
                                and blocks[i + 1]["size"] == body_size
                                and blocks[i + 1]["text"].lstrip().startswith(")")):
                            # both parens bold, the name normal between them:
                            # bold "Sr. Presidente (" + normal "Yoma" + bold
                            # "). — ". Without this the name reads as the first
                            # word of the speech and the chair goes unnamed.
                            label = t + nxt["text"].strip() + ")"
                            i += 1
                current = label      # consumed: label blocks are not emitted
                turn_id += 1         # a printed label opens a NEW turn; speech
                                     # resuming after an event without a label
                                     # stays in the same turn (ParlaMint-style)
                pm = re.search(r"\(([^()]{1,60})\)", label)
                if pm:
                    paren_labels[pm.group(1).strip()] = label
            elif (pm := PAREN_LABEL_RE.match(t)) and pm.group(1).strip() in paren_labels:
                # 2013-era convention: repeated chair turns carry only the
                # bare parenthetical — reuse the full label it belongs to
                current = paren_labels[pm.group(1).strip()]
                turn_id += 1
            elif LABEL_FRAGMENT_RE.match(t):
                current = None       # shattered label: attribution is lost from
                b["type"] = "other"  # here — honest debris, not a phantom heading
                annotated.append(b)
            else:
                b["type"] = "heading"
                current = None
                annotated.append(b)
            continue
        if b["font_style"] == "normal" and b["size"] == body_size:
            if current:
                if turn_id != open_turn:
                    # the ". —" that closes the label is printed in its own
                    # style run, so it lands at the head of the first speech
                    # block of the turn; it is punctuation, not words spoken
                    b["text"] = TURN_LEAD_RE.sub("", b["text"], count=1)
                    open_turn = turn_id
                b["speaker"] = current
                b["type"] = "speech"
                b["turn_id"] = turn_id
                speech += 1
            else:
                b["type"] = "other"
            annotated.append(b)
            continue
        b.setdefault("type", "other")
        annotated.append(b)
    print(f"Identificación de speakers completa. Se anotaron {speech} bloques con speakers.")
    return annotated


def clean_speaker_names(blocks):
    """Drop the terminator printed after a speaker label.

    The formats spell it differently by year (".-", ". —", ".–", " . —"),
    and it separates the name from the words rather than belonging to the
    name — carrying it into the label would make "Sr. Pichetto. —" and
    "Sr. Pichetto" two different people downstream.
    """
    cleaned = 0
    for b in blocks:
        if b.get("speaker"):
            new = re.sub(rf"[\s.\-–—−─{PUA}:]+$", "", b["speaker"]).strip()
            if new != b["speaker"]:
                b["speaker"] = new
                cleaned += 1
    print(f"Limpieza completa. Se limpiaron {cleaned} nombres de speakers.")
    return blocks


# Punctuation that never takes a space before it on a printed page. A word set
# in italics inside a sentence — a foreign word, a newspaper's name, a Latin
# phrase — arrives as its own piece, and the comma or full stop that follows it
# is back in the body face, so it arrives as yet another piece. Joining every
# piece with a space put 4,653 of these marks adrift from the word they close.
NEVER_SPACED_BEFORE = ".,;:!?)]…»\u201d\u2019\""
# and their mirror: an opening mark takes no space AFTER it, which is the same
# fault seen from the other side — a quoted word came out as "caso " strawberry ","
NEVER_SPACED_AFTER = "([\u00ab\u00bf\u00a1\u201c\""


def rejoin(text, piece):
    """Put two pieces of one turn back together with the spacing the page shows."""
    if not text or not piece:
        return text + piece
    if (text.endswith(" ") or piece.startswith(" ")
            or piece[0] in NEVER_SPACED_BEFORE or text[-1] in NEVER_SPACED_AFTER):
        return text + piece
    return text + " " + piece


def consolidate_speaker_blocks(blocks):
    """Merge consecutive same-speaker speech into turns.

    Inline italics are absorbed into the running turn (they are content,
    not events); events, headings, furniture, and unattributed blocks
    break the turn.

    An italic run that OPENS a turn is the exception. A newspaper's name printed
    right after the label — "Sr. Jefe de Gabinete de Ministros. – La Nación es
    un diario opositor…" — would otherwise be swallowed by the turn above,
    putting another senator's words in the previous speaker's mouth. It is
    handed forward instead when the block after it belongs to somebody else and
    continues in lower case, which shows the run opens that sentence rather than
    closing the one before.
    """
    out = []
    cur = None
    inline_merged = 0
    handed_forward = 0
    for i, b in enumerate(blocks):
        if b.get("type") == "inline":
            nxt = blocks[i + 1] if i + 1 < len(blocks) else None
            opens_next = (nxt is not None and nxt.get("speaker")
                          and (cur is None or nxt["speaker"] != cur.get("speaker"))
                          and nxt["text"].lstrip()[:1].islower())
            if opens_next:
                nxt["text"] = b["text"].strip() + nxt["text"]
                nxt["pages"] = sorted(set(nxt["pages"]) | set(b["pages"]))
                handed_forward += 1
            elif cur is not None:
                cur["text"] = rejoin(cur["text"], b["text"].strip())
                cur["pages"] = sorted(set(cur["pages"]) | set(b["pages"]))
                inline_merged += 1
            else:
                b["type"] = "inline_italic"   # orphan: no active turn to join
                out.append(b)
            continue
        speaker = b.get("speaker")
        if not speaker:
            if cur is not None:
                out.append(cur)
                cur = None
            out.append(b)
            continue
        if cur is not None and speaker == cur.get("speaker") and b.get("turn_id") == cur.get("turn_id"):
            # the rest of a sentence broken by an italic word opens with the
            # punctuation that closes it, and that mark belongs to the word
            cur["text"] += (b["text"]
                            if (b["text"][:1] in NEVER_SPACED_BEFORE
                                or cur["text"][-1:] in NEVER_SPACED_AFTER)
                            else " " + b["text"])
            cur["pages"] = sorted(set(cur["pages"]) | set(b["pages"]))
        else:
            if cur is not None:
                out.append(cur)
            cur = b
    if cur is not None:
        out.append(cur)
    print(f"Consolidación completa: {len(out)} bloques finales, {inline_merged} cursivas absorbidas.")
    if handed_forward:
        print(f"Bastardillas que abren un turno, devueltas a quien las dijo: "
              f"{handed_forward}.")
    return out, inline_merged, handed_forward


# ---------------------------------------------------------------------------
# Orchestration: per-session processing, persistence, stats
# ---------------------------------------------------------------------------

SESSION_CLOSE_RE = re.compile(r"queda levantada la sesión|se levanta la sesión", re.IGNORECASE)


def demote_appendix_debris(blocks):
    """After the final session-close formula, unattributed body-size text is
    appendix material (inserted documents, signature block): furniture, not
    debris. Older layouts print appendices at body size; modern ones use
    smaller type and are already furniture by size."""
    last = None
    for idx, b in enumerate(blocks):
        if b.get("type") in ("speech", "event", "other") and SESSION_CLOSE_RE.search(b["text"]):
            last = idx
    demoted = 0
    if last is not None:
        for b in blocks[last + 1:]:
            if b.get("type") == "other":
                b["type"] = "furniture"
                demoted += 1
    if demoted:
        print(f"Apéndice: {demoted} bloques sin atribuir demovidos a furniture tras el cierre.")
    return blocks, demoted


def process_pdf(pdf_path):
    """Run the full pipeline on one PDF. Returns (blocks, chapters, stats)."""
    stats = {}

    chars, page_heights, scanned_share = extract_all_characters(str(pdf_path))
    stats["scanned_page_share"] = round(scanned_share, 3)
    stats["characters_extracted"] = len(chars)

    chars, removed = strip_page_headers(chars)
    stats["header_chars_removed"] = removed

    chars, removed = strip_page_footers(chars, page_heights)
    stats["footer_chars_removed"] = removed

    blocks = group_characters_into_text_blocks(chars)
    blocks, islands = smooth_micro_islands(blocks)
    stats["blocks_generated"] = len(blocks)
    stats["micro_islands_merged"] = islands

    # try body-size candidates until one yields a session opening
    body_size, marker_mode, cut_blocks = None, "none", []
    for cand in body_size_candidates(chars):
        cut_blocks, marker_mode = cut_front_matter(blocks, cand)
        if marker_mode != "none":
            body_size = cand
            break
    if body_size is None:
        body_size = body_size_candidates(chars)[0]
    blocks = cut_blocks
    stats["body_size"] = body_size
    stats["marker_mode"] = marker_mode
    stats["blocks_after_marker"] = len(blocks)
    if not blocks:
        stats["error"] = "no_opening_found"
        return [], {}, stats

    blocks, apparatus_cut = cut_apparatus_text(blocks)
    stats["apparatus_text_cut"] = apparatus_cut

    blocks, empty_removed = remove_empty_blocks(blocks)
    stats["empty_blocks_removed"] = empty_removed

    blocks, split_words = rejoin_split_word(blocks, body_size)
    stats["split_words_rejoined"] = split_words

    blocks, events = classify_blocks(blocks, body_size)
    stats["events_tagged"] = events

    blocks, note_tails = reattach_note_tails(blocks)
    stats["note_tails_reattached"] = note_tails

    blocks, note_dashes, note_colons, note_tails = \
        return_stage_direction_punctuation(blocks)
    stats["note_dashes_returned"] = note_dashes
    stats["note_colons_returned"] = note_colons
    stats["note_tails_returned"] = note_tails

    blocks, chapters, title_label_cuts = assign_chapter_to_blocks(blocks, body_size)
    stats["chapters_detected"] = len(chapters)
    stats["title_labels_cut"] = title_label_cuts

    blocks, fused = split_fused_labels(blocks, body_size)
    stats["fused_labels_split"] = fused

    blocks, inline_labels = split_inline_labels(blocks, body_size)
    stats["inline_labels_recovered"] = inline_labels

    blocks, label_rejoined = reclaim_truncated_label(blocks, body_size)
    stats["labels_rejoined"] = label_rejoined

    blocks, spillover = split_label_spillover(blocks, body_size)
    stats["label_spillover_split"] = spillover

    blocks = identify_speakers(blocks, body_size)
    blocks = clean_speaker_names(blocks)
    blocks, inline_merged, italics_forward = consolidate_speaker_blocks(blocks)
    stats["inline_merged"] = inline_merged
    stats["italics_handed_forward"] = italics_forward

    blocks, demoted = demote_appendix_debris(blocks)
    stats["appendix_demoted"] = demoted

    blocks, links, markers, wordless = clean_final_speech(blocks)
    stats["contents_links_cut"] = links
    stats["footnote_markers_cut"] = markers
    stats["wordless_turns_dropped"] = wordless

    return blocks, chapters, stats


def blocks_to_frame(blocks, chapters, meta):
    """Map pipeline blocks to the schema rows of the session table."""
    rows = []
    for seq, b in enumerate(blocks):
        speaker = b.get("speaker")
        chapter = b.get("capítulo")
        rows.append({
            "session_id": meta["session_id"],
            "session_date": meta["session_date"],
            "session_type": meta["session_type"],
            "sesion": meta["sesion"],
            "reunion": meta["reunion"],
            "seq": seq,
            "type": b.get("type") or ("speech" if speaker else "other"),
            "event_type": b.get("event_type"),
            "turn_id": b.get("turn_id"),
            "chapter": chapter,
            "chapter_title": chapters.get(chapter) if chapter else None,
            "speaker_raw": speaker,
            "text": b["text"],
            "pages": sorted(b["pages"]) if b.get("pages") else [],
            "font": b.get("font"),
            "font_style": b.get("font_style"),
            "size": b.get("size"),
            "source_pdf": meta["source_pdf"],
            "pdf_sha256": meta["pdf_sha256"],
            "parser_version": PARSER_VERSION,
        })
    return pd.DataFrame(rows)


def load_manifest():
    """Index raw_data_manifest.csv by pdf filename (empty dict if absent)."""
    if not MANIFEST_PATH.exists():
        return {}
    df = pd.read_csv(MANIFEST_PATH, dtype=str)
    return {row["pdf_filename"]: row for _, row in df.iterrows()}


def session_meta_for(pdf_path, manifest):
    """Session identity/provenance from the manifest, else from the sidecar."""
    row = manifest.get(pdf_path.name)
    if row is not None:
        date_iso = row["session_date_iso"]
        tipo, sesion, reunion = row["tipo"], row["sesion"], row["reunion"]
        sha = row["pdf_sha256"]
    else:
        sidecar = pdf_path.with_suffix(".json")
        meta = json.loads(sidecar.read_text(encoding="utf-8")) if sidecar.exists() else {}
        try:
            date_iso = datetime.strptime(meta.get("fecha", ""), "%d-%m-%Y").date().isoformat()
        except ValueError:
            date_iso = ""
        tipo = meta.get("tipo", "")
        sesion = str(meta.get("sesion", "") or "")
        reunion = str(meta.get("reunion", "") or "")
        sha = hashlib.sha256(pdf_path.read_bytes()).hexdigest()

    try:
        reunion_tag = f"r{int(reunion):02d}"
    except (TypeError, ValueError):
        reunion_tag = "rxx"
    session_id = f"{date_iso}_{reunion_tag}" if date_iso else pdf_path.stem

    return {
        "session_id": session_id,
        "session_date": date_iso,
        "session_type": tipo,
        "sesion": sesion,
        "reunion": reunion,
        "source_pdf": pdf_path.name,
        "pdf_sha256": sha,
    }


def parse_one(pdf_path_str, meta):
    """Worker: parse one PDF, write its Parquet table and log, return stats."""
    pdf_path = Path(pdf_path_str)
    out_path = OUT_DIR / "blocks" / f"{meta['session_id']}.parquet"
    log_path = OUT_DIR / "logs" / f"{meta['session_id']}.log"
    stats = {"session_id": meta["session_id"], "file_name": pdf_path.name}
    start = time.monotonic()

    try:
        with log_path.open("w", encoding="utf-8") as log, contextlib.redirect_stdout(log):
            blocks, chapters, run_stats = process_pdf(pdf_path)
            stats.update(run_stats)
            if blocks:
                frame = blocks_to_frame(blocks, chapters, meta)
                frame.to_parquet(out_path, index=False)
                counts = frame["type"].value_counts()
                stats["rows_written"] = len(frame)
                stats["speech_blocks"] = int(counts.get("speech", 0))
                stats["heading_blocks"] = int(counts.get("heading", 0))
                stats["furniture_blocks"] = int(counts.get("furniture", 0))
                stats["other_blocks"] = int(counts.get("other", 0))
    except Exception as e:  # per-file isolation: one bad PDF must not kill the run
        stats["error"] = f"{type(e).__name__}: {e}"

    stats["duration_s"] = round(time.monotonic() - start, 1)
    stats["parser_version"] = PARSER_VERSION
    stats["parsed_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return stats


def write_stats(new_rows, stats_path):
    """Merge this run's stats into parse_stats.csv (new rows win per file)."""
    new = pd.DataFrame(new_rows)
    if stats_path.exists():
        old = pd.read_csv(stats_path)
        if not new.empty:
            old = old[~old["file_name"].isin(new["file_name"])]
        new = pd.concat([old, new], ignore_index=True)
    if new.empty:
        return
    for col in STATS_COLUMNS:
        if col not in new.columns:
            new[col] = None
    new = new[STATS_COLUMNS].sort_values("file_name")
    new.to_csv(stats_path, index=False)


def main():
    ap = argparse.ArgumentParser(description="Parse Senate transcript PDFs into per-session Parquet block tables.")
    ap.add_argument("--only", metavar="FILENAME", help="process a single PDF by filename")
    ap.add_argument("--limit", type=int, help="process at most N PDFs")
    ap.add_argument("--force", action="store_true", help="re-parse sessions whose output already exists")
    ap.add_argument("--workers", type=int, default=6, help="parallel worker processes (default: 6)")
    args = ap.parse_args()

    if not RAW_DIR.is_dir():
        sys.exit(f"Raw data dir not found: {RAW_DIR} — is the data/ symlink in place? (see DATA.md)")
    (OUT_DIR / "blocks").mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "logs").mkdir(parents=True, exist_ok=True)

    manifest = load_manifest()
    pdfs = sorted(RAW_DIR.glob("*.pdf"))
    if args.only:
        pdfs = [p for p in pdfs if p.name == args.only]
        if not pdfs:
            sys.exit(f"No PDF named {args.only!r} in {RAW_DIR}")
    if args.limit:
        pdfs = pdfs[:args.limit]

    jobs, skipped = [], 0
    for pdf in pdfs:
        meta = session_meta_for(pdf, manifest)
        if (OUT_DIR / "blocks" / f"{meta['session_id']}.parquet").exists() and not args.force:
            skipped += 1
            continue
        jobs.append((pdf, meta))

    print(f"{len(pdfs)} PDFs selected, {skipped} already parsed, {len(jobs)} to process "
          f"(workers={args.workers}, parser {PARSER_VERSION})", flush=True)

    new_rows = []
    if jobs:
        with ProcessPoolExecutor(max_workers=args.workers) as pool:
            futures = {
                pool.submit(parse_one, str(pdf), meta): meta["session_id"]
                for pdf, meta in jobs
            }
            for i, fut in enumerate(as_completed(futures), 1):
                stats = fut.result()
                new_rows.append(stats)
                flag = f"  ERROR: {stats['error']}" if stats.get("error") else ""
                print(f"[{i}/{len(jobs)}] {stats['session_id']} "
                      f"({stats.get('rows_written', 0)} rows, {stats['duration_s']}s){flag}", flush=True)

    stats_path = OUT_DIR / "parse_stats.csv"
    write_stats(new_rows, stats_path)

    errors = [r for r in new_rows if r.get("error")]
    print(f"\nDone: {len(new_rows)} parsed, {len(errors)} errors. Stats: {stats_path}")
    for r in errors:
        print(f"  {r['file_name']}: {r['error']}")


if __name__ == "__main__":
    main()
