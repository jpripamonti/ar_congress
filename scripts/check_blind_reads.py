"""Re-ask every blind read whether its answer still holds.

`reference/verification/blind_read_*.csv` holds nine rounds in which a reader
was shown a rendered page and asked who was speaking, without ever being shown
the parser's answer — 5,463 turns across 506 sittings. Each row records the
sitting, the page, the words the reader quoted, and what the parser said at the
time. The release checklist has always required that those answers still stand
in the re-parsed corpus, and nothing implemented the check: the rounds were run
by hand, months and a dozen parser versions ago.

This asks the question the records were made for — is the passage the reader
quoted still attributed to the same person? — and it is the only check in the
project whose ground truth was produced without sight of the parser.

WHY THE RECORDED WORDS DO NOT ALWAYS MATCH THE CORPUS ANY MORE. The quoted
words are a snapshot of what the parser held on the day of the round, and the
rounds are what prompted the repairs that followed. A record from before 0.4.22
quotes "artículo 3(cid:47)" because the file's font declared no mapping for the
ordinal; one from before 0.4.33 quotes "artículo 7E" for the same ordinal read
as a capital E; ones from before 0.4.16 carry a letter cut off the front of the
speech ("C En consideración...") or a section number glued to its end. Those
are repairs, not regressions, and a check that reported them as failures would
report the project's own progress as damage. So the lookup is built to survive
them: the known artefacts are cut out of the quoted words, the longest surviving
fragment becomes the key, and it is looked up in three windows so that anything
split off either end since does not defeat it.

A short quote is a different problem and not a repair at all. "Sí.",
"Aprobado.", "Afirmativo.", "¡Sí, juro!" — the chamber says these on every
other page, so the words cannot pin the turn down. Those are matched as the
whole turn on the page the round wrote down, which is exact, and 94 of the 96
short quotes resolve that way.

Two kinds are reported and are not failures: a quote of three characters, all
an unmapped font left of a passage ("E 26"), which nothing can locate; and a
passage a repair has moved out of speech altogether — the note "— Se practica
la votación por medios electrónicos.", which the corpus once had the chair
saying out loud.

Only one thing counts as a failure: the passage is there, and somebody else is
now credited with it.

Usage:
    uv run scripts/check_blind_reads.py

Output: data/processed/senado/blind_read_check.csv — one row per record with
its verdict — plus a printed summary. Exit status is the number of failures.
"""

import argparse
import csv
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
RECORDS_DIR = REPO_ROOT / "reference" / "verification"
BLOCKS_DIR = REPO_ROOT / "data" / "processed" / "senado" / "blocks"
OUT_PATH = REPO_ROOT / "data" / "processed" / "senado" / "blind_read_check.csv"

# Extraction faults the parser has since been repaired for, in the order they
# were found: a font with no Unicode map (0.4.22), characters landing in the
# private-use area (0.4.21), and the ordinal "º" read as a capital E after the
# number it marks (0.4.28-0.4.33). A quoted passage is cut at these, not
# through them, because what sits on either side is the text the page prints.
REPAIRED_ARTEFACT = re.compile(r"\(cid:\d+\)|[-]|(?<=\d)E\b")

WINDOW = 24      # long enough to be unique in a sitting
MIN_KEY = 12     # under this, the record quotes a fragment, not a passage


def flatten(text):
    """Comparison key: no whitespace, no accents, no case, no punctuation.

    The same key the corpus audit uses. Spacing cannot be part of the
    comparison — the records were typed by a reader from a rendered page and
    the corpus stores what the file's own character stream says — and neither
    can punctuation, which several of the repairs moved.
    """
    s = unicodedata.normalize("NFD", str(text or "").casefold())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^0-9a-z]", "", s)


def search_key(quoted):
    """The longest run of the quoted words that no later repair rewrote."""
    parts = [p for p in REPAIRED_ARTEFACT.split(str(quoted or "")) if p]
    return max((flatten(p) for p in parts), key=len, default="")


def probes(key):
    """Windows to look the key up by, or the whole key when it is short.

    Three windows rather than one, because a repair can have taken something
    off either end of the quoted passage since it was recorded: a section
    number that used to be glued to its last sentence, a letter cut off the
    speaker's label and left at its front. A window from the middle survives
    both.
    """
    if len(key) < WINDOW:
        return [key]
    spots = sorted({0, (len(key) - WINDOW) // 2, len(key) - WINDOW})
    return [key[i:i + WINDOW] for i in spots]


def same_person(recorded, found):
    """Whether the label found is the one the round recorded.

    Not string equality: before 0.4.16 a label could keep a letter that
    belonged to the speech after it, and the round recorded the label as it
    then stood ("Sr. Presidente (Pinedo).- C"). The repair gave the letter
    back to the sentence, so the recorded label starts with the current one
    and names the same person.
    """
    a, b = flatten(recorded), flatten(found)
    return a == b or a.startswith(b) or b.startswith(a)


def load_records():
    """Every round's records, oldest file first, tagged with where it came from."""
    rows = []
    for path in sorted(RECORDS_DIR.glob("blind_read_*.csv")):
        with path.open(encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                r["round"] = path.name
                rows.append(r)
    if not rows:
        sys.exit(f"No blind-read records in {RECORDS_DIR}")
    return rows


def verdict_for(record, found, where):
    """Whether the people now credited include the one the round recorded."""
    if any(same_person(record["parser_speaker"], s) for s in found):
        return "holds", record["parser_speaker"], where
    # a speech row always carries a label — the audit checks that — but the
    # verdict must survive one that does not rather than stop the whole run
    return "CHANGED", " | ".join(sorted(str(s) for s in found)), where


def judge(record, blocks):
    """One record against the sitting it was drawn from.

    Returns (verdict, who the corpus now credits, where it was found).
    """
    key = search_key(record["opening_words"])
    if not key:
        return "no words recorded", "", ""

    try:
        page = int(record["page"])
    except (ValueError, TypeError):
        page = None

    speech = [b for b in blocks if b.type == "speech"]
    on_page = [b for b in speech if page is None or page in b.page_set]

    # A quote of a few words is a whole short turn — "Sí.", "Aprobado.",
    # "Afirmativo.", "¡Sí, juro!" — and the words on their own cannot pin it
    # down, because the chamber says them on every other page. Matched as the
    # whole turn instead, on the page the round wrote down. 94 of the 96 short
    # quotes are these; the two that are not are all an unmapped font left of
    # a passage ("E 26"), and nothing can locate those.
    if len(key) < WINDOW:
        whole = {b.speaker_raw for b in on_page if b.flat_text == key}
        if whole:
            return verdict_for(record, whole, "whole turn on the page")
        if len(key) < MIN_KEY:
            return "quote too damaged to locate", "", ""

    windows = probes(key)

    def matches(rows):
        return [(row.speaker_raw, row.type) for row in rows
                if any(w in row.flat_text for w in windows)]

    for where, pool in (("page", on_page), ("sitting", speech)):
        hits = matches(pool)
        if hits:
            return verdict_for(record, {s for s, _ in hits}, where)

    # not speech any more: a repair moved it to the stenographer's notes
    elsewhere = matches([b for b in blocks if b.type != "speech"])
    if elsewhere:
        return "moved out of speech", elsewhere[0][1], "sitting"
    return "passage not found", "", ""


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=OUT_PATH)
    args = ap.parse_args()

    records = load_records()
    by_sitting = defaultdict(list)
    for r in records:
        by_sitting[r["session"]].append(r)

    verdicts = Counter()
    rows = []
    for sitting, group in sorted(by_sitting.items()):
        path = BLOCKS_DIR / f"{sitting}.parquet"
        if not path.exists():
            for r in group:
                verdicts["sitting missing from the corpus"] += 1
                rows.append({**{k: r[k] for k in
                                ("round", "case", "session", "page", "parser_speaker")},
                             "verdict": "sitting missing from the corpus",
                             "now_credited_to": "", "found_on": ""})
            continue
        df = pd.read_parquet(path)
        df["flat_text"] = df.text.map(flatten)
        df["page_set"] = df.pages.map(lambda ps: {int(p) for p in ps})
        blocks = list(df.itertuples(index=False))
        for r in group:
            verdict, who, where = judge(r, blocks)
            verdicts[verdict] += 1
            rows.append({"round": r["round"], "case": r["case"], "session": r["session"],
                         "page": r["page"], "parser_speaker": r["parser_speaker"],
                         "verdict": verdict, "now_credited_to": who, "found_on": where})

    out = pd.DataFrame(rows)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.out, index=False)

    parser_version = "unknown"
    for path in sorted(BLOCKS_DIR.glob("*.parquet"))[:1]:
        parser_version = pd.read_parquet(path, columns=["parser_version"]).iloc[0, 0]

    print(f"Blind reads re-checked — parser {parser_version}, {len(records):,} records "
          f"from {len(sorted(RECORDS_DIR.glob('blind_read_*.csv')))} rounds "
          f"across {len(by_sitting)} sittings\n")
    for verdict, n in verdicts.most_common():
        print(f"  {n:6,}  {verdict}")

    failures = verdicts["CHANGED"] + verdicts["passage not found"] \
        + verdicts["sitting missing from the corpus"]
    if failures:
        print("\nThe answers that no longer hold:")
        bad = out[out.verdict.isin(["CHANGED", "passage not found",
                                    "sitting missing from the corpus"])]
        for _, r in bad.iterrows():
            print(f"  [{r['round']}#{r['case']}] {r['session']} p{r['page']}: "
                  f"recorded {r['parser_speaker']!r} -> {r['verdict']} "
                  f"{r['now_credited_to']!r}")
    else:
        print("\nEvery answer still resolves to the person the round recorded.")

    soft = (verdicts["quote too damaged to locate"] + verdicts["moved out of speech"]
            + verdicts["no words recorded"])
    if soft:
        print(f"\n{soft} record(s) could not be re-asked, and are not failures: a "
              f"passage quoted as the few characters an unmapped font left of it, "
              f"or one a repair has since moved out of speech. They are listed in "
              f"the output with their reason.")

    print(f"\nPer-record detail: {args.out}")
    return failures


if __name__ == "__main__":
    sys.exit(main())
