"""Resolve speaker labels in the parsed corpus to persons.

Implements the join strategy from the roster research (July 2026):

- Labels are routed by shape: Role (Surname) chairs/officers; "Surname,
  Given" comma-disambiguated senators; role-only labels (Presidente de la
  Nación, Jefe de Gabinete); collective labels; bare surnames.
- Chair parentheticals resolve against the authorities table FIRST (VP,
  officer secretaries — non-senators), then the date-filtered senator
  roster (any senator can preside). Where the roster leaves two senators of
  the same surname in window, the sitting's own cover page decides: it names
  who held the gavel that day, which is the only record that does.
- Compound surnames match on the FULL surname string, never tokens
  ("Rodríguez Machado" is not "Rodríguez"; "Ledesma Abdala" is not
  "Abdala").
- Candidates are filtered by session date against the mandate windows
  (INICIO/CESE PERIODO REAL, falling back to LEGAL; "Sin Datos" = open).
- Known chair-name typo variants (Ledezma Abdala, Villarreal, ...) come
  from the authorities table's variants column.

Two different political affiliations are written out, and they are not the
same thing. `elected_ticket` is the list a senator stood on, which is what
the roster records. `bloc` is the caucus they actually sat with, taken from
`bloque_observado.csv` — the Senate's own roll-call records from 2005, and
archived snapshots of its bloc-roster page before that. The two diverge in
most of the corpus: a senator elected on a provincial alliance nearly always
sits with one of the national caucuses, and only the caucus says which side
of the chamber they are on. The old single column was named
`party_or_alliance`, which invited exactly that confusion.

The caucus is observed on particular days, never continuously, so each row
also carries which observation was used, how far it is from the sitting, and
whether it can be trusted: the Senate re-labels old roll calls with caucus
names that did not exist yet, and `bloc_status` marks those rather than
silently passing them on.

Inputs:  data/processed/senado/blocks/*.parquet,
         reference/senado/senadores_historico.json,
         reference/senado/authorities_manual.csv,
         reference/senado/authorities_observed.csv,
         reference/senado/bloque_observado.csv
Output:  data/processed/senado/speakers.parquet — one row per
         (session_id, speaker_raw) with person_id, name, elected_ticket,
         province, bloc, bloc_status, bloc_basis, bloc_observed,
         bloc_gap_days, bloc_span_days, role, match_status — plus a
         printed summary.
"""

import csv
import difflib
import json
import re
import sys
import unicodedata
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
BLOCKS_DIR = REPO_ROOT / "data" / "processed" / "senado" / "blocks"
HISTORICO = REPO_ROOT / "reference" / "senado" / "senadores_historico.json"
AUTHORITIES = REPO_ROOT / "reference" / "senado" / "authorities_manual.csv"
OBSERVED = REPO_ROOT / "reference" / "senado" / "authorities_observed.csv"
# Each masthead states who held the office THAT DAY, so the observed span is
# a floor on a tenure, never a ceiling. The margin covers recesses and the
# sittings whose masthead could not be read; it is safe because no two
# officers in the corpus share a surname (checked when the table is built).
OBSERVED_PAD_DAYS = 200
BLOC_OBS = REPO_ROOT / "reference" / "senado" / "bloque_observado.csv"
BLOC_LIVES = REPO_ROOT / "reference" / "senado" / "blocs_manual.csv"
# How far a sitting may sit from the nearest day the chamber's composition was
# recorded. The composition is only ever observed on particular days: roll
# calls every few weeks from 2005 (longest gap 168 days, an election-year
# recess), and archived roster pages every few months before that (longest gap
# 297 days). 200 reaches across either without reaching into the next mandate,
# which is the thing that would actually be wrong. It is deliberately loose:
# the distance is written on every row, so a stricter cut costs one filter.
BLOC_MAX_GAP_DAYS = 200
OUT_PATH = REPO_ROOT / "data" / "processed" / "senado" / "speakers.parquet"

ROLE_WORDS = re.compile(
    r"presidenta?|vicepresidenta?|secretari[oa]|prosecretari[oa]|jefe de gabinete|ministr[oa]",
    re.I,
)
TITLE_RE = r"(?:Sr|Sra|Srta|Sres)\.?"
# Role words the transcripts misspell often enough to matter ("Sr. Presiente",
# "Sr. Preisdente"). Only long tokens are corrected, and only towards one of
# these, so a surname can never be rewritten into an office.
ROLE_CANON = ["presidente", "presidenta", "vicepresidente", "vicepresidenta",
              "secretario", "secretaria", "prosecretario", "prosecretaria"]
# Offices belonging to some other institution: the lower chamber, a foreign
# state, a ministry. They are named in the record but are not the Senate's
# own people, and no roster covers them.
FOREIGN_OFFICE_RE = re.compile(
    r"c[áa]mara de diputados|rep[úu]blica de|rep[úu]blica del|estado plurinacional"
    r"|escribano|escribana|secretari[oa] de (?:obras|estado|hacienda|gobierno)"
    # A minister summoned to the chamber. Singular and followed by its
    # portfolio, which is what keeps "Jefe de Gabinete de Ministros" — an
    # office the authorities table does cover — out of this branch.
    r"|\bministr[oa]\s+de\b",
    re.I,
)


def norm(s):
    """Accent-insensitive, case-insensitive comparison key."""
    s = unicodedata.normalize("NFD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s).strip().casefold()


def clean_label(label):
    """Strip parser debris around a label and normalize its punctuation."""
    s = unicodedata.normalize("NFC", label or "").strip()
    # glued prefixes: keep from the LAST title token onward
    matches = list(re.finditer(rf"(?:{TITLE_RE}|Varios|Varias|Un\b|Una\b)\s", s))
    if matches and matches[-1].start() > 0:
        s = s[matches[-1].start():]
    s = re.sub("\\.\\s*[\\-\u2013\u2014\u2212\u2500\ue000-\uf8ff].*$", "", s)  # terminator + speech spillover ("Sr. Mayans.- ¡")
    s = re.sub(r"[.\-:…\s]+$", "", s).strip()
    # "Sra.Presidenta", "Sr Pichetto", "Sr.. PRESIDENTE", "Sr- Usandizaga",
    # "SR. PRESIDENTE": how the typist spelled the honorific does not make a
    # different speaker, so it is written the one way before anything is
    # matched against it. A letter must follow, or "Sr." on its own would be
    # turned into a label with nobody in it.
    s = re.sub(r"^(?i:(sres|srta|sra|sr))(?:(?:[.\-]\s*)+|\s+)(?=[^\W\d_])",
               lambda m: f"{m.group(1).capitalize()}. ", s)
    s = re.sub(r"\(\s*", "(", s)
    if ")" in s and "(" not in s:
        s = s.replace(")", "")                              # "Sr. Presidente)" -> stray close paren
    if "(" in s and ")" not in s:
        s += ")"                                            # "…(Abdala" -> closed
    return fix_role_typos(re.sub(r"\s+", " ", s))


def fix_role_typos(s):
    """Repair a misspelled office word ("Presiente", "Preisdente").

    Only tokens of eight characters or more are considered, and only a very
    close match to an office name is accepted, so surnames stay untouched —
    verified against every distinct label in the corpus.
    """
    def repair(m):
        word = m.group(0)
        if len(word) < 8:
            return word
        close = difflib.get_close_matches(norm(word), ROLE_CANON, n=1, cutoff=0.85)
        if not close or norm(word) == close[0]:
            return word
        return close[0].capitalize()

    head, sep, tail = s.partition("(")
    return re.sub(r"\b[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+\b", repair, head) + sep + tail


def parse_date(s):
    try:
        return date.fromisoformat((s or "").strip())
    except ValueError:
        return None


def load_mandates():
    data = json.loads(HISTORICO.read_text(encoding="utf-8"))
    rows = data["table"]["rows"] if isinstance(data, dict) else data
    mandates = []
    for r in rows:
        full = re.sub(r"\s+", " ", r.get("SENADOR", "")).strip()
        surname, _, given = full.partition(",")
        start = parse_date(r.get("INICIO PERIODO REAL")) or parse_date(r.get("INICIO PERIODO LEGAL"))
        end = parse_date(r.get("CESE PERIODO REAL")) or parse_date(r.get("CESE PERIODO LEGAL"))
        if not start:
            continue
        mandates.append({
            "person_id": f"sen:{r['ID']}",
            "surname": surname.strip(),
            "given": given.strip(),
            "surname_key": norm(surname),
            "given_key": norm(given),
            "start": start,
            "end": end,  # None = open mandate
            "province": (r.get("PROVINCIA") or "").strip(),
            "party": (r.get("PARTIDO POLITICO O ALIANZA") or "").strip(),
        })
    return mandates


def load_authorities():
    df = pd.read_csv(AUTHORITIES, dtype=str).fillna("")
    auth = []
    for _, r in df.iterrows():
        keys = {norm(r["label_surname"])} if r["label_surname"] else set()
        # variants may carry annotations: "Villarreal (typo)" -> "Villarreal"
        keys |= {norm(re.sub(r"\([^)]*\)", "", v)) for v in r["label_variants_observed"].split(";") if v.strip()}
        auth.append({
            "person_id": "auth:" + re.sub(r"\W+", "-", norm(r["full_name"])),
            "name": r["full_name"],
            "role": r["role"],
            "category": r["category"],
            "keys": {k for k in keys if k},
            "role_key": norm(r["role"]),
            "role_stem": role_stem(r["role"]),
            "start": parse_date(r["period_start"]),
            "end": parse_date(r["period_end"]),
        })
    return auth


def load_observed_authorities(mandates):
    """Chamber officers, folded out of the sittings' own mastheads.

    `extract_authorities.py` records who sat at the secretaries' table and
    who presided on each day. Here those daily observations become one
    record per officer: the office, the span they were seen holding it, and
    the surnames a speaker label might use for them ("Sr. Secretario
    (Estrada)", "(Calcagno y Maillmann)"). Only the vice-presidency of the
    Nation is taken from the presiding side — the chamber's own presiding
    officers are senators, and the roster already knows them, with the party
    and province an authority record cannot carry.
    """
    if not OBSERVED.exists():
        return []
    df = pd.read_csv(OBSERVED, dtype=str).fillna("")
    groups = {}
    for _, r in df.iterrows():
        office = r["office"]
        if "prosecretari" in office:
            family, role = "prosecretario", "prosecretaria"
        elif "secretari" in office:
            family, role = "secretario", "secretaria"
        elif "president" in office and "de la nacion" in office:
            family, role = "presidencia", "presidencia (vicepresidencia de la Nacion)"
        else:
            continue
        tokens = r["person"].split()
        d = parse_date(r["session_date"])
        if len(tokens) < 2 or not d:
            continue
        surname = norm(tokens[-1])
        if family == "presidencia" and match_senators(mandates, surname, d):
            # A senator in the chair: the roster identifies them better than
            # this table can, with their party and province. Mastheads also
            # sometimes give a presiding senator the vice-president's title
            # (Gioja, 1 March 2003), which this skips as a side effect.
            continue
        g = groups.setdefault((surname, family), {
            "role": role, "spellings": Counter(), "keys": set(), "first": d, "last": d,
        })
        g["spellings"][r["person"]] += 1
        g["keys"] |= {norm(" ".join(tokens[-n:])) for n in (1, 2, 3) if n <= len(tokens)}
        g["first"], g["last"] = min(g["first"], d), max(g["last"], d)

    out = []
    by_surname = {}
    for (surname, family), g in groups.items():
        name = g["spellings"].most_common(1)[0][0]
        by_surname.setdefault(surname, set()).add(norm(name))
        out.append({
            "person_id": "obs:" + re.sub(r"\W+", "-", norm(name)),
            "name": name,
            "role": g["role"],
            "category": "senate_authority_observed",
            "keys": g["keys"],
            "role_key": norm(g["role"]),
            "role_stem": role_stem(g["role"]),
            "start": g["first"] - timedelta(days=OBSERVED_PAD_DAYS),
            "end": g["last"] + timedelta(days=OBSERVED_PAD_DAYS),
        })
    shared = sorted(s for s, names in by_surname.items() if len(names) > 1)
    if shared:
        # Would make a bare surname in a label ambiguous; none exist today,
        # so this is a tripwire for a future officer, not a known problem.
        print(f"  warning: surname used by more than one officer: {shared}")
    return out


# Offices the chamber's own members hold in the chair. The vice-presidency of
# the Nation is left out on purpose: its holder is not a senator, and the
# authorities table already answers for them.
PRESIDING_OFFICES = re.compile(r"^(?:president[ea]\s+provisional|vicepresident[ea](?:\s+[123])?)")


def load_presiding_by_file():
    """Which senators each sitting's own cover page names as presiding.

    A chair label gives a surname and nothing else — "Sr. Presidente (Sapag)"
    — and for four years two senators named Sapag sat at once, so the roster
    alone cannot say which of them held the gavel. The masthead can: it names
    the day's presiding officers in full ("del señor vicepresidente 2° del H.
    Senado, don Felipe R. Sapag"), which settles it from the printed page.

    Keyed by raw file name, not by date, because two sittings can share a day.
    """
    if not OBSERVED.exists():
        return {}
    df = pd.read_csv(OBSERVED, dtype=str).fillna("")
    out = {}
    for _, r in df.iterrows():
        # a list of office holders names every vice-president, presiding or
        # not, so it says nothing about who held the gavel that day
        if r.get("basis") == "roster":
            continue
        if not PRESIDING_OFFICES.match(r["office"]) or "de la nacion" in r["office"]:
            continue
        if r["person"]:
            out.setdefault(r["file"], []).append(r["person"])
    return out


def narrow_by_masthead(sens, presiding):
    """Keep the candidates the masthead names in the chair, if it names any.

    A presiding name only counts for a candidate when it ends in that
    candidate's own surname: otherwise "Mario A. Losada", sitting in the same
    masthead, would answer for a senator whose given name happens to be Mario.
    Initials are ignored, so a masthead that writes "F. R. Sapag" decides
    nothing; the caller uses the result only when it leaves exactly one.
    """
    kept = []
    for sen in sens:
        given = {t for t in sen["given_key"].split() if len(t) > 2}
        for name in presiding:
            n = norm(name)
            if n != sen["surname_key"] and not n.endswith(" " + sen["surname_key"]):
                continue
            rest = {t.strip(".") for t in n[: len(n) - len(sen["surname_key"])].split()}
            if given & {t for t in rest if len(t) > 2}:
                kept.append(sen)
                break
    return kept


# "Sres." is a plural and says nothing about one speaker.
HONORIFIC_RE = re.compile(r"^(Sres|Srta|Sra|Sr)\.?(?=\s|$)")
# A given name must be seen this many times, and agree this often, before the
# corpus is taken to have settled it.
GENDER_MIN_COUNT, GENDER_MIN_SHARE = 4, 0.8


def honorific_is_feminine(label):
    """True, False, or None for a label's courtesy title."""
    m = HONORIFIC_RE.match(label)
    if not m or m.group(1).lower() == "sres":
        return None
    return m.group(1).lower() in ("sra", "srta")


def first_given(given_key):
    """The first given name long enough to identify, or "" if there is none."""
    for t in given_key.split():
        if len(t) > 2:
            return t
    return ""


def learn_honorific_gender(labels, resolved):
    """Which given names the chamber writes as "señora" and which as "señor".

    Read off the corpus, not guessed from the spelling. The rule "ends in -a"
    would call Beatriz, Nancy, Mabel, Carmen and Mercedes masculine, and
    Beatriz alone speaks in 2,518 passages here. Instead every label that
    resolved to exactly one senator lends its courtesy title to that senator's
    first given name, so a name is settled by the number of times the chamber
    wrote it.

    The chamber slips: about 1% of titles in the corpus disagree with the
    senator the label resolves to — "Sr." for a María, "Sra." for a Rubén. A
    name therefore counts as settled only when it is seen at least
    GENDER_MIN_COUNT times and at least GENDER_MIN_SHARE of those agree, which
    keeps a handful of typists' slips from deciding anything. It is a loose
    threshold and it can afford to be: of the 174 given names seen with a
    title, 169 clear the count and every one of those lands outside 20-80%,
    103 of them unanimously. The furthest from unanimous is Olijela at 21 of
    23. The five left unsettled are seen once or twice each.
    """
    tally = {}
    for row, res in zip(labels, resolved):
        if res["match_status"] not in ("matched_senator", "matched_senator_chair"):
            continue
        fem = honorific_is_feminine(clean_label(row.speaker_raw))
        if fem is None:
            continue
        _, _, given = (res.get("person_name") or "").partition(",")
        name = first_given(norm(given))
        if not name:
            continue
        seen, femcount = tally.get(name, (0, 0))
        tally[name] = (seen + row.n_blocks, femcount + row.n_blocks * fem)
    gender = {}
    for name, (seen, femcount) in tally.items():
        if seen < GENDER_MIN_COUNT:
            continue
        share = femcount / seen
        if share >= GENDER_MIN_SHARE:
            gender[name] = True
        elif share <= 1 - GENDER_MIN_SHARE:
            gender[name] = False
    return gender


def narrow_by_honorific(sens, label, gender):
    """Keep the candidate whose given name carries the label's courtesy title.

    This is the last thing tried and the only one that rests on how the
    chamber writes rather than on what it states, so it is deliberately
    narrow. EVERY candidate's given name must be settled, not just the one
    that survives: a name the corpus has not settled would otherwise be
    dropped for being unknown, and the title would appear to decide between
    two women because only one of them was recognised. Rows decided here are
    marked `tiebreak == "honorific"` so a reading that will not accept a
    courtesy title as evidence can drop them with one filter.
    """
    fem = honorific_is_feminine(label)
    if fem is None:
        return []
    known = [gender.get(first_given(sen["given_key"])) for sen in sens]
    if any(g is None for g in known):
        return []
    return [sen for sen, g in zip(sens, known) if g == fem]


def role_contains(haystack, needle):
    """Is `needle` a whole-word phrase inside `haystack`?

    Plain substring matching cannot be used here: "vicepresidencia de la
    Nación" contains "presidencia de la Nación" letter for letter, so the
    Vice-President would answer for every speech the President gave at an
    Asamblea. Requiring a word boundary on both sides keeps the two offices
    apart.
    """
    return bool(needle) and re.search(rf"(?<!\w){re.escape(needle)}(?!\w)", haystack) is not None


def role_stem(s):
    """Canonical role key: presidente/presidenta -> presidencia, jefe -> jefatura, ..."""
    s = norm(s)
    s = re.sub(r"\bvicepresident[ea]\b", "vicepresidencia", s)
    s = re.sub(r"\bpresident[ea]\b", "presidencia", s)
    s = re.sub(r"\bjefe\b", "jefatura", s)
    s = re.sub(r"\bsecretari[oa]\b", "secretaria", s)
    s = re.sub(r"\bprosecretari[oa]\b", "prosecretaria", s)
    # The cabinet chief's office is spelled several ways ("de Ministros", "de
    # la Nación", or nothing at all); they are one office with one holder.
    s = re.sub(r"^jefatura de gabinete\b.*$", "jefatura de gabinete", s)
    # "del H. Senado" only says which house, not which office.
    s = re.sub(r"\s+del?\s+(?:h\.?\s*)?(?:honorable\s+)?senado(?:\s+de\s+la\s+nacion)?", "", s)
    return s.strip()


def role_family(stem):
    """Which office family a role belongs to.

    The record is loose within a family and strict across them. Whoever
    occupies the chair is called "Sr. Presidente" whatever their formal rank
    — vice-president of the Nation, provisional president, second
    vice-president of the chamber — and whoever sits at the secretaries'
    table is called "Sr. Secretario" even when the post is prosecretario.
    But a prosecretario is never the chair, so matching on a shared word
    ("secretaria" inside "prosecretaria", "presidencia" inside
    "vicepresidencia") would put the wrong person behind the words.
    """
    if "jefatura de gabinete" in stem:
        return "cabinet"
    if role_contains(stem, "presidencia de la nacion"):
        return "national_presidency"       # the President, not the chamber's chair
    if "presidencia" in stem:              # covers vicepresidencia of every rank
        return "chair"
    if "secretaria" in stem:               # covers prosecretaria
        return "secretariat"
    return stem


# Offices the chamber fills more than once over: on any given day the Senate
# has two or three secretaries and several vice-presidents, and a label that
# gives only the office does not say which one is speaking.
CHAMBER_OFFICES = {"presidencia", "vicepresidencia", "secretaria", "prosecretaria"}


def in_window(rec, d, grace_days=0):
    """Missing start/end = open bound; grace admits 'electo/a' pre-mandate labels."""
    start_ok = rec["start"] is None or rec["start"].toordinal() - grace_days <= d.toordinal()
    return start_ok and (rec["end"] is None or d <= rec["end"])


def initials(tokens):
    return [t[0] for t in tokens if t]


def given_matches(given_key, roster_given):
    """Does the label's given name pick out this roster given name?

    Labels disambiguate same-surname senators either by a name token
    ("(Gladys)") or by initials ("(A. A.)", "(M. T. M.)"), sometimes fewer
    initials than the person carries. Initials are compared in order from
    the front, which is how the transcripts abbreviate them.
    """
    ltok = given_key.replace(".", " ").split()
    rtok = roster_given.split()
    if not ltok or not rtok:
        return False
    if set(ltok) & set(rtok):
        return True
    if all(len(t) == 1 for t in ltok) and len(ltok) <= len(rtok):
        return initials(rtok)[:len(ltok)] == ltok
    return False


def match_senators(mandates, surname_key, d, given_key=None, grace_days=0, fuzzy=False):
    cands = [m for m in mandates if m["surname_key"] == surname_key and in_window(m, d, grace_days)]
    if not cands:
        # prefix fallback: label "Ledesma Abdala" vs roster "LEDESMA ABDALA DE ZAMORA"
        cands = [m for m in mandates if in_window(m, d, grace_days)
                 and (m["surname_key"].startswith(surname_key + " ")
                      or surname_key.startswith(m["surname_key"] + " "))]
    if not cands:
        # trailing fallback: the record often drops the first half of a
        # compound surname — "Naidenoff" for "Petcoff Naidenoff", "Duhalde"
        # for "González de Duhalde", "Pass de Cresto" for "Martínez Pass de
        # Cresto". Only used when nobody carries the label as their whole
        # surname and exactly one person on the day ends with it, so
        # "Abdala" still means Bartolomé Abdala and never Ledesma Abdala.
        tail = [m for m in mandates if in_window(m, d, grace_days)
                and m["surname_key"].endswith(" " + surname_key)]
        if len({m["person_id"] for m in tail}) == 1:
            cands = tail
    if not cands and fuzzy:
        # last resort for stenographic typos: Parrili, Di Tulio, Schiavone, ...
        pool = {m["surname_key"] for m in mandates if in_window(m, d, grace_days)}
        close = difflib.get_close_matches(surname_key, pool, n=2, cutoff=0.86)
        if len(close) == 1:
            cands = [m for m in mandates if m["surname_key"] == close[0] and in_window(m, d, grace_days)]
    if given_key and len(cands) > 1:
        cands = [m for m in cands if given_matches(given_key, m["given_key"])]
    # collapse duplicate mandate rows for the same person (re-elections)
    return list({m["person_id"]: m for m in cands}.values())


def stepped_down(mandates, auth, key, d):
    """Did someone of exactly this surname hold a seat or office that had
    ended before d, with nobody of it holding one on d?"""
    ended = lambda r: r["end"] is not None and r["end"] < d
    if any(m["surname_key"] == key and in_window(m, d) for m in mandates) \
            or any(key in a["keys"] and in_window(a, d) for a in auth):
        return False    # still in some office: a misprint, not a stale name
    return (any(m["surname_key"] == key and ended(m) for m in mandates)
            or any(key in a["keys"] and ended(a) for a in auth))


def match_authorities(auth, key, d, role_hint=None):
    hits = [a for a in auth if key in a["keys"] and in_window(a, d)]
    if not hits:
        # the label may carry the whole compound surname where the masthead
        # printed only its first half: "(Calcagno y Maillmann)" vs "Calcagno"
        hits = [a for a in auth if in_window(a, d)
                and any(key.startswith(k + " ") for k in a["keys"])]
    if not hits:
        # stenographic typos on officer names: "(Estada)", "(Estradas)"
        pool = {k for a in auth if in_window(a, d) for k in a["keys"]}
        close = difflib.get_close_matches(key, pool, n=2, cutoff=0.86)
        if len(close) == 1:
            hits = [a for a in auth if close[0] in a["keys"] and in_window(a, d)]
    if role_hint:
        # The office the label states has to be the office the person held.
        # Surnames repeat across roles — a Losada presided the chamber in the
        # same years another Losada sat at the prosecretaries' table — and
        # without this the wrong one wins and the senator is never reached.
        family = role_family(role_stem(role_hint))
        hits = [a for a in hits if role_family(a["role_stem"]) == family]
    return prefer_curated(hits)


def prefer_curated(hits):
    """One person, two records valid on the same day: keep the curated one.

    Where both tables know an officer, the curated row is meant to win. Order
    made it win only for a label that names the office, which takes the first
    hit; a bare surname — "Sr. Clark" — needs exactly one, and the same man
    held twice, curated as "Lucas Martín Clark" and read off the cover as
    "Lucas Clark", left it unresolved. The test is taken on the day, among
    records already valid on it, and not across whole spans: a curated row may
    cover a few weeks of a tenure the covers show for years (Tunessi, curated
    only around December 2019, seen on the covers from 2015), and dropping the
    cover record for the whole span lost every label in between.
    """
    curated = [h for h in hits if h["person_id"].startswith("auth:")]
    if not curated:
        return hits
    return curated + [
        h for h in hits if not h["person_id"].startswith("auth:")
        and not any(role_family(h["role_stem"]) == role_family(c["role_stem"])
                    and h["keys"] & c["keys"] for c in curated)]


def break_tie(sens, label, presiding, gender):
    """Try to leave exactly one candidate, and say what did it.

    Two things can separate senators the roster cannot: the sitting's cover
    page, which STATES who presided, and the courtesy title, which only
    reflects how the chamber writes. The cover page is tried first for that
    reason. Either is used only when it leaves exactly one candidate — a
    narrowing to none, or to two, is no narrowing at all and the label stays
    ambiguous.
    """
    if len(sens) < 2:
        return sens, None
    for narrowed, how in ((narrow_by_masthead(sens, presiding), "masthead"),
                          (narrow_by_honorific(sens, label, gender or {}), "honorific")):
        if len(narrowed) == 1:
            return narrowed, how
    return sens, None


def resolve_one(label, session_date, session_type, mandates, auth, presiding=(), gender=None):
    d = session_date
    s = clean_label(label)

    if re.match(r"^(Varios|Varias|Un |Una )", s, re.I) or "no identificado" in norm(s):
        return {"match_status": "collective", "role": "collective"}

    if FOREIGN_OFFICE_RE.search(s):
        # An office of some other body: the lower chamber, a foreign state, a
        # ministry, the government's notary. Named in the record, but outside
        # what any roster of this chamber covers.
        return {"match_status": "out_of_scope",
                "role": re.sub(rf"^{TITLE_RE}\s+", "", s)}

    m = re.match(rf"^{TITLE_RE}\s+(?P<pre>[^(]*?)\s*\.?\s*\((?P<paren>[^)]+)\)$", s)
    if m and ROLE_WORDS.search(m["pre"]):
        # chair/officer: authorities first, then senators presiding
        key = norm(m["paren"].strip(" ."))       # "(Losada.)" -> losada
        hits = match_authorities(auth, key, d, role_hint=m["pre"])
        if hits:
            a = hits[0]
            return {"match_status": "matched_authority", "person_id": a["person_id"],
                    "person_name": a["name"], "role": m["pre"].strip() or a["role"]}
        if FOREIGN_OFFICE_RE.search(m["pre"]):
            return {"match_status": "out_of_scope", "role": m["pre"].strip()}
        sens = match_senators(mandates, key, d, fuzzy=True)
        sens, tiebreak = break_tie(sens, s, presiding, gender)
        if len(sens) == 1:
            sen = sens[0]
            return {"match_status": "matched_senator_chair", "person_id": sen["person_id"],
                    "person_name": f"{sen['surname']}, {sen['given']}", "role": m["pre"].strip(),
                    "party": sen["party"], "province": sen["province"], "tiebreak": tiebreak}
        if not sens and stepped_down(mandates, auth, key, d):
            # A name left over from an earlier year: the record re-used a
            # template that still carried it. Maqueda went to the Supreme
            # Court on 27 December 2002, and three sittings of 2003 still
            # print "Sr. Presidente (Maqueda)" on routine agenda items. The
            # label says the chair spoke and nothing more, so it is read as
            # the bare office, exactly like "Sr. Presidente".
            return {"match_status": "office_only", "role": m["pre"].strip()}
        return {"match_status": "ambiguous" if sens else "unmatched", "role": m["pre"].strip()}

    if m:  # parenthetical WITHOUT role word: "Sra. González (Gladys)" — given in paren
        sens = match_senators(mandates, norm(m["pre"]), d, given_key=norm(m["paren"]))
        sens, tiebreak = break_tie(sens, s, (), gender)
        if len(sens) == 1:
            sen = sens[0]
            return {"match_status": "matched_senator", "person_id": sen["person_id"],
                    "person_name": f"{sen['surname']}, {sen['given']}",
                    "party": sen["party"], "province": sen["province"], "tiebreak": tiebreak}
        return {"match_status": "ambiguous" if sens else "unmatched"}

    if ROLE_WORDS.search(s) and "(" not in s:
        # role-only: Presidente de la Nación, Jefe de Gabinete, bare Presidenta
        role = re.sub(rf"^{TITLE_RE}\s+", "", s)
        elect = bool(re.search(r"\belect[oa]$", role))
        role = re.sub(r"\s+elect[oa]$", "", role)
        stem = role_stem(role)
        if stem in CHAMBER_OFFICES:
            # A chamber office named without a surname. Whoever holds it
            # changes during a sitting and the page does not say who it is,
            # so no person is assigned: the office is all the source states.
            # (A national office — "Presidente de la Nación", "Jefe de
            # Gabinete" — has one holder on a date and resolves below.)
            return {"match_status": "office_only", "role": role}
        grace = 300 if elect else 0     # "electo/a" labels precede the mandate
        family = role_family(stem)
        hits = [a for a in auth if in_window(a, d, grace) and role_family(a["role_stem"]) == family]
        exact = [a for a in hits if a["role_stem"] == stem]
        pick = exact or hits
        if len(pick) > 1:
            # A handover sitting has the outgoing and incoming holder both in
            # window on the day. The sitting IS the swearing-in, so the one
            # whose term opens that day is the one who speaks.
            starting = [a for a in pick if a["start"] == d]
            if starting:
                pick = starting
        if len(pick) == 1:
            a = pick[0]
            return {"match_status": "matched_authority", "person_id": a["person_id"],
                    "person_name": a["name"], "role": role}
        return {"match_status": "ambiguous" if pick else "unmatched", "role": role}

    if re.match(rf"^{TITLE_RE}\s+diputad", s, re.I):
        return {"match_status": "out_of_scope", "role": "diputado/a"}

    # (?i:...) on the two title words: the early transcripts write them in
    # capitals ("Sr. SENADOR ELECTO ALTUNA"), and a case-sensitive class left
    # the whole phrase sitting in the surname, where nothing could match it.
    m = re.match(rf"^{TITLE_RE}\s+(?:(?i:senadora?)\s+)?(?P<elect>(?i:elect[oa])\s+)?"
                 rf"(?P<sur>[^,]+?)(?:,\s*(?P<given>.+))?$", s)
    if m:
        # "Senador electo X" speaks at preparatorias BEFORE the mandate starts
        grace = 300 if m["elect"] else 0
        sens = match_senators(mandates, norm(m["sur"]), d, grace_days=grace, fuzzy=True,
                              given_key=norm(m["given"]) if m["given"] else None)
        sens, tiebreak = break_tie(sens, s, (), gender)
        if len(sens) == 1:
            sen = sens[0]
            return {"match_status": "matched_senator", "person_id": sen["person_id"],
                    "person_name": f"{sen['surname']}, {sen['given']}",
                    "party": sen["party"], "province": sen["province"], "tiebreak": tiebreak}
        if not sens:
            # bare-surname officers (secretaries: Izzo, Chavarría, D. Martínez)
            # and, in Asambleas, the President ("Sr. Fernández")
            hits = match_authorities(auth, norm(m["sur"]), d)
            if not hits:
                hits = [a for a in auth if in_window(a, d)
                        and norm(m["sur"]) == norm(a["name"].split()[-1])
                        and ("executive" in a["category"] if session_type != "ASAMBLEA" else True)]
            if len(hits) == 1:
                a = hits[0]
                return {"match_status": "matched_authority", "person_id": a["person_id"],
                        "person_name": a["name"], "role": a["role"]}
            if not sens and "JUICIO POLITICO" in (session_type or "").upper():
                # Sitting as a court, the chamber hears people who are not
                # its members: the accused, the prosecutors sent by the lower
                # house, defence counsel and expert witnesses. No roster of
                # this chamber covers them, so they are out of scope rather
                # than a failed lookup.
                return {"match_status": "out_of_scope", "role": "parte del juicio político"}
        return {"match_status": "ambiguous" if sens else "unmatched"}

    return {"match_status": "unmatched"}


def load_bloc_observations():
    """The caucus each senator was recorded in, on each day it was recorded.

    Returns {person_id: [(date, bloc, status, basis), ...]} sorted by date.
    """
    if not BLOC_OBS.exists():
        print(f"WARNING: {BLOC_OBS.name} missing — no caucus will be attached")
        return {}
    df = pd.read_csv(BLOC_OBS)
    # 'acta_anacronica' names a caucus that did not yet (or no longer) exist on
    # the day of the vote: the Senate re-labels old roll calls with the caucus a
    # senator later belonged to. Kept, marked, never silently passed on.
    #
    # Both archived-roster readings count as confirmed, including the caucuses
    # too old to appear in the dated list. The asymmetry is the point: a roll
    # call carries a caucus name written long after the vote, which is why it
    # has to be checked, while an archived page was written the day it says —
    # it is the caucus and its members printed together, so it attests itself.
    status = {"acta": "confirmed", "acta_anacronica": "anachronistic",
              "acta_sin_control": "undatable", "foto": "confirmed",
              "foto_bloque_previo": "confirmed",
              # the chair naming a senator's caucus as it gives the floor
              "llamado": "confirmed", "declaracion": "confirmed"}
    basis = {"acta de votacion": "roll call",
             "foto de la pagina de bloques": "archived roster",
             # one senator's own page, captured 2 February 1998: dated the
             # same way as the roster page, by the day it was captured
             "ficha del senador": "archived senator page",
             "llamado de la presidencia": "chair's call",
             "declaracion en el recinto": "floor statement"}
    obs = {}
    for r in df.itertuples(index=False):
        # keyed the same way the roster is, so the join is on the person
        obs.setdefault(f"sen:{r.person_id}", []).append(
            (date.fromisoformat(r.fecha), r.bloque,
             status.get(r.fiabilidad, r.fiabilidad), basis.get(r.fuente, r.fuente)))
    for v in obs.values():
        v.sort(key=lambda x: x[0])
    print(f"{len(df)} caucus observations for {len(obs)} senators, "
          f"{df.fecha.min()} to {df.fecha.max()}")
    return obs


def load_bloc_lives():
    """The hand-dated caucus lives, as {caucus: [(start, end), ...]}.

    The same table `build_bloc_observations.py` checks each reading against.
    A blank start or end is open on that side; a caucus dated with no
    confidence, or absent from the table altogether, is not checkable.
    """
    lives = {}
    with BLOC_LIVES.open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["confidence"] == "none":
                continue
            lives.setdefault(r["bloc"], []).append(
                (parse_date(r["period_start"]), parse_date(r["period_end"])))
    return lives


def bloc_alive_on(bloc, when, lives):
    """Whether the caucus's own dated life covers `when`.

    True where nothing can be checked — an undated caucus is not evidence
    that it did not exist, and saying so would turn silence into a finding.
    """
    spans = lives.get(bloc)
    if not spans:
        return True
    return any((s is None or when >= s) and (e is None or when <= e)
               for s, e in spans)


def bracketed(rows, when, lives, terms):
    """The caucus a senator was seen in on BOTH sides of a sitting too far
    from either to take it from one, or None.

    Nothing is recorded of 1998 and 1999 for the senators the chair never
    introduced by caucus and who never said theirs, except that the same
    senator is observed in the same caucus before and after. Reading the
    sitting as that caucus is an inference, not an observation, and it is
    marked so (`bloc_status = "bracketed"`), with how far apart the two
    observations are (`bloc_span_days`), so a reader can set their own limit.

    It is allowed only where it is safe, and how safe was measured on the
    archived roster pages of 2000-2004, written on the day they describe: of
    1,591 pairs showing a senator in the same caucus 400 to 2,200 days apart,
    2 have a different caucus in between. The roll calls cannot answer this.
    The Senate re-labels old roll calls with a senator's later caucus, so they
    show a change inside only 2 of 338 mandates where the roster pages show
    one inside 17 of 176, and their "none in half a million" says nothing. The two observations must be the nearest on each side, both readings
    that could describe their own day, and all three dates inside one
    mandate: a new mandate is exactly when a senator changes caucus.
    """
    ok = [r for r in rows if r[2] == "confirmed"
          and (r[3] != "roll call" or bloc_alive_on(r[1], when, lives))]
    before = [r for r in ok if r[0] <= when]
    after = [r for r in ok if r[0] >= when]
    if not before or not after:
        return None
    b = max(before, key=lambda r: r[0])
    a = min(after, key=lambda r: r[0])
    if norm(b[1]) != norm(a[1]):
        return None
    if not any(t0 <= b[0] and (t1 is None or a[0] <= t1) for t0, t1 in terms):
        return None
    near = min((b, a), key=lambda r: abs((r[0] - when).days))
    return {"bloc": near[1], "bloc_status": "bracketed", "bloc_basis": near[3],
            "bloc_observed": near[0].isoformat(),
            "bloc_gap_days": abs((near[0] - when).days),
            "bloc_span_days": (a[0] - b[0]).days}


def bloc_on(person_id, when, obs, lives, terms=()):
    """The caucus recorded nearest to `when`, or empty fields if none is close.

    The reading was checked against the caucus's dated life on the day it was
    RECORDED. Carrying it up to 200 days to a sitting re-opens the same
    question for the sitting's date, and a reading can be sound where it was
    taken and anachronistic where it is used: the roll call of 21 Dec 2005
    rightly reads "PJ Frente para la Victoria", a caucus formed that month,
    and the sitting nearest to it is in June, six months before the caucus
    existed. So the check is made again here, against the date being asked
    about, which is the date `bloc_status` has always claimed to speak for.

    Only roll-call readings are re-checked. An archived roster page's dates
    are the days the page was CAPTURED — a floor on the caucus's life, not a
    claim about when it began — so a sitting before the earliest capture is
    expected rather than wrong, and marking it would report the gaps in the
    Internet Archive as a fact about the chamber.
    """
    rows = obs.get(person_id) if person_id is not None else None
    if not rows:
        return {}
    d, bloc, status, basis = min(rows, key=lambda x: abs((x[0] - when).days))
    gap = abs((d - when).days)
    if gap > BLOC_MAX_GAP_DAYS:
        return bracketed(rows, when, lives, terms) or {}
    if (status == "confirmed" and basis == "roll call"
            and not bloc_alive_on(bloc, when, lives)):
        status = "anachronistic"
    elif status == "confirmed":
        # Only a reading that could itself describe the caucus on THIS day can
        # contradict another. A reading the source already flagged, or a roll
        # call naming a caucus that did not exist on the day of the sitting, is
        # not evidence of a switch — it is the very thing `anachronistic`
        # exists to mark. Reading the roll call of 3 Feb 2005 as "PJ Frente
        # para la Victoria" against a September 2004 sitting disputed 1,816
        # passages away from a caucus nobody disagrees they sat in: that roll
        # call is one of 21 the Senate re-labelled with a name the caucus only
        # took on 10 Dec 2005. An archived roster page is exempt from the
        # date test for the same reason as above — its date is when the page
        # was captured, not when the caucus began.
        near = [r for r in rows
                if abs((r[0] - when).days) <= BLOC_MAX_GAP_DAYS
                and r[2] == "confirmed"
                and (r[3] != "roll call" or bloc_alive_on(r[1], when, lives))]
        before = [r for r in near if r[0] <= when]
        after = [r for r in near if r[0] >= when]
        if before and after:
            last = max(before)[1]
            first = min(after, key=lambda r: r[0])[1]
            # compared on the name, not its spelling: one pair differed only in
            # capitalisation ("Bloque Cruzada Renovadora De San Juan")
            if norm(last) != norm(first):
                status = "disputed"
    return {"bloc": bloc, "bloc_status": status, "bloc_basis": basis,
            "bloc_observed": d.isoformat(), "bloc_gap_days": gap}


def main():
    for p in (HISTORICO, AUTHORITIES):
        if not p.exists():
            sys.exit(f"Missing roster input: {p}")
    mandates = load_mandates()
    # Hand-compiled rows first: where both tables know a name, the curated
    # one wins, because it carries verified tenure bounds and a source.
    auth = load_authorities() + load_observed_authorities(mandates)
    print(f"{len(mandates)} mandate rows, {len(auth)} authority rows")
    bloc_obs = load_bloc_observations()
    bloc_lives = load_bloc_lives()
    terms = {}
    for m in mandates:
        terms.setdefault(m["person_id"], []).append((m["start"], m["end"]))
    presiding = load_presiding_by_file()
    print(f"{sum(len(v) for v in presiding.values())} presiding names "
          f"from the mastheads of {len(presiding)} sittings")

    # Only the columns the join needs. Reading all of them pulls 25.7 million
    # words of text in to count rows, and makes pandas guess a dtype for
    # columns that are empty in one sitting and not in the next.
    corpus = pd.concat([pd.read_parquet(p, columns=["session_id", "session_date",
                                                    "session_type", "source_file",
                                                    "type", "speaker_raw"])
                        for p in sorted(BLOCKS_DIR.glob("*.parquet"))],
                       ignore_index=True)
    speech = corpus[corpus.type == "speech"]
    labels = (speech.groupby(["session_id", "session_date", "session_type",
                              "source_file", "speaker_raw"])
              .size().reset_index(name="n_blocks"))
    print(f"{len(labels)} (session, label) pairs across {labels.session_id.nunique()} sessions")

    rows = list(labels.itertuples())

    def resolve(r, gender=None):
        return resolve_one(r.speaker_raw, date.fromisoformat(r.session_date),
                           r.session_type, mandates, auth,
                           presiding.get(Path(r.source_file).stem, ()), gender)

    resolved = [resolve(r) for r in rows]
    # The labels are read twice. The courtesy title can separate two senators
    # of the same surname, but only once the corpus has said which given names
    # the chamber writes as "señora" — and it says that through the labels that
    # needed no tiebreak at all. So: resolve, learn, then try again on what
    # stayed ambiguous. Nothing decided by a title feeds the learning.
    gender = learn_honorific_gender(rows, resolved)
    settled = 0
    for i, r in enumerate(rows):
        if resolved[i]["match_status"] != "ambiguous":
            continue
        again = resolve(r, gender)
        if again["match_status"] != "ambiguous":
            resolved[i] = again
            settled += 1
    print(f"{len(gender)} given names settled by the chamber's own courtesy titles; "
          f"{settled} ambiguous labels resolved by one")

    out = []
    for r, res in zip(rows, resolved):
        d = date.fromisoformat(r.session_date)
        out.append({
            "session_id": r.session_id,
            "session_date": r.session_date,
            "speaker_raw": r.speaker_raw,
            "label_clean": clean_label(r.speaker_raw),
            "n_blocks": r.n_blocks,
            "person_id": res.get("person_id"),
            "person_name": res.get("person_name"),
            "role": res.get("role"),
            "elected_ticket": res.get("party"),
            "province": res.get("province"),
            "match_status": res["match_status"],
            "tiebreak": res.get("tiebreak"),
            **bloc_on(res.get("person_id"), d, bloc_obs, bloc_lives,
                      terms.get(res.get("person_id"), ())),
        })

    df = pd.DataFrame(out)
    for c in ("bloc", "bloc_status", "bloc_basis", "bloc_observed", "bloc_gap_days",
              "bloc_span_days"):
        if c not in df:
            df[c] = None
    df.to_parquet(OUT_PATH, index=False)

    total = df.n_blocks.sum()
    print(f"\nResolution by speech blocks (total {total}):")
    print(df.groupby("match_status").n_blocks.sum().sort_values(ascending=False)
          .apply(lambda n: f"{n} ({n/total:.1%})").to_string())
    bad = df[df.match_status.isin(["unmatched", "ambiguous"])]
    print(f"\nTop unresolved labels ({len(bad)} label-sessions):")
    top = bad.groupby("label_clean").n_blocks.sum().sort_values(ascending=False).head(15)
    print(top.to_string())
    senators = df[df.match_status.isin(["matched_senator", "matched_senator_chair"])]
    n = senators.n_blocks.sum()
    print(f"\nCaucus attached, by speech blocks (senators only, total {n}):")
    got = senators[senators.bloc.notna()]
    print(f"  with a caucus       {got.n_blocks.sum()} ({got.n_blocks.sum()/n:.1%})")
    print(got.groupby("bloc_status").n_blocks.sum().sort_values(ascending=False)
          .apply(lambda x: f"    {x} ({x/n:.1%})").to_string())
    print(got.groupby("bloc_basis").n_blocks.sum()
          .apply(lambda x: f"    {x} ({x/n:.1%})").to_string())
    miss = senators[senators.bloc.isna()]
    print(f"  no caucus           {miss.n_blocks.sum()} ({miss.n_blocks.sum()/n:.1%})")
    if len(got):
        print(f"  median days from the nearest observation: {got.bloc_gap_days.median():.0f}")

    print(f"\nWritten: {OUT_PATH}")
    print("\nNote: elected_ticket is the list each senator STOOD ON, which is what\n"
          "the roster records. bloc is the caucus they SAT WITH. They are different\n"
          "and they disagree across most of the corpus — a senator elected on a\n"
          "provincial alliance nearly always sits with a national caucus, and only\n"
          "bloc says which. Where bloc_status is 'anachronistic' the Senate's own\n"
          "record names a caucus that did not exist on the day of the sitting; those\n"
          "rows are kept and marked, not corrected. Speech from the chair carries a\n"
          "caucus too, because the person did belong to one — but it is procedural\n"
          "speech, so reading it as partisan is a mistake the data cannot prevent.")


if __name__ == "__main__":
    main()
