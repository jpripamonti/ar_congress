"""Download Argentine Senate stenographic transcripts (versiones
taquigraficas) from the Senate open-data portal.

Hardened rewrite of the Jan 2025 downloader:

- Every run archives the raw session listing to data/raw/senado/listings/,
  so "what did the portal say existed on date X" stays answerable and local
  holdings can be diffed against it (--dry-run does exactly that).
- Already-held sessions are recognized by (fecha, reunion) read from the
  existing JSON sidecars — not by filename — so the Jan 2025 files keep
  their names while new downloads use {date-iso}_r{reunion}_{TIPO}.pdf
  (ASCII, sortable, collision-free: reunion is part of the session's URL).
- PDFs stream to a .part file, are validated (%PDF magic, minimum size),
  and are renamed into place atomically; a truncated or bogus download can
  no longer masquerade as a finished one.
- Sidecars now record sha256, size, download timestamp, and the archived
  listing they came from.
"""

import argparse
import hashlib
import json
import re
import sys
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

import requests

REPO_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = REPO_ROOT / "data" / "raw" / "senado" / "taquigraficas"
LISTINGS_DIR = REPO_ROOT / "data" / "raw" / "senado" / "listings"

LISTING_URL = "https://www.senado.gob.ar/micrositios/DatosAbiertos/ExportarListadoVersionesTac/json"
DEFAULT_YEARS = [2020, 2021, 2022, 2023, 2024]
DOWNLOAD_DELAY = 5  # seconds between downloads
MAX_RETRIES = 3
LISTING_TIMEOUT = 30
PDF_TIMEOUT = (10, 60)  # (connect, read)
MIN_PDF_BYTES = 10_000  # smallest real transcript so far is ~200 KB


def fetch_listing():
    """Fetch the session listing. Returns (rows, raw_text) or (None, None)."""
    try:
        response = requests.get(LISTING_URL, timeout=LISTING_TIMEOUT)
        response.raise_for_status()
        # The endpoint emits trailing commas; strip them before parsing.
        cleaned = re.sub(r",\s*([\}\]])", r"\1", response.text)
        data = json.loads(cleaned)
    except (requests.RequestException, json.JSONDecodeError) as e:
        print(f"Failed to fetch/parse the listing from {LISTING_URL}: {e}")
        return None, None

    rows = data.get("table", {}).get("rows") if isinstance(data, dict) else None
    if not isinstance(rows, list):
        print("Unexpected listing structure: missing table.rows")
        return None, None
    return rows, response.text


def parse_sessions(rows):
    """Map raw listing rows to session dicts."""
    return [
        {
            "fecha": row.get("FECHA DE SESION"),
            "tipo": row.get("TIPO DE SESION"),
            "sesion": row.get("NRO DE SESION"),
            "reunion": row.get("NRO DE REUNION"),
            "url": row.get("URL VESION TAQUIGRAFICA"),  # sic: portal field name
        }
        for row in rows
    ]


def filter_sessions(sessions, years, session_types):
    """Filter sessions by year and (optionally) session type."""
    filtered = []
    for item in sessions:
        try:
            year = datetime.strptime(item["fecha"], "%d-%m-%Y").year
        except (ValueError, TypeError):
            print(f"Skipping row with unparseable fecha: {item!r}")
            continue
        if years and year not in years:
            continue
        if session_types and (item.get("tipo") or "").strip().upper() not in [t.upper() for t in session_types]:
            continue
        filtered.append(item)
    return filtered


def session_key(fecha, reunion):
    """Identity of a session: (fecha, reunion) — reunion is in the download URL."""
    try:
        reunion_norm = str(int(str(reunion).strip()))
    except (TypeError, ValueError):
        reunion_norm = str(reunion or "").strip()
    return (str(fecha or "").strip(), reunion_norm)


def held_sessions():
    """Scan existing sidecars: session_key -> sidecar path."""
    held = {}
    for sidecar in RAW_DIR.glob("*.json"):
        try:
            meta = json.loads(sidecar.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            print(f"Warning: unreadable sidecar {sidecar.name}")
            continue
        held[session_key(meta.get("fecha"), meta.get("reunion"))] = sidecar
    return held


def target_basename(session):
    """New-scheme filename: {date-iso}_r{reunion}_{TIPO} (ASCII, sortable)."""
    date_iso = datetime.strptime(session["fecha"], "%d-%m-%Y").date().isoformat()
    _, reunion = session_key(session["fecha"], session["reunion"])
    tipo = unicodedata.normalize("NFD", session["tipo"] or "SESION")
    tipo = "".join(c for c in tipo if not unicodedata.combining(c))
    tipo = re.sub(r"[^A-Za-z0-9]+", "_", tipo).strip("_").upper()
    return f"{date_iso}_r{int(reunion):02d}_{tipo}" if reunion.isdigit() else f"{date_iso}_rxx_{tipo}"


def download_session(session, listing_name):
    """Download one session PDF atomically + write its sidecar. True on success."""
    basename = target_basename(session)
    pdf_path = RAW_DIR / f"{basename}.pdf"
    part_path = RAW_DIR / f"{basename}.pdf.part"
    url = session["url"]

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            with requests.get(url, stream=True, timeout=PDF_TIMEOUT) as response:
                response.raise_for_status()
                first = b""
                with part_path.open("wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if not first and chunk:
                            first = chunk
                            if not first.startswith(b"%PDF"):
                                raise ValueError(f"not a PDF (starts with {first[:8]!r})")
                        f.write(chunk)

            size = part_path.stat().st_size
            if size < MIN_PDF_BYTES:
                raise ValueError(f"suspiciously small download ({size} bytes)")

            sha = hashlib.sha256(part_path.read_bytes()).hexdigest()
            part_path.rename(pdf_path)  # atomic: only complete, validated files get .pdf

            sidecar = dict(session)
            sidecar.update({
                "sha256": sha,
                "size_bytes": size,
                "downloaded_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "listing_file": listing_name,
            })
            (RAW_DIR / f"{basename}.json").write_text(
                json.dumps(sidecar, indent=4, ensure_ascii=False), encoding="utf-8"
            )
            print(f"Downloaded: {pdf_path.name} ({size} bytes)")
            return True

        except (requests.RequestException, ValueError) as e:
            part_path.unlink(missing_ok=True)
            print(f"Attempt {attempt}/{MAX_RETRIES} failed for {session['fecha']} r{session['reunion']}: {e}")
            if attempt < MAX_RETRIES:
                time.sleep(2 ** attempt)

    print(f"Giving up on {session['fecha']} r{session['reunion']} after {MAX_RETRIES} attempts.")
    return False


def main():
    ap = argparse.ArgumentParser(description="Download Senate transcript PDFs from the open-data portal.")
    ap.add_argument("--years", type=int, nargs="+", default=DEFAULT_YEARS,
                    help=f"session years to include (default: {DEFAULT_YEARS})")
    ap.add_argument("--types", nargs="+", help="session types to include (default: all)")
    ap.add_argument("--dry-run", action="store_true",
                    help="archive the listing and report missing sessions without downloading")
    ap.add_argument("--delay", type=int, default=DOWNLOAD_DELAY,
                    help=f"seconds between downloads (default: {DOWNLOAD_DELAY})")
    args = ap.parse_args()

    if not RAW_DIR.is_dir():
        sys.exit(f"Raw data dir not found: {RAW_DIR} — is the data/ symlink in place? (see DATA.md)")

    rows, raw_text = fetch_listing()
    if rows is None:
        sys.exit(1)

    LISTINGS_DIR.mkdir(parents=True, exist_ok=True)
    listing_name = f"listing_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    (LISTINGS_DIR / listing_name).write_text(raw_text, encoding="utf-8")
    print(f"Listing archived: {listing_name} ({len(rows)} rows)")

    sessions = filter_sessions(parse_sessions(rows), args.years, args.types)
    held = held_sessions()
    missing = [s for s in sessions if session_key(s["fecha"], s["reunion"]) not in held]
    listed_keys = {session_key(s["fecha"], s["reunion"]) for s in sessions}
    extra_held = [k for k in held if k not in listed_keys]

    print(f"Listed (after filters): {len(sessions)} | held locally: {len(held)} "
          f"| missing: {len(missing)} | held-but-not-listed: {len(extra_held)}")

    if not missing:
        print("Nothing to download — local holdings cover the filtered listing.")
        return

    for s in missing:
        print(f"  missing: {s['fecha']} r{s['reunion']} {s['tipo']}")

    if args.dry_run:
        print("Dry run — nothing downloaded.")
        return

    ok = 0
    for s in missing:
        if not s.get("url"):
            print(f"  no URL for {s['fecha']} r{s['reunion']} — skipping")
            continue
        if download_session(s, listing_name):
            ok += 1
        time.sleep(args.delay)
    print(f"Done: {ok}/{len(missing)} downloaded.")


if __name__ == "__main__":
    main()
