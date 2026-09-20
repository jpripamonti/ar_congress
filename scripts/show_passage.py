"""Show a blind reader the page around a passage, and nothing else.

A blind round asks a reader who was speaking, having shown them the source and
never the parser's answer.  In the PDF era they open the file at the page the
sheet gives.  An HTML transcript has no pages, so this opens it at the passage
instead: it finds the occurrence the sheet names and prints the run-up to it.

The markup is stripped here rather than through parse_html.py, for the reason
audit_parse.py strips its own: a reader shown the parser's reading of the page
is not reading the page.  Only two things survive the strip — the paragraph
breaks, and the bold runs, marked **like this**, because bold is how this
chamber prints a speaker's label and a reader who cannot see it cannot answer.

Occurrences are counted exactly as the sheet counts them, by the same
`as_read` fold, so "54 of 70" means the same number in both places.

Usage:
    uv run scripts/show_passage.py <source_file.html> <nth> "<opening words>"
    uv run scripts/show_passage.py --sheet <slice.csv>
"""
import argparse
import csv
import html
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from audit_parse import RAW_DIR, as_read          # noqa: E402
from provenance import decode_html                # noqa: E402

BEFORE, AFTER = 2600, 400


def render(name):
    """The file as a reader sees it: paragraphs, and bold marked."""
    raw = decode_html((RAW_DIR / name).read_bytes())
    raw = re.sub(r"(?is)<(script|style).*?</\1>", " ", raw)
    raw = re.sub(r"(?i)<b[^>]*>", "\x01", raw)
    raw = re.sub(r"(?i)</b\s*>", "\x02", raw)
    raw = re.sub(r"(?i)<(?:p|br|div|tr|center|h[1-6])[^>]*>", "\n", raw)
    # An inline tag is not a space. This chamber's export puts every accented
    # letter in a <font> run of its own, so turning each tag into a space
    # printed "se ñ or" and "votaci ó n", and a reader of the first round of
    # September 2026 reported it as damage to the file. The file is fine.
    raw = re.sub(r"(?i)</?(?:font|i|em|b|strong|span|a|sup|sub|u|small|big)"
                 r"(?:\s[^>]*)?>", "", raw)
    raw = re.sub(r"<[^>]+>", " ", raw)
    txt = html.unescape(raw)
    # Collapse runs of blanks, but keep the paragraph breaks.
    txt = re.sub(r"[ \t\r\f\v]+", " ", txt)
    txt = re.sub(r"\n\s*\n+", "\n\n", txt)
    # A bold run split across tags reads as one label, so join the pieces
    # before they are shown: "**Sr.** **PRESIDENTE**" is one printed label.
    txt = re.sub(r"\x02(\s*)\x01", lambda m: m.group(1), txt)
    return txt.replace("\x01", "**").replace("\x02", "**")


def fold(s):
    """as_read(), with the bold markers this renderer added taken back out."""
    return as_read(s.replace("*", ""))


def locate(text, opening, nth):
    """Character offset of the nth occurrence of `opening`, counted as folded."""
    quote = fold(opening)
    if not quote:
        return -1, 0
    # Walk the text once, keeping the folded length of every prefix, so a
    # folded offset can be turned back into a real one.
    keep = [i for i, ch in enumerate(text) if fold(ch)]
    folded = "".join(text[i] for i in keep)
    folded = fold(folded)
    if len(folded) != len(keep):
        # Folding is per-character here; a character that folds to nothing was
        # already dropped by `keep`, so the two must line up.
        return -2, 0
    # A match buried inside a longer word is not an occurrence a reader would
    # count: "Sí." folds to "si." and is otherwise found inside "así.".
    hits = []
    i = 0
    while True:
        i = folded.find(quote, i)
        if i == -1:
            break
        if i == 0 or not folded[i - 1].isalnum():
            hits.append(i)
        i += 1
    total = len(hits)
    if not hits:
        return -1, 0
    at = hits[min(max(1, nth), total) - 1]
    return keep[at], total


def show(name, nth, opening, out=sys.stdout):
    text = render(name)
    at, total = locate(text, opening, nth)
    print(f"=== {name} — occurrence {nth or 1} of {total} ===", file=out)
    if at < 0:
        print("!! could not find the passage in the source", file=out)
        return False
    start = max(0, at - BEFORE)
    head = "…" if start else ""
    print(f"{head}{text[start:at]}", file=out, end="")
    print(f"\n>>>THE PASSAGE STARTS HERE>>> {text[at:at + AFTER]}", file=out)
    return True


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("args", nargs="*")
    ap.add_argument("--sheet", help="a slice CSV; shows every passage in it")
    a = ap.parse_args()
    if a.sheet:
        for r in csv.DictReader(open(a.sheet, encoding="utf-8")):
            occ = (r.get("which_occurrence") or "").strip()
            nth = int(occ.split()[0]) if occ[:1].isdigit() else 1
            print(f"\n########## CASE {r['case']} ##########")
            show(r["source_file"], nth, r["opening_words"])
        return 0
    name, nth, opening = a.args[0], int(a.args[1]), a.args[2]
    return 0 if show(name, nth, opening) else 1


if __name__ == "__main__":
    sys.exit(main())
