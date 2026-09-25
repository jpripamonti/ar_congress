"""Check the caucuses the corpus assigns against the official counts per caucus.

The Chamber of Deputies' parliamentary information office publishes the
Senate's composition per caucus on 1 March of each renewal year, 1984-2024:

    "Composición del H. Senado por bloque y género", Dirección de Información
    Parlamentaria, HCDN, dated 5 February 2025, 27 pages.
    https://www2.hcdn.gob.ar/export/hcdn/secparl/dgral_info_parlamentaria/dip/archivos/SenadoresporBloqueGenero-_Cantidades.pdf

It gives counts, not names, so it cannot say which senator sat where. What it
can do is catch a wrong assignment: on each date the corpus should not put
more senators in a caucus than the chamber counted. The counts are copied
below by hand from pages 8-11 for the dates the corpus reaches.

For each date, every senator the roster has in office is given the caucus the
corpus would attach to a sitting on that day (the same `bloc_on` that
resolve_speakers.py uses), and the two counts are printed side by side, with
the names behind every caucus where they differ.

    uv run scripts/check_bloc_counts.py
"""

import argparse
import collections
import contextlib
import io
import json
import sys
import unicodedata
from datetime import date
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import resolve_speakers as R  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]

# The document's own caucus names and counts, verbatim.
OFFICIAL = {
    "1999-03-01": {"JUSTICIALISTA": 33, "UCR": 20, "MOV POP FUEGUINO": 2,
                   "MOV POP NEUQUINO": 2, "AUTONOMISTA": 1, "BLOQ SJ": 1,
                   "CRUZADA RENOV": 1, "FRENTE CIVICO Y SOCIAL DE CATAMARCA": 1,
                   "FREPASO": 1, "FZA REPUBLICANA": 1, "PCIA STA CRUZ-PJ": 1,
                   "RENOVADOR": 1},
    "2000-03-01": {"JUSTICIALISTA": 37, "UCR": 20, "MOV POP FUEGUINO": 2,
                   "MOV POP NEUQUINO": 2, "AUTONOMISTA": 1, "BLOQ SJ": 1,
                   "FRENTE CIVICO Y SOCIAL DE CATAMARCA": 1, "FREPASO": 1,
                   "PCIA STA CRUZ-PJ": 1, "RENOVADOR": 1},
    # includes Mera, sworn in on 5 March 2002 (the document's footnote 6)
    "2002-03-01": {"JUSTICIALISTA": 40, "UCR": 21,
                   "FRENTE CIVICO Y SOCIAL DE CATAMARCA": 2, "MOV POP NEUQUINO": 2,
                   "CRUZADA RENOV": 1, "FREPASO": 1, "FZA REPUBLICANA": 1,
                   "LIBERAL": 1, "RENOVADOR": 1},
    "2004-03-01": {"JUSTICIALISTA": 41, "UCR": 14, "FRENTE CIVICO JUJEÑO": 2,
                   "FRENTE CIVICO Y SOCIAL DE CATAMARCA": 2, "FREPASO": 2,
                   "FZA REPUBLICANA": 2, "MOV POP NEUQUINO": 2, "CRUZADA RENOV": 1,
                   "PARTIDO SOCIALISTA": 1, "RADICAL INDEPENDIENTE": 1,
                   "RADICAL RIONEGRINO": 1, "RENOVADOR": 1,
                   "VECINALISTA - PARTIDO NUEVO": 1},
}

# The corpus's caucus names, to the document's. First match wins. Frepaso's
# caucus appears on the archived roster pages as "Bloque Frente País
# Solidario" (what the acronym stands for) and later "Bloque Frente Grande";
# the document counts both as FREPASO.
ALIASES = [
    ("frente civico jujeno", "FRENTE CIVICO JUJEÑO"),
    ("frente civico y social", "FRENTE CIVICO Y SOCIAL DE CATAMARCA"),
    ("radical independiente", "RADICAL INDEPENDIENTE"),
    ("radical rionegrino", "RADICAL RIONEGRINO"),
    ("union civica radical", "UCR"), ("ucr", "UCR"),
    ("fueguino", "MOV POP FUEGUINO"), ("neuquino", "MOV POP NEUQUINO"),
    ("autonomista", "AUTONOMISTA"), ("bloquista", "BLOQ SJ"),
    ("cruzada", "CRUZADA RENOV"), ("fre.pa.so", "FREPASO"), ("frepaso", "FREPASO"),
    ("frente pais solidario", "FREPASO"), ("frente grande", "FREPASO"),
    ("fuerza republicana", "FZA REPUBLICANA"), ("liberal", "LIBERAL"),
    ("renovador de salta", "RENOVADOR"), ("socialista", "PARTIDO SOCIALISTA"),
    ("vecinalista", "VECINALISTA - PARTIDO NUEVO"),
    ("justicialista", "JUSTICIALISTA"),
]


def fold(s):
    s = unicodedata.normalize("NFD", str(s).lower())
    return " ".join("".join(c for c in s if not unicodedata.combining(c)).split())


def official_name(bloc):
    k = fold(bloc)
    return next((v for pat, v in ALIASES if pat in k), bloc)


def main():
    with contextlib.redirect_stdout(io.StringIO()):
        mandates = R.load_mandates()
        obs = R.load_bloc_observations()
        lives = R.load_bloc_lives()
    terms = {}
    for m in mandates:
        terms.setdefault(m["person_id"], []).append((m["start"], m["end"]))
    rows = json.load(open(REPO_ROOT / "reference" / "senado" / "senadores_historico.json",
                          encoding="utf-8"))["table"]["rows"]
    names = {f"sen:{r['ID']}": f"{r['SENADOR']} ({r['PROVINCIA'].title()})" for r in rows}

    for day, official in OFFICIAL.items():
        d = date.fromisoformat(day)
        sitting = sorted(pid for pid, ts in terms.items()
                         if any(a <= d and (b is None or d <= b) for a, b in ts))
        ours, who, none = collections.Counter(), collections.defaultdict(list), []
        for pid in sitting:
            r = R.bloc_on(pid, d, obs, lives, terms.get(pid, ()))
            if not r.get("bloc"):
                none.append(names.get(pid, pid))
                continue
            k = official_name(r["bloc"])
            ours[k] += 1
            who[k].append(f"{names.get(pid, pid)}: {r['bloc_basis']} "
                          f"{r['bloc_observed']}, {r['bloc_status']}")
        print(f"\n{day}: the document counts {sum(official.values())}, the roster has "
              f"{len(sitting)} in office, {len(none)} without a caucus in the corpus")
        for k in sorted(set(official) | set(ours), key=lambda k: -official.get(k, 0)):
            a, b = official.get(k, 0), ours.get(k, 0)
            mark = "" if a == b else ("   corpus has MORE" if b > a else "   corpus has fewer")
            print(f"  {k[:38]:38s} {a:4d} {b:6d}{mark}")
            if b > a:
                for w in who[k]:
                    print(f"      {w}")
        if none:
            print("  without a caucus: " + "; ".join(none))


if __name__ == "__main__":
    # no options, but --help must describe the script, not run it
    argparse.ArgumentParser(description=__doc__.strip().split("\n\n")[0]).parse_args()
    main()
