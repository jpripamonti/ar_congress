"""Resolve speaker labels in the parsed corpus to persons.

Implements the join strategy from the roster research (July 2026):

- Labels are routed by shape: Role (Surname) chairs/officers; "Surname,
  Given" comma-disambiguated senators; role-only labels (Presidente de la
  Nación, Jefe de Gabinete); collective labels; bare surnames.
- Chair parentheticals resolve against the authorities table FIRST (VP,
  officer secretaries — non-senators), then the date-filtered senator
  roster (any senator can preside).
- Compound surnames match on the FULL surname string, never tokens
  ("Rodríguez Machado" is not "Rodríguez"; "Ledesma Abdala" is not
  "Abdala").
- Candidates are filtered by session date against the mandate windows
  (INICIO/CESE PERIODO REAL, falling back to LEGAL; "Sin Datos" = open).
- Known chair-name typo variants (Ledezma Abdala, Villarreal, ...) come
  from the authorities table's variants column.

Inputs:  data/processed/senado/blocks/*.parquet,
         reference/senado/senadores_historico.json,
         reference/senado/authorities_manual.csv
Output:  data/processed/senado/speakers.parquet — one row per
         (session_id, speaker_raw) with person_id, name, party_or_alliance,
         province,
         role, match_status — plus a printed resolution summary.
"""

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
    r"|escribano|escribana|secretari[oa] de (?:obras|estado|hacienda|gobierno)",
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
    s = re.sub(r"^((?:Sr|Sra|Srta|Sres)\.)(?=\S)", r"\1 ", s)  # "Sra.Presidenta" -> spaced (dot required, no backtracking)
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
    return hits


def resolve_one(label, session_date, session_type, mandates, auth):
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
        if len(sens) == 1:
            sen = sens[0]
            return {"match_status": "matched_senator_chair", "person_id": sen["person_id"],
                    "person_name": f"{sen['surname']}, {sen['given']}", "role": m["pre"].strip(),
                    "party": sen["party"], "province": sen["province"]}
        return {"match_status": "ambiguous" if sens else "unmatched", "role": m["pre"].strip()}

    if m:  # parenthetical WITHOUT role word: "Sra. González (Gladys)" — given in paren
        sens = match_senators(mandates, norm(m["pre"]), d, given_key=norm(m["paren"]))
        if len(sens) == 1:
            sen = sens[0]
            return {"match_status": "matched_senator", "person_id": sen["person_id"],
                    "person_name": f"{sen['surname']}, {sen['given']}",
                    "party": sen["party"], "province": sen["province"]}
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

    m = re.match(rf"^{TITLE_RE}\s+(?:[Ss]enadora?\s+)?(?P<elect>[Ee]lect[oa]\s+)?(?P<sur>[^,]+?)(?:,\s*(?P<given>.+))?$", s)
    if m:
        # "Senador electo X" speaks at preparatorias BEFORE the mandate starts
        grace = 300 if m["elect"] else 0
        sens = match_senators(mandates, norm(m["sur"]), d, grace_days=grace, fuzzy=True,
                              given_key=norm(m["given"]) if m["given"] else None)
        if len(sens) == 1:
            sen = sens[0]
            return {"match_status": "matched_senator", "person_id": sen["person_id"],
                    "person_name": f"{sen['surname']}, {sen['given']}",
                    "party": sen["party"], "province": sen["province"]}
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


def main():
    for p in (HISTORICO, AUTHORITIES):
        if not p.exists():
            sys.exit(f"Missing roster input: {p}")
    mandates = load_mandates()
    # Hand-compiled rows first: where both tables know a name, the curated
    # one wins, because it carries verified tenure bounds and a source.
    auth = load_authorities() + load_observed_authorities(mandates)
    print(f"{len(mandates)} mandate rows, {len(auth)} authority rows")

    corpus = pd.concat([pd.read_parquet(p) for p in sorted(BLOCKS_DIR.glob("*.parquet"))],
                       ignore_index=True)
    speech = corpus[corpus.type == "speech"]
    labels = (speech.groupby(["session_id", "session_date", "session_type", "speaker_raw"])
              .size().reset_index(name="n_blocks"))
    print(f"{len(labels)} (session, label) pairs across {labels.session_id.nunique()} sessions")

    out = []
    for _, r in labels.iterrows():
        d = date.fromisoformat(r.session_date)
        res = resolve_one(r.speaker_raw, d, r.session_type, mandates, auth)
        out.append({
            "session_id": r.session_id,
            "session_date": r.session_date,
            "speaker_raw": r.speaker_raw,
            "label_clean": clean_label(r.speaker_raw),
            "n_blocks": r.n_blocks,
            "person_id": res.get("person_id"),
            "person_name": res.get("person_name"),
            "role": res.get("role"),
            "party_or_alliance": res.get("party"),
            "province": res.get("province"),
            "match_status": res["match_status"],
        })

    df = pd.DataFrame(out)
    df.to_parquet(OUT_PATH, index=False)

    total = df.n_blocks.sum()
    print(f"\nResolution by speech blocks (total {total}):")
    print(df.groupby("match_status").n_blocks.sum().sort_values(ascending=False)
          .apply(lambda n: f"{n} ({n/total:.1%})").to_string())
    bad = df[df.match_status.isin(["unmatched", "ambiguous"])]
    print(f"\nTop unresolved labels ({len(bad)} label-sessions):")
    top = bad.groupby("label_clean").n_blocks.sum().sort_values(ascending=False).head(15)
    print(top.to_string())
    print(f"\nWritten: {OUT_PATH}")
    print("\nNote: party_or_alliance is the ticket each senator was ELECTED on,\n"
          "which is what the roster records. It is not the bloc they sat with —\n"
          "the two diverge sharply after 2015, when radicals were elected on\n"
          "Cambiemos and Juntos por el Cambio tickets. Do not read it as caucus\n"
          "membership; caucus is only published for sitting senators.")


if __name__ == "__main__":
    main()
