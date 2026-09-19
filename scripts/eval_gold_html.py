"""Score the parser against the HTML era's gold stretches.

The PDF gold set is annotated a page at a time. The chamber's HTML export has
no pages, so the unit here is a stretch: a window of the source file, cut by
character offset on the SOURCE and never on the parser's own segmentation —
cutting at a heading the parser found would hand the annotators only the
passages the parser already reads well, and the thing being measured is
whether any turn is missing.

Two readers annotated every stretch independently; `check_gold_html.py`
reports how far they agree before either is believed. This scores the parser
against reading A, and reports separately how the score moves on reading B,
because a benchmark that hides its own uncertainty is worth less than one
that shows it.

What is scored, as on the PDF side:
- turn starts, on the label alone and on the label with the opening words;
- stenographer events;
- turns the parser puts in the stretch that the readers do not (precision)
  and turns the readers see that the parser does not (recall — the number
  this set exists for, and the one no blind read can produce).

    uv run scripts/eval_gold_html.py
"""

import csv
import html as htmllib
import json
import re
import sys
import unicodedata
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
GOLD_DIR = REPO_ROOT / "reference" / "gold_html"
RAW_DIR = REPO_ROOT / "data" / "raw" / "senado" / "taquigraficas"
BLOCKS_DIR = REPO_ROOT / "data" / "processed" / "senado" / "blocks"
OUT_PATH = REPO_ROOT / "data" / "processed" / "senado" / "gold_html_eval.csv"

sys.path.insert(0, str(Path(__file__).resolve().parent))
from eval_gold import multiset_overlap, norm_event, norm_label, norm_opening, opening_overlap  # noqa: E402
from provenance import decode_html  # noqa: E402


def fold(text):
    """Comparison key: no whitespace, no accents, no case."""
    s = unicodedata.normalize("NFD", str(text or "").casefold())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^0-9a-z]", "", s)


def readable(markup):
    """The words of the markup, tags out, entities decoded."""
    markup = re.sub(r"(?is)<(script|style).*?</\1>", " ", markup)
    return htmllib.unescape(re.sub(r"<[^>]+>", " ", markup))


def place_blocks(session_id, source_file):
    """Every block of a sitting, with where its text falls in the source.

    Walked forward once, in the order the blocks were written, so a passage
    the chamber prints twice is found at its own occurrence rather than at
    the first. A block that cannot be found at all is left without a place
    and counted; the audit puts those at 0.006% of the corpus.
    """
    frame = pd.read_parquet(BLOCKS_DIR / f"{session_id}.parquet")
    source = fold(readable(decode_html((RAW_DIR / source_file).read_bytes())))
    at, places, lost = 0, [], 0
    for text in frame["text"].fillna(""):
        whole = fold(text)
        key = whole[:120]
        found = source.find(key, at) if key else -1
        if found == -1 and key:
            # The walk can overshoot — a heading the parser moved, a block
            # whose text the parser cut in the middle — so a block that is
            # not ahead is looked for from the top before it is given up on.
            found = source.find(key)
        if found == -1:
            places.append(None)
            lost += 1
            continue
        places.append(found)
        # Past the WHOLE block, not just the part used to find it. A short
        # block placed inside the block before it is how "-Asentimiento."
        # came to be found in the middle of "Si hay asentimiento, por
        # Secretaría…" and counted as a turn the parser had invented.
        at = max(at, found + len(whole))
    frame["place"] = places
    return frame, lost


def stretch_bounds(markup, begin, end):
    """Where a stretch starts and ends, in the folded source's own units."""
    return (len(fold(readable(markup[:begin]))),
            len(fold(readable(markup[:end]))))


def parser_starts(frame, lo, hi):
    """The turns the parser opens inside the stretch, and its events."""
    inside = frame[frame["place"].notna() & (frame["place"] >= lo) & (frame["place"] < hi)]
    speech = inside[inside["type"] == "speech"]
    firsts = speech.drop_duplicates("turn_id", keep="first")
    pairs = [(norm_label(r.speaker_raw), norm_opening(r.text))
             for r in firsts.itertuples()]
    events = [norm_event(t) for t in inside.loc[inside["type"] == "event", "text"]]
    return pairs, events


def gold_pairs(doc):
    return [(norm_label(u.get("speaker_label")), norm_opening(u.get("first_words")))
            for u in doc.get("utterance_starts", [])]


def score(reading, rows_out=None):
    """Score every stretch against one reader's annotation."""
    stretches = list(csv.DictReader((GOLD_DIR / "stretches.csv").open(encoding="utf-8")))
    totals = {"gold": 0, "parser": 0, "label_hit": 0, "both_hit": 0,
              "ev_gold": 0, "ev_parser": 0, "ev_hit": 0, "lost": 0}
    rows = []
    for s in stretches:
        path = GOLD_DIR / f"{s['stretch_id']}.{reading}.json"
        if not path.exists():
            continue
        doc = json.loads(path.read_text(encoding="utf-8"))
        markup = decode_html((RAW_DIR / s["source_file"]).read_bytes())
        lo, hi = stretch_bounds(markup, int(s["begin"]), int(s["end"]))
        frame, lost = place_blocks(s["stretch_id"], s["source_file"])
        pairs, events = parser_starts(frame, lo, hi)
        gold = gold_pairs(doc)
        label_hit = multiset_overlap([p[0] for p in pairs], [g[0] for g in gold])
        both_hit = opening_overlap(pairs, gold)
        ev_gold = [norm_event(e) for e in doc.get("events", [])]
        ev_hit = multiset_overlap(events, ev_gold)
        totals["gold"] += len(gold)
        totals["parser"] += len(pairs)
        totals["label_hit"] += label_hit
        totals["both_hit"] += both_hit
        totals["ev_gold"] += len(ev_gold)
        totals["ev_parser"] += len(events)
        totals["ev_hit"] += ev_hit
        totals["lost"] += lost
        rows.append({"stretch": s["stretch_id"], "gold_turns": len(gold),
                     "parser_turns": len(pairs), "matched": both_hit,
                     "missed": len(gold) - both_hit, "invented": len(pairs) - both_hit,
                     "gold_events": len(ev_gold), "parser_events": len(events),
                     "events_matched": ev_hit})
    if rows_out is not None:
        rows_out.extend(rows)
    return totals, rows


def ratio(hit, total):
    return hit / total if total else 1.0


def main():
    rows = []
    a, per_stretch = score("A", rows)
    b, _ = score("B")
    if not per_stretch:
        raise SystemExit("No annotations found under reference/gold_html/")

    print(f"HTML gold set — {len(per_stretch)} stretches, {a['gold']} annotated turns\n")
    print(f"{'stretch':<17}{'gold':>5}{'parser':>7}{'match':>6}{'missed':>7}{'invented':>9}"
          f"{'events g/p/m':>15}")
    for r in per_stretch:
        print(f"{r['stretch']:<17}{r['gold_turns']:>5}{r['parser_turns']:>7}{r['matched']:>6}"
              f"{r['missed']:>7}{r['invented']:>9}"
              f"{r['gold_events']:>10}/{r['parser_events']}/{r['events_matched']}")
    print()
    for name, t in (("reading A", a), ("reading B", b)):
        p = ratio(t["both_hit"], t["parser"])
        rc = ratio(t["both_hit"], t["gold"])
        f1 = 2 * p * rc / (p + rc) if p + rc else 0.0
        print(f"{name}: boundary+attribution P={p:.3f} R={rc:.3f} F1={f1:.3f} "
              f"({t['both_hit']}/{t['gold']} annotated turns matched); "
              f"label alone {ratio(t['label_hit'], t['gold']):.3f}; "
              f"events P={ratio(t['ev_hit'], t['ev_parser']):.3f} "
              f"R={ratio(t['ev_hit'], t['ev_gold']):.3f}")
    print(f"\nBlocks that could not be placed in their source: {a['lost']}")
    with OUT_PATH.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(per_stretch[0].keys()))
        w.writeheader()
        w.writerows(per_stretch)
    print(f"Per-stretch detail: {OUT_PATH}")


if __name__ == "__main__":
    main()
