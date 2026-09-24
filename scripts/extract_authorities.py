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
name only by surname ("Sr. Secretario (Estrada)"), and for which senator
held the gavel on a day when two senators of the same surname sat. This
script turns it into one row per (session, office, person), which
`resolve_speakers.py` folds into tenure windows.

Both formats the portal serves are read: the PDFs of 2000 on through their
first two pages, the HTML of 1998-2003 through the opening of the document.
The masthead reads the same in both.

From December 2023 the cover carries a list of office holders instead (see
roster_rows), which says who held each office but not who presided; the
`basis` column tells the two apart: `masthead` or `roster`.

Output: reference/senado/authorities_observed.csv
"""

import csv
import glob
import html
import re
import sys
import unicodedata
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import pdfplumber

sys.path.insert(0, str(Path(__file__).resolve().parent))
from provenance import decode_html  # noqa: E402

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
# An attendance entry shouts the surname and follows it with a comma:
# "LOSADA, Mario Aníbal". In a two-column roll the right column's first entry
# is printed BEFORE the "PRESENTES" heading, so the heading alone does not
# stop the masthead: without this the roll's first surname is glued to the
# last prosecretary ("Alfredo A. Luques LOSADA") and its given names are
# recorded as an officer of their own, under a surname that belongs to a
# sitting senator. Mastheads never take this shape — they write "señor D.
# Juan Pedro Tunessi", surname last and never shouted before a comma, and the
# given name after it is Capitalized, not shouted. That last condition is what
# keeps a shouted masthead intact: from 2018 the Asambleas print the whole
# cover in capitals, so "SEÑORA VICEPRESIDENTA DE LA NACIÓN, DOCTORA
# CRISTINA ..." has the roll's shape, and only the case of the word after the
# comma tells the two apart.
# (?-i: ...) because the patterns above are compiled case-insensitively and
# the whole signal here is the case.
ROLL_ENTRY = (r"(?-i:[A-ZÁÉÍÓÚÑÜ][A-ZÁÉÍÓÚÑÜ'’]+(?:\s+[A-ZÁÉÍÓÚÑÜ'’]+)*"
              r"\s*,\s*[A-ZÁÉÍÓÚÑÜ][a-záéíóúñü])")
# The masthead ends at whichever comes first: the next officer line or the
# roll. The office words are PREFIXES and take no \b — "prosecretari" is
# followed by a letter in "Prosecretarios:", so a word boundary there can
# never match, and every line used to run on into the next one: the
# secretaries' line swallowed the prosecretaries' and lost its own last name
# to the join ("Jorge Horacio Amarfil Prosecretarios: señor Juan J. Canals"
# reads as no one). The roll words do take \b, being whole words.
END = rf"(?=\n?\s*(?:%s|(?:{ROLL})\b|{ROLL_ENTRY})|$)"
# A masthead line names at most a handful of people; anything longer means the
# boundary was missed and the attendance roll is bleeding in.
MAX_LINE = 260
# How much of an HTML transcript to search for the masthead (see html_cover_text).
HTML_COVER_CHARS = 8_000
# The masthead runs "Presidencia ..." until the secretaries' line or the roll.
COVER_RE = re.compile(
    rf"presidencia\s+(?:de\s+la|del)\s+(?P<pres>.*?)"
    + END % "secretari|prosecretari", re.I | re.S)
SEC_RE = re.compile(rf"\bsecretari[oa]s?\s*:\s*(?P<body>.*?)"
                    + END % "prosecretari", re.I | re.S)
# (?!) never matches: the prosecretaries are the last officer line, so only
# the roll ends it.
PROSEC_RE = re.compile(rf"\bprosecretari[oa]s?\s*:\s*(?P<body>.*?)"
                       + END % "(?!)", re.I | re.S)
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
    # president[ea], not presidenta? — the latter is "president" plus an
    # optional "a", which matches "presidenta" and never "presidente", so
    # every male holder of these three offices went unrecorded.
    r"(?P<office>vicepresident[ea]\s+(?:de\s+la\s+Naci[óo]n|1[ªº°]?|2[ªº°]?|3[ªº°]?)"
    # the chamber's own vice-presidency, which carries no ordinal: it is only
    # ever written out as "vicepresidente del H. Senado", so the office that
    # follows is what tells it from a bare word.
    r"|vicepresident[ea](?=\s+del?\s+(?:H\.?\s*)?Senado)"
    r"|president[ea]\s+provisional"
    r"|president[ea]\s+de\s+la\s+Honorable\s+C[áa]mara\s+de\s+Diputados"
    r"|president[ea]\s+de\s+la\s+Naci[óo]n)"
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


def cover_text(path):
    """The opening text of a held transcript, in whichever format it arrived."""
    if str(path).lower().endswith(".html"):
        return html_cover_text(Path(path).read_bytes())
    with pdfplumber.open(path) as pdf:
        return "\n".join((p.extract_text() or "") for p in pdf.pages[:2])


def html_cover_text(raw):
    """Readable opening text of an HTML transcript.

    Case and accents are kept, unlike provenance.py's window: clean_name()
    reads capitalization to tell a shouted masthead from an ordinary one.

    The window is a guard, not a boundary — the masthead regexes end at the
    attendance roll on their own. It exists for the one file with no masthead
    at all (the joint sitting of both chambers, 12-10-2000), where an
    unbounded search could reach "la presidencia de la Nación" in a speech
    and record a phrase as an officer. 8,000 characters is twice the furthest
    masthead in the holdings (4,099, the special sitting of 01-12-1999).
    """
    text = decode_html(raw)
    text = re.sub(r"(?is)<(script|style).*?</\1>", " ", text)
    text = re.sub(r"(?i)<(?:p|br|hr|li|tr|div|center|h1|table|multicol)[^>]*>", "\n", text)
    text = unicodedata.normalize("NFC", html.unescape(re.sub(r"<[^>]+>", " ", text)))
    return re.sub(r"[ \t]+", " ", text)[:HTML_COVER_CHARS]


# From December 2023 the cover no longer says who presided. It prints a
# standing list headed "A U T O R I D A D E S": each office on a line of its
# own and its holder on the next, vacant posts included —
#
#     Presidencia del Senado          Victoria Villarruel
#     Presidencia Provisional         Bartolomé Esteban Abdala
#     Vicepresidencia primera         Carolina Losada
#     Secretaría Administrativa       Vacante
#
# That is a different statement from the masthead's. "Presidencia del señor
# vicepresidente…, y del señor presidente provisional…" says who presided THIS
# sitting; the list says who HOLDS each office, and names every vice-president
# whether or not they took the chair that day. So its rows are marked
# basis=roster, and resolve_speakers takes them for tenure and never for who
# presided — reading them as the latter would hand the chair to a
# vice-president who was not in it.
ROSTER_HEAD_RE = re.compile(r"A\s*U\s*T\s*O\s*R\s*I\s*D\s*A\s*D\s*E\s*S")
ROSTER_END_RE = re.compile(r"Direcci[óo]n\s+General\s+de\s+Taqu[íi]grafos", re.I)
# The office lines the list uses, and the office each is recorded under. The
# Senate's presidency is the Nation's vice-presidency (Constitution, art. 57),
# and it is recorded under that name so the tenure it feeds is the same one
# the older mastheads feed.
ROSTER_OFFICES = [
    (re.compile(r"^presidencia del senado$", re.I), "presidencia del senado (vicepresidencia de la nacion)"),
    (re.compile(r"^presidencia provisional$", re.I), "presidencia provisional"),
    (re.compile(r"^vicepresidencia(?:\s+(primera|segunda|tercera))?$", re.I), "vicepresidencia"),
    (re.compile(r"^prosecretar[íi]a\s+(.+)$", re.I), "prosecretaria"),
    (re.compile(r"^secretar[íi]a\s+(.+)$", re.I), "secretaria"),
]


def roster_rows(text, name):
    """Rows for the office-holder list, or [] when the cover has none."""
    head = ROSTER_HEAD_RE.search(text)
    if not head:
        return []
    body = text[head.end():]
    end = ROSTER_END_RE.search(body)
    lines = [ln.strip() for ln in body[:end.start() if end else 1500].splitlines()
             if ln.strip()]
    rows = []
    i = 0
    while i < len(lines) - 1:
        for rx, office in ROSTER_OFFICES:
            m = rx.match(lines[i])
            if not m:
                continue
            if m.groups() and m.group(1):
                office = f"{office} {unicodedata.normalize('NFD', m.group(1).lower()).encode('ascii', 'ignore').decode()}"
            holder = lines[i + 1]
            person = "" if holder.lower() == "vacante" else clean_name(holder)
            if person:
                rows.append({"file": name, "office": office, "person": person,
                             "basis": "roster"})
            i += 2
            break
        else:
            i += 1
    return rows


def extract_one(path):
    name = Path(path).stem
    try:
        text = cover_text(path)
    except Exception as exc:                        # unreadable file: recorded, not fatal
        return [{"file": name, "office": "ERROR", "person": str(exc)[:80], "basis": ""}]

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
    for r in rows:
        r.setdefault("basis", "masthead")
    if not rows:
        # only where the masthead gave nothing: no older row is replaced
        rows = roster_rows(text, name)
    if not rows:
        rows.append({"file": name, "office": "NONE", "person": "", "basis": ""})
    return rows


def main():
    files = sorted(glob.glob(str(RAW_DIR / "*.pdf")) + glob.glob(str(RAW_DIR / "*.html")))
    if not files:
        sys.exit(f"No transcripts under {RAW_DIR} — fetch them first with scripts/download.py")
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
        w = csv.DictWriter(fh, fieldnames=["session_date", "file", "office", "person", "basis"])
        w.writeheader()
        w.writerows({k: r[k] for k in w.fieldnames} for r in out)

    missing = sum(1 for r in out if r["office"] in ("NONE", "ERROR"))
    print(f"{len(out)} officer observations from {len(files)} sittings "
          f"({missing} with no masthead found)")
    print(f"Written: {OUT_PATH}")


if __name__ == "__main__":
    main()
