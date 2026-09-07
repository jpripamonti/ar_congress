"""Score the parser against the gold-set page annotations.

Gold files (reference/gold/gold_*.json) record what a careful reader
sees on 24 stratified pages: utterance starts (speaker label + first
words), stenographer events, headings, furniture. This script compares
them with the parsed Parquet corpus:

- Utterance boundaries + attribution: multiset match of normalized
  speaker labels for turns STARTING on the page (parser: pages[0] == N)
  vs. the gold list -> precision / recall / F1. Scored twice: on the
  label alone, and on the label together with the turn's opening words,
  because a page where one speaker takes four turns has four identical
  labels and the label alone cannot say they were found in the right
  places. Neither score checks the order the turns came out in.
- Events: prefix-normalized match of gold event lines vs. parser event
  rows overlapping the page -> precision / recall.
- Appendix leakage: speech rows the parser emits on pages the annotator
  marked as appendix/no-debate.

Output: per-page table + aggregates, written to
data/processed/senado/gold_eval.csv. The gold set is machine-assisted
(annotated from rendered pages) and pending owner verification.
"""

import json
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
GOLD_DIR = REPO_ROOT / "reference" / "gold"
BLOCKS_DIR = REPO_ROOT / "data" / "processed" / "senado" / "blocks"
OUT_PATH = REPO_ROOT / "data" / "processed" / "senado" / "gold_eval.csv"


def norm_label(s):
    """Normalize a speaker label for comparison.

    The terminator printed after a label (".-", ". —", " –") is punctuation
    that separates the name from the words, not part of the name, and the
    formats spell it differently from year to year. Strip it from both the
    annotation and the parser output so the comparison is about who spoke.
    """
    s = unicodedata.normalize("NFC", s or "")
    s = re.sub(r"\s+", " ", s.strip())
    s = re.sub(r"[\s.\-–—−:]+$", "", s)
    return s.casefold()


def norm_opening(s, width=300):
    """Normalize the opening words of a turn, for comparing by prefix.

    The annotation records the first words of every turn, and the label-only
    comparison threw them away. A page where the chair speaks four times has
    four identical labels, so counting labels cannot tell a parser that found
    all four turns from one that found four turns in the wrong places. This is
    what lets the two be told apart.
    """
    s = unicodedata.normalize("NFC", s or "")
    s = re.sub(r"^[\s.\-–—−:]+", "", s)
    s = re.sub(r"\s+", " ", s).strip().casefold()
    return s[:width]


def opening_overlap(parser_pairs, gold_pairs):
    """How many gold turns a parser turn answers on BOTH label and opening.

    Compared by prefix, not over a fixed window: the annotation writes as many
    opening words as it took to identify the turn — four on one page, fifteen
    on the next — so a parser turn answers a gold one when the labels agree and
    the shorter opening opens the longer. The longest annotations are matched
    first, so a short one cannot take a turn that a fuller one identifies.
    """
    left = list(parser_pairs)
    hits = 0
    for lab, op in sorted(gold_pairs, key=lambda p: -len(p[1])):
        for i, (plab, pop) in enumerate(left):
            if plab == lab and (pop.startswith(op) or op.startswith(pop)):
                del left[i]
                hits += 1
                break
    return hits


def norm_event(s):
    """Normalize an event line to a comparable prefix."""
    s = unicodedata.normalize("NFC", s or "").strip()
    s = re.sub(r"^[–—\-(\s]+", "", s)
    s = re.sub(r"\s+", " ", s).casefold()
    return s[:20]


def multiset_overlap(a, b):
    """Size of the multiset intersection."""
    ca, cb = Counter(a), Counter(b)
    return sum(min(ca[k], cb[k]) for k in ca)


def main():
    golds = sorted(GOLD_DIR.glob("gold_*.json"))
    if not golds:
        sys.exit(f"No gold files in {GOLD_DIR}")

    corpus = pd.concat([pd.read_parquet(p) for p in sorted(BLOCKS_DIR.glob("*.parquet"))],
                       ignore_index=True)
    parser_version = corpus["parser_version"].iloc[0]

    rows = []
    for path in golds:
        gold = json.loads(path.read_text(encoding="utf-8"))
        page = gold["page"]
        # NFC-normalize both sides: macOS stores filenames NFD, annotators type NFC
        want = unicodedata.normalize("NFC", gold["pdf"])
        sess = corpus[corpus.source_pdf.map(lambda s: unicodedata.normalize("NFC", s)) == want]
        if sess.empty:
            print(f"!! no parsed session for {gold['pdf']} — skipping {path.name}")
            continue

        on_page = sess[sess.pages.apply(lambda ps: page in list(ps))]
        is_appendix = not gold["utterance_starts"] and "append" in (gold.get("notes") or "").lower()

        # utterance starts: turns (turn_id groups) whose FIRST segment begins on
        # the target page — segments resuming after an event share a turn_id
        speech = sess[sess.type == "speech"]
        firsts = speech.loc[speech.groupby("turn_id").seq.idxmin()]
        starts = firsts[firsts.pages.apply(lambda ps: list(ps)[0] == page)]
        parser_labels = [norm_label(x) for x in starts.speaker_raw.tolist()]
        gold_labels = [norm_label(u["speaker_label"]) for u in gold["utterance_starts"]]
        tp = multiset_overlap(parser_labels, gold_labels)

        # the same comparison with the turn's own opening words carried along,
        # so a right label in the wrong place stops counting as a hit
        parser_pairs = [(norm_label(l), norm_opening(t))
                        for l, t in zip(starts.speaker_raw.tolist(), starts.text.tolist())]
        gold_pairs = [(norm_label(u["speaker_label"]), norm_opening(u.get("first_words")))
                      for u in gold["utterance_starts"]]
        tp_words = opening_overlap(parser_pairs, gold_pairs)

        # events overlapping the page
        parser_events = [norm_event(x) for x in on_page[on_page.type == "event"].text.tolist()]
        gold_events = [norm_event(x) for x in gold["events"]]
        etp = multiset_overlap(parser_events, gold_events)

        rows.append({
            "gold_file": path.name,
            "pdf": gold["pdf"],
            "page": page,
            "appendix_page": is_appendix,
            "gold_utt": len(gold_labels),
            "parser_utt": len(parser_labels),
            "utt_tp": tp,
            "utt_tp_words": tp_words,
            "gold_events": len(gold_events),
            "parser_events": len(parser_events),
            "event_tp": etp,
            "speech_rows_on_page": int((on_page.type == "speech").sum()),
        })

    df = pd.DataFrame(rows)
    df.to_csv(OUT_PATH, index=False)

    # aggregates (debate pages only for utterance scores)
    deb = df[~df.appendix_page]
    up = deb.utt_tp.sum() / max(deb.parser_utt.sum(), 1)
    ur = deb.utt_tp.sum() / max(deb.gold_utt.sum(), 1)
    uf1 = 2 * up * ur / max(up + ur, 1e-9)
    wp = deb.utt_tp_words.sum() / max(deb.parser_utt.sum(), 1)
    wr = deb.utt_tp_words.sum() / max(deb.gold_utt.sum(), 1)
    wf1 = 2 * wp * wr / max(wp + wr, 1e-9)
    ep = df.event_tp.sum() / max(df.parser_events.sum(), 1)
    er = df.event_tp.sum() / max(df.gold_events.sum(), 1)
    leak = df[df.appendix_page].speech_rows_on_page.sum()

    print(f"Gold evaluation — parser {parser_version}, {len(df)} pages "
          f"({int(df.appendix_page.sum())} appendix)")
    print(f"  Utterance boundary+attribution: P={up:.3f} R={ur:.3f} F1={uf1:.3f} "
          f"({int(deb.utt_tp.sum())}/{int(deb.gold_utt.sum())} gold turns matched)")
    print(f"  ...with the turn's opening words too: P={wp:.3f} R={wr:.3f} F1={wf1:.3f} "
          f"({int(deb.utt_tp_words.sum())}/{int(deb.gold_utt.sum())} matched)")
    print(f"  Events: P={ep:.3f} R={er:.3f} "
          f"({int(df.event_tp.sum())}/{int(df.gold_events.sum())} gold events matched)")
    print(f"  Appendix leakage: {int(leak)} speech rows on appendix pages")
    print("  Both scores are multiset comparisons within a page: they ask whether\n"
          "  the same turns were found, not whether they came out in the same order.")
    print(f"\nPer-page detail: {OUT_PATH}")
    worst = deb.assign(miss=deb.gold_utt - deb.utt_tp).sort_values("miss", ascending=False).head(5)
    print("\nWorst pages by missed gold turns:")
    print(worst[["pdf", "page", "gold_utt", "parser_utt", "utt_tp"]].to_string(index=False))


if __name__ == "__main__":
    main()
