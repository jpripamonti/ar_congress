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
- Files stream to a .part file, are validated, and are renamed into place
  atomically; a truncated or bogus download can no longer masquerade as a
  finished one. The portal serves two formats from the same URL: a PDF for
  the sittings from 2004 on, and the chamber's original HTML export for
  most of 1998-2003. Both are kept, in the format served; a sitting the
  portal no longer holds answers 404 and is reported, not stored.
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

from provenance import html_head_text, pdf_head_text, provisional_status, sniff_format

REPO_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = REPO_ROOT / "data" / "raw" / "senado" / "taquigraficas"
LISTINGS_DIR = REPO_ROOT / "data" / "raw" / "senado" / "listings"

LISTING_URL = "https://www.senado.gob.ar/micrositios/DatosAbiertos/ExportarListadoVersionesTac/json"
DEFAULT_YEARS = [2020, 2021, 2022, 2023, 2024]
DOWNLOAD_DELAY = 5  # seconds between downloads
MAX_RETRIES = 3
LISTING_TIMEOUT = 30
FILE_TIMEOUT = (10, 60)  # (connect, read)
MIN_PDF_BYTES = 10_000  # smallest real PDF transcript so far is ~200 KB
MIN_HTML_BYTES = 4_000  # smallest real HTML transcript so far is ~20 KB
# Every real file arrives as an attachment; a sitting the portal lists but no
# longer serves answers 404, so status and this header carry the decision.
HTML_MARKERS = ("SENADO", "ASAMBLEA LEGISLATIVA", "CONGRESO")


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


def looks_like_transcript_html(raw):
    """True when an HTML body reads like a chamber transcript, not a stray page."""
    text = html_head_text(raw)
    return any(marker in text for marker in HTML_MARKERS)


def download_session(session, listing_name):
    """Download one session file atomically + write its sidecar. True on success.

    The portal serves PDF or HTML from the same URL depending on the sitting's
    age, so the format is read off the bytes rather than assumed.
    """
    basename = target_basename(session)
    part_path = RAW_DIR / f"{basename}.part"
    url = session["url"]

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            with requests.get(url, stream=True, timeout=FILE_TIMEOUT) as response:
                response.raise_for_status()
                disposition = response.headers.get("Content-Disposition", "")
                first = b""
                with part_path.open("wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if not first and chunk:
                            first = chunk
                        f.write(chunk)

            fmt = sniff_format(first)
            size = part_path.stat().st_size
            if fmt == "pdf":
                if size < MIN_PDF_BYTES:
                    raise ValueError(f"suspiciously small PDF ({size} bytes)")
            else:
                # Without the attachment header this is a page, not a file.
                if "attachment" not in disposition.lower():
                    raise ValueError(f"not a served file (starts with {first[:16]!r})")
                if size < MIN_HTML_BYTES:
                    raise ValueError(f"suspiciously small HTML ({size} bytes)")
                if not looks_like_transcript_html(part_path.read_bytes()):
                    raise ValueError("HTML body does not read like a transcript")

            # Read off the file itself, so the record says what it is.
            # None where the masthead makes no claim — see provenance.py.
            head = (pdf_head_text(part_path) if fmt == "pdf"
                    else html_head_text(part_path.read_bytes()))
            provisional = provisional_status(head)

            served = re.search(r'filename="([^"]+)"', disposition)
            sha = hashlib.sha256(part_path.read_bytes()).hexdigest()
            final_path = RAW_DIR / f"{basename}.{fmt}"
            part_path.rename(final_path)  # atomic: only validated files get the real name

            sidecar = dict(session)
            sidecar.update({
                "format": fmt,
                "provisional": provisional,
                "served_filename": served.group(1) if served else None,
                "sha256": sha,
                "size_bytes": size,
                "downloaded_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "listing_file": listing_name,
            })
            (RAW_DIR / f"{basename}.json").write_text(
                json.dumps(sidecar, indent=4, ensure_ascii=False), encoding="utf-8"
            )
            print(f"Downloaded: {final_path.name} ({size} bytes)")
            return True

        except (requests.RequestException, ValueError) as e:
            part_path.unlink(missing_ok=True)
            status = getattr(getattr(e, "response", None), "status_code", None)
            print(f"Attempt {attempt}/{MAX_RETRIES} failed for {session['fecha']} r{session['reunion']}: {e}")
            if status == 404:
                # The portal lists the sitting but no longer serves it; retrying cannot help.
                print(f"  not served by the portal (404) — {session['fecha']} r{session['reunion']}")
                return False
            if attempt < MAX_RETRIES:
                time.sleep(2 ** attempt)

    print(f"Giving up on {session['fecha']} r{session['reunion']} after {MAX_RETRIES} attempts.")
    return False


def main():
    ap = argparse.ArgumentParser(description="Download Senate transcripts (PDF or HTML) from the open-data portal.")
    ap.add_argument("--years", type=int, nargs="+", default=DEFAULT_YEARS,
                    help=f"session years to include (default: {DEFAULT_YEARS})")
    ap.add_argument("--all-years", action="store_true",
                    help="every year the listing carries, overriding --years")
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

    years = None if args.all_years else args.years
    sessions = filter_sessions(parse_sessions(rows), years, args.types)
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
