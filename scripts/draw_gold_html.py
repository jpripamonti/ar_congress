"""Draw stretches of the HTML era for annotation, and locate them again later.

The PDF gold set is annotated a page at a time, which the HTML era cannot
copy: the chamber's export has no pages. A stretch is used instead — a window
of the source file, bounded by the words that open and close it.

The window is cut on the SOURCE, by character offset, and never on the
parser's own segmentation. Cutting it at a heading the parser found would
hand the annotator only the stretches the parser already reads well, and the
thing being measured is whether any turn is missing.

    uv run scripts/draw_gold_html.py --n 24 --out reference/gold_html/

Writes one .html fragment per stretch (what the annotator reads) and a
stretches.csv naming each one's file and offsets.
"""

import argparse
import csv
import hashlib
import re
import sys
import unicodedata
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from provenance import decode_html  # noqa: E402

RAW_DIR = REPO_ROOT / "data" / "raw" / "senado" / "taquigraficas"
BLOCKS_DIR = REPO_ROOT / "data" / "processed" / "senado" / "blocks"
# Long enough to hold a real exchange and to make a missing turn visible,
# short enough that one annotator can hold the whole of it at once.
WINDOW_CHARS = 7000


def fold(text):
    """The comparison key: no whitespace, no accents, no case."""
    s = unicodedata.normalize("NFD", str(text or "").casefold())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", "", s)


def readable(raw):
    """The words of a file, tags out, as a reader of the page sees them."""
    import html as htmllib
    raw = re.sub(r"(?is)<(script|style).*?</\1>", " ", raw)
    return htmllib.unescape(re.sub(r"<[^>]+>", " ", raw))


def paragraph_starts(markup):
    """Offsets in the markup where a paragraph opens."""
    return [m.start() for m in re.finditer(r"(?i)<p\b", markup)]


def draw(n, seed):
    """One stretch per sitting, for n sittings spread over the era."""
    files = sorted(RAW_DIR.glob("*.html"))
    rows = []
    for path in files:
        markup = decode_html(path.read_bytes())
        rows.append({"file": path.name, "year": path.name[:4],
                     "kind": path.stem.split("_", 2)[-1], "chars": len(markup)})
    frame = pd.DataFrame(rows)
    # Big enough to hold a debate; a one-page no-quorum record has nothing to
    # annotate and would spend an annotator on a masthead.
    frame = frame[frame.chars > 40000]
    per_year = max(1, n // frame.year.nunique())
    picks = []
    for _, group in frame.groupby("year"):
        group = group.assign(key=[int.from_bytes(
            hashlib.blake2b(f"{seed}|{f}".encode(), digest_size=7).digest(), "big")
            for f in group.file])
        picks += list(group.nsmallest(min(per_year, len(group)), "key").file)
    picks = picks[:n]
    out = []
    for name in picks:
        markup = decode_html((RAW_DIR / name).read_bytes())
        starts = paragraph_starts(markup)
        # Start somewhere in the middle half of the file: the opening is
        # masthead and roll, the end is appendices, and neither is debate.
        body = [s for s in starts if len(markup) * 0.25 < s < len(markup) * 0.75]
        if not body:
            continue
        pick = int.from_bytes(hashlib.blake2b(f"{seed}|w|{name}".encode(),
                                              digest_size=7).digest(), "big")
        begin = body[pick % len(body)]
        end = min(begin + WINDOW_CHARS, len(markup))
        # End on a paragraph boundary, so no turn is cut in half by the draw.
        after = [s for s in starts if s >= end]
        if after:
            end = after[0]
        # The session id, not a truncation of the filename: two sittings of
        # one day differ only in their reunión number, and cutting at 13
        # characters gave them the same name and one file for the two.
        out.append({"stretch_id": name.split("_ORDINARIA")[0].split("_")[0]
                    + "_" + name.split("_")[1],
                    "source_file": name, "begin": begin, "end": end,
                    "markup": markup[begin:end]})
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n", type=int, default=24)
    ap.add_argument("--seed", default="20260919")
    ap.add_argument("--out", default="reference/gold_html")
    args = ap.parse_args()

    out_dir = REPO_ROOT / args.out
    (out_dir / "stretches").mkdir(parents=True, exist_ok=True)
    drawn = draw(args.n, args.seed)
    index = []
    for s in drawn:
        frag = out_dir / "stretches" / f"{s['stretch_id']}.html"
        frag.write_text(s["markup"], encoding="utf-8")
        words = readable(s["markup"])
        index.append({"stretch_id": s["stretch_id"], "source_file": s["source_file"],
                      "begin": s["begin"], "end": s["end"],
                      "opening_words": " ".join(words.split()[:12]),
                      "closing_words": " ".join(words.split()[-12:])})
    with (out_dir / "stretches.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(index[0].keys()))
        w.writeheader()
        w.writerows(index)
    print(f"{len(index)} stretches -> {out_dir}")
    for r in index[:5]:
        print(f"  {r['stretch_id']}  {r['opening_words'][:70]}")


if __name__ == "__main__":
    main()
