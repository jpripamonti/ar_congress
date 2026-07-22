"""Parse Argentine Senate stenographic transcript PDFs (versiones
taquigraficas) into per-session block tables.

v0.3.0 pipeline (empirically recalibrated against the stratified profile of
the corpus — see git history for the v0.2.0 heuristics it replaces):

1. Extract characters with pdfplumber (text, font, size, page, y-position).
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

PARSER_VERSION = "0.4.0"

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

# 2000–2013 layouts split the chair label across styles:
#   bold "Sr. Presidente" + normal "(Pampuro)" + bold ". –"
# The shards need reassembly (identify_speakers) instead of the bold
# punctuation becoming a heading that resets the running speaker.
BOLD_JUNK_RE = re.compile(r'^[\s.:;,\-–—−…"“”«»ºª°()]+$')
PAREN_ONLY_RE = re.compile(r"^\([^()]{1,60}\)$")
LABEL_CLOSED_RE = re.compile(r"[–—−(]")  # label already carries its own paren/terminator
LABEL_SPLIT_RE = re.compile(r"\s(?=(?:Sr|Sra|Srta|Sres)\.\s)")  # fused "TÍTULO Sr. X" headings
LABEL_FRAGMENT_RE = re.compile(r"^[.\s]*(?:Sr|Sra|Srta|Sres)$")  # shattered label: reset, not heading
LEAD_JUNK_RE = re.compile(r'^[\s.:;,\-–—−…"“”«»]+')  # bold-glued tail of the previous sentence
PAREN_LABEL_RE = re.compile(r"^\(([^()]{1,60})\)[\s.\-–—−:]*$")  # bare "(Rojkés de Alperovich).-" chair label
DGT_RE = re.compile(r"^Dirección General de Taquígrafos\b")

# Ordered: first match wins. Applied lowercased.
EVENT_SUBTYPES = [
    ("timestamp", re.compile(r"^[–—-]?\s*(?:a las|son las)\s+\d|^[–—-]?\s*en la ciudad aut")),
    ("vote", re.compile(r"votaci[oó]n|se vota|resulta[n]?\s+(?:aprobad|rechazad)|afirmativ|negativ|unanimidad|asentimiento")),
    ("pause", re.compile(r"luego de (?:unos )?instantes|cuarto intermedio|se reanuda")),
    ("applause", re.compile(r"aplausos")),
    ("laughter", re.compile(r"risas")),
    ("incident", re.compile(r"manifestaciones|interrupci|abucheo|cánticos|murmullos|contenido no inteligible|fuera del alcance del micrófono")),
    ("stage", re.compile(r"ocupa la presidencia|ingresa|se retira|izamiento|entonaci|himno|arrían")),
]

STATS_COLUMNS = [
    "session_id",
    "file_name",
    "characters_extracted",
    "header_chars_removed",
    "footer_chars_removed",
    "body_size",
    "blocks_generated",
    "micro_islands_merged",
    "marker_mode",
    "blocks_after_marker",
    "empty_blocks_removed",
    "chapters_detected",
    "events_tagged",
    "inline_merged",
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
    with pdfplumber.open(pdf_path) as pdf:
        pages = pdf.pages if max_pages is None else pdf.pages[:max_pages]
        for i, page in enumerate(pages):
            page_heights[i + 1] = page.height
            for c in page.chars:
                family = SUBSET_RE.sub("", c["fontname"])
                low = family.lower()
                if "bold" in low:
                    style = "bold"
                elif "italic" in low or "oblique" in low:
                    style = "italic"
                else:
                    style = "normal"
                chars.append({
                    "text": c["text"],
                    "font": family,
                    "font_style": style,
                    "size": round(c["size"], 1),
                    "page": i + 1,
                    "top": c["top"],
                })
    print(f"Extracción completa. Se extrajeron {len(chars)} caracteres en total.")
    return chars, page_heights


def strip_page_headers(chars):
    """Drop every char at or above the per-page "Pág. N" dateline.

    The dateline (with the motto above it, where present) is the one
    running-header invariant across all 2020-2024 formats. Pages without
    a dateline (cover, plates) are left untouched — the front-matter cut
    handles those at block level.
    """
    # line assembly per page, top band only
    lines = {}
    for c in chars:
        if c["top"] < 150:
            lines.setdefault((c["page"], round(c["top"] / 3)), []).append(c)

    cutoffs = {}
    for (page, _), line_chars in sorted(lines.items()):
        if page in cutoffs:
            continue
        text = "".join(ch["text"] for ch in line_chars)  # extraction order = reading order
        if PAG_LINE_RE.search(text):
            cutoffs[page] = max(ch["top"] for ch in line_chars) + 0.5

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
    """
    lines = {}
    for c in chars:
        h = page_heights.get(c["page"], 842)
        if c["top"] > h - 70:
            lines.setdefault((c["page"], round(c["top"] / 3)), []).append(c)

    cutoffs = {}
    for (page, _), line_chars in sorted(lines.items()):
        text = "".join(ch["text"] for ch in line_chars)
        if "Taquígrafo" in text or "Direcci" in text:
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
    return reassign_hyphens_to_italic_blocks(blocks)


def reassign_hyphens_to_italic_blocks(blocks):
    """Mueve los guiones finales al inicio del siguiente bloque cursivo."""
    for i in range(len(blocks) - 1):
        cur, nxt = blocks[i], blocks[i + 1]
        if cur["text"].strip().endswith("-") and nxt["font_style"] == "italic":
            cur["text"] = cur["text"].strip().rstrip("-")
            nxt["text"] = "-" + nxt["text"].strip()
    return blocks


def smooth_micro_islands(blocks):
    """Weld letterless micro-blocks back into their neighbors.

    2000–2013 PDFs flip style on single characters ("29º", stray dots),
    splitting one sentence into three blocks; a bold island then acts as a
    phantom heading that resets speaker attribution. Absorb the island into
    the preceding block and, when the following block resumes the preceding
    block's style, rejoin that continuation too.
    """
    out = []
    merged = 0
    resume_key = None
    for b in blocks:
        t = b["text"].strip()
        if out and t and len(t) <= 2 and not any(ch.isalpha() for ch in t) \
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


def remove_empty_blocks(blocks):
    """Elimina los bloques vacíos o de solo espacios."""
    kept = [b for b in blocks if b["text"].strip()]
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


def assign_chapter_to_blocks(blocks, body_size):
    """Detect bold body-size "N. Título" headings; assign chapters to blocks."""
    chapters = {}
    current = None
    out = []
    for b in blocks:
        t = LEAD_JUNK_RE.sub("", b["text"].strip())
        if (b.get("type") is None and b["font_style"] == "bold" and b["size"] == body_size
                and CHAPTER_RE.match(t)):
            # split fused "N. Título  Sra. Presidenta..." blocks on double spaces
            parts = [p.strip() for p in t.split("  ") if p.strip()] if "  " in t else [t]
            # 2000–2013 fuses with single spaces: cut a trailing speaker label
            # off each part so it can open its own turn downstream
            fission = []
            for p in parts:
                last = None
                for last in LABEL_SPLIT_RE.finditer(p):
                    pass
                if last and SPEAKER_RE.match(p[last.end():]):
                    fission += [p[:last.start()].strip(), p[last.end():].strip()]
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
    print(f"Asignación de capítulos completa. Se detectaron {len(chapters)} capítulos.")
    return out, chapters


def identify_speakers(blocks, body_size):
    """Attribute speech to speakers; gate labels on ^Sr./Sra. patterns.

    Bold body-size blocks that are NOT speaker labels become typed
    headings and RESET the current speaker (they mark section changes:
    INSERCIONES, Actas, signature) instead of becoming phantom speakers.
    """
    annotated = []
    current = None
    turn_id = 0
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
                            and PAREN_ONLY_RE.match(nxt["text"].strip())):
                        label = f"{t} {nxt['text'].strip()}"
                        i += 1
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
    """Elimina el ".-" final de los nombres de speakers."""
    cleaned = 0
    for b in blocks:
        if b.get("speaker"):
            new = re.sub(r"\.\-$", "", b["speaker"]).strip()
            if new != b["speaker"]:
                b["speaker"] = new
                cleaned += 1
    print(f"Limpieza completa. Se limpiaron {cleaned} nombres de speakers.")
    return blocks


def consolidate_speaker_blocks(blocks):
    """Merge consecutive same-speaker speech into turns.

    Inline italics are absorbed into the running turn (they are content,
    not events); events, headings, furniture, and unattributed blocks
    break the turn.
    """
    out = []
    cur = None
    inline_merged = 0
    for b in blocks:
        if b.get("type") == "inline":
            if cur is not None:
                cur["text"] += " " + b["text"].strip()
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
            cur["text"] += " " + b["text"]
            cur["pages"] = sorted(set(cur["pages"]) | set(b["pages"]))
        else:
            if cur is not None:
                out.append(cur)
            cur = b
    if cur is not None:
        out.append(cur)
    print(f"Consolidación completa: {len(out)} bloques finales, {inline_merged} cursivas absorbidas.")
    return out, inline_merged


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

    chars, page_heights = extract_all_characters(str(pdf_path))
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

    blocks, empty_removed = remove_empty_blocks(blocks)
    stats["empty_blocks_removed"] = empty_removed

    blocks, events = classify_blocks(blocks, body_size)
    stats["events_tagged"] = events

    blocks, chapters = assign_chapter_to_blocks(blocks, body_size)
    stats["chapters_detected"] = len(chapters)

    blocks = identify_speakers(blocks, body_size)
    blocks = clean_speaker_names(blocks)
    blocks, inline_merged = consolidate_speaker_blocks(blocks)
    stats["inline_merged"] = inline_merged

    blocks, demoted = demote_appendix_debris(blocks)
    stats["appendix_demoted"] = demoted

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
