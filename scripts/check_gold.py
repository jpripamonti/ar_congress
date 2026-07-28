"""Check the gold annotations against the source pages, not the parser.

`eval_gold.py` asks whether the parser agrees with the annotations. This
asks the prior question: are the annotations themselves right? It reads the
annotated page straight out of the PDF and checks that

- every utterance the annotation records really is printed on that page,
  with those opening words, in that order;
- every speaker label printed on the page was recorded — a missed turn in
  the gold set silently forgives the same miss in the parser;
- every recorded event line appears on the page.

The annotations were produced with machine assistance, so this is a second
machine reading of the same pages, not an independent human audit. It
catches transcription slips and omissions; it cannot catch a shared
misreading of what the page means.

Output: a per-file report; exit status 1 if any check fails.
"""

import json
import re
import sys
import unicodedata
from pathlib import Path

import pdfplumber

REPO_ROOT = Path(__file__).resolve().parents[1]
GOLD_DIR = REPO_ROOT / "reference" / "gold"
RAW_DIR = REPO_ROOT / "data" / "raw" / "senado" / "taquigraficas"

# A printed speaker label: title, name, then the terminator that closes it.
LABEL_RE = re.compile(
    r"(?:Sr|Sra|Srta|Sres)\.\s+[^\n]{0,60}?\s*[.:]\s*[–—−\-─]",
)


def norm(s):
    s = unicodedata.normalize("NFC", s or "")
    return re.sub(r"\s+", " ", s).strip()


def squash(s, drop_digits=False):
    """Comparison key: no spaces, no accents, no case.

    The formats lose and add spaces at line joins ("AlbertoFernández"), so
    spacing cannot be part of the comparison. `drop_digits` additionally
    removes the footnote markers some formats glue to the word they follow
    ("Aprobado.5"), which an annotator quoting the spoken words leaves out.
    """
    s = unicodedata.normalize("NFD", norm(s).casefold())
    keep = r"[^a-z]" if drop_digits else r"[^a-z0-9]"
    return re.sub(keep, "", "".join(c for c in s if not unicodedata.combining(c)))


def page_text(pdf_path, page_no):
    with pdfplumber.open(pdf_path) as pdf:
        if page_no > len(pdf.pages):
            return None
        return pdf.pages[page_no - 1].extract_text() or ""


def check(gold_path):
    gold = json.loads(gold_path.read_text(encoding="utf-8"))
    pdf_path = RAW_DIR / unicodedata.normalize("NFC", gold["pdf"])
    if not pdf_path.exists():                       # macOS stores filenames NFD
        alt = [p for p in RAW_DIR.glob("*.pdf")
               if unicodedata.normalize("NFC", p.name) == unicodedata.normalize("NFC", gold["pdf"])]
        if not alt:
            return [f"source PDF not found: {gold['pdf']}"]
        pdf_path = alt[0]

    text = page_text(pdf_path, gold["page"])
    if text is None:
        return [f"page {gold['page']} is past the end of {gold['pdf']}"]

    problems = []
    cursor = 0
    for u in gold["utterance_starts"]:
        found = False
        for drop in (False, True):                  # retry ignoring footnote digits
            flat = squash(text, drop)
            label = squash(re.sub(r"[.:\s–—−\-─]+$", "", u["speaker_label"]), drop)
            words = squash(u["first_words"], drop)[:40]
            at_label = flat.find(label, cursor)
            at_words = flat.find(words, cursor) if words else at_label
            if at_label >= 0 and at_words >= 0:
                cursor, found = at_label, True      # order check: turns advance
                break
        if not found:
            where = "label not printed on the page" if at_label < 0 else \
                    "opening words do not follow the label"
            problems.append(f"{where}: {u['speaker_label']!r} -> {u['first_words'][:45]!r}")

    printed = len(LABEL_RE.findall(text))
    recorded = len(gold["utterance_starts"])
    # A turn continuing from the previous page prints no label, and the last
    # label on a page may open a turn the annotator assigned to the next one.
    if printed > recorded:
        problems.append(f"{printed} labels printed on the page but {recorded} recorded "
                        f"— a turn may be missing from the annotation")

    page_flat = squash(text)
    for ev in gold.get("events", []):
        key = squash(ev)[:30]
        if key and key not in page_flat:
            problems.append(f"event not on page: {ev[:60]!r}")

    return problems


def main():
    golds = sorted(GOLD_DIR.glob("gold_*.json"))
    if not golds:
        sys.exit(f"No gold files in {GOLD_DIR}")
    bad = 0
    for path in golds:
        problems = check(path)
        if problems:
            bad += 1
            print(f"\n{path.name}")
            for p in problems:
                print(f"   - {p}")
    print(f"\n{len(golds)} gold pages checked against the source PDFs, "
          f"{bad} with something to look at.")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
