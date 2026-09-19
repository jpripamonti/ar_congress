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

import html
import re
import unicodedata

HEAD_CHARS = 4_000

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
    """
    match = re.search(rb'charset\s*=\s*"?([\w-]+)', raw[:2000], re.I)
    encoding = match.group(1).decode("ascii", "replace") if match else "latin-1"
    try:
        return raw.decode(encoding, "replace")
    except LookupError:
        return raw.decode("latin-1", "replace")


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
