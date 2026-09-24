"""Fetch Argentine Senate roster datasets (current + historic senators)
from the Senate open-data portal.

Companion to download.py: where that script acquires the transcript PDFs,
this one acquires the reference data needed to resolve transcript speaker
labels ("Sr. Mayans", "Sra. Presidenta (Ledesma Abdala)") to persons.

- ExportarListadoSenadores/json ........ the 72 sitting senators, with
  BLOQUE, PARTIDO O ALIANZA, PROVINCIA and legal/real mandate dates.
- ExportarListadoSenadoresHistorico/json one row per mandate back to 1983
  (and earlier), with per-mandate legal/real dates, province and party.
  Persons are keyed by the same numeric ID in both datasets.

Raw responses are archived byte-for-byte under reference/senado/ and
described in manifest.json (source URL, fetch timestamp, sha256, row count).
Like the transcript listing endpoint, these endpoints have emitted trailing
commas in the past, so JSON is validated with a trailing-comma fallback;
the archived file is always the raw body, not the cleaned text.

Senate authorities (presidencia, presidencia provisional, secretaries) have
no open-data endpoint; they are maintained by hand in authorities_manual.csv
next to the files this script writes.
"""

import argparse
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

BASE = "https://www.senado.gob.ar/micrositios/DatosAbiertos"
DATASETS = {
    "senadores_actuales.json": f"{BASE}/ExportarListadoSenadores/json",
    "senadores_historico.json": f"{BASE}/ExportarListadoSenadoresHistorico/json",
}
FETCH_TIMEOUT = (10, 120)  # (connect, read)
MAX_RETRIES = 3
FETCH_DELAY = 5  # seconds between endpoint hits


def parse_rows(raw_text):
    """Parse a portal response; tolerate trailing commas. Returns rows or None."""
    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError:
        cleaned = re.sub(r",\s*([\}\]])", r"\1", raw_text)
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            return None
    rows = data.get("table", {}).get("rows") if isinstance(data, dict) else None
    return rows if isinstance(rows, list) else None


def fetch_dataset(name, url):
    """Fetch one dataset, validate it, archive it. Returns a manifest entry or None."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.get(url, timeout=FETCH_TIMEOUT)
            response.raise_for_status()
            rows = parse_rows(response.text)
            if rows is None:
                raise ValueError("response is not the expected table.rows JSON")

            raw = response.content
            path = REF_DIR / name
            part = REF_DIR / f"{name}.part"
            part.write_bytes(raw)
            part.rename(path)  # only validated responses land under the final name

            entry = {
                "file": name,
                "source_url": url,
                "fetched_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "sha256": hashlib.sha256(raw).hexdigest(),
                "size_bytes": len(raw),
                "row_count": len(rows),
            }
            print(f"Fetched {name}: {len(rows)} rows ({len(raw)} bytes)")
            return entry

        except (requests.RequestException, ValueError) as e:
            print(f"Attempt {attempt}/{MAX_RETRIES} failed for {name}: {e}")
            if attempt < MAX_RETRIES:
                time.sleep(2 ** attempt)

    print(f"Giving up on {name} after {MAX_RETRIES} attempts.")
    return None


def main():
    ap = argparse.ArgumentParser(description="Fetch Senate roster datasets into data/reference/senado/.")
    ap.add_argument("--delay", type=int, default=FETCH_DELAY,
                    help=f"seconds between endpoint requests (default: {FETCH_DELAY})")
    args = ap.parse_args()

    if not (REPO_ROOT / "data").is_dir():
        sys.exit(f"data/ not found under {REPO_ROOT} — is the symlink in place? (see DATA.md in the repository)")
    REF_DIR.mkdir(parents=True, exist_ok=True)

    manifest_path = REF_DIR / "manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        manifest = {"datasets": {}}

    ok = 0
    for i, (name, url) in enumerate(DATASETS.items()):
        if i:
            time.sleep(args.delay)
        entry = fetch_dataset(name, url)
        if entry:
            manifest["datasets"][name] = entry
            ok += 1

    if ok:
        manifest_path.write_text(
            json.dumps(manifest, indent=4, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        print(f"Manifest updated: {manifest_path}")
    print(f"Done: {ok}/{len(DATASETS)} datasets fetched.")
    if ok < len(DATASETS):
        sys.exit(1)


if __name__ == "__main__":
    main()
