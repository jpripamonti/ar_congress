"""Read the caucus the chair names when it gives a senator the floor, 1998-2000.

WHY THIS EXISTS. Between August 1998 and May 2000 no record of the chamber's
caucuses survives outside the transcripts: the Senate's bloc-roster page was
first captured by the Internet Archive on 25 May 2000, and its per-senator
pages last on 2 February 1998 (fetch_archived_profiles.py). But the chair of
those years often named the caucus of the senator it called:

    Tiene la palabra el señor senador por Mendoza del bloque de la Unión
    Cívica Radical.
    Sr. GENOUD.- Señor presidente: ...

That is the chamber's own record, dated to the sitting, and it is read here.

THE CHAIR CAN CALL ONE SENATOR AND ANOTHER SPEAK. So a call counts only when
the province the chair names is the province of the senator whose label
follows, and the senator is identified by surname, province and date
together. Four calls fail that test (the chair names Entre Ríos and Maglietti
of Formosa speaks; La Pampa and Pardo of Corrientes; Corrientes and Meneghini,
whom the roster seats for Santiago del Estero; La Rioja and Vaquir) and are
reported, never used.

THE CHAIR DOES NOT ALWAYS SAY "BLOQUE". It says "del bloque de la Unión
Cívica Radical" and, of the same senator a week later, "de la Unión Cívica
Radical" or "del Partido Cruzada Renovadora"; it puts a comma before the
caucus or not; once it says "ha pedido la palabra" instead of "tiene". The
first version of this script read only "del bloque ..." with no comma, and
kept 153 calls. Reading the other forms adds 158, and before they were
trusted each was checked against every other reading of the same senator
within a year (archived pages, floor statements, the calls already kept):
153 agree, none disagrees, 5 have nothing to compare with. A party name is
read as its caucus only through the table below, which is what makes this
safe: Villarroel belonged to the Radical party and sat in the Frente Cívico
y Social caucus (he says so, 3 November 1999), and no call ever names him by
the party.

WHAT A CALL NAMES IS NOT ALWAYS A CAUCUS. The chair speaks loosely: "bloque
radical" and "bloque de la Unión Cívica Radical" are one caucus, and each
spelling is mapped below, by hand, to the name the rest of the caucus data
uses — only in the province where that caucus sat, so a name is never carried
to a senator of another province. "Bloque de la Alianza" and "aliancista" are
NOT mapped: the Alianza was the coalition of the Unión Cívica Radical and
Frepaso, which sat as separate caucuses (the roster page of May 2000 lists
them apart), so the words do not say which one a senator sat with. Anything
not in the table is reported and left out.

Scope: HTML transcripts dated before 25 May 2000, where no other source
reaches. Every row carries the transcript's file, its address on the Senate's
site, and the chair's words verbatim, so it can be checked against the page.

    uv run scripts/extract_chair_caucus.py

Output: reference/senado/bloque_por_llamado.csv
"""

import argparse
import csv
import json
import re
import sys
import unicodedata
from collections import Counter
from html import unescape
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from provenance import decode_html, require_sources, source_url  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
RAW = REPO_ROOT / "data" / "raw" / "senado" / "taquigraficas"
HISTORICO = REPO_ROOT / "reference" / "senado" / "senadores_historico.json"
OUT = REPO_ROOT / "reference" / "senado" / "bloque_por_llamado.csv"
# the roster page takes over from its first capture
UNTIL = "2000-05-25"

TAG = re.compile(r"<[^>]+>")
# The provinces spelt out, so "Santiago del Estero" is never read as the
# province "Santiago" and the caucus "Estero".
PROVINCE = (r"(?:la provincia del? |el |la )?(?:Buenos Aires|la Capital(?: Federal)?|"
            r"Capital(?: Federal)?|(?i:la ciudad(?: autónoma)? de buenos aires)|Catamarca|"
            r"C[óo]rdoba|Corrientes|Chaco|Chubut|Entre R[íi]os|Formosa|Jujuy|La Pampa|"
            r"La Rioja|Mendoza|Misiones|Neuqu[ée]n|R[íi]o Negro|Salta|San Juan|San Luis|"
            r"Santa Cruz|Santa Fe|Santiago del Estero|Tierra del Fuego|Tucum[áa]n)")
CALL = re.compile(
    r"(?P<call>(?:Tiene|ha pedido) la palabra (?:el|la) se[ñn]ora? senador(?:a)? por "
    r"(?P<prov>" + PROVINCE + r")"
    r"(?:,?\s+(?:y\s+)?(?P<pres>president[ea]))?"
    r",?\s+(?:del?|perteneciente al?) (?P<bloc>[^.]{1,90}?)\.)"
    r"\s*(?P<label>Sra?\.?\s*[A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ' ]{1,40}?)\s*\.?\s*[-–—]")

# What the chair calls a province, against the roster's name for it.
PROVINCE_ALIASES = {
    "la capital": "ciudad autonoma de buenos aires",
    "capital": "ciudad autonoma de buenos aires",
    "capital federal": "ciudad autonoma de buenos aires",
    "la capital federal": "ciudad autonoma de buenos aires",
    "la ciudad de buenos aires": "ciudad autonoma de buenos aires",
    "la ciudad autonoma de buenos aires": "ciudad autonoma de buenos aires",
}

# The chair's spellings of a caucus, the name the caucus data already uses for
# it, and the provinces it sat for. A judgement, recorded here rather than
# buried in a normalisation rule; None means a province does not narrow it.
CAUCUS = {
    "union civica radical": ("UCR - UNIÓN CÍVICA RADICAL", None),
    "radical": ("UCR - UNIÓN CÍVICA RADICAL", None),
    "justicialista": ("JUSTICIALISTA", None),
    "partido justicialista": ("JUSTICIALISTA", None),
    "autonomista": ("Autonomista", {"corrientes"}),
    "partido autonomista": ("Autonomista", {"corrientes"}),
    "liberal": ("Liberal", {"corrientes"}),
    "partido liberal": ("Liberal", {"corrientes"}),
    "cruzada renovadora": ("Cruzada Renovadora De San Juan", {"san juan"}),
    "partido cruzada renovadora": ("Cruzada Renovadora De San Juan", {"san juan"}),
    "bloquista": ("Bloquista De La Provincia De San Juan", {"san juan"}),
    "partido bloquista": ("Bloquista De La Provincia De San Juan", {"san juan"}),
    "partido renovador": ("PARTIDO RENOVADOR DE SALTA", {"salta"}),
    "frente civico": ("FRENTE CÍVICO Y SOCIAL DE CATAMARCA", {"catamarca"}),
    "frente civico y social": ("FRENTE CÍVICO Y SOCIAL DE CATAMARCA", {"catamarca"}),
    # Frepaso sat as a caucus of its own, apart from the Radicals it was in
    # coalition with; both archived pages list it, spelt "Fre.Pa.So"
    "frepaso": ("Fre.Pa.So", None),
}
# Named, and deliberately not read as a caucus: see the docstring.
COALITION = {"alianza", "aliancista", "la alianza"}


def fold(s):
    s = unicodedata.normalize("NFD", str(s).lower())
    return " ".join("".join(c for c in s if not unicodedata.combining(c)).split())


def bloc_key(printed):
    """'bloque de la Unión Cívica Radical, quien también dispone…' -> 'union civica radical'."""
    k = fold(printed.split(",")[0])
    k = re.sub(r"^(?:la\s+)?(?:bloque|bancada)\s+", "", k)
    k = re.sub(r"^(?:de la|del|de los|de|la)\s+", "", k)
    return k.strip()


def province_key(printed):
    p = fold(printed)
    p = PROVINCE_ALIASES.get(p, p)
    return re.sub(r"^(?:la provincia de|la provincia del|el|la)\s+", "", p)


def load_roster():
    rows = json.load(open(HISTORICO, encoding="utf-8"))["table"]["rows"]
    out = []
    for r in rows:
        ini = r.get("INICIO PERIODO REAL") or ""
        if not ini:
            continue
        out.append({"id": r["ID"], "name": r["SENADOR"],
                    "surname": fold(r["SENADOR"].split(",")[0]),
                    "province": fold(r["PROVINCIA"]),
                    "ini": ini, "fin": r.get("CESE PERIODO REAL") or "2100-01-01"})
    return out


def who(label, province, date, roster):
    """The one senator in office that day with this surname, for this province."""
    printed = fold(label)
    hits = {r["id"]: r for r in roster
            if r["ini"] <= date <= r["fin"]
            and (r["surname"] == printed or r["surname"].split()[-1] == printed.split()[-1])
            and (province in r["province"] or r["province"].endswith(province))}
    return next(iter(hits.values())) if len(hits) == 1 else None


def main():
    require_sources(RAW, formats=("html",), until=UNTIL)
    roster = load_roster()
    kept, refused = [], Counter()
    notes = []
    for f in sorted(RAW.glob("*.html")):
        date = f.name[:10]
        if not (re.match(r"\d{4}-\d{2}-\d{2}$", date) and date < UNTIL):
            continue
        url = source_url(f.name)
        text = " ".join(unescape(TAG.sub(" ", decode_html(f.read_bytes()))).split())
        for m in CALL.finditer(text):
            label = re.sub(r"^Sra?\.?\s*", "", m["label"]).strip()
            province = province_key(m["prov"])
            person = who(label, province, date, roster)
            key = bloc_key(m["bloc"])
            if person is None:
                refused["the province the chair names is not the speaker's"] += 1
                notes.append(f"{date} {label}: chair said '{m['prov']}' — no senator "
                             f"of that surname sat for it that day")
                continue
            if key in COALITION or key.startswith("alianza") or "alianza" in key.split(", ")[0]:
                refused["names the Alianza coalition, not a caucus"] += 1
                continue
            mapped = CAUCUS.get(key)
            if mapped is None:
                refused[f"caucus wording not in the table: '{key}'"] += 1
                continue
            bloc, provinces = mapped
            if provinces is not None and person["province"] not in provinces:
                refused["caucus named for a province it did not sit for"] += 1
                continue
            kept.append({
                "fecha": date,
                "person_id": person["id"],
                "person_name": person["name"],
                "bloque": bloc,
                "bloque_dicho": m["bloc"].split(",")[0],
                "presidente_del_bloque": "si" if m["pres"] else "",
                "archivo": f.name,
                "url": url,
                "cita": f"{m['call']} {m['label']}",
            })

    kept.sort(key=lambda r: (r["fecha"], r["person_name"]))
    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(kept[0].keys()))
        w.writeheader()
        w.writerows(kept)

    print(f"{len(kept)} calls kept, {len({r['person_id'] for r in kept})} senators, "
          f"{kept[0]['fecha']} to {kept[-1]['fecha']}")
    print(Counter(r["bloque"] for r in kept).most_common())
    print(f"{sum(refused.values())} calls left out:")
    for why, n in refused.most_common():
        print(f"  {n:4d}  {why}")
    for n in notes:
        print(f"      {n}")
    print(f"Written: {OUT}")


if __name__ == "__main__":
    # no options, but --help must describe the script, not run it
    argparse.ArgumentParser(description=__doc__.strip().split("\n\n")[0]).parse_args()
    main()
