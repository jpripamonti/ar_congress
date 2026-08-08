"""How many sittings had more than one person in the chair, by their own cover page.

WHY THIS EXISTS. Most speech from the chair is recorded under an office and no
name — "Sr. Presidente" — and the corpus deliberately leaves those turns without
a person, because the chair changes hands mid-sitting and the page never says
when. The claim behind that decision needs a number, and the number has to be
one anybody can recompute: the cover page of each transcript names who presided,
and often names two or three.

WHAT IT COUNTS. The block that begins "Presidencia" on the first pages, up to
the secretaries' line. Officers inside it are counted by the courtesy title that
introduces each one ("del señor …, y de la señora …"), falling back to the roles
named. A sitting whose cover page carries no such line is reported separately and
never guessed at.
"""
import glob
import re
import unicodedata
import warnings
from pathlib import Path

import pdfplumber

REPO_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = REPO_ROOT / "data" / "raw" / "senado" / "taquigraficas"
FRONT_PAGES = 8          # the line is on the cover, but some formats run a title page first
BLOCK = re.compile(r"presidencia (.*?)(?:secretari|prosecretari|presentes|sumario|$)")
BY_TITLE = re.compile(r"\b(?:del senor|de la senora|y del|y de la)\b")
BY_ROLE = re.compile(r"\b(?:vicepresidenta?|presidenta? provisional"
                     r"|presidenta? de la nacion|presidenta? del h\.? senado)\b")


def flatten(s):
    s = unicodedata.normalize("NFKD", str(s))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s.lower())


def officers_named(pdf_path):
    """How many people the cover page says presided, or None if it does not say."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        with pdfplumber.open(pdf_path) as pdf:
            text = " ".join((p.extract_text() or "") for p in pdf.pages[:FRONT_PAGES])
    m = BLOCK.search(flatten(text))
    if not m:
        return None
    segment = m.group(1)[:400]
    return max(len(BY_TITLE.findall(segment)), len(BY_ROLE.findall(segment)), 1)


def main():
    files = sorted(glob.glob(str(RAW_DIR / "*.pdf")))
    named, silent, multi = 0, 0, 0
    for path in files:
        n = officers_named(path)
        if n is None:
            silent += 1
            continue
        named += 1
        if n >= 2:
            multi += 1
    print(f"{len(files)} transcripts")
    print(f"  {named} name who presided on the cover page, {silent} do not")
    print(f"  {multi} of those {named} name two or more")


if __name__ == "__main__":
    main()
