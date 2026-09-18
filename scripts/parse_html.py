"""Parse the Senate's HTML transcripts into the session table.

The portal serves most sittings of 1998-2003 as the chamber's own HTML export
(212 of the 214 held come from Corel WordPerfect) rather than as a PDF. The
markup carries what the PDF only implies: a speaker's label is <b>, a
stenographer's note is <i>, a section heading is a centred <b> number and
title, and the attendance lists and the sumario sit in their own <multicol>
and <li> containers. None of the PDF pipeline's work — measuring a missing
space, telling body text from apparatus by font size, rejoining a name split
across a change of face — applies here, so this is a separate reader rather
than a branch inside parse.py. The taxonomy is shared: the same speaker
pattern and the same event subtypes classify both, so the two eras of the
corpus mean the same thing.

What the HTML cannot give is the page: there is no pagination, so `pages` is
empty and `size` is null for every row. `font_style` comes from the markup
instead of a font name, and `font` is null.

Structure is read from containers, not from offsets. The files disagree about
how many <hr> rules they carry (one to four) and three have no sumario at all,
so front matter is recognized by what encloses it — the masthead before the
first rule, the attendance list inside <multicol>, the sumario inside <li> or
in a paragraph that is nothing but a link — rather than by "the body starts
after the second rule", which is wrong in 124 of the 214 files.
"""

import re
import sys
from html.parser import HTMLParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from parse import SPEAKER_RE, classify_event  # noqa: E402

PARSER_VERSION = "0.5.0-html"

# A paragraph break: WordPerfect writes <p> with no closing tag and uses <br>
# for the lines of a masthead or the two lines of a heading.
BREAK_TAGS = {"p", "br", "hr", "li", "tr", "div", "h1", "center", "table",
              "ul", "multicol", "blockquote", "dir"}
BOLD_TAGS = {"b", "strong"}
ITALIC_TAGS = {"i", "em", "cite"}
# Footnote markers; the PDF pipeline cuts these too.
DROP_TAGS = {"sup", "script", "style", "title"}
# Two sittings of 2003 come from a different exporter that carries emphasis in
# CSS rather than in tags: <span style="font-weight: bold">. Without this the
# speaker labels in those two files are invisible and nothing is attributed.
CSS_BOLD_RE = re.compile(r"font-weight\s*:\s*(bold|[6-9]00)", re.I)
CSS_ITALIC_RE = re.compile(r"font-style\s*:\s*italic", re.I)

# The label a paragraph opens with, e.g. "Sr. Presidente" — then the chamber
# prints the holder in parentheses: "Sr. Presidente (Cafiero). -- Se gira..."
QUALIFIER_RE = re.compile(r"^\s*\(([^)]{1,60})\)")
# What separates a label from the speech: ". --", ". –", ".-", or a bare dash.
TERMINATOR_RE = re.compile(r"^\s*[.:]?\s*[-–—]{1,2}\s*")
# The same terminator when the bold run carries it: "<b>Sr. Vaquir. -- </b>".
LABEL_END_RE = re.compile(r"[.:]?\s*[-–—]{1,2}\s*$")
# A note's opening dash is presentation, and the two formats print it
# differently ("-- Se vota." against "-Se vota."); the subtype patterns are
# anchored, so it comes off before they run.
LEADING_DASH_RE = re.compile(r"^\s*[-–—−]+\s*")
CHAPTER_NUM_RE = re.compile(r"^\d{1,3}$")
# "[Volver al sumario]" and the sumario's own entries are navigation.
NAV_RE = re.compile(r"volver al sumario|^\s*\[?\s*sumario\s*\]?\s*$", re.I)


class TranscriptHTML(HTMLParser):
    """Collect paragraphs of styled text runs, with the container they sit in.

    Style is tracked by depth rather than by tag, because WordPerfect nests
    <b> inside <font> inside <b> and leaves tags unclosed across paragraphs.
    """

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.paragraphs = []
        self._runs = []
        self.bold = 0
        self.italic = 0
        # One entry per open tag, so a tag returns exactly what it added.
        self._stack = []
        self.center = 0
        self.multicol = 0
        self.listitem = 0
        self.drop = 0
        self.rules_seen = 0
        self._link = 0
        self._link_chars = 0
        self._chars = 0

    # -- paragraph handling -------------------------------------------------
    def _flush(self):
        runs = [r for r in self._runs if r["text"].strip()]
        self._runs = []
        if not runs:
            return
        self.paragraphs.append({
            "runs": runs,
            "center": self.center > 0,
            "multicol": self.multicol > 0,
            "listitem": self.listitem > 0,
            "after_rule": self.rules_seen > 0,
            # A paragraph that is only a link is navigation, not speech.
            "link_only": self._chars > 0 and self._link_chars >= self._chars,
        })
        self._link_chars = self._chars = 0

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag in DROP_TAGS:
            self.drop += 1
            return
        if tag in BREAK_TAGS:
            self._flush()
        if tag == "hr":
            self.rules_seen += 1
            return

        style = " ".join(v or "" for k, v in attrs if k.lower() == "style")
        bold = int(tag in BOLD_TAGS or bool(CSS_BOLD_RE.search(style)))
        italic = int(tag in ITALIC_TAGS or bool(CSS_ITALIC_RE.search(style)))
        self.bold += bold
        self.italic += italic
        self._stack.append((tag, bold, italic))

        if tag == "center":
            self.center += 1
        elif tag == "multicol":
            self.multicol += 1
        elif tag == "li":
            self.listitem += 1
        elif tag == "a":
            self._link += 1

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in DROP_TAGS:
            self.drop = max(0, self.drop - 1)
            return
        if tag in BREAK_TAGS:
            self._flush()

        # Unwind to the most recent matching open tag. WordPerfect leaves tags
        # unclosed, so an unmatched close is ignored rather than trusted.
        for i in range(len(self._stack) - 1, -1, -1):
            if self._stack[i][0] == tag:
                _, bold, italic = self._stack.pop(i)
                self.bold = max(0, self.bold - bold)
                self.italic = max(0, self.italic - italic)
                break

        if tag == "center":
            self.center = max(0, self.center - 1)
        elif tag == "multicol":
            self.multicol = max(0, self.multicol - 1)
        elif tag == "li":
            self.listitem = max(0, self.listitem - 1)
        elif tag == "a":
            self._link = max(0, self._link - 1)

    def handle_data(self, data):
        if self.drop or not data.strip():
            if data.strip():
                return
            # Keep a separating space so words do not run together.
            if self._runs and not self._runs[-1]["text"].endswith(" "):
                self._runs[-1]["text"] += " "
            return
        style = ("bold" if self.bold and not self.italic else
                 "italic" if self.italic and not self.bold else
                 "bold-italic" if self.bold and self.italic else "normal")
        text = re.sub(r"\s+", " ", data)
        self._runs.append({"text": text, "style": style})
        self._chars += len(text.strip())
        if self._link:
            self._link_chars += len(text.strip())

    def close(self):
        super().close()
        self._flush()


def read_paragraphs(path):
    """Styled paragraphs from one HTML transcript."""
    raw = path.read_bytes()
    match = re.search(rb'charset\s*=\s*"?([\w-]+)', raw[:2000], re.I)
    encoding = match.group(1).decode("ascii", "replace") if match else "latin-1"
    try:
        text = raw.decode(encoding, "replace")
    except LookupError:
        text = raw.decode("latin-1", "replace")
    parser = TranscriptHTML()
    parser.feed(text)
    parser.close()
    return parser.paragraphs


def paragraph_text(para):
    """The readable text of a paragraph, single-spaced."""
    return re.sub(r"\s+", " ", "".join(r["text"] for r in para["runs"])).strip()


def italic_share(para):
    """Fraction of a paragraph's characters set in italics."""
    total = sum(len(r["text"].strip()) for r in para["runs"])
    if not total:
        return 0.0
    ital = sum(len(r["text"].strip()) for r in para["runs"]
               if r["style"] in ("italic", "bold-italic"))
    return ital / total


def split_label(para):
    """(label, speech) when a paragraph opens with a speaker's label, else None.

    The chamber prints the label in bold and the holder after it in the body
    face — "<b>Sr. Presidente </b>(Cafiero). -- Como último intento" — so the
    parenthetical is picked up from the run that follows, which is how the PDF
    side spells these too ("Sr. Presidente (Cafiero)").
    """
    runs = para["runs"]
    if not runs or runs[0]["style"] not in ("bold", "bold-italic"):
        return None
    raw = runs[0]["text"].strip()
    if not SPEAKER_RE.match(raw):
        return None
    # Two shapes, both common: the terminator sits inside the bold run
    # ("<b>Sr. Vaquir. -- </b>Pido la palabra.") or after it, past the
    # holder's name ("<b>Sr. Presidente </b>(Preto)<b>. -- </b>Para una...").
    closed = bool(LABEL_END_RE.search(raw))
    label = LABEL_END_RE.sub("", raw).strip().rstrip(".")
    rest = "".join(r["text"] for r in runs[1:])

    # Only when the bold run stopped short of the holder's name. A label that
    # already closed with its terminator is complete, and the parenthesis that
    # follows it belongs to the speech: "Sr. SECRETARIO (Piuzzi).- (Lee:)"
    # names the secretary, it does not name a secretary called "Lee".
    if not closed and "(" not in label:
        qualifier = QUALIFIER_RE.match(rest)
        if qualifier:
            label = f"{label} ({qualifier.group(1).strip()})"
            rest = rest[qualifier.end():]
    terminator = TERMINATOR_RE.match(rest)
    if terminator:
        rest = rest[terminator.end():]
    elif not closed:
        return None
    return label, re.sub(r"\s+", " ", rest).strip()


def classify(paragraphs):
    """Turn paragraphs into pipeline blocks, and collect the chapter titles."""
    blocks = []
    chapters = {}
    chapter = None
    pending_number = None
    turn = 0
    speaker = None
    stats = {"paragraphs": len(paragraphs), "front_matter": 0, "nav_cut": 0}

    for para in paragraphs:
        text = paragraph_text(para)
        if not text:
            continue

        # -- furniture, by the container it sits in -------------------------
        if para["multicol"] or para["listitem"] or not para["after_rule"]:
            stats["front_matter"] += 1
            blocks.append({"type": "furniture", "text": text})
            speaker = None
            continue
        if para["link_only"] or NAV_RE.search(text):
            stats["nav_cut"] += 1
            blocks.append({"type": "furniture", "text": text})
            continue

        # -- section headings ------------------------------------------------
        if para["center"]:
            if CHAPTER_NUM_RE.match(text):
                pending_number = text
                blocks.append({"type": "heading", "text": text})
                speaker = None
                continue
            if pending_number is not None:
                chapter = pending_number
                chapters[chapter] = f"{chapter} {text}"
                pending_number = None
                blocks.append({"type": "heading", "text": text, "capítulo": chapter})
                speaker = None
                continue
            blocks.append({"type": "heading", "text": text})
            speaker = None
            continue

        # -- a speaker taking the floor ---------------------------------------
        label = split_label(para)
        if label is not None:
            speaker, speech = label
            turn += 1
            blocks.append({
                "type": "speech", "speaker": speaker, "turn_id": turn,
                "text": speech, "capítulo": chapter, "font_style": "normal",
            })
            continue

        # -- a stenographer's note --------------------------------------------
        # Set in italics, and it ends the turn it interrupts.
        if italic_share(para) >= 0.6:
            blocks.append({
                "type": "event",
                "event_type": classify_event(LEADING_DASH_RE.sub("", text)),
                "text": text, "capítulo": chapter, "font_style": "italic",
            })
            speaker = None
            continue

        # -- the same speaker carrying on -------------------------------------
        if speaker is not None:
            blocks.append({
                "type": "speech", "speaker": speaker, "turn_id": turn,
                "text": text, "capítulo": chapter, "font_style": "normal",
            })
            continue

        blocks.append({"type": "other", "text": text, "capítulo": chapter})

    stats["chapters_detected"] = len(chapters)
    return blocks, chapters, stats


def consolidate(blocks):
    """Join a speaker's consecutive paragraphs into one block, as the PDF side does."""
    merged = []
    for block in blocks:
        last = merged[-1] if merged else None
        if (last is not None and block.get("type") == "speech"
                and last.get("type") == "speech"
                and last.get("turn_id") == block.get("turn_id")):
            last["text"] = f"{last['text']} {block['text']}".strip()
            continue
        merged.append(dict(block))
    return merged


def process_html(path):
    """Parse one HTML transcript. Returns (blocks, chapters, stats)."""
    paragraphs = read_paragraphs(Path(path))
    blocks, chapters, stats = classify(paragraphs)
    blocks = consolidate(blocks)
    counts = {}
    for block in blocks:
        counts[block.get("type", "other")] = counts.get(block.get("type", "other"), 0) + 1
    stats.update({
        "blocks_generated": len(blocks),
        "speech_blocks": counts.get("speech", 0),
        "heading_blocks": counts.get("heading", 0),
        "furniture_blocks": counts.get("furniture", 0),
        "other_blocks": counts.get("other", 0),
        "events_tagged": counts.get("event", 0),
    })
    return blocks, chapters, stats


# ---------------------------------------------------------------------------
# Writing the session table
# ---------------------------------------------------------------------------

def blocks_to_frame(blocks, chapters, meta):
    """Map blocks to the session-table schema the PDF side writes.

    `pages` and `size` are empty for every row: the HTML export has no
    pagination and no type size, and inventing either would let a reader
    believe a passage can be traced to a printed page when it cannot.
    """
    import pandas as pd

    rows = []
    for seq, block in enumerate(blocks):
        speaker = block.get("speaker")
        chapter = block.get("capítulo")
        rows.append({
            "session_id": meta["session_id"],
            "session_date": meta["session_date"],
            "session_type": meta["session_type"],
            "sesion": meta["sesion"],
            "reunion": meta["reunion"],
            "seq": seq,
            "type": block.get("type") or ("speech" if speaker else "other"),
            "event_type": block.get("event_type"),
            "turn_id": block.get("turn_id"),
            "chapter": chapter,
            "chapter_title": chapters.get(chapter) if chapter else None,
            "speaker_raw": speaker,
            "text": block["text"],
            "pages": [],
            "font": None,
            "font_style": block.get("font_style"),
            "size": None,
            "source_file": meta["source_file"],
            "source_format": meta["source_format"],
            "source_sha256": meta["source_sha256"],
            "parser_version": PARSER_VERSION,
        })
    return pd.DataFrame(rows)


def parse_one(path_str, meta, out_dir):
    """Worker: parse one HTML transcript, write its Parquet table, return stats."""
    import time
    from datetime import datetime, timezone

    path = Path(path_str)
    stats = {"session_id": meta["session_id"], "file_name": path.name}
    start = time.monotonic()
    try:
        blocks, chapters, run_stats = process_html(path)
        stats.update(run_stats)
        if blocks:
            frame = blocks_to_frame(blocks, chapters, meta)
            frame.to_parquet(out_dir / "blocks" / f"{meta['session_id']}.parquet", index=False)
            stats["rows_written"] = len(frame)
    except Exception as e:  # per-file isolation, as on the PDF side
        stats["error"] = f"{type(e).__name__}: {e}"
    stats["duration_s"] = round(time.monotonic() - start, 1)
    stats["parser_version"] = PARSER_VERSION
    stats["parsed_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return stats


def main():
    import argparse

    from parse import OUT_DIR, RAW_DIR, load_manifest, session_meta_for, write_stats

    ap = argparse.ArgumentParser(description="Parse the Senate's HTML transcripts.")
    ap.add_argument("--only", help="parse a single file by name")
    ap.add_argument("--limit", type=int, help="parse at most this many files")
    ap.add_argument("--force", action="store_true", help="re-parse sessions already written")
    args = ap.parse_args()

    (OUT_DIR / "blocks").mkdir(parents=True, exist_ok=True)
    manifest = load_manifest()

    files = sorted(RAW_DIR.glob("*.html"))
    if args.only:
        files = [f for f in files if f.name == args.only]
        if not files:
            raise SystemExit(f"No HTML file named {args.only!r} in {RAW_DIR}")
    if args.limit:
        files = files[:args.limit]

    jobs, skipped = [], 0
    for path in files:
        meta = session_meta_for(path, manifest)
        if (OUT_DIR / "blocks" / f"{meta['session_id']}.parquet").exists() and not args.force:
            skipped += 1
            continue
        jobs.append((path, meta))

    print(f"{len(files)} HTML transcripts, {skipped} already parsed, {len(jobs)} to process "
          f"(parser {PARSER_VERSION})", flush=True)

    rows = []
    for i, (path, meta) in enumerate(jobs, 1):
        stats = parse_one(str(path), meta, OUT_DIR)
        rows.append(stats)
        flag = f"  ERROR: {stats['error']}" if stats.get("error") else ""
        print(f"[{i}/{len(jobs)}] {stats['session_id']} "
              f"({stats.get('rows_written', 0)} rows){flag}", flush=True)

    if rows:
        write_stats(rows, OUT_DIR / "parse_stats.csv")
    errors = [r for r in rows if r.get("error")]
    print(f"\nDone: {len(rows)} parsed, {len(errors)} errors.")
    for r in errors:
        print(f"  {r['file_name']}: {r['error']}")


if __name__ == "__main__":
    main()
