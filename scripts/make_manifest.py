"""Regenerate raw_data_manifest.csv from the raw session tree.

One row per held PDF: session identity, the portal URL it came from, size,
sha256 of both the PDF and its JSON sidecar, and when it was downloaded.
Checksums are recomputed here rather than copied from the sidecar, so the
manifest reflects the bytes actually on disk. The January 2025 downloads
have sidecars that predate the size/checksum fields; their download time is
recorded as unknown rather than guessed.
"""

import csv
import hashlib
import json
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = REPO_ROOT / "data" / "raw" / "senado" / "taquigraficas"
OUT_PATH = REPO_ROOT / "raw_data_manifest.csv"

COLUMNS = [
    "pdf_filename", "session_date_iso", "fecha", "tipo", "sesion", "reunion",
    "source_url", "pdf_size_bytes", "pdf_sha256", "json_sha256",
    "downloaded_at_utc",
]


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    rows = []
    missing_sidecar = []
    for pdf in sorted(RAW_DIR.glob("*.pdf")):
        side = pdf.with_suffix(".json")
        if not side.exists():
            missing_sidecar.append(pdf.name)
            continue
        meta = json.loads(side.read_text(encoding="utf-8"))
        fecha = meta.get("fecha", "")
        try:
            iso = datetime.strptime(fecha, "%d-%m-%Y").date().isoformat()
        except ValueError:
            iso = ""
        rows.append({
            "pdf_filename": pdf.name,
            "session_date_iso": iso,
            "fecha": fecha,
            "tipo": meta.get("tipo", ""),
            "sesion": meta.get("sesion", ""),
            "reunion": meta.get("reunion", ""),
            "source_url": meta.get("url", ""),
            "pdf_size_bytes": pdf.stat().st_size,
            "pdf_sha256": sha256(pdf),
            "json_sha256": sha256(side),
            "downloaded_at_utc": meta.get("downloaded_at_utc", ""),
        })

    rows.sort(key=lambda r: (r["session_date_iso"], r["reunion"]))
    with open(OUT_PATH, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    undated = sum(1 for r in rows if not r["downloaded_at_utc"])
    print(f"Wrote {len(rows)} rows to {OUT_PATH}")
    print(f"  without a recorded download time (pre-2026 sidecars): {undated}")
    if missing_sidecar:
        print(f"  PDFs with no sidecar, SKIPPED: {len(missing_sidecar)}")
        for name in missing_sidecar[:10]:
            print(f"    {name}")


if __name__ == "__main__":
    main()
