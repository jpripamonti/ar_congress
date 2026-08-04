"""Turn the roll-call caucus readings into one row per senator per caucus spell.

fetch_blocs.py leaves 23,000 readings — one per senator per sitting date. This
collapses them into spells ("this senator sat with this caucus from here to
here") and files each caucus under the same coarse party families the analysis
already uses for electoral tickets, so the two can be compared like with like.

WHAT THIS IS AND IS NOT. The Senate records a caucus once per MANDATE, not per
sitting, so a spell here is at best mandate-grained: a senator who crossed the
floor mid-term shows one unbroken spell. Worse, the recorded caucus is sometimes
one the senator only joined later — 16 of the 18 senators filed under Frente de
Todos carry it back to 2016 or earlier, and that caucus was formed in 2019. So
the caucus NAME is trustworthy and the DATE is not. That is tolerable at family
level, where the usual error (Frente para la Victoria read as Frente de Todos)
stays inside the peronist family, and it is not tolerable for any claim about
WHEN the chamber realigned. Roll-call records begin in 2005; 2000-2004 gets
nothing here and must stay unlabelled rather than be filled in from the ticket.

Two family rules are added to the analysis's own, because they only bite on
caucus names and would otherwise put 27 senators in the residual bucket:

  FRENTE PRO ................ the PRO is the other half of Cambiemos/JxC; as an
                              electoral ticket it appeared as "Cambiemos", so
                              the existing keywords never had to name it.
  FRENTE NACIONAL Y POPULAR . the name the peronist bloc took after 2020.

The federal-peronist splinters (Unidad Federal, Convicción Federal, Cambio
Federal, Justicia Social Federal, Hay Futuro Argentina) are deliberately LEFT in
the residual bucket. They are peronist in origin but sat apart from the peronist
bloc on purpose, and the analysis's ticket-side rules leave their equivalents
there too — moving them would inflate the peronist share on the caucus side only
and make the very comparison this exists for meaningless.
"""

import argparse
import csv
import unicodedata
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
REF_DIR = REPO_ROOT / "reference" / "senado"
SRC = REF_DIR / "bloques_por_fecha.csv"
OUT = REF_DIR / "bloque_por_senador_periodo.csv"


def deaccent(s):
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if not unicodedata.combining(c))


def family(name):
    """Group a caucus into a party family. Coarse and auditable, by design.

    Order matters: era-specific coalition labels are tested before the parties
    that ran inside them, exactly as on the ticket side.
    """
    a = deaccent(str(name or "")).upper()
    if "LIBERTAD AVANZA" in a:
        return "La Libertad Avanza"
    if ("CAMBIEMOS" in a or "JUNTOS POR EL CAMBIO" in a or "CIVICA RADICAL" in a
            or "UCR" in a or "FRENTE PRO" in a):
        return "Radical / Cambiemos / JxC"
    if any(k in a for k in ("JUSTICIALIS", "PERONIS", "PARA LA VICTORIA",
                            "DE LA VICTORIA", "P/VICTORIA", "DE TODOS",
                            "UNIDAD CIUDADANA", "UNION POR LA PATRIA",
                            "NACIONAL Y POPULAR")):
        return "Peronist / Justicialist"
    return "Provincial & other alliances"


def spells(readings):
    """Collapse per-date readings into one row per unbroken run of one caucus."""
    out = []
    for senator, g in readings.sort_values("fecha").groupby("senador"):
        run_start = run_bloc = None
        last = None
        for fecha, bloc in g[["fecha", "bloque"]].itertuples(index=False):
            bloc = bloc if isinstance(bloc, str) and bloc.strip() else ""
            if bloc != run_bloc:
                if run_bloc:
                    out.append((senator, run_start, last, run_bloc))
                run_start, run_bloc = fecha, bloc
            last = fecha
        if run_bloc:
            out.append((senator, run_start, last, run_bloc))
    return out


def main():
    ap = argparse.ArgumentParser(
        description="Collapse roll-call caucus readings into per-senator spells.")
    ap.add_argument("--src", type=Path, default=SRC)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    readings = pd.read_csv(args.src)
    rows = [{
        "senador": s, "desde": a, "hasta": b, "bloque": c, "familia": family(c),
    } for s, a, b, c in spells(readings)]
    rows.sort(key=lambda r: (r["senador"], r["desde"]))

    with args.out.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    df = pd.DataFrame(rows)
    print(f"{len(rows)} caucus spells for {df.senador.nunique()} senators, "
          f"{df.bloque.nunique()} caucuses -> {args.out}")
    print(f"senators with more than one spell: "
          f"{(df.groupby('senador').size() > 1).sum()}")
    print("\nsenators per family (a senator can appear in more than one):")
    print(df.groupby("familia").senador.nunique().sort_values(ascending=False)
          .to_string())
    missing = readings.bloque.isna().sum()
    print(f"\nreadings with no caucus recorded: {missing} "
          f"({missing / len(readings):.1%})")


if __name__ == "__main__":
    main()
