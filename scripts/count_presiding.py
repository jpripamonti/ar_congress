"""How many sittings had more than one person in the chair, by their own cover page.

WHY THIS EXISTS. Most speech from the chair is recorded under an office and no
name — "Sr. Presidente" — and the corpus deliberately leaves those turns without
a person, because the chair changes hands mid-sitting and the page never says
when. The claim behind that decision needs a number, and the number has to be
one anybody can recompute: the cover page of each transcript names who presided,
and usually names more than one.

TWO COVER-PAGE FORMATS, and a count that must handle both.

The older one is a sentence: "Presidencia del señor vicepresidente de la Nación,
D. Amado Boudou, y de la señora presidenta provisional del H. Senado, senadora
Beatriz Rojkés de Alperovich". Officers are counted by the courtesy title that
introduces each one, with the offices named as a fallback for the pages that
drop the courtesy.

From about mid-2020 the Senate replaced it with a list under the heading
"AUTORIDADES", where each office is a label and the name sits on the line below:
"Presidencia del Senado / Victoria Villarruel / Presidencia Provisional /
Bartolomé Esteban Abdala / Vicepresidencia / Silvia Sapag / …". These pages
never contain the sentence, so a count that only looks for it reads five
officers as one, or as none — which is what the first version of this script did
for every sitting after mid-2020.

A sitting whose cover page carries neither form is reported separately and never
guessed at.
"""
import glob
import sys
import re
import unicodedata
import warnings
from pathlib import Path

import pdfplumber

sys.path.insert(0, str(Path(__file__).resolve().parent))
from extract_authorities import html_cover_text  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = REPO_ROOT / "data" / "raw" / "senado" / "taquigraficas"
FRONT_PAGES = 8          # the cover, plus the title pages some formats run first

# the sentence format: everything from "presidencia" to the secretaries
SENTENCE = re.compile(r"presidencia\s*(.*?)(?:secretari|prosecretari"
                      r"|presentes|sumario|$)")
BY_COURTESY = re.compile(r"\b(?:del senor|de la senora|y del|y de la)\b")
# "vicepresidente 1o del honorable senado" is one officer, not two; the office
# words are matched with whatever follows them so each officer counts once
BY_OFFICE = re.compile(r"\b(?:vicepresidente|vicepresidenta"
                       r"|presidente|presidenta)\s+"
                       r"(?:[0-9]\S{0,8}\s+)?"      # "vicepresidente 2o del H. Senado"
                       r"(?:provisional|de la nacion|del h|del honorable|de la comision)")

# the list format: each office is its own label, the name follows on the next line
LABEL = re.compile(r"\b(?:vice)?presidencia\b")
LIST_START = re.compile(r"\bautoridades\b")
LIST_END = re.compile(r"\b(?:secretaria|prosecretaria|presentes|sumario)\b")


def flatten(text):
    """Lower-case, strip accents, and close up the letter-spaced headings."""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c)).lower()
    text = re.sub(r"\b(?:[a-z]\s){3,}[a-z]\b",
                  lambda m: m.group(0).replace(" ", ""), text)   # "a u t o r i d a d e s"
    return re.sub(r"\s+", " ", text)


def officers_named(path):
    """How many people the cover page says presided, or None if it does not say."""
    if str(path).lower().endswith(".html"):
        # The 1998-2003 holdings are HTML, and read through the same helper the
        # authorities extraction uses, so the count covers one corpus and not
        # one format of it.
        text = html_cover_text(Path(path).read_bytes())
    else:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            with pdfplumber.open(path) as pdf:
                text = " ".join((p.extract_text() or "") for p in pdf.pages[:FRONT_PAGES])
    flat = flatten(text)

    start = LIST_START.search(flat)
    if start:
        rest = flat[start.end():]
        end = LIST_END.search(rest)
        block = rest[:end.start()] if end else rest[:600]
        labels = len(LABEL.findall(block))
        if labels:
            return labels

    m = SENTENCE.search(flat)
    if not m:
        return None
    segment = m.group(1)
    end = re.search(r"\b(?:secretari|presentes|sumario)", segment)
    if end:
        segment = segment[:end.start()]
    # the offices are the surer count: a page may drop the courtesy on the first
    # officer ("Presidencia del vicepresidente de la Nación…") but never the office
    return max(len(BY_OFFICE.findall(segment)), len(BY_COURTESY.findall(segment)), 1)


def main():
    files = sorted(glob.glob(str(RAW_DIR / "*.pdf")) + glob.glob(str(RAW_DIR / "*.html")))
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
