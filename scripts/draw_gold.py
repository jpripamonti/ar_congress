"""Draw pages of the PDF era for annotation, as images an annotator can read.

The PDF gold set is 36 pages, and 28 of them are 2016 or later. Eight pages
carrying 50 turns stand for the 404 sittings printed before 2016, which is the
part of the record whose conventions least resemble today's. This draws more
of them.

Two properties matter and both are about not flattering the parser:

- **The unit is a printed page**, so the sample's boundaries are the
  document's and not the parser's. A stretch cut at a heading the parser found
  would hand the annotator only the passages it already segments well, and
  what is being measured is whether a turn is missing.
- **The annotator is given an IMAGE**, never extracted text. Handing over
  pdfplumber's characters would make the gold set agree with the extractor by
  construction, including where the extractor is wrong. The page image is what
  the chamber printed.

Pages that are a scan rather than a page are dropped: a full-sheet image
carries no characters to compare against, and an annotator sent to one spends
the draw on a blank. This is decided page by page with the parser's own test,
not sitting by sitting — 179 sittings hold at least one such page while only
three are nothing else, so excluding whole sittings would throw away most of
2012 and 2018 for the sake of a handful of sheets.

    uv run scripts/draw_gold.py --n 40 --until 2016

Writes reference/gold/pages/<page_id>.png, one per drawn page, and
reference/gold/pages.csv naming each one's sitting, file and page number.
Nothing is annotated here; the draw can be thrown away and taken again with a
different --seed until the spread is right, at no cost in annotation.
"""

import argparse
import csv
import hashlib
import sys
from pathlib import Path

import pandas as pd
import pdfplumber

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from parse import page_is_scanned  # noqa: E402

RAW_DIR = REPO_ROOT / "data" / "raw" / "senado" / "taquigraficas"
GOLD_DIR = REPO_ROOT / "reference" / "gold"
STATS = REPO_ROOT / "data" / "processed" / "senado" / "parse_stats.csv"

# Enough characters that the page holds something to annotate. A page under
# this is a part-title or the tail of a document, and costs an annotator a
# slot without measuring anything.
MIN_CHARS = 400
# 150 dpi renders the Diario's body type legibly without making a file an
# annotator has to pan around.
RESOLUTION = 150


def key(seed, *parts):
    """A stable draw order. Keyed on the seed and the thing, never on
    position, so adding a sitting does not reshuffle a draw already made."""
    raw = "|".join([seed, *(str(p) for p in parts)]).encode()
    return int.from_bytes(hashlib.blake2b(raw, digest_size=7).digest(), "big")


def already_annotated():
    """(pdf, page) pairs the gold set already holds, so a draw does not spend
    an annotator on a page that has been read."""
    import json
    held = set()
    for path in GOLD_DIR.glob("*.json"):
        try:
            g = json.loads(path.read_text(encoding="utf-8"))
        except ValueError:
            continue
        if "pdf" in g and "page" in g:
            held.add((g["pdf"], int(g["page"])))
    return held


def candidate_sittings(until_year, from_year):
    """The PDF sittings in range, newest numbering aside, as (id, file)."""
    stats = pd.read_csv(STATS)
    stats = stats[stats["rows_written"].notna()]
    year = stats["session_id"].str[:4].astype(int)
    stats = stats[(year >= from_year) & (year < until_year)]
    rows = []
    for _, r in stats.iterrows():
        path = RAW_DIR / str(r["file_name"])
        if path.suffix.lower() != ".pdf" or not path.exists():
            continue
        rows.append({"session_id": r["session_id"], "file_name": r["file_name"],
                     "year": r["session_id"][:4], "path": path})
    return pd.DataFrame(rows)


def eligible_pages(path, held, file_name):
    """Page numbers of this PDF an annotator could be sent to."""
    out = []
    with pdfplumber.open(str(path)) as doc:
        for i, page in enumerate(doc.pages, start=1):
            if (file_name, i) in held:
                continue
            if page_is_scanned(page):
                continue
            if len(page.chars) < MIN_CHARS:
                continue
            out.append(i)
    return out


def draw(n, seed, until_year, from_year):
    frame = candidate_sittings(until_year, from_year)
    if frame.empty:
        return []
    held = already_annotated()
    years = sorted(frame.year.unique())
    per_year = max(1, round(n / len(years)))

    picks = []
    for y in years:
        group = frame[frame.year == y].copy()
        group["k"] = [key(seed, "sitting", f) for f in group.file_name]
        group = group.sort_values("k")
        taken = 0
        for _, r in group.iterrows():
            if taken >= per_year:
                break
            try:
                pages = eligible_pages(r.path, held, r.file_name)
            except Exception as exc:                      # a file we cannot open
                print(f"  ! {r.session_id}: {exc}", file=sys.stderr)
                continue
            if not pages:
                continue
            pick = pages[key(seed, "page", r.file_name) % len(pages)]
            picks.append({"session_id": r.session_id, "file_name": r.file_name,
                          "page": pick, "year": y, "path": r.path,
                          "of_pages": len(pages)})
            held.add((r.file_name, pick))
            taken += 1
    picks.sort(key=lambda p: (p["session_id"], p["page"]))
    return picks[:n]


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--n", type=int, default=40, help="how many pages to draw")
    ap.add_argument("--until", type=int, default=2016,
                    help="draw sittings printed before this year")
    ap.add_argument("--from", dest="from_year", type=int, default=1998,
                    help="and not before this one")
    ap.add_argument("--seed", default="20260920",
                    help="change it to take a different draw at no cost")
    ap.add_argument("--out", default="reference/gold")
    args = ap.parse_args()

    out_dir = REPO_ROOT / args.out
    (out_dir / "pages").mkdir(parents=True, exist_ok=True)

    print(f"drawing {args.n} pages from {args.from_year}–{args.until - 1}, "
          f"seed {args.seed}")
    drawn = draw(args.n, args.seed, args.until, args.from_year)

    index = []
    for p in drawn:
        page_id = f"{p['session_id']}_p{p['page']}"
        with pdfplumber.open(str(p["path"])) as doc:
            page = doc.pages[p["page"] - 1]
            page.to_image(resolution=RESOLUTION).save(
                str(out_dir / "pages" / f"{page_id}.png"))
            words = " ".join((page.extract_text() or "").split())
        index.append({"page_id": page_id, "session_id": p["session_id"],
                      "source_file": p["file_name"], "page": p["page"],
                      "eligible_pages_in_sitting": p["of_pages"],
                      # For a maintainer checking the draw landed where the
                      # index says. The annotator is given the image only.
                      "opening_words": words[:90]})

    with (out_dir / "pages.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(index[0].keys()))
        w.writeheader()
        w.writerows(index)

    by_year = {}
    for r in index:
        by_year[r["session_id"][:4]] = by_year.get(r["session_id"][:4], 0) + 1
    print(f"\n{len(index)} pages -> {out_dir}/pages/")
    print("  by year: " + "  ".join(f"{y}:{c}" for y, c in sorted(by_year.items())))
    for r in index:
        print(f"  {r['page_id']:24s} p{r['page']:<4d} {r['opening_words'][:58]}")


if __name__ == "__main__":
    main()
