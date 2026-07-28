"""Read each sitting's cover page and record who held each chamber office.

Every versión taquigráfica opens with the same masthead: who presided, and
who sat at the secretaries' table, with full names —

    Presidencia del señor vicepresidente de la Nación, D. Julio César Cleto
    Cobos, y del señor presidente provisional del H. Senado, senador José
    Juan Bautista Pampuro
    Secretarios: señor D. Juan Héctor Estrada y señor D. Antonio Benigno Rins
    Prosecretarios: señor D. Juan J. Canals, señor D. Mario Daniele y señor
    D. Gustavo Carlos Vélez

That masthead is the primary source for the officers the speaker labels
name only by surname ("Sr. Secretario (Estrada)"). This script turns it
into one row per (session, office, person), which
`build_authorities.py` folds into tenure windows.

Output: reference/senado/authorities_observed.csv
"""

import csv
import glob
import re
import sys
import unicodedata
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import pdfplumber

REPO_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = REPO_ROOT / "data" / "raw" / "senado" / "taquigraficas"
OUT_PATH = REPO_ROOT / "reference" / "senado" / "authorities_observed.csv"

# Honorifics and academic titles printed before a name, in every spelling the
# formats use. Stripped so only the person's name is recorded.
HONORIFIC = re.compile(
    r"^(?:se[ñn]or(?:a|es)?|sra?\.?|don|do[ñn]a|D[ªº]?\.?|doctor(?:a)?|dr[a]?\.?"
    r"|licenciad[oa]|lic\.?|ingenier[oa]|ing\.?|arquitect[oa]|contador(?:a)?"
    r"|profesor(?:a)?|senador(?:a)?(?:\s+nacional)?|diputad[oa]|escriban[oa]"
    r"|elect[oa]|\(m\.c\.\))\s+",
    re.I,
)
# One masthead prints "Doctoracristina Fernández de Kirchner" with the space
# lost. Only this title is re-split, and only before a run of lower-case
# letters, so a name like "Donato" is never cut apart.
GLUED_TITLE_RE = re.compile(r"\b(doctora?)(?=[a-záéíóúñ]{3})", re.I)
# What follows the masthead: the attendance roll, under any of its headings.
# Some files split a heading mid-word ("P RESENTES"), so every letter may be
# followed by stray whitespace.
def _spaced(word):
    return r"\s*".join(re.escape(c) for c in word)


ROLL = "(?:" + "|".join(_spaced(w) for w in
                        ("presentes", "senadores", "sumario", "ausentes")) + \
       r"|orden del d[íi]a|\d+[ªº°]?\s+reuni[óo]n)"
# A masthead line names at most a handful of people; anything longer means the
# boundary was missed and the attendance roll is bleeding in.
MAX_LINE = 260
# The masthead runs "Presidencia ..." until the secretaries' line or the roll.
COVER_RE = re.compile(
    rf"presidencia\s+(?:de\s+la|del)\s+(?P<pres>.*?)"
    rf"(?=\n?\s*(?:secretari|prosecretari|{ROLL})\b|$)",
    re.I | re.S,
)
SEC_RE = re.compile(rf"\bsecretari[oa]s?\s*:\s*(?P<body>.*?)"
                    rf"(?=\n?\s*(?:prosecretari|{ROLL})\b|$)", re.I | re.S)
PROSEC_RE = re.compile(rf"\bprosecretari[oa]s?\s*:\s*(?P<body>.*?)"
                       rf"(?=\n?\s*(?:{ROLL})\b|$)", re.I | re.S)
# A comma-separated fragment that describes the post rather than naming a
# person: "…, secretario del Honorable Senado".
POST_RE = re.compile(r"^(?:pro)?secretari[oa]\b|^(?:vice)?president[ea]\b|^del?\b"
                     r"|^elect[oa]$|^h\.\s*senado", re.I)
# Where a name runs into the next sentence ("Villarruel Se encuentran…").
SENTENCE_START = {"se", "ocupa", "ocupan", "y", "en", "el", "la", "los", "que",
                  "con", "es", "son", "al", "ante", "sobre",
                  "señor", "señora", "senor", "senora", "secretario", "secretarios"}
NAME_PARTICLES = {"de", "del", "la", "las", "los", "y", "da", "di", "van", "von", "san"}
# Offices named inside the presidency sentence, each followed by its holder.
OFFICE_RE = re.compile(
    r"(?P<office>vicepresident[ea]\s+(?:de\s+la\s+Naci[óo]n|1[ªº°]?|2[ªº°]?|3[ªº°]?)"
    r"|presidenta?\s+provisional|presidenta?\s+de\s+la\s+Honorable\s+C[áa]mara\s+de\s+Diputados"
    r"|presidenta?\s+de\s+la\s+Naci[óo]n)"
    r"\s*(?:del?\s+(?:H\.?\s*)?Senado(?:\s+de\s+la\s+Naci[óo]n)?)?\s*,?\s*"
    r"(?P<name>[^,;]{3,90}?)"
    r"(?=\s*(?:,|;|\sy\s(?:del?|de\s+la)\b|$))",
    re.I | re.S,
)
NAME_OK = re.compile(r"^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ'’\-\. ]{4,60}$")


def clean_name(raw):
    """Strip honorifics and line noise; return "" when nothing usable is left."""
    s = unicodedata.normalize("NFC", raw or "")
    s = re.sub(r"\s+", " ", s.replace("\n", " ")).strip(" ,;.")
    s = GLUED_TITLE_RE.sub(r"\1 ", s)
    prev = None
    while prev != s:                       # "señor D. Juan" -> "Juan"
        prev = s
        s = HONORIFIC.sub("", s).strip()
    s = re.sub(r"\s*\(m\.?\s*c\.?\)\s*", " ", s, flags=re.I).strip(" ,;.")
    if POST_RE.match(s):
        return ""                          # a description of the post, not a name
    s = cut_at_next_sentence(s)
    if s.isupper():
        s = " ".join(w.capitalize() if w.lower() not in NAME_PARTICLES else w.lower()
                     for w in s.split())   # the 2018+ mastheads shout the name
    s = s[:1].upper() + s[1:]
    return s if NAME_OK.match(s) else ""


def cut_at_next_sentence(s):
    """Keep the name, drop the prose the masthead runs into after it."""
    kept = []
    for tok in s.split():
        low = tok.lower().strip(".,;")
        if kept and (low in SENTENCE_START or (tok[:1].islower() and low not in NAME_PARTICLES)):
            break
        kept.append(tok)
    while kept and kept[-1].lower().strip(".,;") in NAME_PARTICLES | SENTENCE_START:
        kept.pop()
    return " ".join(kept)


def split_people(body):
    """Split a "A, B y C" enumeration into names."""
    body = re.sub(r"\s+", " ", (body or "").replace("\n", " "))
    parts = re.split(r",|\by\b(?!\s*Maillmann)", body)   # one surname contains "y"
    return [n for n in (clean_name(p) for p in parts) if n]


def cover_text(pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        return "\n".join((p.extract_text() or "") for p in pdf.pages[:2])


def extract_one(pdf_path):
    name = Path(pdf_path).stem
    try:
        text = cover_text(pdf_path)
    except Exception as exc:                        # unreadable file: recorded, not fatal
        return [{"file": name, "office": "ERROR", "person": str(exc)[:80]}]

    rows = []
    cover = COVER_RE.search(text)
    if cover:
        for m in OFFICE_RE.finditer(cover.group("pres")):
            person = clean_name(m.group("name"))
            if person:
                office = re.sub(r"\s+", " ", m.group("office")).lower()
                office = office.replace("ó", "o").replace("á", "a")
                rows.append({"file": name, "office": office, "person": person})
    for regex, office in ((SEC_RE, "secretario"), (PROSEC_RE, "prosecretario")):
        m = regex.search(text)
        if m:
            for person in split_people(m.group("body")[:MAX_LINE]):
                rows.append({"file": name, "office": office, "person": person})
    if not rows:
        rows.append({"file": name, "office": "NONE", "person": ""})
    return rows


def main():
    files = sorted(glob.glob(str(RAW_DIR / "*.pdf")))
    if not files:
        sys.exit(f"No PDFs under {RAW_DIR} — is the data/ symlink in place? (see DATA.md)")
    out = []
    with ProcessPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(extract_one, f) for f in files]
        for i, fut in enumerate(as_completed(futures), 1):
            out.extend(fut.result())
            if i % 100 == 0:
                print(f"  {i}/{len(files)} cover pages read")

    for r in out:
        stem = r["file"]
        m = re.match(r"(\d{4})-(\d{2})-(\d{2})", stem) or re.match(r"(\d{2})-(\d{2})-(\d{4})", stem)
        if m and len(m.group(1)) == 4:
            r["session_date"] = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
        elif m:
            r["session_date"] = f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
        else:
            r["session_date"] = ""
    out.sort(key=lambda r: (r["session_date"], r["office"], r["person"]))

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["session_date", "file", "office", "person"])
        w.writeheader()
        w.writerows({k: r[k] for k in w.fieldnames} for r in out)

    missing = sum(1 for r in out if r["office"] in ("NONE", "ERROR"))
    print(f"{len(out)} officer observations from {len(files)} sittings "
          f"({missing} with no masthead found)")
    print(f"Written: {OUT_PATH}")


if __name__ == "__main__":
    main()
