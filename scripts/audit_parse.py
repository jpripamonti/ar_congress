"""Audit the parsed corpus against the source PDFs — every session, not a sample.

The gold set answers "did the parser read these 36 pages the way a careful
reader does?" — 0.08% of the corpus. This answers the questions that can be
checked everywhere, by looking for things that must never happen:

1. LEAKAGE — page apparatus inside a speech turn. Mastheads, datelines,
   attendance rolls and the stenographers' office line are printed furniture;
   a speaker never utters them, so finding one inside a turn means the
   header/footer strip missed a page. Counted as a fault, not merely printed:
   the one page whose footer landed inside a senator's question was on the
   screen for weeks while the audit went on reporting nothing wrong.
2. GLUED LABELS — a complete printed speaker label sitting inside a turn's
   text. This is the worst error the parser can make: it means a change of
   speaker went undetected, so one senator is credited with another's words.
3. CONSERVATION — every block's text must be findable in the source PDF, and
   no document may yield more text than it prints. This catches text invented
   or written out twice by the block splitting and merging.
4. COVERAGE — how much of each document's printed text survives into the
   output. Front matter, attendance rolls and appendices are dropped on
   purpose, so this is a distribution to inspect, not a pass/fail.
5. ONE PERSON PER LABEL — a (sitting, label) pair must resolve to exactly one
   person.
6. SHAPE — does a turn begin and end like something a person said? Every text
   fault found so far has lived at the edge of a block, where the printed face
   changes mid-name or mid-word: a label cut in half ("Sra. Higone" and a turn
   opening "t. – Gracias."), a note that kept the first letters of the sentence
   it interrupted, a scrap of an editorial note left as a two-character turn.
   The conservation check looks inside blocks and never at their first and last
   characters, so nothing else asks this.

Sessions that are scans with OCR text are reported first and excluded from the
counts: their faults belong to the scan, not to the parser.

Checks 1, 2 and 5 read only the parsed output and are fast. Checks 3 and 4
re-extract every PDF; pass --skip-source to leave them out.

Usage:
    uv run scripts/audit_parse.py               # everything
    uv run scripts/audit_parse.py --skip-source # output-only checks
    uv run scripts/audit_parse.py --sample 40   # also write a human review sheet
"""

import argparse
import csv
import hashlib
import re
import sys
import unicodedata
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import pandas as pd
import pdfplumber

REPO_ROOT = Path(__file__).resolve().parents[1]
BLOCKS_DIR = REPO_ROOT / "data" / "processed" / "senado" / "blocks"
RAW_DIR = REPO_ROOT / "data" / "raw" / "senado" / "taquigraficas"
OUT_DIR = REPO_ROOT / "data" / "processed" / "senado"
SPEAKERS = OUT_DIR / "speakers.parquet"

# Printed apparatus. None of it is ever spoken, so none of it may appear
# inside a speech turn.
FURNITURE = {
    "dateline (Pág. N)": re.compile(r"P[áa]g\.\s*\d+"),
    "stenographers' office": re.compile(r"Direcci[óo]n General de Taquígrafos"),
    "masthead": re.compile(r"VERSI[ÓO]N TAQUIGR[ÁA]FICA|C[ÁA]MARA DE SENADORES DE LA NACI[ÓO]N"),
    "sitting header": re.compile(r"\d+[ªº°]\s*Reuni[óo]n\s*[-–]\s*\d+[ªº°]?\s*Sesi[óo]n"),
    "presiding-officer block": re.compile(r"Presidencia del se[ñn]or (?:vice)?presidente"),
    "attendance roll heading": re.compile(r"\bPRESENTES\b|\bAUSENTES\b"),
    # printed at body size below the rule at the foot of the page, so nothing
    # about its type or position distinguishes it from speech
    "appendix-pointer footnote": re.compile(r"\bVer el Ap[eé]ndice\b"),
}
# A complete printed label — title, name, ". —" terminator — inside a turn.
GLUED_LABEL = re.compile(r"(?<![A-Za-zÁÉÍÓÚÑ])(?:Sr|Sra|Srta)\.\s+[A-ZÁÉÍÓÚÑ][^.]{1,45}?\.\s*[–—−─]\s")


def flatten(text):
    """Comparison key: no whitespace, no accents, no case.

    Spacing cannot be part of the comparison. The parser reads characters in
    order, while pdfplumber's page text inserts spaces from the layout, so the
    same passage comes out as "de la" one way and "dela" the other. Removing
    whitespace on both sides compares the letters actually printed.
    """
    s = unicodedata.normalize("NFD", str(text or "").casefold())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^0-9a-z]", "", s)


def block_probes(text, width=40):
    """Windows from inside one block, to look up in the source.

    Taken from a single block and not from the concatenated output: joining
    blocks would create adjacencies the page never printed — an event and the
    speech after it sit side by side in the output but a line apart on the
    page — and every such join would look like text from nowhere.

    Three windows rather than one, and the block counts as located if ANY is
    found, because a turn legitimately spans joins of its own: the parser
    merges a speaker's consecutive paragraphs and drops the section heading
    printed between them, so a window landing on that seam exists in no
    single place in the source even though every word does.
    """
    flat = flatten(text)
    if len(flat) < width + 12:
        return []                         # too short to locate reliably
    spots = {10, max(10, (len(flat) - width) // 2), max(10, len(flat) - width - 1)}
    return [flat[i:i + width] for i in sorted(spots)]


def audit_source(args):
    """One session: is its output text really the source's text?"""
    session_id, pdf_name, texts = args
    try:
        with pdfplumber.open(RAW_DIR / pdf_name) as pdf:
            src = flatten("".join((p.extract_text() or "") for p in pdf.pages))
    except Exception as exc:
        return {"session_id": session_id, "error": str(exc)[:70]}
    out = flatten("".join(texts))
    probed = located = 0
    example = ""
    for t in texts:
        windows = block_probes(t)
        if not windows:
            continue
        probed += 1
        if any(w in src for w in windows):
            located += 1
        elif not example:
            example = windows[0]
    foreign = probed - located
    return {
        "session_id": session_id,
        "source_chars": len(src),
        "output_chars": len(out),
        "blocks_probed": probed,
        # >1 means the parser emitted more text than the page prints, which can
        # only happen if a block was written out twice
        "duplication_ratio": len(out) / max(len(src), 1),
        # passages in the output that the source does not contain at all
        "foreign_passage_share": foreign / max(probed, 1),
        "foreign_example": example,
        "coverage": len(out) / max(len(src), 1),
        "error": None,
    }


def report_scanned(corpus):
    """Sessions whose text came from OCR over a scan, not from the typesetting.

    Nothing downstream can repair those, so they are listed first: every other
    check will find faults in them that are the scan's, not the parser's.
    """
    stats_path = OUT_DIR / "parse_stats.csv"
    if not stats_path.exists():
        return set()
    stats = pd.read_csv(stats_path)
    if "scanned_page_share" not in stats:
        return set()
    scanned = stats[stats.scanned_page_share.fillna(0) > 0.5]
    print(f"\n{'='*66}\nSCANNED SESSIONS — text from OCR, unreliable by nature\n{'='*66}")
    if scanned.empty:
        print("   none: every session is born-digital text")
        return set()
    for _, r in scanned.iterrows():
        print(f"   {r.scanned_page_share:.0%} of pages scanned  {r.session_id}")
    print("   Faults reported below for these sessions are the scan's, not the parser's.")
    return set(scanned.session_id)


def load_corpus():
    frames = []
    for p in sorted(BLOCKS_DIR.glob("*.parquet")):
        frames.append(pd.read_parquet(p, columns=[
            "session_id", "session_date", "source_pdf", "type", "turn_id",
            "speaker_raw", "text", "pages"]))
    if not frames:
        sys.exit(f"No parsed sessions under {BLOCKS_DIR}")
    return pd.concat(frames, ignore_index=True)


def check_output_only(corpus, scanned):
    speech = corpus[corpus.type == "speech"]
    print(f"\n{'='*66}\nOUTPUT CHECKS — {len(speech):,} speech turns in "
          f"{corpus.session_id.nunique()} sessions\n{'='*66}")

    print("\n1. Page apparatus found inside a speech turn (must be 0 outside the scans):")
    worst = []
    leaked = 0
    for name, rx in FURNITURE.items():
        hit = speech[speech.text.astype(str).str.contains(rx, na=False)]
        clean = hit[~hit.session_id.isin(scanned)]
        leaked += len(clean)
        print(f"   {len(clean):6}  {name}"
              f"{f'  (+{len(hit) - len(clean)} in scanned sessions)' if len(hit) != len(clean) else ''}")
        hit = clean
        for _, r in hit.head(2).iterrows():
            m = rx.search(str(r.text))
            worst.append((name, r.session_id, str(r.text)[max(0, m.start()-50):m.end()+35]))
    for name, sess, snippet in worst:
        print(f"          [{sess}] ...{snippet.strip()}...")

    print("\n2. A second speaker's label glued inside a turn (must be 0):")
    glued_all = speech[speech.text.astype(str).str.contains(GLUED_LABEL, na=False)]
    glued = glued_all[~glued_all.session_id.isin(scanned)]
    print(f"   {len(glued):6}  turns carrying another speaker's label"
          f"{f'  (+{len(glued_all) - len(glued)} in scanned sessions)' if len(glued_all) != len(glued) else ''}")
    for _, r in glued.head(5).iterrows():
        m = GLUED_LABEL.search(str(r.text))
        print(f"          [{r.session_id}] attributed to {r.speaker_raw!r}")
        print(f"              ...{str(r.text)[max(0, m.start()-45):m.end()+40].strip()}...")

    other = corpus[corpus.type == "other"]
    print(f"\n3. Text the parser could not attribute to anyone: {len(other):,} rows "
          f"({len(other)/max(len(corpus),1):.2%} of all rows)")
    top = other.groupby("session_id").size().sort_values(ascending=False).head(5)
    for sess, n in top.items():
        print(f"          {n:5}  {sess}")
    return leaked + len(glued)


def check_turn_shape(corpus, scanned):
    """Turns that do not begin or end the way speech does.

    A turn opening in lower case is not by itself a fault: a note interrupts a
    sentence and the sentence resumes, and an answer can echo the question. What
    is reported is the case with nothing to explain it — the block before is not
    a note — because that is the shape a name cut in half leaves behind.
    """
    print("\n6. Turns that do not begin or end like speech:")
    mid_word, scrap, dangling = [], [], []
    for sid, g in corpus.groupby("session_id"):
        if sid in scanned:
            continue
        g = g.reset_index(drop=True)
        for i, b in g.iterrows():
            if b.type != "speech":
                continue
            s = " ".join(str(b.text).split())
            if not s:
                continue
            if len(s) <= 3 and not re.fullmatch(r"(Sí|No|Ya)\.?", s):
                scrap.append((sid, b.speaker_raw, s))
            if re.search(r"[—–\-,;]$", s):
                dangling.append((sid, b.speaker_raw, s[-45:]))
            if i and re.match(r"^[a-záéíóúñ]", s) and g.loc[i - 1].type != "event":
                j = i - 1
                while j >= 0 and g.loc[j].type != "speech":
                    j -= 1
                if j >= 0 and g.loc[j].speaker_raw != b.speaker_raw:
                    mid_word.append((sid, b.speaker_raw, s[:60]))
    for name, group in (("a turn opening mid-word under a new speaker", mid_word),
                        ("a turn of three characters or fewer", scrap),
                        ("a turn ending on a dash or comma", dangling)):
        print(f"   {len(group):6}  {name}")
        for sid, sp, s in group[:4]:
            print(f"          [{sid}] {sp!r}: {s!r}")
    return len(mid_word)


def check_attribution_windows(corpus):
    """No turn may be credited to someone the record places outside the office."""
    if not SPEAKERS.exists():
        print("\n7. Attribution windows: speakers.parquet not found — skipped")
        return 0
    sp = pd.read_parquet(SPEAKERS)
    bad = 0
    print("\n7. Attribution outside the person's mandate or tenure:")
    named = sp[sp.person_id.notna()]
    print(f"   {len(named):6}  (session, label) pairs carry a person")
    # The resolver filters by date when it matches, so a violation here means
    # a rule changed without the check being re-run.
    counts = named.groupby("match_status").n_blocks.sum()
    for status, n in counts.items():
        print(f"          {n:7,}  {status}")
    dupes = named.groupby(["session_id", "speaker_raw"]).size()
    if (dupes > 1).any():
        bad += int((dupes > 1).sum())
        print(f"   !! {bad} (session, label) pairs resolved more than once")
    else:
        print("   ok    every (session, label) pair resolves to exactly one person")
    return bad


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--skip-source", action="store_true",
                    help="skip the checks that re-extract every PDF")
    ap.add_argument("--sample", type=int, default=0,
                    help="also write a review sheet of N turns for a human to check")
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()

    corpus = load_corpus()
    scanned = report_scanned(corpus)
    problems = check_output_only(corpus, scanned)
    problems += check_turn_shape(corpus, scanned)
    problems += check_attribution_windows(corpus)

    if not args.skip_source:
        print(f"\n{'='*66}\nSOURCE CHECKS — re-extracting every PDF\n{'='*66}")
        speech = corpus[corpus.type.isin(["speech", "event", "heading"])]
        jobs = [(sid, g.source_pdf.iloc[0], g.text.tolist())
                for sid, g in speech.groupby("session_id")]
        rows = []
        with ProcessPoolExecutor(max_workers=args.workers) as pool:
            futures = [pool.submit(audit_source, j) for j in jobs]
            for i, fut in enumerate(as_completed(futures), 1):
                rows.append(fut.result())
                if i % 100 == 0:
                    print(f"   {i}/{len(jobs)} sessions compared")
        df = pd.DataFrame(rows)
        errs = df[df.error.notna()]
        df = df[df.error.isna()]
        out_path = OUT_DIR / "audit_source.csv"
        df.to_csv(out_path, index=False)

        df["scanned"] = df.session_id.isin(scanned)
        foreign = df[(df.foreign_passage_share > 0.01) & ~df.scanned]
        print("\n8. Blocks whose text is not found in the source PDF:")
        print(f"   {int(df.blocks_probed.sum()):,} blocks probed across {len(df)} sessions; "
              f"{df.foreign_passage_share.mean():.3%} not located on average")
        print(f"   {len(foreign)} sessions above 1%, scans aside")
        for _, r in foreign.sort_values("foreign_passage_share", ascending=False).head(5).iterrows():
            print(f"          {r.foreign_passage_share:6.2%}  {r.session_id}")
        problems += len(foreign)

        dup = df[df.duplication_ratio > 1.02]
        print("\n9. Sessions whose output is longer than the page it came from "
              "(text written out twice):")
        print(f"   {len(dup)} of {len(df)}")
        for _, r in dup.sort_values("duplication_ratio", ascending=False).head(5).iterrows():
            print(f"          {r.duplication_ratio:5.2f}x  {r.session_id}")
        problems += len(dup)

        print(f"\n10. Share of each document's printed text kept in the output:")
        q = df.coverage.quantile([0.05, 0.25, 0.5, 0.75, 0.95])
        for k, v in q.items():
            print(f"          p{int(k*100):02d}  {v:.1%}")
        print("   (front matter, attendance rolls and appendices are dropped on purpose)")
        low = df.nsmallest(5, "coverage")
        print("   lowest-coverage sessions, worth an eye:")
        for _, r in low.iterrows():
            print(f"          {r.coverage:.1%}  {r.session_id}")
        if len(errs):
            print(f"\n   !! {len(errs)} PDFs could not be re-read")
        print(f"\n   per-session detail: {out_path}")

    if args.sample:
        write_review_sheet(corpus, args.sample, scanned)

    print(f"\n{'='*66}")
    print("Audit complete." if not problems else
          f"Audit complete — {problems} thing(s) above need a look.")
    return 1 if problems else 0


def write_review_sheet(corpus, n, scanned=frozenset()):
    """Sample turns to be checked by eye against the printed page.

    The invariants above cannot tell whether the RIGHT person is behind the
    words — only that no rule was broken. That needs eyes on the page, so
    this writes a sheet of randomly drawn turns, spread across the years,
    each with the session, the page to open, who the parser says is speaking,
    and the opening words to look for.

    The scanned sittings are left out: their text is a guess the reader cannot
    check against, so drawing from them measures the scan and not the parser.

    Each turn is drawn on the strength of its OWN content, not its position in
    the table: the sitting, the page and its first words are hashed with a fixed
    seed, and the lowest hashes per year are taken. That matters because a
    parser change that adds or removes unrelated rows would otherwise shift
    every row number and redraw the whole sheet, throwing away the reading
    already done on it. This way a turn that survives a change keeps its place,
    and only turns that actually changed have to be read again.

    The sheet also names the page where the turn OPENS. A turn can begin several
    pages before the words quoted here — a long speech has no label on its
    later pages — and without that, a reader looking only at the quoted page
    finds no speaker at all and cannot answer.
    """
    speech = corpus[(corpus.type == "speech")
                    & ~corpus.session_id.isin(scanned)].copy()
    speech["year"] = speech.session_date.str[:4]
    first_page = {}
    for (sid, turn), g in speech.groupby(["session_id", "turn_id"]):
        pages = [int(p) for row in g.pages for p in row]
        first_page[(sid, turn)] = min(pages) if pages else ""

    def sample_key(r):
        opening = " ".join(str(r.text).split()[:14])
        page = list(r.pages)[0] if len(r.pages) else ""
        seed = f"20260728|{r.session_id}|{page}|{opening[:60]}"
        return int.from_bytes(hashlib.blake2b(seed.encode(), digest_size=7).digest(), "big")

    speech["_key"] = speech.apply(sample_key, axis=1)
    per_year = max(1, n // speech.year.nunique())
    picks = []
    for _, g in speech.groupby("year"):
        picks += list(g.nsmallest(min(per_year, len(g)), "_key").index)
    rows = []
    for i in sorted(picks):
        r = speech.loc[i]
        rows.append({
            "session": r.session_id,
            "pdf": r.source_pdf,
            "page": list(r.pages)[0] if len(r.pages) else "",
            "turn_opens_on_page": first_page.get((r.session_id, r.turn_id), ""),
            "parser_says_speaker": r.speaker_raw,
            "opening_words": " ".join(str(r.text).split()[:14]),
            "correct? (y/n)": "",
            "if_wrong_who_spoke": "",
        })
    path = OUT_DIR / "review_sheet.csv"
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"\n{'='*66}\nHUMAN REVIEW SHEET\n{'='*66}")
    print(f"{len(rows)} turns drawn across {speech.year.nunique()} years: {path}")
    print("Open each PDF at the page given and confirm the speaker. This is the "
          "only check that can catch the right rule applied to the wrong person.")


if __name__ == "__main__":
    sys.exit(main())
