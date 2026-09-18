"""Record, in every sidecar, what the held file is: the format the portal
served and whether the record is the provisional version.

Downloads from 2026-09 on carry both fields already; the 559 files fetched
before that have sidecars that predate them. This fills them in for every
held file, new and old alike, reading each one the same way (see
provenance.py) so the two eras stay comparable.

Idempotent: re-running rewrites the same values. --check reports what would
change without writing.
"""

import argparse
import json
import sys
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from provenance import head_text, provisional_status, sniff_format  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = REPO_ROOT / "data" / "raw" / "senado" / "taquigraficas"


def inspect(path):
    """(name, format, provisional) for one held transcript, read from its bytes.

    provisional is True, False, or None where the masthead makes no claim.
    """
    with open(path, "rb") as fh:
        fmt = sniff_format(fh.read(8))
    try:
        provisional = provisional_status(head_text(path, fmt))
    except Exception as e:  # a file we cannot read is reported, never guessed
        return path.name, fmt, None, str(e)
    return path.name, fmt, provisional, None


def main():
    ap = argparse.ArgumentParser(description="Mark format and provisional status in every sidecar.")
    ap.add_argument("--check", action="store_true", help="report without writing")
    ap.add_argument("--workers", type=int, default=6)
    args = ap.parse_args()

    files = sorted(p for p in RAW_DIR.iterdir() if p.suffix in (".pdf", ".html"))
    if not files:
        sys.exit(f"No held transcripts under {RAW_DIR}")

    tally = Counter()
    unreadable, no_sidecar, changed = [], [], []

    with ProcessPoolExecutor(args.workers) as ex:
        futures = {ex.submit(inspect, p): p for p in files}
        for fut in as_completed(futures):
            path = futures[fut]
            name, fmt, provisional, error = fut.result()
            if error:
                unreadable.append((name, error))
                continue
            tally[(fmt, provisional)] += 1

            side = path.with_suffix(".json")
            if not side.exists():
                no_sidecar.append(name)
                continue
            meta = json.loads(side.read_text(encoding="utf-8"))
            if meta.get("format") == fmt and meta.get("provisional") == provisional:
                continue
            changed.append(name)
            if not args.check:
                meta["format"] = fmt
                meta["provisional"] = provisional
                side.write_text(json.dumps(meta, indent=4, ensure_ascii=False), encoding="utf-8")

    print(f"Held transcripts: {len(files)}")
    for (fmt, provisional), n in sorted(tally.items(), key=lambda kv: (kv[0][0], str(kv[0][1]))):
        label = {True: "yes", False: "no", None: "unstated"}[provisional]
        print(f"  {fmt:<4} provisional={label:<8} {n:>4}")
    verb = "would change" if args.check else "updated"
    print(f"Sidecars {verb}: {len(changed)}")
    if no_sidecar:
        print(f"  files with no sidecar, SKIPPED: {len(no_sidecar)}")
        for name in no_sidecar[:10]:
            print(f"    {name}")
    if unreadable:
        print(f"  unreadable, left unmarked: {len(unreadable)}")
        for name, error in unreadable[:10]:
            print(f"    {name}: {error}")


if __name__ == "__main__":
    main()
