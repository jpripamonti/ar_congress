"""Score the parser against the gold-set page annotations.

Gold files (reference/gold/gold_*.json) record what a careful reader
sees on 24 stratified pages: utterance starts (speaker label + first
words), stenographer events, headings, furniture. This script compares
them with the parsed Parquet corpus:

- Utterance boundaries + attribution: multiset match of normalized
  speaker labels for turns STARTING on the page (parser: pages[0] == N)
  vs. the gold list -> precision / recall / F1.
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
    """Normalize a speaker label for comparison."""
    s = unicodedata.normalize("NFC", s or "")
    s = re.sub(r"\.\-\s*$", "", s.strip())
    s = re.sub(r"\s+", " ", s)
    return s.rstrip(".").casefold()


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
    ep = df.event_tp.sum() / max(df.parser_events.sum(), 1)
    er = df.event_tp.sum() / max(df.gold_events.sum(), 1)
    leak = df[df.appendix_page].speech_rows_on_page.sum()

    print(f"Gold evaluation — parser {parser_version}, {len(df)} pages "
          f"({int(df.appendix_page.sum())} appendix)")
    print(f"  Utterance boundary+attribution: P={up:.2f} R={ur:.2f} F1={uf1:.2f} "
          f"({int(deb.utt_tp.sum())}/{int(deb.gold_utt.sum())} gold turns matched)")
    print(f"  Events: P={ep:.2f} R={er:.2f} "
          f"({int(df.event_tp.sum())}/{int(df.gold_events.sum())} gold events matched)")
    print(f"  Appendix leakage: {int(leak)} speech rows on appendix pages")
    print(f"\nPer-page detail: {OUT_PATH}")
    worst = deb.assign(miss=deb.gold_utt - deb.utt_tp).sort_values("miss", ascending=False).head(5)
    print("\nWorst pages by missed gold turns:")
    print(worst[["pdf", "page", "gold_utt", "parser_utt", "utt_tp"]].to_string(index=False))


if __name__ == "__main__":
    main()
