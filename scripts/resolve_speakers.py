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
         (session_id, speaker_raw) with person_id, name, party, province,
         role, match_status — plus a printed resolution summary.
"""

import difflib
import json
import re
import sys
import unicodedata
from datetime import date
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
BLOCKS_DIR = REPO_ROOT / "data" / "processed" / "senado" / "blocks"
HISTORICO = REPO_ROOT / "reference" / "senado" / "senadores_historico.json"
AUTHORITIES = REPO_ROOT / "reference" / "senado" / "authorities_manual.csv"
OUT_PATH = REPO_ROOT / "data" / "processed" / "senado" / "speakers.parquet"

ROLE_WORDS = re.compile(
    r"presidenta?|vicepresidenta?|secretari[oa]|prosecretari[oa]|jefe de gabinete|ministr[oa]",
    re.I,
)
TITLE_RE = r"(?:Sr|Sra|Srta|Sres)\.?"


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
    s = re.sub(r"\.\-.*$", "", s)          # ".-" terminator + speech spillover ("Sr. Mayans.- ¡")
    s = re.sub(r"[.\-:…\s]+$", "", s).strip()
    s = re.sub(r"^((?:Sr|Sra|Srta|Sres)\.)(?=\S)", r"\1 ", s)  # "Sra.Presidenta" -> spaced (dot required, no backtracking)
    s = re.sub(r"\(\s*", "(", s)
    if "(" in s and ")" not in s:
        s += ")"                                            # "…(Abdala" -> closed
    return re.sub(r"\s+", " ", s)


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


def role_stem(s):
    """Canonical role key: presidente/presidenta -> presidencia, jefe -> jefatura, ..."""
    s = norm(s)
    s = re.sub(r"\bvicepresident[ea]\b", "vicepresidencia", s)
    s = re.sub(r"\bpresident[ea]\b", "presidencia", s)
    s = re.sub(r"\bjefe\b", "jefatura", s)
    s = re.sub(r"\bsecretari[oa]\b", "secretaria", s)
    s = re.sub(r"\bprosecretari[oa]\b", "prosecretaria", s)
    return s


def in_window(rec, d, grace_days=0):
    """Missing start/end = open bound; grace admits 'electo/a' pre-mandate labels."""
    start_ok = rec["start"] is None or rec["start"].toordinal() - grace_days <= d.toordinal()
    return start_ok and (rec["end"] is None or d <= rec["end"])


def match_senators(mandates, surname_key, d, given_key=None, grace_days=0, fuzzy=False):
    cands = [m for m in mandates if m["surname_key"] == surname_key and in_window(m, d, grace_days)]
    if not cands:
        # prefix fallback: label "Ledesma Abdala" vs roster "LEDESMA ABDALA DE ZAMORA"
        cands = [m for m in mandates if in_window(m, d, grace_days)
                 and (m["surname_key"].startswith(surname_key + " ")
                      or surname_key.startswith(m["surname_key"] + " "))]
    if not cands and fuzzy:
        # last resort for stenographic typos: Parrili, Di Tulio, Schiavone, ...
        pool = {m["surname_key"] for m in mandates if in_window(m, d, grace_days)}
        close = difflib.get_close_matches(surname_key, pool, n=2, cutoff=0.86)
        if len(close) == 1:
            cands = [m for m in mandates if m["surname_key"] == close[0] and in_window(m, d, grace_days)]
    if given_key and len(cands) > 1:
        gtok = set(given_key.split())
        cands = [m for m in cands if gtok & set(m["given_key"].split())]
    # collapse duplicate mandate rows for the same person (re-elections)
    return list({m["person_id"]: m for m in cands}.values())


def match_authorities(auth, key, d, role_hint=None):
    hits = [a for a in auth if key in a["keys"] and in_window(a, d)]
    if role_hint:
        stem = role_stem(role_hint)
        pref = [a for a in hits if stem[:12] in a["role_stem"] or a["role_stem"][:12] in stem]
        if pref:
            hits = pref
    return hits


def resolve_one(label, session_date, session_type, mandates, auth):
    d = session_date
    s = clean_label(label)

    if re.match(r"^(Varios|Varias|Un |Una )", s, re.I) or "no identificado" in norm(s):
        return {"match_status": "collective", "role": "collective"}

    m = re.match(rf"^{TITLE_RE}\s+(?P<pre>[^(]*?)\s*\((?P<paren>[^)]+)\)$", s)
    if m and ROLE_WORDS.search(m["pre"]):
        # chair/officer: authorities first, then senators presiding
        key = norm(m["paren"].strip(" ."))       # "(Losada.)" -> losada
        hits = match_authorities(auth, key, d, role_hint=m["pre"])
        if hits:
            a = hits[0]
            return {"match_status": "matched_authority", "person_id": a["person_id"],
                    "person_name": a["name"], "role": m["pre"].strip() or a["role"]}
        sens = match_senators(mandates, key, d)
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
        if stem == "presidencia":
            # The chamber's chair, named by office alone. Whoever is in the
            # chair changes during a sitting, and the page does not say who
            # it is, so no person is assigned: the office is all the source
            # states. (A national office — "Presidente de la Nación", "Jefe
            # de Gabinete" — has one holder on a date and resolves below.)
            return {"match_status": "office_only", "role": role}
        grace = 300 if elect else 0     # "electo/a" labels precede the mandate
        hits = [a for a in auth if in_window(a, d, grace)
                and (stem in a["role_stem"] or a["role_stem"] in stem)]
        exact = [a for a in hits if a["role_stem"] == stem]
        pick = exact or hits
        if len(pick) == 1:
            a = pick[0]
            return {"match_status": "matched_authority", "person_id": a["person_id"],
                    "person_name": a["name"], "role": role}
        return {"match_status": "ambiguous" if pick else "unmatched", "role": role}

    if re.match(rf"^{TITLE_RE}\s+Diputad", s):
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
        return {"match_status": "ambiguous" if sens else "unmatched"}

    return {"match_status": "unmatched"}


def main():
    for p in (HISTORICO, AUTHORITIES):
        if not p.exists():
            sys.exit(f"Missing roster input: {p}")
    mandates = load_mandates()
    auth = load_authorities()
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
            "party": res.get("party"),
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


if __name__ == "__main__":
    main()
