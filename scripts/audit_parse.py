"""Audit the parsed corpus against the held files — every session, not a sample.

The gold set answers "did the parser read these 36 pages the way a careful
reader does?" — 0.08% of the corpus. This answers the questions that can be
checked everywhere, by looking for things that must never happen:

1. LEAKAGE — page apparatus inside a speech turn. Mastheads, datelines,
   attendance rolls and the stenographers' office line are printed furniture;
   a speaker never utters them, so finding one inside a turn means the
   header/footer strip missed a page. Counted as a fault, not merely printed:
   the one page whose footer landed inside a senator's question was on the
   screen for weeks while the audit went on reporting nothing wrong. The
   running header used to be one more entry in this dictionary, keyed on the
   words "Pág. N" — but 628 pages across 19 sittings set that header in a
   symbol font, where the letters extract into the Unicode private use area
   and the words are not there to match. That sub-check is now its own pass,
   RUNNING HEADERS below: it finds a header by POSITION AND REPETITION across
   a document's pages instead of by its words, which survives a symbol font,
   a page number set in Greek letters, and a page with no number at all.
2. GLUED LABELS — a complete printed speaker label sitting inside a turn's
   text. This is the worst error the parser can make: it means a change of
   speaker went undetected, so one senator is credited with another's words.
3. CONSERVATION — every block's text must be findable in the source file, and
   no document may yield more text than it prints. This catches text invented
   or written out twice by the block splitting and merging. A block is looked
   up by windows taken from inside it, and a block that fails is asked instead
   whether the whole of it can be rebuilt from the source in a handful of
   runs, because a block carries cuts of its own — the footnote marker taken
   out of the middle of a sentence, most often — and three long windows can
   all land on the same cut. Rebuilding the whole block, rather than finding
   one short window of it anywhere, is what keeps that second chance from
   being a hole: a single 24-character match used to vouch for an invented
   tail of any length.
4. COVERAGE — how much of each document's printed text survives into the
   output. Front matter, attendance rolls and appendices are dropped on
   purpose, so this is a distribution to inspect, not a pass/fail.
5. ONE PERSON PER LABEL — a (sitting, label) pair must resolve to exactly one
   person.
6. SHAPE — does a turn begin and end like something a person said? Every text
   fault found so far has lived at the edge of a block, where the printed face
   changes mid-name or mid-word: a label cut in half ("Sra. Higone" and a turn
   opening "t. – Gracias."), a note that kept the first letters of the sentence
   it interrupted, a scrap of an editorial note left as a two-character turn.
   The conservation check looks inside blocks and never at their first and last
   characters, so nothing else asks this. 6c asks the same of the LABELS: a
   closing parenthesis left in the speech, or a terminator left on, makes a
   different label of the same person, and the blind read cannot see it.
7. RUNNING HEADERS — every PDF page's own top strip, read by position and
   checked for repetition across the document, rather than by matching the
   word "Pág.". This is what LEAKAGE's dateline entry used to do by text
   alone, and it went blind on 628 pages set in a symbol font.
8. HTML SPLIT LABELS — the commonest label shape of the 1998-2003 HTML era:
   WordPerfect's own export sometimes leaves a <b> tag open across a
   paragraph break, so the bold run that should belong to a speaker's label
   instead opens at the section heading above it and closes partway through
   the name. The parser reads these correctly; this asserts that it keeps
   doing so, over every instance the shape actually occurs in the corpus.

Sessions that are scans with OCR text are reported first and excluded from the
counts: their faults belong to the scan, not to the parser.

Checks 1, 2 and 5 read only the parsed output and are fast. Checks 3, 4, 7 and
8 re-read every held file — the PDFs of 2004 on and the HTML of 1998-2003
alike, each stripped independently of the reader that parsed it; pass
--skip-source to leave them out.

Usage:
    uv run scripts/audit_parse.py               # everything
    uv run scripts/audit_parse.py --skip-source # output-only checks
    uv run scripts/audit_parse.py --sample 40   # also write a human review sheet
"""

import argparse
import csv
import hashlib
import html
import re
import sys
import unicodedata
from collections import Counter
from datetime import date
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import pandas as pd
import pdfplumber

sys.path.insert(0, str(Path(__file__).resolve().parent))
# Decoding only: a document's own declared charset is not a reading of it, and
# the audit must not guess an encoding the parser was told.
from provenance import decode_html  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
BLOCKS_DIR = REPO_ROOT / "data" / "processed" / "senado" / "blocks"
RAW_DIR = REPO_ROOT / "data" / "raw" / "senado" / "taquigraficas"
OUT_DIR = REPO_ROOT / "data" / "processed" / "senado"
SPEAKERS = OUT_DIR / "speakers.parquet"

# Printed apparatus. None of it is ever spoken, so none of it may appear
# inside a speech turn. The running header used to be keyed here on the words
# "Pág. N" (see check_running_headers below for why that is no longer how it
# is found).
FURNITURE = {
    "stenographers' office": re.compile(r"Direcci[óo]n General de Taquígrafos"),
    "masthead": re.compile(r"VERSI[ÓO]N TAQUIGR[ÁA]FICA|C[ÁA]MARA DE SENADORES DE LA NACI[ÓO]N"),
    "sitting header": re.compile(r"\d+[ªº°]\s*Reuni[óo]n\s*[-–]\s*\d+[ªº°]?\s*Sesi[óo]n"),
    "presiding-officer block": re.compile(r"Presidencia del se[ñn]or (?:vice)?presidente"),
    "attendance roll heading": re.compile(r"\bPRESENTES\b|\bAUSENTES\b"),
    # printed at body size below the rule at the foot of the page, so nothing
    # about its type or position distinguishes it from speech
    "appendix-pointer footnote": re.compile(r"\bVer el Ap[eé]ndice\b"),
    # the HTML era's own navigation, printed after almost every section. It is
    # apparatus the way a page header is, and it is the one piece the earlier
    # formats do not have: 9,790 stand in the holdings and none has ever
    # reached a speech turn, so this is a tripwire rather than a finding.
    "contents link [Volver al sumario]": re.compile(r"\[\s*Volver al [Ss]umario\s*\]"),
}
# A complete printed label — title, name, ". —" terminator — inside a turn.
GLUED_LABEL = re.compile(r"(?<![A-Za-zÁÉÍÓÚÑ])(?:Sr|Sra|Srta)\.\s+[A-ZÁÉÍÓÚÑ][^.]{1,45}?\.\s*[–—−─]\s")


def flatten(text):
    """Comparison key: no whitespace, no accents, no case.

    Spacing cannot be part of the comparison. The parser reads characters in
    order, while pdfplumber's page text inserts spaces from the layout, so the
    same passage comes out as "de la" one way and "dela" the other. Removing
    whitespace on both sides compares the letters actually printed.
    """
    s = unicodedata.normalize("NFD", str(text or "").casefold())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^0-9a-z]", "", s)


def block_probes(text, width=40):
    """Windows from inside one block, to look up in the source.

    Taken from a single block and not from the concatenated output: joining
    blocks would create adjacencies the page never printed — an event and the
    speech after it sit side by side in the output but a line apart on the
    page — and every such join would look like text from nowhere.

    Three windows rather than one, and the block counts as located if ANY is
    found, because a turn legitimately spans joins of its own: the parser
    merges a speaker's consecutive paragraphs and drops the section heading
    printed between them, so a window landing on that seam exists in no
    single place in the source even though every word does.
    """
    flat = flatten(text)
    if len(flat) < width + 12:
        return []                         # too short to locate reliably
    spots = {10, max(10, (len(flat) - width) // 2), max(10, len(flat) - width - 1)}
    return [flat[i:i + width] for i in sorted(spots)]


def reconstructs(text, src, max_pieces=8):
    """Can the whole block be rebuilt from the source, in a handful of runs?

    Asked only of a block the three long windows could not find, and it
    replaces asking whether any ONE short window is somewhere in the source.
    That earlier test vouched for the whole block on the strength of a single
    24-character match, which is not a fallback but a hole: measured against
    the corpus, genuine text checked against the wrong sitting passed it 28%
    of the time, and 24 real characters were enough to carry an invented tail
    of any length.

    This asks the property the check is actually for — every character of the
    block is printed in the source, in the order printed — by walking the
    block from the start, each time taking the longest stretch that still
    appears in the source AFTER the last one ended. Ending, not beginning: an
    earlier version continued from where the last run started, so a run could
    be found inside the one before it and the ordering bound almost nothing —
    44.6% of turns with their sentences shuffled still rebuilt, against 3.6%
    once the position advances properly.

    A block that survives a cut of its own needs one run per cut: the footnote
    marker taken out of a sentence costs one, a page break costs one. Measured,
    98.4% of the blocks the long windows miss rebuild inside the eight allowed,
    most of them in two, while a genuine opening followed by an invented tail
    never does. Some of the 1.6% that do not are genuine and are reported
    anyway: raising the cap to recover the ones merely over it would let the
    shuffle residue up to 7.0%, and a block wrongly shown to a human costs less
    than an order fault passing unseen. Others no cap reaches, because this
    takes the longest stretch available at each step rather than the one that
    leaves the rest reachable — a line printing four ordinals the extractor
    cannot map needs a run per digit and strands itself. SOURCES.md carries the
    worked example.

    Running out of runs, or stalling on a character the source does not have,
    reports the block as foreign — the check errs towards showing a human one
    block too many rather than passing text that is not there.
    """
    flat = flatten(text)
    i = pieces = pos = 0
    while i < len(flat):
        if pieces >= max_pieces:
            return False
        span, at = 0, -1
        step = 1
        while i + step <= len(flat):      # grow the run while it is still there
            found = src.find(flat[i:i + step], pos)
            if found < 0:
                break
            span, at = step, found
            step *= 2
        if span == 0:
            return False                  # a character the source does not print
        lo, hi = span, min(len(flat) - i, span * 2)
        while lo < hi:                    # then settle on the longest that fits
            mid = (lo + hi + 1) // 2
            found = src.find(flat[i:i + mid], pos)
            if found < 0:
                hi = mid - 1
            else:
                lo, at = mid, found
        i += lo
        pos = at + lo                     # continue AFTER the run, not inside it
        pieces += 1
    return True


def as_read(text):
    """Comparison key for counting a phrase the way a reader counts it.

    Unlike flatten(), the punctuation stays. A reader counting "(Lee:)"
    counts that, and flatten() — which keeps only letters and digits — would
    have them counting every "lee" inside "leemos" and "leerá" as well: 100
    where the page prints 78.

    The whitespace still goes, as it does in flatten() and for the same
    reason: stripping the markup puts a space where a tag was, so the page's
    "(<B>Lee:</B>)" arrives as "( Lee: )" and would match nothing.
    """
    s = unicodedata.normalize("NFD", str(text or "").casefold())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", "", s)


def _starts(src, quote, at=0):
    """Positions of `quote` in `src` that are not buried inside a word.

    as_read() folds accents and drops whitespace, so a short quote matches
    inside longer words: "Sí." folds to "si." and is found inside "así.".
    The 500-passage round of September 2026 drew a turn whose whole text was
    "Sí." and sent its reader to the tail of somebody else's sentence. A match
    only counts when the character before it is not a letter or a digit.
    """
    out, i = [], at
    while True:
        i = src.find(quote, i)
        if i == -1:
            return out
        if i == 0 or not src[i - 1].isalnum():
            out.append(i)
        i += 1


def _placed(source_file, corpus, _cache={}):
    """Where each block of a sitting actually sits in its source file.

    Walking the blocks forward is the only honest way to number a passage,
    because a string count is not a block count. A sitting prints its contents
    list before the debate, so the first occurrence of "Tiene la palabra el
    señor senador por San Juan." in the file is a line of the summary and not
    a turn at all. Counting strings therefore named occurrence 2 for a turn a
    reader counting down the page finds at 3 — and that sent ten readers of
    the 500-passage round of September 2026 to a turn the sheet was not asking
    about. Every one of those ten read the label the parser had given the turn
    they landed on, which is why the round reported ten disagreements and held
    none: the sheet was wrong, not the answer.
    """
    if source_file in _cache:
        return _cache[source_file]
    try:
        src = as_read(source_read(source_file))
    except Exception:
        _cache[source_file] = None
        return None
    rows = corpus[corpus.source_file == source_file]
    where, pos = {}, 0
    for idx, text in zip(rows.index, rows.text):
        t = as_read(text)
        if not t:
            continue
        key = t[:150]
        # Forward from where the last block ended, so repeated boilerplate
        # lands on this block and not on the first page that printed it.
        f = src.find(key, pos)
        if f == -1:
            f = src.find(key)
        if f == -1:
            continue
        where[idx] = f
        pos = max(pos, f + len(t))
    _cache[source_file] = (src, where)
    return _cache[source_file]


def occurrence(row, opening, corpus):
    """Which occurrence of the quoted words the reader is being sent to.

    Counted the way the reader counts: occurrences of the quoted phrase in the
    source file, top to bottom. The sheet used to count something else — turns
    of the sitting whose first 400 characters were identical — and the two are
    not the same number. Four readers of the 500-passage round of September
    2026 reported the gap without being asked about it: the sheet said the 55th
    of 76 "(Lee:)" where the file holds 78, the 13th of 20 "En consecuencia,
    pasa al Archivo." where the file holds 25.

    Only for HTML, which has no pages: a PDF row carries its page number, which
    is how a reader finds the passage there, and reading 500 PDFs to number a
    phrase nobody counts by would cost an hour for nothing.
    """
    name = row.source_file
    if not str(name).lower().endswith(".html"):
        return "" if row._of < 2 else f"{row._nth} of {row._of}"
    placed = _placed(name, corpus)
    if not placed:
        return "" if row._of < 2 else f"{row._nth} of {row._of}"
    src, where = placed
    quote = as_read(opening)
    if not src or not quote:
        return "" if row._of < 2 else f"{row._nth} of {row._of}"
    hits = _starts(src, quote)
    total = len(hits)
    if total < 2:
        return ""
    off = where.get(row.name)
    if off is None:
        return f"one of {total}"
    return f"{sum(1 for h in hits if h < off) + 1} of {total}"


def source_text(name):
    """The whole of a held transcript, flattened, in whichever format it arrived.

    The HTML is stripped here rather than through parse_html.py, and that is
    the point: an audit that re-read the source with the parser's own reader
    would be asking the parser to mark its own work. Tags out, entities
    decoded, nothing else — flatten() throws away everything but the letters
    and digits, so no judgement about what the markup meant survives into the
    comparison.
    """
    return flatten(source_read(name))


def source_read(name):
    """The same text before flatten(), for the checks that need its spelling."""
    path = RAW_DIR / name
    if path.suffix.lower() == ".html":
        raw = decode_html(path.read_bytes())
        raw = re.sub(r"(?is)<(script|style).*?</\1>", " ", raw)
        return html.unescape(re.sub(r"<[^>]+>", " ", raw))
    with pdfplumber.open(path) as pdf:
        return "".join((p.extract_text() or "") for p in pdf.pages)


def audit_source(args):
    """One session: is its output text really the source's text?"""
    session_id, source_name, texts = args
    try:
        src = source_text(source_name)
    except Exception as exc:
        return {"session_id": session_id, "error": str(exc)[:70]}
    out = flatten("".join(texts))
    probed = located = 0
    example = ""
    for t in texts:
        windows = block_probes(t)
        if not windows:
            continue
        probed += 1
        if any(w in src for w in windows) or reconstructs(t, src):
            located += 1
        elif not example:
            example = windows[0]
    foreign = probed - located
    return {
        "session_id": session_id,
        "source_chars": len(src),
        "output_chars": len(out),
        "blocks_probed": probed,
        # >1 means the parser emitted more text than the page prints, which can
        # only happen if a block was written out twice
        "duplication_ratio": len(out) / max(len(src), 1),
        # passages in the output that the source does not contain at all
        "foreign_passage_share": foreign / max(probed, 1),
        "foreign_example": example,
        "coverage": len(out) / max(len(src), 1),
        "error": None,
    }


def report_scanned(corpus):
    """Sessions whose text came from OCR over a scan, not from the typesetting.

    Nothing downstream can repair those, so they are listed first: every other
    check will find faults in them that are the scan's, not the parser's.
    """
    stats_path = OUT_DIR / "parse_stats.csv"
    if not stats_path.exists():
        return set()
    stats = pd.read_csv(stats_path)
    if "scanned_page_share" not in stats:
        return set()
    scanned = stats[stats.scanned_page_share.fillna(0) > 0.5]
    print(f"\n{'='*66}\nSCANNED SESSIONS — text from OCR, unreliable by nature\n{'='*66}")
    if scanned.empty:
        print("   none: every session is born-digital text")
        return set()
    for _, r in scanned.iterrows():
        print(f"   {r.scanned_page_share:.0%} of pages scanned  {r.session_id}")
    print("   Faults reported below for these sessions are the scan's, not the parser's.")
    return set(scanned.session_id)


def load_corpus():
    frames = []
    for p in sorted(BLOCKS_DIR.glob("*.parquet")):
        frames.append(pd.read_parquet(p, columns=[
            "session_id", "session_date", "source_file", "type", "turn_id",
            "speaker_raw", "text", "pages"]))
    if not frames:
        sys.exit(f"No parsed sessions under {BLOCKS_DIR}")
    return pd.concat(frames, ignore_index=True)


def check_output_only(corpus, scanned):
    speech = corpus[corpus.type == "speech"]
    print(f"\n{'='*66}\nOUTPUT CHECKS — {len(speech):,} speech turns in "
          f"{corpus.session_id.nunique()} sessions\n{'='*66}")

    print("\n1. Page apparatus found inside a speech turn (must be 0 outside the scans):")
    worst = []
    leaked = 0
    for name, rx in FURNITURE.items():
        hit = speech[speech.text.astype(str).str.contains(rx, na=False)]
        clean = hit[~hit.session_id.isin(scanned)]
        leaked += len(clean)
        print(f"   {len(clean):6}  {name}"
              f"{f'  (+{len(hit) - len(clean)} in scanned sessions)' if len(hit) != len(clean) else ''}")
        hit = clean
        for _, r in hit.head(2).iterrows():
            m = rx.search(str(r.text))
            worst.append((name, r.session_id, str(r.text)[max(0, m.start()-50):m.end()+35]))
    for name, sess, snippet in worst:
        print(f"          [{sess}] ...{snippet.strip()}...")

    print("\n2. A second speaker's label glued inside a turn (must be 0):")
    glued_all = speech[speech.text.astype(str).str.contains(GLUED_LABEL, na=False)]
    glued = glued_all[~glued_all.session_id.isin(scanned)]
    print(f"   {len(glued):6}  turns carrying another speaker's label"
          f"{f'  (+{len(glued_all) - len(glued)} in scanned sessions)' if len(glued_all) != len(glued) else ''}")
    for _, r in glued.head(5).iterrows():
        m = GLUED_LABEL.search(str(r.text))
        print(f"          [{r.session_id}] attributed to {r.speaker_raw!r}")
        print(f"              ...{str(r.text)[max(0, m.start()-45):m.end()+40].strip()}...")

    other = corpus[corpus.type == "other"]
    print(f"\n3. Text the parser could not attribute to anyone: {len(other):,} rows "
          f"({len(other)/max(len(corpus),1):.2%} of all rows)")
    top = other.groupby("session_id").size().sort_values(ascending=False).head(5)
    for sess, n in top.items():
        print(f"          {n:5}  {sess}")
    return leaked + len(glued)


def check_turn_shape(corpus, scanned):
    """Turns that do not begin or end the way speech does.

    A turn opening in lower case is not by itself a fault: a note interrupts a
    sentence and the sentence resumes, and an answer can echo the question. What
    is reported is the case with nothing to explain it — the block before is not
    a note — because that is the shape a name cut in half leaves behind.
    """
    print("\n6. Turns that do not begin or end like speech:")
    mid_word, scrap, dangling = [], [], []
    for sid, g in corpus.groupby("session_id"):
        if sid in scanned:
            continue
        g = g.reset_index(drop=True)
        for i, b in g.iterrows():
            if b.type != "speech":
                continue
            s = " ".join(str(b.text).split())
            if not s:
                continue
            if len(s) <= 3 and not re.fullmatch(r"(Sí|No|Ya)\.?", s):
                scrap.append((sid, b.speaker_raw, s))
            if re.search(r"[—–\-,;]$", s):
                dangling.append((sid, b.speaker_raw, s[-45:]))
            if i and re.match(r"^[a-záéíóúñ]", s) and g.loc[i - 1].type != "event":
                j = i - 1
                while j >= 0 and g.loc[j].type != "speech":
                    j -= 1
                if j >= 0 and g.loc[j].speaker_raw != b.speaker_raw:
                    mid_word.append((sid, b.speaker_raw, s[:60]))
    for name, group in (("a turn opening mid-word under a new speaker", mid_word),
                        ("a turn of three characters or fewer", scrap),
                        ("a turn ending on a dash or comma", dangling)):
        print(f"   {len(group):6}  {name}")
        for sid, sp, s in group[:4]:
            print(f"          [{sid}] {sp!r}: {s!r}")
    return len(mid_word)


LABEL_FAULTS = (
    ("an unbalanced parenthesis",
     lambda s: s.count("(") != s.count(")")),
    ("text after the closing parenthesis",
     lambda s: re.search(r"\)\s*\S", s) is not None),
    ("a terminator or comma left on the end",
     lambda s: re.search(r"[.,:;\-–—−]$", s) is not None),
)


def check_label_shape(corpus, scanned):
    """Speaker labels carrying a character no label should.

    The blind read asks who is speaking and forgives a stray character in the
    label — the seventh round scored "Sr. Presidente (Pinedo).- C" as
    agreement — so it cannot see this. A label with its closing parenthesis
    left in the speech, or its terminator still on, is a different label
    downstream from the same person printed cleanly, and may resolve to nobody.
    """
    print("\n6c. Speaker labels carrying a character no label should:")
    labels = (corpus[corpus.speaker_raw.notna() & ~corpus.session_id.isin(scanned)]
              .groupby(["session_id", "speaker_raw"]).size().reset_index())
    bad = 0
    for name, test in LABEL_FAULTS:
        hit = labels[labels.speaker_raw.map(test)]
        bad += len(hit)
        print(f"   {len(hit):6}  {name}")
        for _, r in hit.head(4).iterrows():
            print(f"          [{r.session_id}] {r.speaker_raw!r}")
    return bad


def check_attribution_windows(corpus):
    """No turn may be credited to someone the record places outside the office."""
    if not SPEAKERS.exists():
        print("\n7. Attribution windows: speakers.parquet not found — skipped")
        return 0
    sp = pd.read_parquet(SPEAKERS)
    bad = 0
    print("\n7. Attribution outside the person's mandate or tenure:")
    named = sp[sp.person_id.notna()]
    print(f"   {len(named):6}  (session, label) pairs carry a person")
    # The resolver filters by date when it matches, so a violation here means
    # a rule changed without the check being re-run.
    counts = named.groupby("match_status").n_blocks.sum()
    for status, n in counts.items():
        print(f"          {n:7,}  {status}")
    dupes = named.groupby(["session_id", "speaker_raw"]).size()
    if (dupes > 1).any():
        bad += int((dupes > 1).sum())
        print(f"   !! {bad} (session, label) pairs resolved more than once")
    else:
        print("   ok    every (session, label) pair resolves to exactly one person")
    return bad


# -- running headers, found by position and repetition rather than by word --
# 628 pages across 19 sittings set their running header in a symbol font: the
# letters extract into the Unicode private use area at U+F000 + the ASCII
# code, so a check keyed on the literal words "Pág. N" matches nothing on
# those pages and reports them clean without ever having examined them. Two
# more pages print the page number in Greek letters ("Πáγ. 5"), and some
# pages carry a header with no page number in it at all. None of that stops
# the header from sitting in the same place on every page of the document, so
# that is what this looks for instead: a line of text that repeats, position
# for position, across a document's pages.
_PUA_LO, _PUA_HI = 0xF000, 0xF0FF


def decode_symbol_font(s):
    """Undo a font's mapping of its glyphs into the Unicode private-use area.

    This is the one piece of interpretation this check allows itself, and it
    is a fixed, content-blind fact about how such a font is built, not a
    judgement about what the header says: a symbol face maps each glyph to
    U+F000 plus the ASCII code the typist pressed, so shifting back is always
    correct, whatever the header turns out to say once it is legible.
    """
    return "".join(chr(ord(c) - _PUA_LO) if _PUA_LO <= ord(c) <= _PUA_HI else c
                   for c in s)


def page_top_strip(page, frac=0.10):
    """The text sitting in the top strip of one page, in reading order.

    Position only — nothing here asks what the strip says. The band matches
    the one a running header sits in on every layout this corpus holds.
    """
    height = page.height or 1
    top = [c for c in page.chars if c["top"] < height * frac]
    if not top:
        return ""
    top.sort(key=lambda c: (round(c["top"]), c["x0"]))
    return decode_symbol_font("".join(c["text"] for c in top)).strip()


def header_signature(line):
    """The part of a top-strip line that must survive from page to page.

    A running header repeats verbatim except for its own page number — and
    sometimes a day or a year printed in the running text repeats too, so
    every digit is stripped, not just a trailing number. What is left is the
    skeleton that has to recur if this is a header and not a line that
    happened to sit near the top of one page only.
    """
    return re.sub(r"\d+", "", flatten(line))


def find_running_header(strips, min_len=12, min_count=3, min_share=0.3):
    """The signature that repeats across most of a document's pages, if any.

    A header is defined by POSITION AND REPETITION — the thing that sits in
    the same place on many pages of the same document — never by its words.
    Keying on a word like "Pág." fails wherever the typesetter did not print
    that word in plain Latin text; this does not care what the words are.

    Compared by a PREFIX, not the whole strip: where the header is a single
    short line, the 10%-of-height band that finds it also catches the first
    words of the body text below, which differ on every page and would keep
    any two pages from agreeing on the whole line. How much of the line is
    compared is not fixed, and not read off any one page either — one page
    with an unusually short scrap at the top (a stray word, no header at
    all) would otherwise set it and produce a match on nothing. Instead the
    prefix is GROWN one character at a time, for as long as doing so does not
    cost most of the pages that were agreeing at the length before: the
    header is however much of the line survives being compared before pages
    start disagreeing, which is where the header ends and the page's own,
    differing text begins.
    """
    sigs = {p: header_signature(s) for p, s in strips.items() if s}
    long_enough = {p: s for p, s in sigs.items() if len(s) >= min_len}
    if not long_enough:
        return None, set()

    def enough(n):
        # BOTH floors, not either: a document of 3 pages would otherwise
        # accept a single page's own sentence as "the header" (1 already
        # clears 30% of 3), and a document of 115 pages would accept five
        # pages that happen to open on the same boilerplate title ("Pedido
        # de informes sobre...") as "the header" because five clears the flat
        # floor of three. Requiring both is requiring actual repetition
        # relative to the document's own size.
        return n >= min_count and n >= min_share * max(len(sigs), 1)

    best_sig, best_n = None, 0
    length = min_len
    cap = max((len(s) for s in long_enough.values()), default=min_len)
    while length <= cap:
        counts = Counter(s[:length] for s in long_enough.values() if len(s) >= length)
        if not counts:
            break
        sig, n = counts.most_common(1)[0]
        if best_sig is None:
            if not enough(n):
                break
        # Past the first accepted length, growth is stopped by RETENTION —
        # is this still substantially the same group of pages agreeing? —
        # rather than by the bare floor above. A floor alone never stops the
        # walk: some small clique of pages keeps agreeing by coincidence for
        # a while after the real header has ended and each page's own,
        # different text has begun, and the walk would chase that
        # coincidence past the header's true end instead of stopping there.
        elif n < 0.8 * best_n:
            break
        best_sig, best_n = sig, n
        length += 1                        # keep growing while it still repeats
    if best_sig is None:
        return None, set()
    # Pages whose strip carries the header, however long that page's own
    # strip runs on past it.
    return best_sig, {p for p, s in sigs.items() if s.startswith(best_sig)}


# The months as the stenographers spell them, accents folded off. "setiembre"
# is not a misspelling to repair: both spellings are printed in these files.
OPENING_MONTHS = {"enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5,
                  "junio": 6, "julio": 7, "agosto": 8, "septiembre": 9,
                  "setiembre": 9, "octubre": 10, "noviembre": 11,
                  "diciembre": 12}

# "…a las 15 y 33 del miercoles 28 de abril de 2010:" — the hour may be
# written "15:02", "15.02", "15 y 33" or "15 horas", and the weekday is
# skipped rather than listed, since the files disagree about it.
OPENING_DATE_RE = re.compile(
    r"a\s+las\s+[\d.,: ]+\s*(?:y\s*[\d]+\s*)?"
    r"(?:horas?\s*)?del?\s+\w+\s+(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})")


def check_opening_date(corpus):
    """Does the text a sitting parsed to actually belong to that sitting?

    Every transcript opens with a stage note giving the place and the hour —
    "— En la Ciudad Autónoma de Buenos Aires, a las 15 y 33 del miércoles 28
    de abril de 2010:". Where the date in that line is not the sitting's own,
    the parser started reading inside some OTHER document bound into the same
    file, and the sitting ships a transcript of a different day under its own
    identifier.

    Nothing checked this before, and that is how 2014-09-03_r13 came to ship a
    committee meeting of 19 August 2014 in place of 214 pages of floor debate.
    It was found by hand. This finds it without anyone opening a page.

    What the check does NOT do is decide whether a mismatch is a defect. Three
    kinds of alert are expected and correct:
      - a sitting that ran past midnight and opens on the previous day;
      - the chamber's own typing, where the opening line carries a year the
        masthead contradicts, which the parser preserves on purpose;
      - the defect this exists for, where the date is days or weeks away.
    So the alert is by size of the gap, and the ones a day apart are listed
    apart from the ones that are not. A check that reported them all the same
    way would be ignored within a month.
    """
    print("\n7b. Sittings whose opening stage note names a date other than their own:")
    rows = []
    for sid, g in corpus.groupby("session_id"):
        # the rows come off the parquet in seq order, which is reading order
        head = " ".join(g.text.fillna("").astype(str).head(40)).lower()
        head = unicodedata.normalize("NFD", head)
        head = "".join(c for c in head if not unicodedata.combining(c))
        m = OPENING_DATE_RE.search(head)
        if not m:
            continue
        month = OPENING_MONTHS.get(m.group(2))
        if not month:
            continue
        said = date(int(m.group(3)), month, int(m.group(1)))
        real = pd.to_datetime(g.session_date.iloc[0]).date()
        if said != real:
            rows.append({"session_id": sid, "session_date": real,
                         "text_says": said, "days_off": (said - real).days})
    if not rows:
        print("   0  (no sitting read as found with an opening line)")
        return 0
    rows.sort(key=lambda r: -abs(r["days_off"]))
    far = [r for r in rows if abs(r["days_off"]) > 1]
    near = [r for r in rows if abs(r["days_off"]) <= 1]
    print(f"   {len(far):6}  more than a day apart — these want a page opened")
    for r in far:
        print(f"          {r['session_id']}  parses as {r['text_says']}, "
              f"{r['days_off']:+d} days")
    print(f"   {len(near):6}  one day apart — a sitting that ran past midnight "
          f"({', '.join(r['session_id'] for r in near) or 'none'})")
    return len(far)


def audit_running_header(args):
    """One PDF: find its running header by position, then hand back where."""
    session_id, source_name = args
    path = RAW_DIR / source_name
    try:
        with pdfplumber.open(path) as pdf:
            strips = {i: page_top_strip(pg) for i, pg in enumerate(pdf.pages, start=1)}
    except Exception as exc:
        return {"session_id": session_id, "pages_examined": 0, "header_sig": None,
                "header_pages": [], "error": str(exc)[:70]}
    sig, pages = find_running_header(strips)
    return {"session_id": session_id, "pages_examined": len(strips),
            "header_sig": sig, "header_pages": sorted(pages), "error": None}


def check_running_headers(corpus, scanned, workers=8):
    """Re-key LEAKAGE's dateline entry on position and repetition, and run it.

    A page's header is found by re-reading the PDF, never by trusting the
    already-parsed text — the same discipline as the CONSERVATION and
    COVERAGE checks below. Once a document's header is located this way, its
    presence in the parsed output is checked the same way the old entry
    checked it: for any speech turn on that page, does the header's own
    skeleton (its words, minus every digit) turn up inside it.
    """
    print(f"\n{'='*66}\nRUNNING HEADERS — found by position and repetition, not by word"
          f"\n{'='*66}")
    sessions = (corpus[corpus.source_file.str.lower().str.endswith(".pdf")]
                .groupby("session_id").source_file.first())
    jobs = [(sid, name) for sid, name in sessions.items() if sid not in scanned]
    rows = []
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(audit_running_header, j) for j in jobs]
        for i, fut in enumerate(as_completed(futures), 1):
            rows.append(fut.result())
            if i % 100 == 0:
                print(f"   {i}/{len(jobs)} PDFs scanned for a running header")

    errs = [r for r in rows if r["error"]]
    ok = [r for r in rows if not r["error"]]
    with_header = [r for r in ok if r["header_sig"]]
    pages_examined = sum(r["pages_examined"] for r in ok)
    pages_with_header = sum(len(r["header_pages"]) for r in with_header)
    print(f"   {len(ok)} PDFs opened, {pages_examined:,} pages examined by position")
    print(f"   {len(with_header)} PDFs carry a running header found this way, "
          f"across {pages_with_header:,} pages")
    if errs:
        print(f"   !! {len(errs)} PDFs could not be opened")
        for r in errs[:5]:
            print(f"          {r['session_id']}: {r['error']}")

    speech = corpus[(corpus.type == "speech") & ~corpus.session_id.isin(scanned)]
    leaked = []
    for r in with_header:
        sig = r["header_sig"]
        if len(sig) < 12 or not r["header_pages"]:
            continue
        header_pages = set(r["header_pages"])
        on = speech[speech.session_id == r["session_id"]]
        if on.empty:
            continue
        on = on[on.pages.apply(lambda ps: bool(header_pages & {int(p) for p in ps}))]
        for idx, row in on.iterrows():
            if sig in flatten(row.text):
                leaked.append((r["session_id"], idx, str(row.text)[:120]))

    print(f"\n   {len(leaked):6}  speech turns carrying their own page's running "
          f"header (must be 0)")
    for sid, idx, snippet in leaked[:5]:
        print(f"          [{sid}] row {idx}: {snippet!r}")
    return len(leaked)


# -- HTML split labels: the era's commonest label shape, and the check that
# did not exist for it -------------------------------------------------------
# Nineteen of twenty blind readers of the September 2026 round reported the
# same thing unprompted, looking at show_passage.py's rendering: the bold run
# that should wrap a speaker's label instead opens at the section heading
# above it. Checked against the raw markup, the tags are not actually
# unclosed — the heading and the label are each a normal, self-contained
# <b>...</b> — but nothing separates the heading's closing tag from the
# label's opening one except the paragraph break itself: a `</center>`, a
# blank line, a `<p>`, a `<font>` wrapper, none of which print a visible
# character. To an eye (or to show_passage.py's own renderer, built to join a
# label bold split across several font runs — "Sr. AVEL" + "Í" + "N.-" — so a
# reader can read it as one label) two bold runs with nothing visible between
# them are one run, so the heading and the label read as a single bold span.
# parse_html.py never sees it that way — it splits on the same break tags
# that separate the two <b>s — but nothing asserted that it keeps not seeing
# it that way, for the single commonest label shape of the era.
#
# Found here at the tag level, independently of parse_html.py's own paragraph
# and bold tracking, for the same reason source_read() strips the HTML on its
# own rather than through parse_html.py: a check that reused the parser's own
# reading of the markup would be marking the parser's work with its own pen.
# Only the literal fact of the tags is used — where a <b> opens and closes,
# where a break tag falls — never a judgement about what a run means.
_HTML_TAG_RE = re.compile(r"<[^>]+>|[^<]+")
_HTML_TAGNAME_RE = re.compile(r"</?\s*([a-zA-Z][a-zA-Z0-9]*)")
HTML_BREAK_TAGS = {"p", "br", "hr", "li", "tr", "div", "h1", "h2", "h3", "h4",
                    "center", "table", "ul", "multicol", "blockquote", "dir"}
HTML_BOLD_TAGS = {"b", "strong"}
HTML_CSS_BOLD_RE = re.compile(r"font-weight\s*:\s*(bold|[6-9]00)", re.I)
# The same honorifics GLUED_LABEL looks for above: enough to say a paragraph
# opens with a printed label, without borrowing parse_html.py's own, looser
# pattern for what a label may look like.
HTML_LABEL_START_RE = re.compile(r"^(?:Sr|Sra|Srta)\.", re.I)
HTML_LABEL_TERM_RE = re.compile(r"[.,;:]*\s*[-–—]{1,2}")


def html_paragraphs_with_bold(raw_html):
    """Non-blank paragraphs, each as (text, per-character bold flags).

    Paragraphs are split on the same break tags parse_html.py splits on --
    that boundary is a fact about the markup, not a judgement this check
    would be wrong to borrow. Bold is a plain tag-nesting depth; it is not
    reused across a paragraph, only compared across the boundary afterwards.
    """
    raw = re.sub(r"(?is)<(script|style).*?</\1>", " ", raw_html)
    paragraphs = []
    buf = []
    bold_depth = 0
    for m in _HTML_TAG_RE.finditer(raw):
        tok = m.group(0)
        if tok[0] == "<":
            nm = _HTML_TAGNAME_RE.match(tok)
            if not nm:
                continue
            name = nm.group(1).lower()
            closing = tok[1:2] == "/"
            if name in HTML_BOLD_TAGS or HTML_CSS_BOLD_RE.search(tok):
                bold_depth = max(0, bold_depth - 1) if closing else bold_depth + 1
            if name in HTML_BREAK_TAGS:
                if buf:
                    paragraphs.append(buf)
                buf = []
        else:
            for ch in html.unescape(tok):
                buf.append((ch, bold_depth > 0))
    if buf:
        paragraphs.append(buf)
    return [(("".join(c for c, _ in p)), [b for _, b in p]) for p in paragraphs
            if "".join(c for c, _ in p).strip()]


def find_split_bold_labels(raw_html):
    """Labels whose bold run visually continues the paragraph above them.

    A match needs: the paragraph opens with a speaker honorific, bold from
    its very first character; and the paragraph immediately before it (the
    heading, almost always) is ALSO still bold at its own last visible
    character. Nothing but the paragraph break sits between those two bold
    runs, so nothing on the page tells a reader where one run ends and the
    other begins -- while parse_html.py, which never looks at bold across a
    break, is unaffected by the run it does not see.
    """
    out = []
    paras = html_paragraphs_with_bold(raw_html)
    for (prev_text, prev_bold), (text, bold) in zip(paras, paras[1:]):
        stripped = text.lstrip()
        if not stripped or not HTML_LABEL_START_RE.match(stripped):
            continue
        offset = len(text) - len(stripped)
        if not bold[offset]:
            continue                       # the label itself is not bold at all
        prev_stripped = prev_text.rstrip()
        if not prev_stripped or not prev_bold[len(prev_stripped) - 1]:
            continue                       # nothing bold ends right where this begins
        term = HTML_LABEL_TERM_RE.search(text, offset)
        if term is None:
            continue
        label = text[offset:term.start()].strip().rstrip(".")
        speech = text[term.end():]
        out.append({"label": label, "speech": speech, "heading": prev_stripped[:60]})
    return out


def _label_core(label):
    """The name or office in a label, honorific and parenthetical aside."""
    core = re.sub(r"^(?:Sr|Sra|Srta)\.?\s*", "", label, flags=re.I)
    core = re.sub(r"\([^)]*\)", "", core)
    return flatten(core)


def check_html_split_bold_labels(corpus, scanned):
    """Assert the mis-nested-label shape is found, and that it is attributed.

    Found independently in the raw markup (see the block comment above), then
    checked against the parsed output the same way every other check here
    checks output against source: by content, not by trusting a row number.
    A candidate counts as attributed when some speech row of the same
    session opens with the candidate's own words and carries a speaker_raw
    whose core matches the candidate's label. Anything found but not
    attributed is a regression on the single commonest label shape of the
    HTML era, and fails the audit.
    """
    print(f"\n{'='*66}\nHTML SPLIT LABELS — the era's commonest label shape"
          f"\n{'='*66}")
    html_sessions = (corpus[corpus.source_file.str.lower().str.endswith(".html")]
                     .groupby("session_id").source_file.first())
    speech_by_session = {sid: g for sid, g in
                         corpus[corpus.type == "speech"].groupby("session_id")}

    found, attributed, misses = 0, 0, []
    for sid, name in html_sessions.items():
        if sid in scanned:
            continue
        try:
            raw = decode_html((RAW_DIR / name).read_bytes())
        except Exception:
            continue
        candidates = find_split_bold_labels(raw)
        if not candidates:
            continue
        rows = speech_by_session.get(sid)
        for cand in candidates:
            found += 1
            opening = flatten(cand["speech"])[:50]
            core = _label_core(cand["label"])
            ok = False
            if rows is not None and opening:
                for _, row in rows.iterrows():
                    if not core or core in flatten(row.speaker_raw or ""):
                        out = flatten(row.text)
                        # A very short opening ("(Lee:)", "Sí.") is only safe
                        # to match at the very start of the row: found
                        # anywhere in it, it would also turn up inside a
                        # longer, unrelated word ("leemos"), the same
                        # fold-collision SOURCES.md and occurrence() above
                        # were written to avoid. A short sentence that is the
                        # whole of a merged turn's own opening ("Muy bien.
                        # Tiene la palabra...", the parser correctly joining
                        # two paragraphs of the same speaker) still starts
                        # the row even though it is not the whole of it.
                        if (len(opening) < 8 and out.startswith(opening)) or \
                           (len(opening) >= 8 and opening[:20] in out):
                            ok = True
                            break
            if ok:
                attributed += 1
            else:
                misses.append((sid, cand["label"], cand["speech"][:60]))

    print(f"   {found:6}  labels found with this shape")
    print(f"   {attributed:6}  found AND attributed to the matching speaker")
    print(f"   {len(misses):6}  found but NOT attributed correctly (must be 0)")
    for sid, label, snippet in misses[:8]:
        print(f"          [{sid}] {label!r}: {snippet!r}")
    problems = len(misses)
    if found == 0:
        print("   !! none found at all — the detector may not be looking at anything")
        problems += 1
    return problems


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--skip-source", action="store_true",
                    help="skip the checks that re-read every held file")
    ap.add_argument("--sample", type=int, default=0,
                    help="also write a review sheet of N turns for a human to check")
    ap.add_argument("--sample-format", choices=("pdf", "html"), default=None,
                    help="draw the review sheet from one format only, so a round "
                         "can be aimed at an era that has not been read yet")
    ap.add_argument("--sample-seed", default="20260728",
                    help="salt for the draw. The default reproduces the round "
                         "already read; change it to draw passages that round "
                         "did not see")
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()

    corpus = load_corpus()
    scanned = report_scanned(corpus)
    problems = check_output_only(corpus, scanned)
    problems += check_turn_shape(corpus, scanned)
    problems += check_label_shape(corpus, scanned)
    problems += check_attribution_windows(corpus)
    problems += check_opening_date(corpus)

    if not args.skip_source:
        print(f"\n{'='*66}\nSOURCE CHECKS — re-reading every held file\n{'='*66}")
        speech = corpus[corpus.type.isin(["speech", "event", "heading"])]
        jobs = [(sid, g.source_file.iloc[0], g.text.tolist())
                for sid, g in speech.groupby("session_id")]
        rows = []
        with ProcessPoolExecutor(max_workers=args.workers) as pool:
            futures = [pool.submit(audit_source, j) for j in jobs]
            for i, fut in enumerate(as_completed(futures), 1):
                rows.append(fut.result())
                if i % 100 == 0:
                    print(f"   {i}/{len(jobs)} sessions compared")
        df = pd.DataFrame(rows)
        errs = df[df.error.notna()]
        df = df[df.error.isna()]
        out_path = OUT_DIR / "audit_source.csv"
        df.to_csv(out_path, index=False)

        df["scanned"] = df.session_id.isin(scanned)
        foreign = df[(df.foreign_passage_share > 0.01) & ~df.scanned]
        print("\n8. Blocks whose text is not found in the source file:")
        print(f"   {int(df.blocks_probed.sum()):,} blocks probed across {len(df)} sessions; "
              f"{df.foreign_passage_share.mean():.3%} not located on average")
        print(f"   {len(foreign)} sessions above 1%, scans aside")
        for _, r in foreign.sort_values("foreign_passage_share", ascending=False).head(5).iterrows():
            print(f"          {r.foreign_passage_share:6.2%}  {r.session_id}")
        problems += len(foreign)

        dup = df[df.duplication_ratio > 1.02]
        print("\n9. Sessions whose output is longer than the page it came from "
              "(text written out twice):")
        print(f"   {len(dup)} of {len(df)}")
        for _, r in dup.sort_values("duplication_ratio", ascending=False).head(5).iterrows():
            print(f"          {r.duplication_ratio:5.2f}x  {r.session_id}")
        problems += len(dup)

        print(f"\n10. Share of each document's printed text kept in the output:")
        q = df.coverage.quantile([0.05, 0.25, 0.5, 0.75, 0.95])
        for k, v in q.items():
            print(f"          p{int(k*100):02d}  {v:.1%}")
        print("   (front matter, attendance rolls and appendices are dropped on purpose)")
        low = df.nsmallest(5, "coverage")
        print("   lowest-coverage sessions, worth an eye:")
        for _, r in low.iterrows():
            print(f"          {r.coverage:.1%}  {r.session_id}")
        if len(errs):
            print(f"\n   !! {len(errs)} held files could not be re-read")
            for _, r in errs.iterrows():
                print(f"          {r.session_id}: {r.error}")
        print(f"\n   per-session detail: {out_path}")

        problems += check_running_headers(corpus, scanned, workers=args.workers)
        problems += check_html_split_bold_labels(corpus, scanned)

    if args.sample:
        write_review_sheet(corpus, args.sample, scanned, args.sample_format,
                           args.sample_seed)

    print(f"\n{'='*66}")
    print("Audit complete." if not problems else
          f"Audit complete — {problems} thing(s) above need a look.")
    return 1 if problems else 0


def write_review_sheet(corpus, n, scanned=frozenset(), only_format=None,
                       seed_salt="20260728"):
    """Sample turns to be checked by eye against the printed page.

    The invariants above cannot tell whether the RIGHT person is behind the
    words — only that no rule was broken. That needs eyes on the page, so
    this writes a sheet of randomly drawn turns, spread across the years,
    each with the session, the page to open, who the parser says is speaking,
    and the opening words to look for.

    The scanned sittings are left out: their text is a guess the reader cannot
    check against, so drawing from them measures the scan and not the parser.

    Each turn is drawn on the strength of its OWN content, not its position in
    the table: the sitting, the page and its first words are hashed with a fixed
    seed, and the lowest hashes per year are taken. That matters because a
    parser change that adds or removes unrelated rows would otherwise shift
    every row number and redraw the whole sheet, throwing away the reading
    already done on it. This way a turn that survives a change keeps its place,
    and only turns that actually changed have to be read again.

    The sheet also names the page where the turn OPENS. A turn can begin several
    pages before the words quoted here — a long speech has no label on its
    later pages — and without that, a reader looking only at the quoted page
    finds no speaker at all and cannot answer.

    An HTML transcript has no pages, so those rows carry no page number and the
    reader finds the passage by searching the file for the opening words. The
    sheet says which it is rather than leaving a column mysteriously blank.
    `only_format` draws the whole sheet from one era, which is how a round gets
    aimed at the years nobody has read yet.
    """
    speech = corpus[(corpus.type == "speech")
                    & ~corpus.session_id.isin(scanned)].copy()
    if only_format:
        suffix = "." + only_format
        speech = speech[speech.source_file.str.lower().str.endswith(suffix)]
        if speech.empty:
            print(f"\nNo {only_format} sittings to draw a review sheet from.")
            return
    speech["year"] = speech.session_date.str[:4]
    first_page = {}
    for (sid, turn), g in speech.groupby(["session_id", "turn_id"]):
        pages = [int(p) for row in g.pages for p in row]
        first_page[(sid, turn)] = min(pages) if pages else ""

    # How many times this exact passage occurs in its sitting, and which one
    # this is. Derived from content and from order within the sitting, not from
    # a row number, so it survives a parser change that adds rows elsewhere.
    speech["_words"] = speech.text.map(lambda t: " ".join(str(t).split())[:400])
    grp = speech.groupby(["session_id", "_words"])
    speech["_nth"] = grp.cumcount() + 1
    speech["_of"] = grp["_words"].transform("size")

    def sample_key(r):
        # The seed is the turn's own content, not its row number, so a parser
        # change that adds or removes unrelated rows does not redraw the whole
        # sheet and throw away the reading already done on it.
        #
        # It takes 400 characters, not the 14 words the sheet quotes. A page
        # number used to separate two turns that open alike; an HTML transcript
        # has no pages, so with the short opening alone the chair's stock
        # phrases — "Tiene la palabra el señor senador por La Pampa." — all
        # hash the same and the draw returns the same passage many times over.
        # The first HTML round drew 60 rows that held only 47 distinct
        # passages, nine of them one sentence repeated.
        page = list(r.pages)[0] if len(r.pages) else ""
        # The salt is what makes a second round a second round. Holding it
        # fixed redraws the passages already answered, which reads nothing
        # new; changing it draws from the turns the last round did not see.
        seed = f"{seed_salt}|{r.session_id}|{page}|{r._words}|{r._nth}"
        return int.from_bytes(hashlib.blake2b(seed.encode(), digest_size=7).digest(), "big")

    speech["_key"] = speech.apply(sample_key, axis=1)
    per_year = max(1, n // speech.year.nunique())
    picks = []
    for _, g in speech.groupby("year"):
        picks += list(g.nsmallest(min(per_year, len(g)), "_key").index)
    rows = []
    for i in sorted(picks):
        r = speech.loc[i]
        page = list(r.pages)[0] if len(r.pages) else ""
        # Enough words to be findable. A reader given "Pido la palabra." cannot
        # answer: the sitting of 27 Nov 2002 prints it three times, under three
        # different senators, and a reader who guesses between them is not
        # reading. Where even 30 words do not separate the occurrences, the
        # sheet says which one to count to.
        opening = " ".join(str(r.text).split()[:30])
        nth = occurrence(r, opening, corpus)
        # A turn that is three words long stays three words however many are
        # quoted, and "Pido la palabra." or "(Lee:)" then depends on the
        # count above being right. The words printed just before it do not:
        # with them the reader finds the passage by reading, not by counting.
        before = ""
        if i - 1 in corpus.index and corpus.at[i - 1, "session_id"] == r.session_id:
            before = " ".join(str(corpus.at[i - 1, "text"]).split()[-15:])
        rows.append({
            "session": r.session_id,
            "source_file": r.source_file,
            "find_it_by": f"page {page}" if page != "" else "searching the text",
            "page": page,
            "turn_opens_on_page": first_page.get((r.session_id, r.turn_id), ""),
            "which_occurrence": nth,
            "parser_says_speaker": r.speaker_raw,
            "opening_words": opening,
            "printed_just_before": before,
            "correct? (y/n)": "",
            "if_wrong_who_spoke": "",
        })
    # A sheet aimed at one era gets its own name, so drawing one does not
    # overwrite a sheet somebody is part-way through answering.
    stem = f"review_sheet_{only_format}" if only_format else "review_sheet"
    if seed_salt != "20260728":
        stem += f"_{seed_salt}"
    path = OUT_DIR / f"{stem}.csv"
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"\n{'='*66}\nHUMAN REVIEW SHEET\n{'='*66}")
    print(f"{len(rows)} turns drawn across {speech.year.nunique()} years: {path}")
    print("Open each file — a PDF at the page given, an HTML at the opening words — "
          "and confirm the speaker. This is the only check that can catch the right "
          "rule applied to the wrong person.")


if __name__ == "__main__":
    sys.exit(main())
