"""Fetch which caucus (bloque) each senator sat with, on each sitting date.

The roster endpoints fetched by fetch_roster.py give the ticket a senator was
ELECTED on, which is what the historic roster records — and that is not the
caucus they sat with. The two diverge sharply after 2015, when radicals were
elected on Cambiemos and Juntos por el Cambio tickets, so reading the ticket as
a caucus makes the floor look like it realigned when nobody changed seats.
Caucus is published only for the 72 sitting senators, never historically.

The Senate's roll-call records fill the gap. Every recorded vote publishes the
whole chamber — including the members absent for it — with the caucus each was
sitting in ON THAT DAY, so one record per sitting date is a complete snapshot of
the chamber's composition that day. This fetches one per date, not all of them:
a second vote on the same afternoon would only repeat the same 72 rows.

    https://www.senado.gob.ar/votaciones/actas          index, one year per POST
    https://www.senado.gob.ar/votaciones/detalleActa/N  one recorded vote

The records begin in 2005. Sittings before that get no caucus from this source
and must stay unlabelled rather than be filled in from the ticket, which is the
very confusion this exists to remove.

Raw HTML is archived under data/raw/senado/votaciones/ so a re-run neither
refetches nor depends on the site still answering; the parsed result is written
to reference/senado/bloques_por_fecha.csv and described in manifest.json.
"""

import argparse
import csv
import hashlib
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

REPO_ROOT = Path(__file__).resolve().parents[1]
REF_DIR = REPO_ROOT / "reference" / "senado"
CACHE_DIR = REPO_ROOT / "data" / "raw" / "senado" / "votaciones"

INDEX_URL = "https://www.senado.gob.ar/votaciones/actas"
RECORD_URL = "https://www.senado.gob.ar/votaciones/detalleActa/{}"
OUT_NAME = "bloques_por_fecha.csv"

FIRST_YEAR = 2005  # the first year with roll-call records
FETCH_TIMEOUT = (10, 120)  # (connect, read)
MAX_RETRIES = 3
FETCH_DELAY = 2  # seconds between requests

ROW_RE = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S)
CELL_RE = re.compile(r"<t[dh][^>]*>(.*?)</t[dh]>", re.S)
ID_RE = re.compile(r"/votaciones/detalleActa/(\d+)")
DATE_RE = re.compile(r"(\d{2})/(\d{2})/(\d{4})")


def text_of(html):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).strip()


def get(url, data=None):
    """One request, retried. Returns the body text, or None."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            if data is None:
                r = requests.get(url, timeout=FETCH_TIMEOUT)
            else:
                r = requests.post(url, data=data, timeout=FETCH_TIMEOUT)
            r.raise_for_status()
            return r.text
        except requests.RequestException as e:
            print(f"  attempt {attempt}/{MAX_RETRIES} failed: {e}")
            if attempt < MAX_RETRIES:
                time.sleep(2 ** attempt)
    return None


def index_for_year(year):
    """Every recorded vote that year, as {iso date: [record id, ...]}."""
    html = get(INDEX_URL, data={"busqueda_actas[anio]": str(year)})
    if html is None:
        return {}
    by_date = {}
    for row in ROW_RE.findall(html):
        rid = ID_RE.search(row)
        day = DATE_RE.search(text_of(row))
        if rid and day:
            d, m, y = day.groups()
            by_date.setdefault(f"{y}-{m}-{d}", []).append(int(rid.group(1)))
    return by_date


def record_html(record_id):
    """One recorded vote, from the cache when it is already there."""
    path = CACHE_DIR / f"acta_{record_id}.html"
    if path.exists():
        return path.read_text(encoding="utf-8", errors="replace"), False
    html = get(RECORD_URL.format(record_id))
    if html is None:
        return None, False
    path.write_text(html, encoding="utf-8")
    return html, True


def parse_record(html):
    """The chamber as that record lists it: (senator, caucus, province, vote)."""
    out = []
    for row in ROW_RE.findall(html):
        cells = [text_of(c) for c in CELL_RE.findall(row)]
        # Foto | Senador | Bloque | Provincia | ¿Cómo votó?
        if len(cells) >= 5 and cells[1] and cells[1] != "Senador":
            out.append((cells[1], cells[2], cells[3], cells[4]))
    return out


def main():
    ap = argparse.ArgumentParser(
        description="Fetch each senator's caucus per sitting date from roll-call records.")
    ap.add_argument("--from-year", type=int, default=FIRST_YEAR)
    ap.add_argument("--to-year", type=int, default=datetime.now(timezone.utc).year)
    ap.add_argument("--delay", type=float, default=FETCH_DELAY,
                    help=f"seconds between requests (default: {FETCH_DELAY})")
    args = ap.parse_args()

    if not (REPO_ROOT / "data").is_dir():
        sys.exit(f"data/ not found under {REPO_ROOT} — is the symlink in place? (see DATA.md)")
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    REF_DIR.mkdir(parents=True, exist_ok=True)

    rows, dates_done, fetched = [], 0, 0
    for year in range(args.from_year, args.to_year + 1):
        by_date = index_for_year(year)
        if not by_date:
            print(f"{year}: no recorded votes")
            continue
        print(f"{year}: {len(by_date)} sitting dates "
              f"({sum(len(v) for v in by_date.values())} records, one read per date)",
              flush=True)
        for date in sorted(by_date):
            html = None
            for rid in sorted(by_date[date]):  # fall through if one record is unreadable
                html, was_fetched = record_html(rid)
                fetched += was_fetched
                if was_fetched:
                    time.sleep(args.delay)
                if html and (parsed := parse_record(html)):
                    for senator, bloc, province, vote in parsed:
                        rows.append({
                            "fecha": date, "acta_id": rid, "senador": senator,
                            "bloque": bloc, "provincia": province, "voto": vote,
                        })
                    dates_done += 1
                    break
        time.sleep(args.delay)

    if not rows:
        sys.exit("No caucus rows parsed — nothing written.")

    out_path = REF_DIR / OUT_NAME
    with out_path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    raw = out_path.read_bytes()
    manifest_path = REF_DIR / "manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        manifest = {"datasets": {}}
    manifest["datasets"][OUT_NAME] = {
        "file": OUT_NAME,
        "source_url": INDEX_URL,
        "fetched_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "size_bytes": len(raw),
        "row_count": len(rows),
        "sitting_dates": dates_done,
        "years": f"{args.from_year}-{args.to_year}",
        "note": ("one roll-call record per sitting date; each lists the whole "
                 "chamber with the caucus each senator sat in that day"),
    }
    manifest_path.write_text(json.dumps(manifest, indent=4, ensure_ascii=False) + "\n",
                             encoding="utf-8")
    print(f"\n{len(rows)} rows over {dates_done} sitting dates "
          f"({fetched} records newly fetched) -> {out_path}")


if __name__ == "__main__":
    main()
