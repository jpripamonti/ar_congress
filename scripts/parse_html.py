"""Parse the Senate's HTML transcripts into the session table.

The portal serves most sittings of 1998-2003 as the chamber's own HTML export
(212 of the 214 held come from Corel WordPerfect) rather than as a PDF. The
markup carries what the PDF only implies: a speaker's label is <b>, a
stenographer's note is <i>, a section heading is a centred <b> number and
title, and the attendance lists and the sumario sit in their own <multicol>
and <li> containers. None of the PDF pipeline's work — measuring a missing
space, telling body text from apparatus by font size, rejoining a name split
across a change of face — applies here, so this is a separate reader rather
than a branch inside parse.py. The taxonomy is shared: the same speaker
pattern and the same event subtypes classify both, so the two eras of the
corpus mean the same thing.

What the HTML cannot give is the page: there is no pagination, so `pages` is
empty and `size` is null for every row. `font_style` comes from the markup
instead of a font name, and `font` is null.

Structure is read from containers, not from offsets. The files disagree about
how many <hr> rules they carry (one to four) and three have no sumario at all,
so front matter is recognized by what encloses it — the masthead before the
first rule, the attendance list inside <multicol>, the sumario inside <li> or
in a paragraph that is nothing but a link — rather than by "the body starts
after the second rule", which is wrong in 124 of the 214 files.
"""

import re
import sys
from html.parser import HTMLParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from parse import (DOC_FOLLOWS_RE, SIGNOFF_RE, SPEAKER_RE, classify_event,  # noqa: E402
                   split_embedded_notes, strip_label_residue, write_blocks)
from provenance import decode_html  # noqa: E402
from session_kind import convened_as_for, quorum_failed_for, session_kind_for  # noqa: E402

PARSER_VERSION = "0.5.11-html"

# A paragraph break: WordPerfect writes <p> with no closing tag and uses <br>
# for the lines of a masthead or the two lines of a heading.
BREAK_TAGS = {"p", "br", "hr", "li", "tr", "div", "h1", "center", "table",
              "ul", "multicol", "blockquote", "dir"}
BOLD_TAGS = {"b", "strong"}
ITALIC_TAGS = {"i", "em", "cite"}
# Footnote markers; the PDF pipeline cuts these too.
DROP_TAGS = {"sup", "script", "style", "title"}
# Two sittings of 2003 come from a different exporter that carries emphasis in
# CSS rather than in tags: <span style="font-weight: bold">. Without this the
# speaker labels in those two files are invisible and nothing is attributed.
# The same exporter that carries emphasis in CSS carries centring there too —
# <p style="text-align: CENTER"> and <h1 style="text-align: CENTER"> where the
# older files write <center>. A section heading is recognised by being centred,
# so without this its number and title fall through to the running speaker and
# are read as words he said: 117 of them in the sitting of 6 March 2003, every
# item of the day's agenda credited to the chair as speech.
CSS_CENTER_RE = re.compile(r"text-align\s*:\s*center", re.I)
# A heading tag is a heading wherever it sits, centred or not.
HEADING_TAGS = {"h1", "h2", "h3", "h4"}
CSS_BOLD_RE = re.compile(r"font-weight\s*:\s*(bold|[6-9]00)", re.I)
CSS_ITALIC_RE = re.compile(r"font-style\s*:\s*italic", re.I)

# The label a paragraph opens with, e.g. "Sr. Presidente" — then the chamber
# prints the holder in parentheses: "Sr. Presidente (Cafiero). -- Se gira..."
QUALIFIER_RE = re.compile(r"^\s*\(([^)]{1,60})\)")
UNCLOSED_QUALIFIER_RE = re.compile(r"^\s*\(([^()]{2,40}?)(?=\s*[.,]\s*[-–—])")
# The same, with one or two characters stranded between the bold label and the
# holder, which otherwise hide the parenthetical and lose the chair the turn.
# Two ways round, and the office word settles which: the typist struck a key
# too many — "<B>Sr. Presidente</B>d (Maqueda). --" — and the letter is
# dropped; or the bold stopped one letter short — "<B>Sr. President</B>e
# (Maqueda). --" — and the letter is given back. Read only where the holder
# and a terminator follow, and only where one of the two readings spells an
# office the chamber actually prints, so a sentence that merely contains a
# bracket cannot be mistaken for one.
STRAY_QUALIFIER_RE = re.compile(r"^(?P<stray>[^\s()]{1,2})\s*\((?P<holder>[^)]{1,60})\)")
# What separates a label from the speech: ". --", ". –", ".-", or a bare dash.
# The stop before the dash is a full stop by convention, but the typist
# sometimes hits the comma beside it — "Sr. Presidente (Gioja), -- Corresponde
# elegir al vicepresidente 2" — and the label was refused for it. The dash is
# what does the work here, so which stop precedes it does not matter.
TERMINATOR_RE = re.compile(r"^\s*[.,:]?\s*[-–—]{1,2}\s*")
# What a label is made of, once the honorific is past: a short name or office
# carrying no stop of its own, and sometimes the holder in parentheses. The
# cap of five words is what keeps a sentence from being read as a name.
_LABEL_BODY = (r"[^\s.,;:()]+(?:\s+[^\s.,;:()]+){0,4}"
               r"(?:\s*\([^)]{1,40}\))?")
_HONORIFIC = (r"(?:(?i:Sr|Sra|Srta|Sres)(?:(?:[.\-]\s*)+|\s+)"
              r"|(?i:Varios señores|Varias señoras|Un señor|Una señora)\s+)")
# Everything before the terminator, when what is before it really is a label.
LABEL_HEAD_RE = re.compile(rf"^{_HONORIFIC}{_LABEL_BODY}\s*$")
# The same terminator, found wherever it falls inside the bold run. It need
# not fall last: the opening character of the speech is often set in bold
# along with it ("<b>Sr. YOMA.- ¿</b>Me permite una interrupción?"), as is
# the ellipsis that resumes an interrupted turn ("<b>Sr. CAFIERO.- ...</b>").
# The dash must be preceded by a stop, a space, or the holder's closing
# parenthesis, so that a hyphenated surname is not read as a terminator and
# "Sr. LÓPEZ-ARIAS.- " does not become a senator called LÓPEZ.
LABEL_TERM_RE = re.compile(r"(?:(?<=\))\s*|[.,;:]+\s*|\s+)[-–—]{1,2}[.,;:]*\s*")
# The dash with nothing at all before it, glued to the last letter of the
# name: "Sr. AVELÍN- Pido la palabra." Read only at the end of the bold run
# and only behind a label-shaped prefix, which is what keeps a hyphenated
# surname from being cut in two.
LABEL_GLUED_RE = re.compile(r"[-–—]{1,2}[.,;:]*\s*$")
# The terminator written twice, once before the holder and once after:
# "Sr. PRESIDENTE.- (Losada).- Tiene la palabra el señor senador".
DOUBLED_HOLDER_RE = re.compile(r"^\(([^)]{1,40})\)\s*[.,;:]*\s*[-–—]{1,2}\s*")
# A label the typist ended with a full stop and no dash at all: "Sr. GENOUD.
# Si no le daban mandato al bloque, hoy se votaba la figura." Read only when
# the whole shape is there and a new sentence opens after it. The stop may be
# a full stop or a comma the typist doubled ("Sr. PRESIDENTE (Menem),.
# Corresponde"), never a colon: a colon after an office is how an inserted
# letter greets its addressee, not how the chamber gives someone the floor.
# Tighter than the dashed path: with no dash to mark the end of the label,
# only a name of one or two words keeps an inserted letter's salutation —
# "Sr. Presidente de la Honorable Cámara. Tengo el agrado de dirigirme" —
# from being read as the chamber giving the floor to somebody.
LABEL_BARE_RE = re.compile(
    rf"^(?P<label>{_HONORIFIC}"
    r"[^\s.,;:()]+(?:\s+[^\s.,;:()]+)?(?:\s*\([^)]{1,40}\))?)"
    r"\s*[.,]+\s*(?=[¿¡(\"«A-ZÁÉÍÓÚÑÜ])"
)
# The attendance roll: a shouted heading, then one senator to a line. The PDF
# side never sees this — it is cut with the front matter, before the sitting
# opens — but the HTML export prints it inside the document, where nothing
# else marks it off, so it is recognised by its own shape. The heading must
# be shouted and the entry must be "SURNAME, Given" with the surname shouted
# and the given name not, which is what keeps an ordinary sentence out.
ROLL_HEAD_RE = re.compile(
    r"^(?:PRESENTES|AUSENTES|AUSENTE|EN COMISI[ÓO]N|SUSPENDIDO|SUSPENDIDOS"
    r"|CON LICENCIA|LICENCIA)\b[^a-záéíóúñü]*$")
ROLL_ENTRY_RE = re.compile(
    r"^[A-ZÁÉÍÓÚÑÜ][A-ZÁÉÍÓÚÑÜ'’.\s]+,\s*[A-ZÁÉÍÓÚÑÜ][a-záéíóúñü]")

# A note's opening dash is presentation, and the two formats print it
# differently ("-- Se vota." against "-Se vota."); the subtype patterns are
# anchored, so it comes off before they run.
LEADING_DASH_RE = re.compile(r"^\s*[-–—−]+\s*")
CHAPTER_NUM_RE = re.compile(r"^\d{1,3}$")
# "[Volver al sumario]" and the sumario's own entries are navigation.
# How a note the typist left without its dash still opens: the chamber's
# stage language, impersonal or about the room — "Se lee el dictamen.",
# "Varios señores senadores rodean…", "Ocupa la Presidencia…".
NOTE_OPENING_RE = re.compile(
    r"\s*(?:Se\s|Varios\s|Varias\s|Ocupa\s|Ocupan\s|Puestos\s|Puestas\s|Son las\s"
    r"|A las\s|Siendo las\s|Ingresa|Se retira|Aplausos|Risas|Murmullos|Manifestaciones"
    r"|La votación|En particular|Así se hace|No se alcanza|Hablan)")
NAV_TEXT_RE = re.compile(r"\s*\[?\s*volver al sumario\s*\]?\s*", re.I)
NAV_RE = re.compile(r"volver al sumario|^\s*\[?\s*sumario\s*\]?\s*$", re.I)
# Printed apparatus with no speaker: the footnote pointing at the appendix
# ("1. Ver el Apéndice."), and the sign-off the stenographers' office puts at
# the foot of the record, with or without the director's name above it.
APPARATUS_RE = re.compile(
    r"^\s*(?:\d+\s*[.)]?\s*Ver el Ap[ée]ndice\s*\.?"
    r"|(?:[^\n]{0,60}\s)?(?:Sub)?[Dd]irector(?:a)?\s+(?:a/c\s+)?del\s+Cuerpo"
    r"\s+de\s+Taqu[íi]grafos)\s*$")


class TranscriptHTML(HTMLParser):
    """Collect paragraphs of styled text runs, with the container they sit in.

    Style is tracked by depth rather than by tag, because WordPerfect nests
    <b> inside <font> inside <b> and leaves tags unclosed across paragraphs.
    """

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.paragraphs = []
        self._runs = []
        self.bold = 0
        self.italic = 0
        # One entry per open tag, so a tag returns exactly what it added.
        self._stack = []
        self.center = 0
        self.para_center = False
        self.multicol = 0
        self.listitem = 0
        self.drop = 0
        self.rules_seen = 0
        self._link = 0
        self._link_chars = 0
        self._chars = 0
        self.small = 0
        self._small_chars = 0

    # -- paragraph handling -------------------------------------------------
    def _flush(self):
        runs = [r for r in self._runs if r["text"].strip()]
        self._runs = []
        centred, self.para_center = self.para_center, False
        if not runs:
            return
        self.paragraphs.append({
            "runs": runs,
            "center": self.center > 0 or centred,
            "multicol": self.multicol > 0,
            "listitem": self.listitem > 0,
            "after_rule": self.rules_seen > 0,
            # A paragraph that is only a link is navigation, not speech.
            "link_only": self._chars > 0 and self._link_chars >= self._chars,
            # set in a smaller type, as the chamber printed the text of an
            # insertion: <FONT SIZE=-1>
            "small": self._chars > 0 and self._small_chars >= 0.6 * self._chars,
        })
        self._link_chars = self._chars = self._small_chars = 0

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag in DROP_TAGS:
            self.drop += 1
            return
        if tag in BREAK_TAGS:
            self._flush()
        if tag == "hr":
            self.rules_seen += 1
            return

        style = " ".join(v or "" for k, v in attrs if k.lower() == "style")
        bold = int(tag in BOLD_TAGS or bool(CSS_BOLD_RE.search(style)))
        italic = int(tag in ITALIC_TAGS or bool(CSS_ITALIC_RE.search(style)))
        size = " ".join(v or "" for k, v in attrs if k.lower() == "size").strip()
        small = int(tag == "font" and size in ("-1", "-2", "1", "2"))
        self.bold += bold
        self.italic += italic
        self.small += small
        self._stack.append((tag, bold, italic, small))
        # Centring belongs to the paragraph this tag OPENS, and is cleared at
        # the next flush rather than at a closing tag: these files use <p> as a
        # separator and never close it, so a depth counter set here would stay
        # up for the rest of the document and read every later paragraph as a
        # heading. <center> keeps its own counter below, because it does nest.
        if tag in BREAK_TAGS and (tag in HEADING_TAGS or CSS_CENTER_RE.search(style)):
            self.para_center = True

        if tag == "center":
            self.center += 1
        elif tag == "multicol":
            self.multicol += 1
        elif tag == "li":
            self.listitem += 1
        elif tag == "a":
            self._link += 1

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in DROP_TAGS:
            self.drop = max(0, self.drop - 1)
            return
        if tag in BREAK_TAGS:
            self._flush()

        # Unwind to the most recent matching open tag. WordPerfect leaves tags
        # unclosed, so an unmatched close is ignored rather than trusted.
        for i in range(len(self._stack) - 1, -1, -1):
            if self._stack[i][0] == tag:
                _, bold, italic, small = self._stack.pop(i)
                self.bold = max(0, self.bold - bold)
                self.italic = max(0, self.italic - italic)
                self.small = max(0, self.small - small)
                break

        if tag == "center":
            self.center = max(0, self.center - 1)
        elif tag == "multicol":
            self.multicol = max(0, self.multicol - 1)
        elif tag == "li":
            self.listitem = max(0, self.listitem - 1)
        elif tag == "a":
            self._link = max(0, self._link - 1)

    def handle_data(self, data):
        if self.drop or not data.strip():
            if data.strip():
                return
            # Keep a separating space so words do not run together.
            if self._runs and not self._runs[-1]["text"].endswith(" "):
                self._runs[-1]["text"] += " "
            return
        style = ("bold" if self.bold and not self.italic else
                 "italic" if self.italic and not self.bold else
                 "bold-italic" if self.bold and self.italic else "normal")
        text = re.sub(r"\s+", " ", data)
        # One run per change of STYLE, not per tag. WordPerfect puts each
        # accented letter in a font of its own, which splits a name across
        # three <font> spans inside one <b> — "Sr. AVEL", "Í", "N.-" — and a
        # label read from the first run alone is then "Sr. AVEL", which
        # matches nothing. The turn stops being a turn: the senator's words
        # are swallowed into the chair's, or dropped. In the sitting of 13 May
        # 1998 that happened to every senator with an accent in their name.
        if self._runs and self._runs[-1]["style"] == style:
            self._runs[-1]["text"] += text
        else:
            self._runs.append({"text": text, "style": style})
        self._chars += len(text.strip())
        if self._link:
            self._link_chars += len(text.strip())
        if self.small:
            self._small_chars += len(text.strip())

    def close(self):
        super().close()
        self._flush()


def read_paragraphs(path):
    """Styled paragraphs from one HTML transcript."""
    text = decode_html(path.read_bytes())
    parser = TranscriptHTML()
    parser.feed(text)
    parser.close()
    return parser.paragraphs


def paragraph_text(para):
    """The readable text of a paragraph, single-spaced."""
    return re.sub(r"\s+", " ", "".join(r["text"] for r in para["runs"])).strip()


def italic_share(para):
    """Fraction of a paragraph's characters set in italics."""
    total = sum(len(r["text"].strip()) for r in para["runs"])
    if not total:
        return 0.0
    ital = sum(len(r["text"].strip()) for r in para["runs"]
               if r["style"] in ("italic", "bold-italic"))
    return ital / total


OFFICES = {"presidente", "presidenta", "vicepresidente", "vicepresidenta",
           "secretario", "secretaria", "prosecretario", "prosecretaria",
           "ministro", "ministra"}


def mend_stray(label, stray):
    """(label) with a stray character given back or dropped, else None."""
    last = label.rsplit(" ", 1)[-1].lower()
    if (last + stray.lower()) in OFFICES:
        return label + stray
    if last in OFFICES:
        return label
    return None


def split_label(para):
    """(label, speech) when a paragraph opens with a speaker's label, else None.

    The chamber prints the label in bold and the holder after it in the body
    face — "<b>Sr. Presidente </b>(Cafiero). -- Como último intento" — so the
    parenthetical is picked up from the run that follows, which is how the PDF
    side spells these too ("Sr. Presidente (Cafiero)").

    A label set wholly in the body face is still a label: 42 paragraphs of the
    HTML era print one with no bold at all. Those are read only on the strict
    path, where an explicit dash separates the label from the speech, because
    without the bold there is nothing else to tell a label from an inserted
    letter that opens "Sr. Presidente:".
    """
    runs = para["runs"]
    if not runs:
        return None
    raw = runs[0]["text"].strip()
    if not SPEAKER_RE.match(raw):
        return broken_label(para)
    bold = runs[0]["style"] in ("bold", "bold-italic")
    rest = "".join(r["text"] for r in runs[1:])

    # The bold run sometimes stops inside the holder's name — "<b>Sr.
    # PRESIDENTE (Cafiero</b>).- La Presidencia informa" — so the parenthesis
    # is closed from what follows before the label is read off it.
    if "(" in raw and ")" not in raw:
        close = rest.find(")")
        if close != -1:
            raw, rest = raw + rest[:close + 1], rest[close + 1:]
        else:
            # The typist never closed it — "Sr. PRESIDENTE (Cafiero.- Queda
            # aprobada" — so it is closed where the terminator falls, which
            # is where the name ends and where the reader closes it too.
            term = LABEL_TERM_RE.search(raw) or LABEL_GLUED_RE.search(raw)
            if term is None:
                return broken_label(para)
            raw = f"{raw[:term.start()]}){raw[term.start():]}"

    # Two shapes, both common: the terminator sits inside the bold run
    # ("<b>Sr. Vaquir. -- </b>Pido la palabra.") or after it, past the
    # holder's name ("<b>Sr. Presidente </b>(Preto)<b>. -- </b>Para una...").
    # Cutting inside the run is safe when the terminator ends it, as it did
    # before this was read at all, and otherwise only when what precedes it
    # is shaped like a label — without that, the first parenthetical dash of
    # an ordinary sentence would be read as the end of somebody's name.
    inside = LABEL_TERM_RE.search(raw)
    if inside and (inside.end() == len(raw)
                   or LABEL_HEAD_RE.match(raw[:inside.start()])):
        return tidy(raw[:inside.start()], raw[inside.end():] + rest)
    glued = LABEL_GLUED_RE.search(raw)
    if glued and LABEL_HEAD_RE.match(raw[:glued.start()]):
        return tidy(raw[:glued.start()], rest)

    # Only when the bold run stopped short of the holder's name. A label that
    # already closed with its terminator is complete, and the parenthesis that
    # follows it belongs to the speech: "Sr. SECRETARIO (Piuzzi).- (Lee:)"
    # names the secretary, it does not name a secretary called "Lee".
    # The trailing stop comes off before the holder is appended, so that
    # "<b>Sr. Presidente. </b>(Losada)" is the same speaker as
    # "Sr. Presidente (Losada)" and not a third one.
    label = raw.strip().rstrip(".")
    if "(" not in label:
        qualifier = QUALIFIER_RE.match(rest)
        if qualifier is None and bold:
            stray = STRAY_QUALIFIER_RE.match(rest)
            if stray and TERMINATOR_RE.match(rest[stray.end():]):
                mended = mend_stray(label, stray.group("stray"))
                if mended is not None:
                    label = f"{mended} ({stray.group('holder').strip()})"
                    rest = rest[stray.end():]
        if qualifier is None:
            # the holder's parenthesis never closed: "<b>Sr. Presidente </b>
            # (Maqueda<b>. -- </b>En consideración" (23 May 2002, twice)
            qualifier = UNCLOSED_QUALIFIER_RE.match(rest)
        if qualifier:
            label = f"{label} ({qualifier.group(1).strip()})"
            rest = rest[qualifier.end():]
    terminator = TERMINATOR_RE.match(rest)
    if terminator:
        return tidy(label, rest[terminator.end():])

    # No dash anywhere: the typist ended the label on a full stop. Read off
    # the whole paragraph, and only where the label was printed in bold.
    if bold:
        bare = LABEL_BARE_RE.match(f"{raw}{rest}")
        if bare:
            return tidy(bare.group("label"), f"{raw}{rest}"[bare.end():])
    return broken_label(para)


# A label whose bold the typist broke or started late — "<b>Sr. Vaqui</b>r.
# --", "<b>Sr</b>. <b>PRESIDENTE.-</b>", "Sr. <b>MAYA.-</b>" — or put a dash
# or dots in front of — "-<b>Sr. Presidente</b>", "..<b>Sr. PRESIDENTE.-</b>".
# The runs do not line up with the label, so it is read off the paragraph's
# plain text instead, and only with a dash to end it and some bold inside it,
# which is what an inserted letter's "Sr. Presidente:" never has.
_HONORIFIC_LOOSE = (r"(?:(?i:Sr|Sra|Srta|Sres)(?:(?:\s*[.\-]\s*)+|\s+)"
                    # the typist's slips on the honorific: "S r. Presidente",
                    # "S. Presidente (Genoud)" — only before an office
                    r"|(?:S\s+r|S)\.\s*(?=(?i:President|Secretari|Prosecretari))"
                    r"|(?i:Varios señores|Varias señoras|Un señor|Una señora)\s+)")
BROKEN_LABEL_RE = re.compile(
    rf"(?P<label>{_HONORIFIC_LOOSE}{_LABEL_BODY})"
    r"(?:(?:(?<=\))\s*|[.,;:]+\s*|\s+)[-–—]{1,2}[.,;:]*\s*"
    # no terminator at all, which only the holder's name in parentheses
    # makes safe: "Pido la palabra. Sr. Presidente (Losada) Tiene la palabra"
    r"|(?<=\))\s+(?=[¿¡A-ZÁÉÍÓÚÑ]))")
LEADING_JUNK_RE = re.compile(r"^[\s.\-–—…]*")


def bold_mask(para):
    """The paragraph's raw text, and for each character whether it is bold."""
    text, mask = "", []
    for r in para["runs"]:
        text += r["text"]
        mask += [r["style"] in ("bold", "bold-italic")] * len(r["text"])
    return text, mask


# A label printed with no honorific at all, in bold: the chair's office and
# holder, "PRESIDENTE (Cafiero).-", "Presidente (Losada). --", or a surname
# shouted with its terminator, "DEL PIERO.-". Read only when the whole label is
# bold and a dash ends it (or, for the chair, the holder closes it), which is
# how no section title or emphasised word is printed.
BARE_LABEL_RE = re.compile(
    r"(?P<label>(?i:president[ae]|secretari[oa]|prosecretari[oa])\s*\([^)]{2,40}\)"
    r"|[A-ZÁÉÍÓÚÑ]{2,}(?:\s+[A-ZÁÉÍÓÚÑ]{2,}){0,2})"
    r"\s*[.,]\s*[-–—]{1,2}[.,;:]*\s*")


# The chair's label with the holder's opening parenthesis dropped: "<b>Sr.
# Presidente </b>López Arias)<b>. -- </b>" (11 June 2003). Put it back, so the
# label reads as the chair's and not as a senator called Presidente.
MISSING_PAREN_RE = re.compile(
    r"(?i:Sr|Sra)\.\s*(?i:president[ae])\s+(?=[A-ZÁÉÍÓÚÑ][^()]{1,40}\)\s*[.,]?\s*[-–—]{1,2})")


def broken_label(para):
    """(label, speech) read off the plain text, where the runs hide the label."""
    text, mask = bold_mask(para)
    start = LEADING_JUNK_RE.match(text).end()
    slip = MISSING_PAREN_RE.match(text, start)
    if slip and mask[slip.start()]:
        text = text[:slip.end()] + "(" + text[slip.end():]
        mask = mask[:slip.end()] + [False] + mask[slip.end():]
    match = BROKEN_LABEL_RE.match(text, start)
    if match is None:
        bare = BARE_LABEL_RE.match(text, start)
        # the whole label bold, or for an office only the office word — the
        # holder is set roman, as in "<b>Presidente </b>(Losada)<b>. -- </b>"
        head_end = text.find("(", bare.start("label"), bare.end("label")) if bare else -1
        bold_part = (bare.start("label"), head_end if head_end != -1 else bare.end("label")) if bare else None
        if (bare and all(mask[bold_part[0]:bold_part[1]])
                and re.search(r"\w", text[bare.end():])):
            return tidy(bare.group("label"), text[bare.end():])
        return None
    if not any(mask[match.start():match.end()]):
        return None
    label = re.sub(r"\s+", " ", match.group("label"))
    label = re.sub(r"^((?i:Sr|Sra|Srta|Sres))\s+\.", r"\1.", label)
    label = re.sub(r"^S\s+r\.", "Sr.", label)
    label, speech = tidy(label, text[match.end():])
    if not re.search(r"\w", speech):
        return None
    if slip:
        label = label.replace("(", "", 1)   # as printed; the resolver reads it
    return label, speech


# A label printed in the middle of a paragraph, with no <P> before it: the
# typist ran the next speaker on after the last one's full stop —
# "…de la Unión Cívica Radical.<b>Sr. GENOUD.- </b>Señor presidente: rindo
# este homenaje" (11 August 1999), which gave Genoud's 1,415 words to the
# chair. Split there, as the page reads, when the label follows the end of a
# sentence, ends in a dash, and carries some bold. Or when the typist left
# out the full stop too — "…eminentemente católica<b>Sr. PRESIDENTE (Menem).-
# </b>Es correcto" (13 May 1998) — where the whole label is bold and the word
# before it is not, which no emphasised word inside a sentence looks like.
EMBEDDED_LABEL_RE = re.compile(
    r"(?<=[.?!:…)»\"a-záéíóúñ])\s*[-–—]?\s*(?=" + _HONORIFIC_LOOSE + ")")


def slice_runs(runs, cut):
    """The runs before and after character offset `cut`."""
    head, tail, pos = [], [], 0
    for r in runs:
        end = pos + len(r["text"])
        if end <= cut:
            head.append(r)
        elif pos >= cut:
            tail.append(r)
        else:
            head.append(dict(r, text=r["text"][:cut - pos]))
            tail.append(dict(r, text=r["text"][cut - pos:]))
        pos = end
    return head, tail


def split_embedded_labels(para):
    """One paragraph as several, at each label run on inside it."""
    text, mask = bold_mask(para)
    for m in EMBEDDED_LABEL_RE.finditer(text):
        at = m.start()
        if not re.search(r"\w", text[:at]):
            continue
        # the stop behind it is the honorific's own: "Sr. Varios señores
        # senadores" is one label, printed that way, not two
        if re.search(r"\b(?i:Sr|Sra|Srta|Sres)\s*[.\-]?\s*$", text[:at]):
            continue
        label = BROKEN_LABEL_RE.match(text, m.end())
        if label is None or not any(mask[label.start():label.end()]):
            continue
        if text[at - 1].isalpha() and (
                mask[at - 1] or not all(mask[m.end():label.end("label")])):
            continue
        if not re.search(r"\w", text[label.end():]):
            continue
        head, tail = slice_runs(para["runs"], at)
        return [dict(para, runs=head)] + split_embedded_labels(
            dict(para, runs=tail, center=False))
    return [para]


def tidy(label, speech):
    """A label and its speech, with the printing cleaned off both."""
    label = label.strip().rstrip(".")
    speech = re.sub(r"\s+", " ", speech).strip()
    if "(" not in label:
        again = DOUBLED_HOLDER_RE.match(speech)
        if again:
            label = f"{label} ({again.group(1).strip()})"
            speech = speech[again.end():]
    return label, speech


# A document's title and the chair's next label, welded into one bold run
# with nothing between them: "<B>Orden del Día N° 1230Sr. PRESIDENTE.-</B>".
# The chamber botched two paragraphs this way in the 214 files, one centred
# and one not, and both cost a turn: the title makes the paragraph look like
# a heading, and the label inside it is never reached. Split only where the
# label is welded to a document pointer with no space at all — a space, or
# anything else before it, and this does not fire.
WELD_RE = re.compile(
    r"^(?P<title>(?:Orden del D[íi]a|Dictamen|Expediente)[^\n]{0,40}?\d)"
    r"(?=(?:Sr|Sra|Srta|Sres)\.?\s*[^\W\d_])", re.I)


def unweld(para):
    """One paragraph as two, when a label is welded to a document title."""
    runs = para["runs"]
    if not runs or runs[0]["style"] not in ("bold", "bold-italic"):
        return None
    match = WELD_RE.match(runs[0]["text"].strip())
    if not match:
        return None
    title = match.group("title")
    rest = runs[0]["text"].strip()[match.end():]
    head = dict(para, runs=[dict(runs[0], text=title)], center=True)
    tail = dict(para, runs=[dict(runs[0], text=rest)] + runs[1:], center=False)
    return head, tail


# A note that says a text is read out: what follows is the text, read by the
# Secretariat, not the words of whoever spoke before the note.
VOCATIVE_RE = re.compile(r"\s*Se[ñn]or[a]?\s+president[ae]\b", re.IGNORECASE)
READ_OUT_RE = re.compile(r"^[\W_]*(?:Se\s+lee|Lee)\b", re.IGNORECASE)


def speech_then_note(para):
    """A sentence in roman and the note that follows it, as two parts.

    "En primer lugar anuncio que el Estado argentino suspenderá el pago de
    la deuda externa. (Aplausos prolongados…)" (22 December 2001) is one
    paragraph: the words are roman and only the note is italic. Read whole,
    it was an applause note and the announcement nobody's. Only where the
    roman part is a finished sentence and the italic part opens with the
    note's bracket; a book title in italics after "Libro " is neither.
    """
    runs = [r for r in para["runs"] if r["text"].strip()]
    lead = ""
    for i, run in enumerate(runs):
        if run["style"] in ("italic", "bold-italic"):
            break
        lead += run["text"]
    else:
        return None
    rest = "".join(r["text"] for r in runs[i:])
    if lead.rstrip().endswith("("):
        lead, rest = lead.rstrip()[:-1], "(" + rest
    lead = re.sub(r"\s+", " ", lead).strip()
    rest = re.sub(r"\s+", " ", rest).strip()
    if (not rest.startswith("(") or re.match(r"[-–—(]", lead)
            or len(re.findall(r"\w+", lead)) < 2
            or not re.search(r"(?:[.!?…]|\.\.\.)$", lead)):
        return None
    return lead, rest


def note_then_document(para):
    """A note that a text follows, and the text, printed as one paragraph.

    "-- *El texto del plan de labor parlamentaria es el siguiente:*Plan de
    labor parlamentaria para la sesión…" (15 August 2001): the italic note
    and the roman work plan share a paragraph, so the plan was read as the
    chair's words.
    """
    runs = [r for r in para["runs"] if r["text"].strip()]
    note = ""
    for i, run in enumerate(runs):
        if run["style"] in ("italic", "bold-italic"):
            note += run["text"]
            if DOC_FOLLOWS_RE.search(note):
                rest = re.sub(r"\s+", " ", "".join(r["text"] for r in runs[i + 1:])).strip()
                if re.search(r"\w", rest):
                    return re.sub(r"\s+", " ", note).strip(), rest
                return None
        elif re.search(r"\w", run["text"]):
            return None
        else:
            note += run["text"]
    return None


def classify(paragraphs):
    """Turn paragraphs into pipeline blocks, and collect the chapter titles."""
    blocks = []
    chapters = {}
    chapter = None
    pending_number = None
    turn = 0
    speaker = None
    in_roll = False
    stats = {"paragraphs": len(paragraphs), "front_matter": 0, "nav_cut": 0,
             "roll_cut": 0}

    split = []
    for para in paragraphs:
        pair = unweld(para)
        split.extend(pair if pair else [para])
    paragraphs = []
    for para in split:
        paragraphs.extend(split_embedded_labels(para))
    stats["embedded_labels_split"] = len(paragraphs) - len(split)

    after_note = False
    inserted_by = None    # who asked for the text being inserted
    inserted_small = False
    for n, para in enumerate(paragraphs):
        text = paragraph_text(para)
        if not text:
            continue
        follows_note, after_note = after_note, False

        # -- furniture, by the container it sits in -------------------------
        if para["multicol"] or para["listitem"] or not para["after_rule"]:
            stats["front_matter"] += 1
            blocks.append({"type": "furniture", "text": text})
            speaker = None
            continue
        # a back-link printed in a turn's own paragraph does not make the turn
        # page matter: "Sr. PRESIDENTE (Menem).- Queda aprobada… [Volver al
        # sumario]" (1 September 1999) is the chair speaking, link and all
        if para["link_only"] or APPARATUS_RE.match(text) or (
                NAV_RE.search(text) and split_label(para) is None):
            stats["nav_cut"] += 1
            blocks.append({"type": "furniture", "text": text})
            continue

        # -- the attendance roll ---------------------------------------------
        # It only ever starts at its own heading, so a surname shouted in the
        # body of a speech cannot open one.
        if ROLL_HEAD_RE.match(text):
            in_roll = True
        elif in_roll and not ROLL_ENTRY_RE.match(text):
            in_roll = False
        if in_roll:
            stats["roll_cut"] += 1
            blocks.append({"type": "furniture", "text": text})
            speaker = None
            continue

        # -- section headings ------------------------------------------------
        # A label the typist centred is still a speaker taking the floor:
        # "Sr. Presidente (Gioja). -- En consideración en general." (7 May
        # 2003) was read as a section title, and the chair's words after it
        # as nobody's. Only with words after the label, which a title lacks.
        label = split_label(para) if para["center"] else None
        if label is not None and re.search(r"\w", label[1]):
            speaker, speech = label
            inserted_by = None
            turn += 1
            blocks.append({
                "type": "speech", "speaker": speaker, "turn_id": turn,
                "text": speech, "capítulo": chapter, "font_style": "normal",
            })
            continue
        if para["center"]:
            inserted_by = None
            if CHAPTER_NUM_RE.match(text):
                pending_number = text
                blocks.append({"type": "heading", "text": text})
                speaker = None
                continue
            if pending_number is not None:
                chapter = pending_number
                chapters[chapter] = f"{chapter} {text}"
                pending_number = None
                blocks.append({"type": "heading", "text": text, "capítulo": chapter})
                speaker = None
                continue
            blocks.append({"type": "heading", "text": text})
            speaker = None
            continue

        # -- a speaker taking the floor ---------------------------------------
        label = split_label(para)
        if label is not None:
            speaker, speech = label
            speech = NAV_TEXT_RE.sub(" ", speech).strip()
            turn += 1
            blocks.append({
                "type": "speech", "speaker": speaker, "turn_id": turn,
                "text": speech, "capítulo": chapter, "font_style": "normal",
            })
            continue

        # -- the stenographers' director signing off ---------------------------
        # "Rubén A. Marino" over "Director del Cuerpo de Taquígrafos": his
        # name is page matter, not the last speaker going on after the time
        # note.
        later = next((paragraph_text(q) for q in paragraphs[n + 1:]
                      if re.search(r"\w", paragraph_text(q))), "")
        if len(text.split()) <= 5 and SIGNOFF_RE.match(later):
            blocks.append({"type": "furniture", "text": text})
            speaker = None
            continue

        parts = note_then_document(para)
        if parts is not None:
            note, document = parts
            blocks.append({
                "type": "event", "event_type": classify_event(LEADING_DASH_RE.sub("", note)),
                "text": note, "capítulo": chapter, "font_style": "italic",
            })
            blocks.append({"type": "other", "text": document, "capítulo": chapter})
            inserted_by, inserted_small = speaker, False
            speaker = None
            continue

        # -- a sentence and the note after it, printed as one paragraph --------
        parts = speech_then_note(para) if italic_share(para) >= 0.6 else None
        if parts is not None:
            said, note = parts
            if speaker is not None:
                blocks.append({
                    "type": "speech", "speaker": speaker, "turn_id": turn,
                    "text": said, "capítulo": chapter, "font_style": "normal",
                })
            else:
                blocks.append({"type": "other", "text": said, "capítulo": chapter})
            blocks.append({
                "type": "event", "event_type": classify_event(note),
                "text": note, "capítulo": chapter, "font_style": "italic",
            })
            stats["speech_then_note_split"] = stats.get("speech_then_note_split", 0) + 1
            after_note = True
            continue

        # -- a stenographer's note --------------------------------------------
        # Set in italics. The speaker goes on after it, as on the PDF side:
        # "-- Ocupa la Presidencia el señor presidente provisional…" falls in
        # the middle of Cafiero's speech (26 April 2000), and the 789 words
        # after it are still his. Two kinds of note do end the turn: one that
        # introduces a text printed into the record ("El texto de la
        # inserción solicitada es el siguiente:"), and one that says a text is
        # read out ("Se lee el expediente.").
        # A paragraph in italics is a note when it reads as one: it opens with
        # the note's dash or bracket, or says what notes say (a vote, applause,
        # the time). Otherwise it is words set in italics — a passage the
        # speaker quotes, a list of titles — and the speaker goes on: Gómez
        # Diez quoting the US Treasury secretary (5 March 2002), Avelín's song
        # titles (4 November 1998). Read as notes, they ended the turn and the
        # rest of the speech went to nobody.
        # Italics straight after a note carry the note on: the delegations
        # the note says came in, the senators it says voted (10 December
        # 1999, 11 September 2002).
        if italic_share(para) >= 0.6 and (
                follows_note
                or re.match(r"\s*(?:[-–—(\[_]|\.\.)", text)
                or NOTE_OPENING_RE.match(text) or text.rstrip().endswith(")")
                or classify_event(LEADING_DASH_RE.sub("", text)) != "unspecified"
                or speaker is None):
            blocks.append({
                "type": "event",
                "event_type": classify_event(LEADING_DASH_RE.sub("", text)),
                "text": text, "capítulo": chapter, "font_style": "italic",
            })
            if DOC_FOLLOWS_RE.search(text) or READ_OUT_RE.match(text):
                inserted_by, inserted_small = speaker, False
                speaker = None
            after_note = True
            continue

        # a note printed in roman straight after another note: "-- La
        # votación resulta afirmativa." then "-- El artículo 7° es de
        # forma." (14 March 2002)
        if follows_note and re.match(r"\s*-{1,2}\s*[A-ZÁÉÍÓÚÑ]", text):
            blocks.append({
                "type": "event",
                "event_type": classify_event(LEADING_DASH_RE.sub("", text)),
                "text": text, "capítulo": chapter, "font_style": "normal",
            })
            after_note = True
            continue

        # a lone full stop after a note is the note's own
        if follows_note and not re.search(r"\w", text):
            blocks.append({"type": "furniture", "text": text})
            continue

        # -- the speaker back after a text inserted in small type ---------------
        # Melgarejo's insertion (24 November 1999) is set in a smaller type,
        # and he goes on in the body type, unlabelled: "Señor presidente:
        # quisiera terminar ahora con mi discurso." Only where the inserted
        # text was small and this paragraph is not, and turns to the chair:
        # an insertion can change type size halfway through (Berhongaray's,
        # 2 June 1999).
        if speaker is None and inserted_by is not None:
            if para["small"]:
                inserted_small = True
            elif inserted_small and VOCATIVE_RE.match(text):
                speaker, inserted_by = inserted_by, None
                stats["resumed_after_insertion"] = stats.get("resumed_after_insertion", 0) + 1

        # -- the same speaker carrying on -------------------------------------
        if speaker is not None:
            blocks.append({
                "type": "speech", "speaker": speaker, "turn_id": turn,
                "text": text, "capítulo": chapter, "font_style": "normal",
            })
            continue

        blocks.append({"type": "other", "text": text, "capítulo": chapter})

    stats["chapters_detected"] = len(chapters)
    return blocks, chapters, stats


def consolidate(blocks):
    """Join a speaker's consecutive paragraphs into one block, as the PDF side does."""
    merged = []
    for block in blocks:
        last = merged[-1] if merged else None
        if (last is not None and block.get("type") == "speech"
                and last.get("type") == "speech"
                and last.get("turn_id") == block.get("turn_id")):
            last["text"] = f"{last['text']} {block['text']}".strip()
            continue
        merged.append(dict(block))
    return merged


def inserted_debates():
    """Earlier debates reprinted inside a later sitting's record.

    Three sittings reprint an earlier speech or exchange under its original
    speakers' labels, as an insertion a senator asked for: on 23 February
    2000 Villarroel's part in the debate of 6/7 May 1998, on 15 November 2000
    Menem's speech of 25 October, on 8 August 2001 the tribute of 13 June
    2001. The labels are real but the words were not said that day, so they
    are nobody's speech in this sitting, and the notes printed inside them
    are not that day's events. Nothing on the page closes the reprint, so
    each is listed in
    reference/senado/inserted_debates.csv by its first and last words, with
    the evidence.
    """
    import csv
    path = (Path(__file__).resolve().parents[1]
            / "reference" / "senado" / "inserted_debates.csv")
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def unattribute_inserted_debate(blocks, stem):
    """The speech and notes of a listed reprint, as unattributed text."""
    for row in inserted_debates():
        if not stem.startswith(row["session_id"] + "_"):
            continue
        first = next(i for i, b in enumerate(blocks)
                     if b.get("text", "").strip().startswith(row["first_words"]))
        last = next(i for i in range(first, len(blocks))
                    if blocks[i].get("text", "").strip().startswith(row["last_words"])
                    or row["last_words"] in blocks[i].get("text", ""))
        for block in blocks[first:last + 1]:
            if block.get("type") in ("speech", "event"):
                block.update(type="other", speaker=None, turn_id=None,
                             event_type=None)
                block.pop("font_style", None)
        # the reprint's turns are gone, and the turns after it close up, so
        # every turn number still leaves a row
        order = {}
        for block in blocks:
            if block.get("turn_id") is not None:
                order.setdefault(block["turn_id"], len(order) + 1)
        for block in blocks:
            if block.get("turn_id") is not None:
                block["turn_id"] = order[block["turn_id"]]
    return blocks


def process_html(path):
    """Parse one HTML transcript. Returns (blocks, chapters, stats)."""
    paragraphs = read_paragraphs(Path(path))
    blocks, chapters, stats = classify(paragraphs)
    blocks = consolidate(blocks)
    blocks = unattribute_inserted_debate(blocks, Path(path).stem)
    blocks, _ = split_embedded_notes(blocks)
    for block in blocks:
        if block.get("type") == "other":
            block.pop("font_style", None)   # as every other HTML row nobody spoke
    blocks, _ = strip_label_residue(blocks)
    # counted as written: blocks_to_frame drops a block with no visible text
    blocks = [b for b in blocks if (b.get("text") or "").strip()]
    counts = {}
    for block in blocks:
        counts[block.get("type", "other")] = counts.get(block.get("type", "other"), 0) + 1
    stats.update({
        "blocks_generated": len(blocks),
        "speech_blocks": counts.get("speech", 0),
        "heading_blocks": counts.get("heading", 0),
        "furniture_blocks": counts.get("furniture", 0),
        "other_blocks": counts.get("other", 0),
        "events_tagged": counts.get("event", 0),
    })
    return blocks, chapters, stats


# ---------------------------------------------------------------------------
# Writing the session table
# ---------------------------------------------------------------------------

def blocks_to_frame(blocks, chapters, meta):
    """Map blocks to the session-table schema the PDF side writes.

    `pages` and `size` are empty for every row: the HTML export has no
    pagination and no type size, and inventing either would let a reader
    believe a passage can be traced to a printed page when it cannot.
    """
    import pandas as pd

    # A block with no visible text is nothing a reader could cite: whitespace
    # left by a spacer line, or, in the HTML era, a label printed with nothing
    # after it before the document it introduces ("Sr. SECRETARIO (Oyarzún).-"
    # over an Orden del Día, 16 June 1999). The PDF side already drops a
    # wordless turn; six such rows, in both formats, were reaching the corpus.
    blocks = [b for b in blocks if (b.get("text") or "").strip()]
    rows = []
    for seq, block in enumerate(blocks):
        speaker = block.get("speaker")
        chapter = block.get("capítulo")
        rows.append({
            "session_id": meta["session_id"],
            "session_date": meta["session_date"],
            "session_type": meta["session_type"],
            "session_kind": session_kind_for(meta["session_type"]),
            "convened_as": convened_as_for(meta["session_type"], meta["session_id"]),
            "quorum_failed": quorum_failed_for(meta["session_type"]),
            "sesion": meta["sesion"],
            "reunion": meta["reunion"],
            "seq": seq,
            "type": block.get("type") or ("speech" if speaker else "other"),
            "event_type": block.get("event_type"),
            "turn_id": block.get("turn_id"),
            "chapter": chapter,
            "chapter_title": chapters.get(chapter) if chapter else None,
            "speaker_raw": speaker,
            "text": block["text"],
            "pages": [],
            "font": None,
            "font_style": block.get("font_style"),
            "size": None,
            "source_file": meta["source_file"],
            "source_format": meta["source_format"],
            "source_sha256": meta["source_sha256"],
            "parser_version": PARSER_VERSION,
        })
    return pd.DataFrame(rows)


def parse_one(path_str, meta, out_dir):
    """Worker: parse one HTML transcript, write its Parquet table, return stats."""
    import time
    from datetime import datetime, timezone

    path = Path(path_str)
    stats = {"session_id": meta["session_id"], "file_name": path.name}
    start = time.monotonic()
    try:
        blocks, chapters, run_stats = process_html(path)
        stats.update(run_stats)
        if blocks:
            frame = blocks_to_frame(blocks, chapters, meta)
            write_blocks(frame, out_dir / "blocks" / f"{meta['session_id']}.parquet")
            stats["rows_written"] = len(frame)
    except Exception as e:  # per-file isolation, as on the PDF side
        stats["error"] = f"{type(e).__name__}: {e}"
    stats["duration_s"] = round(time.monotonic() - start, 1)
    stats["parser_version"] = PARSER_VERSION
    stats["parsed_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return stats


def superseded():
    """Held files the portal serves under a session they are not.

    One of these exists: 29 October 2003, which the portal returns at the URL
    of reunión 27 and again at the URL of reunión 28, byte for byte. The
    document says in its own masthead which sitting it is, so the other slot
    is the portal's error, and parsing both would count that day's words
    twice. Listed in reference/senado/superseded_sources.csv with the reason,
    and still held on disk and in the manifest: what the portal serves is a
    fact about the portal, and dropping it from the record would hide it.
    """
    import csv
    path = (Path(__file__).resolve().parents[1]
            / "reference" / "senado" / "superseded_sources.csv")
    if not path.exists():
        return set()
    with path.open(encoding="utf-8") as fh:
        return {row["filename"] for row in csv.DictReader(fh)}


def main():
    import argparse

    from parse import OUT_DIR, RAW_DIR, load_manifest, session_meta_for, write_stats

    ap = argparse.ArgumentParser(description="Parse the Senate's HTML transcripts.")
    ap.add_argument("--only", help="parse a single file by name")
    ap.add_argument("--limit", type=int, help="parse at most this many files")
    ap.add_argument("--force", action="store_true", help="re-parse sessions already written")
    args = ap.parse_args()

    (OUT_DIR / "blocks").mkdir(parents=True, exist_ok=True)
    manifest = load_manifest()

    files = [f for f in sorted(RAW_DIR.glob("*.html")) if f.name not in superseded()]
    if args.only:
        files = [f for f in files if f.name == args.only]
        if not files:
            raise SystemExit(f"No HTML file named {args.only!r} in {RAW_DIR}")
    if args.limit:
        files = files[:args.limit]

    jobs, skipped = [], 0
    for path in files:
        meta = session_meta_for(path, manifest)
        if (OUT_DIR / "blocks" / f"{meta['session_id']}.parquet").exists() and not args.force:
            skipped += 1
            continue
        jobs.append((path, meta))

    print(f"{len(files)} HTML transcripts, {skipped} already parsed, {len(jobs)} to process "
          f"(parser {PARSER_VERSION})", flush=True)

    rows = []
    for i, (path, meta) in enumerate(jobs, 1):
        stats = parse_one(str(path), meta, OUT_DIR)
        rows.append(stats)
        flag = f"  ERROR: {stats['error']}" if stats.get("error") else ""
        print(f"[{i}/{len(jobs)}] {stats['session_id']} "
              f"({stats.get('rows_written', 0)} rows){flag}", flush=True)

    if rows:
        write_stats(rows, OUT_DIR / "parse_stats.csv")
    errors = [r for r in rows if r.get("error")]
    print(f"\nDone: {len(rows)} parsed, {len(errors)} errors.")
    for r in errors:
        print(f"  {r['file_name']}: {r['error']}")


if __name__ == "__main__":
    main()
