"""How far the two annotators of each stretch agree, before either is believed.

Two readers annotated every stretch of the HTML gold set independently. This
asks what they agree on. A gold set built from one reading records that
reader's judgement; two readings and this script record how much of it is
judgement at all.

Agreement is reported on the turn starts, which is what the set exists to
measure, matched on the speaker's name and the opening words together — the
label alone cannot tell a chair who speaks four times from a chair who speaks
once and was found in four places.

    uv run scripts/check_gold_html.py
"""

import json
import re
import sys
import unicodedata
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
GOLD_DIR = REPO_ROOT / "reference" / "gold_html"
sys.path.insert(0, str(Path(__file__).resolve().parent))
from eval_gold import norm_label, norm_opening  # noqa: E402


def starts(doc):
    """The turn starts of one annotation, as comparable pairs."""
    out = []
    for u in doc.get("utterance_starts", []):
        out.append((norm_label(u.get("speaker_label")),
                    norm_opening(u.get("first_words"), 60)))
    return out


def overlap(a, b):
    """How many pairs the two readings share, counting repeats properly."""
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
    rows = []
    for path in sorted(GOLD_DIR.glob("*.A.json")):
        stretch = path.name[:-len(".A.json")]
        other = GOLD_DIR / f"{stretch}.B.json"
        if not other.exists():
            print(f"  {stretch}: only one reading, skipped")
            continue
        a = json.loads(path.read_text(encoding="utf-8"))
        b = json.loads(other.read_text(encoding="utf-8"))
        sa, sb = starts(a), starts(b)
        hit = overlap(sa, sb)
        rows.append({
            "stretch": stretch, "A": len(sa), "B": len(sb), "shared": hit,
            "mid_A": a.get("opens_mid_utterance"), "mid_B": b.get("opens_mid_utterance"),
            "events_A": len(a.get("events", [])), "events_B": len(b.get("events", [])),
        })

    print(f"{'stretch':<17}{'A':>4}{'B':>4}{'both':>6}{'agree':>8}   opens-mid   events")
    for r in rows:
        denom = max(r["A"], r["B"])
        share = r["shared"] / denom if denom else 1.0
        mid = "ok" if r["mid_A"] == r["mid_B"] else f"{r['mid_A']}/{r['mid_B']}"
        print(f"{r['stretch']:<17}{r['A']:>4}{r['B']:>4}{r['shared']:>6}{share:>7.0%}   "
              f"{mid:<11} {r['events_A']}/{r['events_B']}")
    tot_a = sum(r["A"] for r in rows)
    tot_b = sum(r["B"] for r in rows)
    tot_h = sum(r["shared"] for r in rows)
    print()
    print(f"{len(rows)} stretches read twice. Turn starts: {tot_a} by one reader, "
          f"{tot_b} by the other, {tot_h} the same.")
    if tot_a + tot_b:
        print(f"Agreement on turn starts: {2 * tot_h / (tot_a + tot_b):.1%} "
              f"(the harmonic view: a start counts only if both readers found it)")
    disagree = [r for r in rows if r["A"] != r["B"] or r["shared"] < min(r["A"], r["B"])]
    print(f"{len(rows) - len(disagree)} of {len(rows)} stretches agree exactly.")
    mid = [r for r in rows if r["mid_A"] != r["mid_B"]]
    if mid:
        print(f"opens_mid_utterance disagrees on: {[r['stretch'] for r in mid]}")


if __name__ == "__main__":
    main()
