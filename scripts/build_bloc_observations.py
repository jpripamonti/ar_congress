"""One row per day the chamber's composition was actually recorded.

This is the source of truth for "which caucus did this senator sit with on this
day". It does not interpolate, and it does not collapse anything into spells:
each row is a single observation, on a single date, with the record it came
from. Everything downstream picks the observation nearest the sitting it cares
about and can see how far away that was.

TWO SOURCES, and they are not equally precise.

  Roll-call records, 2005 onward. Every recorded vote publishes the whole
  chamber, absentees included, with the caucus beside each name, so one record
  per sitting date is a complete snapshot of that day. Collected by
  fetch_blocs.py into bloques_por_fecha.csv.

  Archived roster pages, 2000-2004. The Senate ran a page listing every senator
  under their caucus. It is long dead, but the Internet Archive holds sixteen
  captures spanning 25 May 2000 to 19 Jun 2004, which is the whole span the
  roll-call records do not reach. A capture says what the page said on the day
  it was captured, which is not the same as the day the chamber changed: the
  page lags, and twice in 1,112 rows it is provably stale — a senator listed four
  days after his term ended, another a month before his began. Bracketing a
  change between two captures is sound; dating it to the day is not.

WHAT bloque_observado.csv's fiabilidad COLUMN MEANS. The Senate re-labels old
roll calls with the caucus a senator joined later: Frente de Todos, formed in
December 2019, is stamped on votes back to 2010. Every reading is therefore
checked against the caucus's own dated life in blocs_manual.csv, and one of:

  acta ................. the caucus existed on the day of the vote
  acta_anacronica ...... it did not — the name postdates (or predates) the vote
  acta_sin_control ..... the caucus has no dated start, so nothing can be checked
  foto ................. from an archived roster page
  foto_bloque_previo ... likewise, but a caucus that died before the roll-call
                         records begin, so it has no entry in blocs_manual.csv
  llamado .............. named by the chair giving the floor, in the transcript

Nothing is deleted or corrected. A reading known to be misdated is more useful
marked than removed, because removing it would hide how much of the Senate's
own record is like this.

  Archived per-senator pages, 2 February 1998. The same site ran one page per
  senator, each stating "Bloque: ..." in so many words, and the Archive holds
  58 of them from three weeks before the first sitting in this corpus — the
  only record of the chamber's caucuses before May 2000. Read exactly like the
  roster page, and marked apart from it by source.

  The chair's call, 1998 to February 2000. Giving the floor, the chair of
  those years often named the caucus of the senator it called: "Tiene la
  palabra el señor senador por Mendoza del bloque de la Unión Cívica
  Radical." extract_chair_caucus.py keeps a call only where the province
  named is the speaker's own. Where a call and an archived page are within
  200 days of each other they agree in all 66 cases. Dated to the sitting,
  and the only source for August 1998 to May 2000.

Inputs:  reference/senado/bloques_por_fecha.csv     (fetch_blocs.py)
         reference/senado/bloque_por_foto.csv       (fetch_archived_blocs.py)
         reference/senado/bloque_por_ficha.csv      (fetch_archived_profiles.py)
         reference/senado/bloque_por_llamado.csv    (extract_chair_caucus.py)
         reference/senado/blocs_manual.csv          (hand-dated caucus lives)
         reference/senado/senadores_historico.json  (the roster)
Output:  reference/senado/bloque_observado.csv
"""

import json
import re
import sys
import unicodedata
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from map_blocs import family  # noqa: E402  — one definition of the families

REPO_ROOT = Path(__file__).resolve().parents[1]
REF = REPO_ROOT / "reference" / "senado"
ROLLCALL = REF / "bloques_por_fecha.csv"
SNAPSHOTS = REF / "bloque_por_foto.csv"
PROFILES = REF / "bloque_por_ficha.csv"
CHAIR_CALLS = REF / "bloque_por_llamado.csv"
LIVES = REF / "blocs_manual.csv"
HISTORICO = REF / "senadores_historico.json"
OUT = REF / "bloque_observado.csv"

# The Senate's own placeholder for "no caucus recorded". Not the name of
# anything, so it is dropped rather than carried as if it were a caucus.
PLACEHOLDER = "SIN ESPECIFICAR"

# The archived pages write a caucus's name shorter than the roll-call records
# later do. Where the two are the same string once case, accents, punctuation
# and a leading "Bloque" are set aside, they are matched automatically. These
# five are not, and are a judgement that the shorter printed name is the same
# caucus — recorded here rather than buried in a normalisation rule.
SAME_CAUCUS = {
    "RENOVADOR DE SALTA": "PARTIDO RENOVADOR DE SALTA",
    "FTE CIV Y SOCIAL DE CATAMARCA": "FRENTE CÍVICO Y SOCIAL DE CATAMARCA",
    "UNION CIVICA RADICAL": "UCR - UNIÓN CÍVICA RADICAL",
    "LIBERAL DE CORRIENTES": "PARTIDO LIBERAL DE CORRIENTES",
    # a single Santa Cruz senator, filed under the province's own name for the
    # national party he sat with
    "PROVINCIA DE SANTA CRUZ PARTIDO JUSTICIALISTA": "JUSTICIALISTA",
}


def norm(s):
    s = unicodedata.normalize("NFKD", str(s))
    return " ".join("".join(c for c in s if not unicodedata.combining(c)).upper().split())


def load_people():
    """The roster, with each mandate's real dates, for resolving printed names."""
    rows = json.load(open(HISTORICO, encoding="utf-8"))["table"]["rows"]
    p = pd.DataFrame(rows)
    p["ini"] = pd.to_datetime(p["INICIO PERIODO REAL"], errors="coerce")
    p["fin"] = pd.to_datetime(p["CESE PERIODO REAL"], errors="coerce")
    p["fin"] = p.fin.fillna(pd.Timestamp("2100-01-01"))
    p = p[p.ini.notna()].copy()
    p["full"] = p.SENADOR.map(norm)
    p["ape"] = p.SENADOR.str.split(",").str[0].map(norm)
    p["nom"] = p.SENADOR.str.split(",").str[1].fillna("").map(norm)
    return p


def resolve_person(printed, when, roster):
    """Who the archived page meant, decided by name and by who was in office.

    The pages and the roster do not always spell a name the same way: a senator
    under her maiden name on one and her married name on the other, a hyphen
    present in one and not the other, half a compound surname. So an exact match
    is tried first, then surname-token overlap with a shared given name, and
    both are tried against the senators actually in office on the capture date
    before falling back to the whole roster. Several rows of one person are one
    person: the roster holds one per mandate.
    """
    # a hyphen in a compound surname is present on one side and not the other
    # ("MIKKELSEN LÖTH" against "MIKKELSEN-LÖTH"), so it splits like a space
    def parts(s):
        return set(norm(s).replace("-", " ").split())

    full = norm(printed)
    ape, nom = printed.split(",")[0], (printed.split(",")[1] if "," in printed else "")
    serving = roster[(roster.ini <= when) & (roster.fin >= when)]
    for pool, how in ((serving, "in office"), (roster, "any date")):
        hit = pool[pool.full == full]
        if len(hit) == 1:
            return hit.iloc[0], f"exact name, {how}"
        want_ape, want_nom = parts(ape), parts(nom)
        c = pool[pool.ape.map(lambda x: bool(want_ape & parts(x)))]
        if want_nom:
            c = c[c.nom.map(lambda x: bool(want_nom & parts(x))).astype(bool)]
        if len(c) and c.ID.nunique() == 1:
            return c.assign(_d=(c.ini - when).abs()).sort_values("_d").iloc[0], \
                f"surname and given name, {how}"
    return None, None


def load_lives():
    """When each caucus is known to have existed, life by life.

    A caucus can have lived more than once: Unidad Ciudadana sat from 2017 to
    2019, was absorbed into the Frente de Todos bloc, and formed again when that
    bloc split in May 2022. Folding the two into one span running from the first
    start to the last close makes the whole second life impossible, which is how
    163 readings of it — including the sitting that attests the caucus — came to
    be marked as naming a caucus that did not exist. map_blocs.py keeps the
    lives apart already; this now does too.
    """
    b = pd.read_csv(LIVES)
    standing = set(b[b.basis == "standing bloc"].bloc)
    lives = {}
    for bloc, first, last in zip(b.bloc, b.period_start, b.period_end):
        lives.setdefault(bloc, []).append(
            (None if pd.isna(first) else first, None if pd.isna(last) else last))
    undated = {bloc for bloc, spans in lives.items()
               if all(first is None for first, _ in spans)} - standing
    return lives, undated


def was_alive(bloc, day, lives):
    """Was the caucus alive that day, by any one of the lives it is known to have had?

    A caucus nobody has dated cannot be contradicted, and neither can a life
    left open at one end; both count as alive.
    """
    spans = lives.get(bloc)
    if spans is None:
        return True
    return any((first is None or day >= first) and (last is None or day <= last)
               for first, last in spans)


def from_rollcalls(roster, lives, undated):
    people = {n: (i, s) for n, i, s in zip(roster.full, roster.ID, roster.SENADOR)}
    r = pd.read_csv(ROLLCALL)
    r = r[r.bloque.notna() & (r.bloque.str.strip() != "")
          & (r.bloque != PLACEHOLDER)].copy()

    def status(row):
        b, f = row.bloque, row.fecha
        if not was_alive(b, f, lives):
            return "acta_anacronica"
        return "acta_sin_control" if b in undated else "acta"

    key = r.senador.map(norm)
    return pd.DataFrame({
        "fecha": r.fecha,
        "person_id": key.map(lambda k: people[k][0]),
        "person_name": key.map(lambda k: people[k][1]),
        "bloque": r.bloque,
        "fiabilidad": r.apply(status, axis=1),
        "fuente": "acta de votacion",
        "procedencia": "https://www.senado.gob.ar/votaciones/detalleActa/"
                       + r.acta_id.astype(str),
    })


def canonical_bloc(printed, known):
    """The name blocs_manual.csv uses for this caucus, or '' if it has none.

    A caucus that died before 2005 never reaches the roll-call records and so
    has no entry there. Those keep the name the page printed.
    """
    k = re.sub(r"^BLOQUE\s+", "", norm(printed).replace(".", " ").replace("-", " "))
    k = " ".join(k.split())
    return known.get(k) or SAME_CAUCUS.get(k, "")


def from_snapshots(people):
    if not SNAPSHOTS.exists():
        print(f"  {SNAPSHOTS.name} missing — no pre-2005 observations")
        return pd.DataFrame()
    s = pd.read_csv(SNAPSHOTS)
    known = {}
    for b in pd.read_csv(LIVES).bloc.dropna().unique():
        k = re.sub(r"^BLOQUE\s+", "", norm(b).replace(".", " ").replace("-", " "))
        known[" ".join(k.split())] = b
    canon = s.bloque_impreso.map(lambda p: canonical_bloc(p, known))
    unknown = sorted(set(s.bloque_impreso[canon == ""]))
    if unknown:
        print(f"  {len(unknown)} caucuses with no entry in {LIVES.name}, kept as "
              f"printed (they died before the roll-call records begin):")
        for u in unknown:
            print(f"      {u}")
    ids, names, unresolved, rules = [], [], [], []
    for printed, when in zip(s.senador_impreso, pd.to_datetime(s.snapshot_date)):
        hit, how = resolve_person(printed, when, people)
        if hit is None:
            unresolved.append(printed)
            ids.append(None); names.append(printed); continue
        ids.append(hit.ID); names.append(hit.SENADOR); rules.append(how)
        if not (hit.ini <= when <= hit.fin):
            print(f"  {when:%Y-%m-%d}: the page still lists {hit.SENADOR}, whose "
                  f"mandate ran {hit.ini:%Y-%m-%d} to {hit.fin:%Y-%m-%d} — the page "
                  f"lagged the chamber, kept as printed")
    if unresolved:
        sys.exit(f"{len(unresolved)} printed names match nobody: {unresolved[:6]}")
    print("  names resolved by: " + ", ".join(
        f"{v} {k}" for k, v in pd.Series(rules).value_counts().items()))
    return pd.DataFrame({
        "fecha": s.snapshot_date,
        "person_id": ids,
        "person_name": names,
        "bloque": [c or p for c, p in zip(canon, s.bloque_impreso)],
        "fiabilidad": ["foto" if c else "foto_bloque_previo" for c in canon],
        "fuente": "foto de la pagina de bloques",
        "procedencia": s.snapshot_url,
    })


def resolve_given_first(printed, when, roster):
    """Who a per-senator page meant. It prints "AUGUSTO ALASINO", given names
    first and no comma, so where the surname starts is not written down; a
    senator in office that day whose surname AND given names both meet the
    printed words is taken, and only if exactly one does."""
    def parts(x):
        return set(norm(x).replace("-", " ").replace(",", " ").split())
    words = parts(printed)
    seq = norm(printed).replace("-", " ").split()

    def ends_with_surname(ape):
        # the page puts the surname last, so "EDUARDO PEDRO VACA" is Vaca and
        # not De Pedro, Eduardo Enrique, whose names share two of its words
        tail = norm(ape).replace("-", " ").split()
        return len(tail) < len(seq) and seq[-len(tail):] == tail

    serving = roster[(roster.ini <= when) & (roster.fin >= when)]
    for pool, how in ((serving, "in office"), (roster, "any date")):
        c = pool[pool.ape.map(lambda a: bool(parts(a) & words))
                 & pool.nom.map(lambda n: bool(parts(n) & words))]
        if c.ID.nunique() > 1:
            c = c[c.ape.map(ends_with_surname)]
        if c.ID.nunique() == 1:
            return (c.assign(_d=(c.ini - when).abs()).sort_values("_d").iloc[0],
                    f"surname and given name, {how}")
    return None, None


def from_profiles(people, spelled):
    """The 2 February 1998 per-senator pages, one observation per page."""
    if not PROFILES.exists():
        print(f"  {PROFILES.name} missing — no observations before May 2000")
        return pd.DataFrame()
    s = pd.read_csv(PROFILES)
    known = {}
    for b in pd.read_csv(LIVES).bloc.dropna().unique():
        k = re.sub(r"^BLOQUE\s+", "", norm(b).replace(".", " ").replace("-", " "))
        known[" ".join(k.split())] = b
    canon = s.bloque_impreso.map(lambda p: canonical_bloc(p, known))
    ids, names, rules = [], [], []
    for printed, when in zip(s.senador_impreso, pd.to_datetime(s.capture_date)):
        hit, how = resolve_given_first(printed, when, people)
        if hit is None:
            sys.exit(f"a per-senator page matches nobody in the roster: {printed!r}")
        ids.append(hit.ID); names.append(hit.SENADOR); rules.append(how)
        if not (hit.ini <= when <= hit.fin):
            print(f"  {when:%Y-%m-%d}: a per-senator page still lists {hit.SENADOR}, "
                  f"whose mandate ran {hit.ini:%Y-%m-%d} to {hit.fin:%Y-%m-%d} — the "
                  f"page lagged the chamber, kept as printed")
    print("  per-senator pages resolved by: " + ", ".join(
        f"{v} {k}" for k, v in pd.Series(rules).value_counts().items()))
    # a caucus with no dated life keeps its printed name, in the spelling the
    # roster page already gave it where it gave one, so the same caucus is not
    # two strings that differ only in capitals
    bloque = [c or spelled.get(norm(p), p) for c, p in zip(canon, s.bloque_impreso)]
    return pd.DataFrame({
        "fecha": s.capture_date,
        "person_id": ids,
        "person_name": names,
        "bloque": bloque,
        "fiabilidad": ["foto" if c else "foto_bloque_previo" for c in canon],
        "fuente": "ficha del senador",
        "procedencia": s.capture_url,
    })


def from_chair_calls():
    """The caucus the chair named when giving the floor, 1998-2000.

    Already resolved to a person by extract_chair_caucus.py, from surname,
    province and date together, so nothing is looked up here. procedencia is
    the transcript's address on the Senate's site; the chair's exact words are
    in bloque_por_llamado.csv beside it.
    """
    if not CHAIR_CALLS.exists():
        print(f"  {CHAIR_CALLS.name} missing — no chair-call observations")
        return pd.DataFrame()
    c = pd.read_csv(CHAIR_CALLS, dtype={"person_id": str})
    return pd.DataFrame({
        "fecha": c.fecha,
        "person_id": c.person_id,
        "person_name": c.person_name,
        "bloque": c.bloque,
        "fiabilidad": "llamado",
        "fuente": "llamado de la presidencia",
        "procedencia": c.url,
    })


def main():
    people = load_people()
    lives, undated = load_lives()
    snaps = from_snapshots(people)
    spelled = {norm(b): b for b in snaps.bloque} if len(snaps) else {}
    parts = [from_rollcalls(people, lives, undated), snaps,
             from_profiles(people, spelled), from_chair_calls()]
    o = pd.concat([p for p in parts if len(p)], ignore_index=True)
    o["familia"] = o.bloque.map(family)
    o = o.sort_values(["fecha", "person_name"]).reset_index(drop=True)

    missing = o[o.person_id.isna()]
    if len(missing):
        sys.exit(f"{len(missing)} observations name someone not in the roster:\n"
                 f"{missing.person_name.unique()[:10]}")
    o.to_csv(OUT, index=False)

    print(f"{len(o):,} observations, {o.person_id.nunique()} senators, "
          f"{o.fecha.nunique()} dates, {o.fecha.min()} to {o.fecha.max()}")
    print("\nby source and how far it can be trusted:")
    print(o.groupby(["fuente", "fiabilidad"]).size().to_string())
    bad = (o.fiabilidad == "acta_anacronica").sum()
    print(f"\nreadings naming a caucus that did not exist that day: {bad:,} "
          f"({bad/len(o):.1%}) — kept and marked, not corrected")
    print(f"\nWritten: {OUT}")


if __name__ == "__main__":
    main()
