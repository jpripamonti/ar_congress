"""Regenerate raw_data_manifest.csv from the raw session tree.

One row per held transcript: session identity, the portal URL it came from,
the format the portal served (PDF from 2004 on, the chamber's HTML export for
most of 1998-2003), whether the record is the provisional version, size,
sha256 of both the file and its JSON sidecar, and when it was downloaded.

The file columns were named pdf_* through release 0.4.37, when every holding
was a PDF; they are filename/file_size_bytes/file_sha256 now that they are not.
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

# Written out in words: an empty cell would not say whether the record makes no
# claim or whether we never looked.
PROVISIONAL_LABEL = {True: "true", False: "false", None: "unstated"}

COLUMNS = [
    "filename", "session_date_iso", "fecha", "tipo", "sesion", "reunion",
    "source_url", "format", "provisional", "file_size_bytes", "file_sha256",
    "json_sha256", "downloaded_at_utc",
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
    held = sorted(p for p in RAW_DIR.iterdir() if p.suffix in (".pdf", ".html"))
    unmarked = []
    for pdf in held:
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
        if "format" not in meta or "provisional" not in meta:
            unmarked.append(pdf.name)
        rows.append({
            "filename": pdf.name,
            "session_date_iso": iso,
            "fecha": fecha,
            "tipo": meta.get("tipo", ""),
            "sesion": meta.get("sesion", ""),
            "reunion": meta.get("reunion", ""),
            "source_url": meta.get("url", ""),
            "format": meta.get("format", ""),
            "provisional": PROVISIONAL_LABEL.get(meta.get("provisional"), ""),
            "file_size_bytes": pdf.stat().st_size,
            "file_sha256": sha256(pdf),
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
    if unmarked:
        print(f"  without format/provisional — run mark_provenance.py: {len(unmarked)}")
    if missing_sidecar:
        print(f"  files with no sidecar, SKIPPED: {len(missing_sidecar)}")
        for name in missing_sidecar[:10]:
            print(f"    {name}")


if __name__ == "__main__":
    main()
