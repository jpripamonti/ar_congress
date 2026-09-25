"""What a held transcript is: the format the portal served, and whether the
record is the provisional (uncorrected) version.

Both facts are read from the file itself rather than assumed from the year,
and both formats go through the same window — the first 4,000 characters of
normalized text, which covers the masthead where the chamber declares them.
Reading them the same way is the point: a difference between the PDF and HTML
holdings should be a difference in the records, not in how we looked.

Provisional status has three values, not two, because the chamber stopped
saying it. A masthead reading "VERSIÓN TAQUIGRÁFICA (PROVISIONAL)" is a draft
and one reading "VERSIÓN TAQUIGRÁFICA" alone is not, but from 2018 the words
leave the masthead altogether: they are on all 46 sittings of 2016-2017, on 1
of the 21 in 2018, and on none from 2019 to 2026. For those the honest answer
is None — the document does not say — and calling them final would invent a
fact about 134 sittings. Read the status off the raw file: the parser drops the
masthead as page apparatus, so parsed text puts every PDF at "not provisional"
when 261 of 605 are.

Do not loosen PROVISIONAL_RE to a bare "provisional". The Senate's presiding
officer is the "Presidente Provisional del H. Senado", an office named in the
masthead of most sittings before 2004, and a bare match counts those as draft
records: it puts the figure at 87% of the HTML holdings where the truth is 22%.
"""

import csv
import html
import re
import sys
import unicodedata
from functools import lru_cache
from pathlib import Path

HEAD_CHARS = 4_000

MANIFEST = Path(__file__).resolve().parents[1] / "raw_data_manifest.csv"


@lru_cache(maxsize=1)
def manifest_rows():
    """Every source file the corpus was built from, as the manifest lists it."""
    with open(MANIFEST, encoding="utf-8", newline="") as fh:
        return tuple(csv.DictReader(fh))


def source_url(filename):
    """The URL the chamber served a source file from, by its file name."""
    key = unicodedata.normalize("NFC", filename)
    for row in manifest_rows():
        if unicodedata.normalize("NFC", row["filename"]) == key:
            return row["source_url"]
    return ""


def require_sources(raw_dir, formats=("pdf", "html"), until=None):
    """Stop, naming what is missing, unless every listed source is held.

    A table built from all the sources is only right when all of them are
    there: run on three files, the authorities extractor wrote a 17-row
    table over the 3,000-odd rows the corpus needs, and speaker resolution
    went on to leave 3.5% of speech unresolved without a word of warning.
    """
    held = {unicodedata.normalize("NFC", p.name) for p in Path(raw_dir).iterdir()} \
        if Path(raw_dir).is_dir() else set()
    missing = [r["filename"] for r in manifest_rows()
               if r["format"] in formats
               and (until is None or r["session_date_iso"] < until)
               and unicodedata.normalize("NFC", r["filename"]) not in held]
    if missing:
        sys.exit(f"{len(missing)} of the source files in raw_data_manifest.csv are "
                 f"not under {raw_dir} (first: {missing[0]}). This step reads all "
                 f"of them and would write an incomplete table; fetch them first "
                 f"with: uv run scripts/download.py --from-manifest")

# The chamber prints "VERSIÓN TAQUIGRÁFICA (PROVISIONAL)" on an uncorrected record.
PROVISIONAL_RE = re.compile(r"VERSION\s+TAQUIGRAFICA\s*\(?\s*PROVISIONAL")
# Without this phrase the masthead makes no claim either way (2018 on).
DECLARES_RE = re.compile(r"VERSION\s+TAQUIGRAFICA")


def normalize(text):
    """Upper-case, accent-free, single-spaced — so one pattern fits both formats."""
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", text).upper()


def sniff_format(raw_head):
    """Format from the bytes, not the file name: 'pdf' or 'html'."""
    return "pdf" if raw_head.startswith(b"%PDF") else "html"


# What a browser does with these, and what the exporter meant. See decode_html.
LATIN1_ALIASES = {"iso-8859-1", "iso8859-1", "latin-1", "latin1", "l1",
                  "iso-ir-100", "8859-1", "cp819"}

# Three WordPerfect exports store the inverted marks as the ASCII parenthesis
# that occupies the same slot in their switched font. Across all 214 HTML
# sources, the only such one-character font runs are 147 questions and 16
# exclamations; every one closes with ? or !, and none is a real parenthesis.
INVERTED_MARK_RE = re.compile(
    r'(<font\b(?=[^>]*\bface\s*=\s*["\'](?:WP TypographicSymbols|Courier New)'
    r'["\'])[^>]*>\s*)([()])(?=\s*</font\s*>)', re.I)


def repair_inverted_marks(text):
    """Read the inverted mark selected by a WordPerfect font switch."""
    return INVERTED_MARK_RE.sub(
        lambda match: match.group(1) + {")": "¿", "(": "¡"}[match.group(2)],
        text,
    )


def decode_html(raw):
    """Text from a held HTML transcript, in the encoding it declares.

    Do not assume iso-8859-1 because 212 of the 214 files are. Two — the
    sitting of 29 October 2003, which the portal serves twice — come from a
    later exporter and declare utf-8, and reading those as latin-1 turns
    "VERSIÓN TAQUIGRÁFICA" into "VERSIA\x93N TAQUIGRA\x81FICA". That is not a
    cosmetic difference: the masthead then matches nothing, so the sitting
    declares no provisional status and names no officers, and an audit
    comparing parsed text against the file reports a third of it as text the
    source does not contain.

    A declaration of iso-8859-1 is read as windows-1252, which is what every
    browser does with it and what the exporter meant: 40 of the 212 files
    declaring iso-8859-1 put bytes in the 0x80-0x9f range, which latin-1 has
    no printable character for. Read as latin-1 they become control codes;
    read as windows-1252 they are the curly quotes, dashes and ellipses the
    page shows — 252 quotation marks, 46 dashes and 12 ellipses in the file,
    of which 16, 32 and 12 survive tag-stripping into readable text. The dash
    matters beyond typography: it is the em dash that ends a speaker's label,
    so under latin-1 the label has no terminator the parser recognises and
    the sitting loses the speaker entirely.

    One byte resists: 0x80, which windows-1252 calls the euro sign and which
    these files draw as the degree sign ("Escuela N\x80 3", "artículo 5\x80").
    All 16 occurrences sit inside anchor names, which the parser drops before
    any text is written, so the euro is never printed; it is left as the
    encoding says rather than corrected to a degree sign nothing reads.
    """
    match = re.search(rb'charset\s*=\s*"?([\w-]+)', raw[:2000], re.I)
    encoding = match.group(1).decode("ascii", "replace") if match else "latin-1"
    if encoding.lower().replace("_", "-") in LATIN1_ALIASES:
        encoding = "cp1252"
    try:
        text = raw.decode(encoding, "replace")
    except LookupError:
        text = raw.decode("cp1252", "replace")
    return repair_inverted_marks(text)


def html_head_text(raw):
    """Readable text from an HTML transcript."""
    text = decode_html(raw)
    text = re.sub(r"(?is)<(script|style).*?</\1>", " ", text)
    text = re.sub(r"<[^>]+>", " ", html.unescape(text))
    return normalize(text)[:HEAD_CHARS]


def pdf_head_text(path):
    """Readable text from the opening pages of a PDF transcript."""
    import pdfplumber  # imported lazily: the HTML path must not need it

    chunks = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages[:2]:
            chunks.append(page.extract_text() or "")
            if sum(len(c) for c in chunks) >= HEAD_CHARS:
                break
    return normalize(" ".join(chunks))[:HEAD_CHARS]


def head_text(path, fmt):
    """The masthead window for a held file, in whichever format it arrived."""
    if fmt == "pdf":
        return pdf_head_text(path)
    with open(path, "rb") as fh:
        return html_head_text(fh.read())


def provisional_status(text):
    """True / False / None for a masthead: draft, final, or no claim made."""
    if PROVISIONAL_RE.search(text):
        return True
    return False if DECLARES_RE.search(text) else None


def is_provisional(path, fmt):
    """Provisional status of a held file: True, False, or None when unstated."""
    return provisional_status(head_text(path, fmt))
