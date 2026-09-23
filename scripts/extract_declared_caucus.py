"""The caucus senators of 1998-2000 declared on the floor, read by hand.

WHY THIS EXISTS. For August 1998 to May 2000 the only record of the chamber's
caucuses is what the transcripts themselves say (see extract_chair_caucus.py).
Besides the chair's call, senators often said which caucus they spoke for:

    Señor presidente: en nombre del bloque justicialista, ratifico una vez
    más el homenaje ...

That is a senator stating their own caucus, on the day, in the chamber's own
record — as good a source as the chair's call.

WHY BY HAND. The phrase is used loosely, so no pattern can be trusted to read
it. "El bloque de la mayoría", "mi bloque", "el bloque que integro" do not name
the caucus. "Bloque de la Alianza" names the coalition of the Radicals and
Frepaso, which sat as two caucuses. "Bloque peronista" does not say which
Peronist caucus, and there was more than one. "Los integrantes del bloque
justicialista", said by someone asking for their signatures, does not say the
speaker is one of them. So every candidate was read in context: a pattern
search over every 1998-2000 speech by the 58 senators who then had no caucus
found 74 passages, and only the ones below say plainly which caucus a named
senator sat with. Two more, both Oyarzún's for the Movimiento Popular
Fueguino ("el bloque del Movimiento Popular Fueguino, a través de mi
persona"), were missed by that search and found in September 2026 by a web
search that fetched the same transcript. Two are said of a colleague (`de otro`), the rest by the
senator themselves (`propia`).

Each entry is checked against the parsed transcript at run time, quote and
speaker both, so an entry that stops matching fails loudly instead of standing
on text that is no longer there.

    uv run scripts/extract_declared_caucus.py

Output: reference/senado/bloque_por_declaracion.csv
"""

import csv
import json
import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
BLOCKS = REPO_ROOT / "data" / "processed" / "senado" / "blocks"
RAW = REPO_ROOT / "data" / "raw" / "senado" / "taquigraficas"
SPEAKERS = REPO_ROOT / "data" / "processed" / "senado" / "speakers.parquet"
OUT = REPO_ROOT / "reference" / "senado" / "bloque_por_declaracion.csv"

PJ = "JUSTICIALISTA"
UCR = "UCR - UNIÓN CÍVICA RADICAL"

# (sitting, seq, person the statement is about, caucus in the name the caucus
#  data uses, propia | de otro, the words, verbatim)
DECLARED = [
    ("1998-02-25_r01", 48, "sen:229", PJ, "propia",
     "en nombre del bloque justicialista vengo a proponer como vicepresidente"),
    ("1998-04-15_r09", 365, "sen:90", PJ, "propia",
     "en nombre de mi bloque, que los señores senadores del justicialismo nos sentimos"),
    ("1998-04-01_r06", 280, "sen:31", "MOVIMIENTO POPULAR FUEGUINO", "propia",
     "el bloque del Movimiento Popular Fueguino, a través de mi persona"),
    ("1998-05-13_r15", 235, "sen:42", "MOVIMIENTO POPULAR NEUQUINO", "propia",
     "en nombre del bloque del Movimiento Popular Neuquino"),
    ("1998-05-20_r18", 947, "sen:244", UCR, "propia",
     "en nombre del bloque de senadores de la Unión Cívica Radical adelanto nuestro"),
    ("1998-05-27_r21", 139, "sen:106", PJ, "propia",
     "en nombre del bloque de senadores justicialistas"),
    ("1998-06-10_r24", 388, "sen:205", UCR, "propia",
     "En nombre del bloque de la Unión Cívica Radical quiero dejar expresamente aclarado"),
    ("1998-06-24_r26", 140, "sen:205", UCR, "propia",
     "en nombre del bloque de la Unión Cívica Radical adherimos"),
    ("1998-07-15_r29", 906, "sen:90", PJ, "propia",
     "en nombre del bloque justicialista solicito la aprobación"),
    ("1998-10-21_r53", 397, "sen:232", PJ, "de otro",
     "la credibilidad de Reutemann, que participa del bloque justicialista"),
    ("1998-10-21_r53", 135, "sen:31", "MOVIMIENTO POPULAR FUEGUINO", "propia",
     "solicito se autorice al bloque del Movimiento Popular Fueguino a abstenerse"),
    ("1998-11-25_r64", 303, "sen:228", UCR, "propia",
     "A nosotros, en el bloque de la Unión Cívica Radical, se nos ha autorizado"),
    ("1998-12-09_r71", 375, "sen:88", PJ, "propia",
     "los hombres que integramos el bloque justicialista de este Senado"),
    ("1998-12-09_r71", 1654, "sen:234", UCR, "propia",
     "en nombre del bloque de la Unión Cívica Radical, la posición que hemos tomado"),
    ("1998-12-16_r73", 145, "sen:226", PJ, "propia",
     "en nombre del bloque justicialista quiero hacer presente"),
    ("1999-03-03_r02", 154, "sen:226", PJ, "propia",
     "en nombre del bloque justicialista, ratifico"),
    ("1999-03-10_r03", 29, "sen:238", "PARTIDO RENOVADOR DE SALTA", "propia",
     "mi bloque, el del Partido Renovador de Salta"),
    ("1999-03-10_r03", 43, "sen:226", PJ, "propia",
     "en nombre de los integrantes del bloque justicialista que hemos suscripto"),
    ("1999-04-07_r06", 125, "sen:226", PJ, "propia",
     "En nombre del bloque del Partido Justicialista adhiero"),
    ("1999-04-14_r08", 125, "sen:205", UCR, "propia",
     "esto lo hago en nombre del bloque de la Unión Cívica Radical"),
    ("1999-04-28_r14", 121, "sen:223", "MOVIMIENTO POPULAR FUEGUINO", "propia",
     "en nombre de los miembros del bloque del Movimiento Popular Fueguino venimos"),
    ("1999-06-30_r30", 120, "sen:6", "Bloquista De La Provincia De San Juan", "propia",
     "en nombre del bloque del Partido Bloquista, al cual represento"),
    ("1999-07-07_r31", 321, "sen:88", PJ, "propia",
     "en nombre del bloque justicialista, el mismo éxito"),
    ("1999-08-04_r37", 1679, "sen:106", PJ, "propia",
     "como miembro del bloque justicialista"),
    ("1999-08-11_r39", 151, "sen:229", PJ, "propia",
     "en nombre del bloque justicialista vengo a adherir"),
    ("1999-08-25_r43", 150, "sen:234", UCR, "propia",
     "en nombre del bloque radical, solicito"),
    ("1999-10-27_r52", 351, "sen:95", PJ, "propia",
     "el bloque justicialista va a insistir"),
    ("1999-11-24_r62", 202, "sen:226", PJ, "propia",
     "en nombre del bloque justicialista, adelanto que aceptamos"),
    ("1999-12-09_r67", 123, "sen:226", PJ, "propia",
     "lo quiero despedir en nombre del bloque justicialista"),
    ("1999-12-09_r67", 151, "sen:219", UCR, "propia",
     "Los integrantes del bloque de la Unión Cívica Radical hemos compartido"),
    ("1999-12-09_r67", 159, "sen:229", PJ, "propia",
     "en nombre del bloque justicialista adhiero"),
    ("1999-12-22_r69", 554, "sen:226", PJ, "propia",
     "asumí la responsabilidad, en nombre del bloque justicialista"),
    ("1999-12-28_r72", 251, "sen:208", PJ, "propia",
     "el bloque justicialista va a trabajar sobre el dictamen"),
    ("2000-05-17_r17", 708, "sen:11", PJ, "de otro",
     "el señor senador Costanzo, que ha acudido en nombre del bloque justicialista"),
]


def squash(s):
    return " ".join(str(s).split())


def main():
    speakers = pd.read_parquet(SPEAKERS)
    who = {(r.session_id, r.speaker_raw): (r.person_id, r.person_name)
           for r in speakers.itertuples()}
    names = dict(zip(speakers.person_id, speakers.person_name))
    rows, bad = [], []
    for session, seq, person, bloc, kind, quote in DECLARED:
        b = pd.read_parquet(BLOCKS / f"{session}.parquet")
        hit = b[b.seq == seq]
        if hit.empty or squash(quote) not in squash(hit.text.iat[0]):
            bad.append(f"{session} seq {seq}: quote not found")
            continue
        r = hit.iloc[0]
        speaker_id, speaker_name = who.get((session, r.speaker_raw), (None, None))
        if kind == "propia" and speaker_id != person:
            bad.append(f"{session} seq {seq}: speaker is {speaker_id}, not {person}")
            continue
        side = RAW / Path(r.source_file).with_suffix(".json").name
        url = json.loads(side.read_text(encoding="utf-8")).get("url", "") if side.exists() else ""
        rows.append({
            "fecha": r.session_date,
            "person_id": person.removeprefix("sen:"),
            "person_name": names[person],
            "bloque": bloc,
            "tipo": kind,
            "orador": speaker_name or r.speaker_raw,
            "archivo": r.source_file,
            "seq": seq,
            "url": url,
            "cita": quote,
        })
    if bad:
        sys.exit("Entries that no longer match the transcripts:\n  " + "\n  ".join(bad))

    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} statements, {len({r['person_id'] for r in rows})} senators, "
          f"{rows[0]['fecha']} to {rows[-1]['fecha']}")
    print(f"Written: {OUT}")


if __name__ == "__main__":
    main()
