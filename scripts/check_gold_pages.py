"""How far the two annotators of each drawn page agree, before either is believed.

The 36 pages drawn by `draw_gold.py` were each read twice, by annotators who
never saw one another's work. This asks what the two readings share. A gold
set built from one reading records that reader's judgement and calls it
ground truth; two readings and this script say how much of it was judgement.

Run it BEFORE scoring the parser. A page the two readers disagree about is not
evidence against the parser — it is a page whose right answer the project does
not yet have, and it has to be settled by looking at the page.

Agreement is reported on the turn starts, which is what the set exists to
measure, matched on the speaker's label and the opening words together: the
label alone cannot tell a chair who speaks four times from a chair who spoke
once and was found in four places.

    uv run scripts/check_gold_pages.py

The twin of `check_gold_html.py`, which does the same for the HTML era's
stretches. Kept apart because the unit differs — a printed page there, a
window of the source here — and merging them would hide which era a
disagreement came from.
"""

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
GOLD_DIR = REPO_ROOT / "reference" / "gold"
sys.path.insert(0, str(Path(__file__).resolve().parent))
from eval_gold import norm_label, norm_opening  # noqa: E402


def starts(doc):
    """The turn starts of one annotation, as comparable pairs."""
    return [(norm_label(u.get("speaker_label")),
             norm_opening(u.get("first_words"), 60))
            for u in doc.get("utterance_starts", [])]


def overlap(a, b):
    """How many pairs the two readings share, counting repeats properly.

    A page where the chair speaks four times holds four pairs with the same
    label, so a matched pair is removed from the pool rather than counted
    again.
    """
    rest = list(b)
    hit = 0
    for pair in a:
        for i, other in enumerate(rest):
            if pair[0] == other[0] and (pair[1].startswith(other[1][:40])
                                        or other[1].startswith(pair[1][:40])):
                rest.pop(i)
                hit += 1
                break
    return hit


def main():
    rows, lonely = [], []
    for path in sorted(GOLD_DIR.glob("*.A.json")):
        page_id = path.name[len("gold_"):-len(".A.json")]
        other = GOLD_DIR / f"gold_{page_id}.B.json"
        if not other.exists():
            lonely.append(page_id)
            continue
        a = json.loads(path.read_text(encoding="utf-8"))
        b = json.loads(other.read_text(encoding="utf-8"))
        sa, sb = starts(a), starts(b)
        rows.append({
            "page": page_id, "A": len(sa), "B": len(sb), "shared": overlap(sa, sb),
            "mid_A": a.get("opens_mid_utterance"), "mid_B": b.get("opens_mid_utterance"),
            "events_A": len(a.get("events", [])), "events_B": len(b.get("events", [])),
        })

    if not rows:
        print("No page has two readings yet.")
        return 1

    print(f"{'page':<22}{'A':>4}{'B':>4}{'both':>6}{'agree':>8}   opens-mid   events")
    for r in rows:
        denom = max(r["A"], r["B"])
        share = r["shared"] / denom if denom else 1.0
        mid = "ok" if r["mid_A"] == r["mid_B"] else f"{r['mid_A']}/{r['mid_B']}"
        flag = "" if share == 1.0 and r["A"] == r["B"] else "   <-"
        print(f"{r['page']:<22}{r['A']:>4}{r['B']:>4}{r['shared']:>6}{share:>7.0%}   "
              f"{mid:<11} {r['events_A']}/{r['events_B']}{flag}")

    tot_a = sum(r["A"] for r in rows)
    tot_b = sum(r["B"] for r in rows)
    tot_h = sum(r["shared"] for r in rows)
    print()
    print(f"{len(rows)} pages read twice. Turn starts: {tot_a} by one reader, "
          f"{tot_b} by the other, {tot_h} the same.")
    if tot_a + tot_b:
        print(f"Agreement on turn starts: {2 * tot_h / (tot_a + tot_b):.1%} "
              f"(the harmonic view: a start counts only if both readers found it)")
    disagree = [r for r in rows if r["A"] != r["B"] or r["shared"] < min(r["A"], r["B"])]
    print(f"{len(rows) - len(disagree)} of {len(rows)} pages agree exactly.")
    if disagree:
        print("\nPages to settle against the printed page before scoring:")
        for r in disagree:
            print(f"   {r['page']:<22} A={r['A']} B={r['B']} shared={r['shared']}")
    mid = [r for r in rows if r["mid_A"] != r["mid_B"]]
    if mid:
        print(f"\nopens_mid_utterance disagrees on: {[r['page'] for r in mid]}")
    ev = [r for r in rows if r["events_A"] != r["events_B"]]
    if ev:
        print(f"events counted differently on: {[r['page'] for r in ev]}")
    if lonely:
        print(f"\n{len(lonely)} page(s) have only one reading: {lonely}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
