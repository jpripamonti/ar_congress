"""The caucus of a senator deduced from the chamber's official count per caucus.

WHY THIS EXISTS. For 1998-1999 some senators were never called by caucus,
never said theirs and appear on no archived page. The Chamber of Deputies'
count of the Senate per caucus on 1 March (see check_bloc_counts.py for the
document) gives no names, but where every other senator's caucus is known it
leaves room for only one answer. On 1 March 1999 the Fuerza Republicana
caucus had one senator, the corpus has none there, and the only senator in
office without a caucus who was elected for Fuerza Republicana is Almirón.

THE RULE. On a date the document covers, take every senator in office, give
each the caucus the corpus already attaches on that day from its own
readings (never from this file), and count. Where the document counts more
in a caucus than the corpus has, that shortfall is room; the senators the
corpus leaves without a caucus are the ones who can fill it. A senator is
placed only where:

  - they can go to exactly one caucus: one of the ticket they were elected
    on, with room for them. A caucus is matched to a ticket by name
    (JUSTICIALISTA to a Justicialista ticket, FZA REPUBLICANA to Fuerza
    Republicana); the one-senator "PCIA STA CRUZ-PJ" only to a Santa Cruz
    Peronist;
  - the room in that group of caucuses equals the number of senators who
    can fill it, so nobody else could be the one counted there;
  - the room across the whole chamber equals the number of senators without
    a caucus, so every one of them is accounted for.

Peronist caucuses are counted together. On 1 March 1999 the document has a
one-senator Santa Cruz caucus the corpus does not: it puts both Santa Cruz
Peronists in JUSTICIALISTA, from the chair's calls of June 1999. Counted
apart, JUSTICIALISTA would show five places for six Peronists without a
caucus, none from Santa Cruz. Counted together there are six places for six,
and since none of the six is from Santa Cruz, each can only be JUSTICIALISTA
— whichever of Varizat and Arnold sat apart.

What it depends on, stated plainly: that the document's counts are right,
and that the corpus's other assignments on that day are. check_bloc_counts.py
shows where the two agree and where they do not. A deduced caucus is marked
`bloc_status = "deduced"`, is used only for sittings within 200 days of the
count and inside the same mandate, and never where the corpus has a reading
of its own within 200 days.

    uv run scripts/deduce_bloc_from_counts.py

Run it after build_bloc_observations.py, then run that again to take it in.
Output: reference/senado/bloque_por_conteo.csv
"""

import collections
import contextlib
import csv
import io
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import resolve_speakers as R  # noqa: E402
from check_bloc_counts import OFFICIAL, fold, official_name  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT = REPO_ROOT / "reference" / "senado" / "bloque_por_conteo.csv"
SOURCE = ("https://www2.hcdn.gob.ar/export/hcdn/secparl/dgral_info_parlamentaria/"
          "dip/archivos/SenadoresporBloqueGenero-_Cantidades.pdf")
PAGE = {"1999-03-01": 8, "2000-03-01": 9, "2002-03-01": 10, "2004-03-01": 11}

# The document's caucus, the name the corpus uses for it, the ticket it can
# take a senator from, and the group it is counted in.
CAUCUS = {
    "JUSTICIALISTA": ("JUSTICIALISTA", "justicialista", "peronist"),
    "PCIA STA CRUZ-PJ": (None, "justicialista", "peronist"),
    "UCR": ("UCR - UNIÓN CÍVICA RADICAL", "union civica radical", "UCR"),
    "MOV POP FUEGUINO": ("MOVIMIENTO POPULAR FUEGUINO", "fueguino", "MPF"),
    "MOV POP NEUQUINO": ("MOVIMIENTO POPULAR NEUQUINO", "neuquino", "MPN"),
    "FZA REPUBLICANA": ("FUERZA REPUBLICANA", "fuerza republicana", "FR"),
}


def can_sit(caucus, ticket, province):
    known = CAUCUS.get(caucus)
    if known is None or known[1] not in fold(ticket):
        return False
    return caucus != "PCIA STA CRUZ-PJ" or fold(province) == "santa cruz"


def main():
    with contextlib.redirect_stdout(io.StringIO()):
        mandates = R.load_mandates()
        obs = R.load_bloc_observations()
        lives = R.load_bloc_lives()
    # the corpus's own readings only: never deduce from a deduction
    obs = {p: [r for r in rows if r[2] != "deduced"] for p, rows in obs.items()}
    terms = {}
    for m in mandates:
        terms.setdefault(m["person_id"], []).append((m["start"], m["end"]))
    rows = json.load(open(REPO_ROOT / "reference" / "senado" / "senadores_historico.json",
                          encoding="utf-8"))["table"]["rows"]
    names = {f"sen:{r['ID']}": r["SENADOR"] for r in rows}

    out = []
    for day, official in OFFICIAL.items():
        d = date.fromisoformat(day)
        seat = {m["person_id"]: m for m in mandates
                if m["start"] <= d and (m["end"] is None or d <= m["end"])}
        ours, loose = collections.Counter(), []
        for pid in seat:
            r = R.bloc_on(pid, d, obs, lives, terms.get(pid, ()))
            if r.get("bloc"):
                ours[official_name(r["bloc"])] += 1
            else:
                loose.append(pid)
        if not loose:
            continue
        room = {k: n - ours.get(k, 0) for k, n in official.items() if n > ours.get(k, 0)}
        print(f"\n{day}: {len(loose)} without a caucus, room in "
              + ", ".join(f"{k} {n}" for k, n in room.items()))
        if sum(room.values()) != len(loose):
            print("  refused: the room does not equal the senators without a caucus")
            continue
        fits = {pid: [k for k in room if can_sit(k, seat[pid]["party"], seat[pid]["province"])]
                for pid in loose}
        groups = collections.defaultdict(list)
        for k, n in room.items():
            groups[CAUCUS[k][2] if k in CAUCUS else k].append(k)
        for g, ks in groups.items():
            slots = sum(room[k] for k in ks)
            who = [pid for pid in loose if set(fits[pid]) & set(ks)]
            if slots != len(who):
                print(f"  {g}: {slots} places for {len(who)} senators — refused")
                continue
            for pid in who:
                mine = [k for k in fits[pid] if k in ks and CAUCUS[k][0]]
                if len(mine) != 1:
                    print(f"  {names.get(pid, pid)}: could sit in {fits[pid]} — refused")
                    continue
                k = mine[0]
                out.append({
                    "fecha": day,
                    "person_id": pid.removeprefix("sen:"),
                    "person_name": names.get(pid, pid),
                    "bloque": CAUCUS[k][0],
                    "bloque_en_el_documento": k,
                    "lugares": slots,
                    "candidatos": len(who),
                    "electo_por": seat[pid]["party"],
                    "url": f"{SOURCE}#page={PAGE[day]}",
                })
                print(f"  {names.get(pid, pid)} ({seat[pid]['party'].title()}): {k}"
                      f" — {slots} place(s) for {len(who)} senator(s)")

    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["fecha", "person_id", "person_name", "bloque",
                                           "bloque_en_el_documento", "lugares", "candidatos",
                                           "electo_por", "url"])
        w.writeheader()
        w.writerows(out)
    print(f"\n{len(out)} caucuses deduced. Written: {OUT}")


if __name__ == "__main__":
    main()
