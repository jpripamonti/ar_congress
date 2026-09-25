"""Recover which caucus each senator sat with in 1997-2000, from the Senate's
own per-senator pages as the Internet Archive captured them.

WHY THIS EXISTS. fetch_archived_blocs.py reads the Senate's bloc-roster page,
but the Internet Archive holds no capture of it before 25 May 2000, which left
1998 and most of 1999 — 19,797 senator speech blocks — with no caucus at all.
The same site also ran one page per senator, and each of those states the
caucus in so many words:

    Distrito: Provincia de Entre Ríos .   Bloque: Justicialista .

The Archive captured those pages in March, July and October 1997 and on
2 February 1998, which is three weeks before the first sitting in this corpus.
Only the 1998 captures can be used: the 1997 pages print "Partido:", the
party, where the 1998 ones print "Bloque:", and a party is not a caucus.
They are the chamber's own statement of its own composition, as good a source
as the roster page and captured earlier.

WHAT A CAPTURE IS AND IS NOT. The same as for the roster page: it says what
the page said on the day it was captured, not the day a senator changed
caucus. The capture date travels with every row, and so does the address of
the exact capture it came from, so anyone can open the page the row rests on.

WHAT IT CANNOT REACH. The chamber was partly renewed on 10 December 1998, and
no per-senator page was captured after 2 February 1998. A senator who took
their seat that December is not here; one who sat through it is observed on
both sides of the gap, here and on the roster page from May 2000, and how far
a sitting lies from its nearest observation is build_bloc_observations.py's
and resolve_speakers.py's business, not this script's.

Raw HTML is archived under data/raw/senado/fichas_archivadas/ beside a .url
file naming the capture, so a re-run neither refetches nor depends on the
archive still answering. Names and caucuses are left exactly as printed.

    uv run scripts/fetch_archived_profiles.py

Output: reference/senado/bloque_por_ficha.csv
"""

import argparse
import csv
import hashlib
import json
import re
import time
from datetime import datetime, timezone
from html import unescape
from pathlib import Path

import requests

REPO_ROOT = Path(__file__).resolve().parents[1]
CACHE_DIR = REPO_ROOT / "data" / "raw" / "senado" / "fichas_archivadas"
OUT = REPO_ROOT / "reference" / "senado" / "bloque_por_ficha.csv"

CDX = "http://web.archive.org/cdx/search/cdx"
RAW = "https://web.archive.org/web/{ts}id_/{url}"
# The per-senator pages lived under two paths on the old site; the roster page
# fetch_archived_blocs.py reads takes over from 25 May 2000.
PREFIXES = [
    "senado.gov.ar/cgi-bin/filtro?/senadores/",
    "senado.gov.ar/senadores/",
]
UNTIL = "20000524"
FETCH_TIMEOUT = (10, 120)
MAX_RETRIES = 4
FETCH_DELAY = 3  # the archive rate-limits hard; 503 is its way of saying slow down

TAG = re.compile(r"<[^>]+>")
TITLE_RE = re.compile(r"<title>\s*(.*?)\s*</title>", re.I | re.S)
# "Bloque: Justicialista ." and "Distrito: Provincia de Entre Ríos ." — the
# page closes each with a spaced full stop before a link to the list.
BLOQUE_RE = re.compile(r"\bBloque\s*:\s*(.+?)\s*\.(?:\s|$)")
DISTRITO_RE = re.compile(r"\bDistrito\s*:\s*(.+?)\s*\.(?:\s|$)")
# The 1997 pages print "Partido: Justicialista" instead: the party the senator
# belongs to, not the caucus they sit with. Recognised only to be reported.
PARTY_RE = re.compile(r"\bPartido\s*:\s*\S")
# index pages and anything that is not one senator's own page
NOT_A_PROFILE = re.compile(r"/senadores(?:\.html)?$|/senadores/$|index", re.I)


def text_of(fragment):
    s = unescape(TAG.sub(" ", fragment))
    return " ".join(s.replace("\xa0", " ").split())


def get(url, params=None):
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            r = requests.get(url, params=params, timeout=FETCH_TIMEOUT)
            r.raise_for_status()
            return r
        except requests.RequestException as e:
            print(f"    attempt {attempt}/{MAX_RETRIES}: {e}")
            if attempt < MAX_RETRIES:
                time.sleep(FETCH_DELAY * 2 ** attempt)
    return None


def list_captures():
    """Every successful capture of a per-senator page before 25 May 2000."""
    found = []
    for prefix in PREFIXES:
        print(f"  index: {prefix}")
        r = get(CDX, {"url": prefix, "matchType": "prefix", "to": UNTIL,
                      "fl": "timestamp,original,statuscode",
                      "filter": "statuscode:200"})
        if r is None:
            print("    index unavailable — falling back to whatever is cached")
            continue
        for line in r.text.splitlines():
            parts = line.split()
            if len(parts) >= 2 and not NOT_A_PROFILE.search(parts[1]):
                found.append((parts[0], parts[1]))
        time.sleep(FETCH_DELAY)
    return sorted(set(found))


def cache_name(ts, url):
    page = re.sub(r"\W+", "_", url.rsplit("/", 1)[-1]).strip("_")
    return CACHE_DIR / f"{ts}_{page}"


def fetch(ts, url):
    """One capture, from the cache if it is already there."""
    base = cache_name(ts, url)
    html_path, url_path = base.with_suffix(".html"), base.with_suffix(".url")
    if html_path.exists():
        return html_path.read_bytes()
    r = get(RAW.format(ts=ts, url=url))
    if r is None:
        return None
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    html_path.write_bytes(r.content)
    url_path.write_text(url + "\n", encoding="utf-8")
    time.sleep(FETCH_DELAY)
    return r.content


def cached_captures():
    """(ts, url) for every capture already on disk, for an offline re-run."""
    out = []
    for p in sorted(CACHE_DIR.glob("*.url")):
        out.append((p.name.split("_", 1)[0], p.read_text(encoding="utf-8").strip()))
    return out


def parse(raw, ts, url):
    html = raw.decode("latin-1")
    title = TITLE_RE.search(html)
    body = text_of(html)
    bloque = BLOQUE_RE.search(body)
    if not title or not bloque:
        return None
    distrito = DISTRITO_RE.search(body)
    return {
        "capture_date": f"{ts[:4]}-{ts[4:6]}-{ts[6:8]}",
        "capture_url": RAW.format(ts=ts, url=url),
        "senador_impreso": text_of(title.group(1)),
        "distrito_impreso": distrito.group(1) if distrito else "",
        "bloque_impreso": bloque.group(1),
    }


def main():
    captures = list_captures() or cached_captures()
    print(f"{len(captures)} captures of per-senator pages")
    rows, party_only, unread, failed = [], [], [], []
    for i, (ts, url) in enumerate(captures, 1):
        raw = fetch(ts, url)
        if raw is None:
            failed.append(f"{ts} {url}")
            continue
        row = parse(raw, ts, url)
        if row is not None:
            rows.append(row)
        elif PARTY_RE.search(text_of(raw.decode("latin-1"))):
            party_only.append(f"{ts} {url}")
        else:
            unread.append(f"{ts} {url}")
        if i % 20 == 0:
            print(f"  {i}/{len(captures)} read")
    rows.sort(key=lambda r: (r["capture_date"], r["senador_impreso"]))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    fields = ["capture_date", "capture_url", "senador_impreso",
              "distrito_impreso", "bloque_impreso"]
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    dates = sorted({r["capture_date"] for r in rows})
    raw = OUT.read_bytes()
    manifest_path = OUT.parent / "manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        manifest = {"datasets": {}}
    manifest["datasets"][OUT.name] = {
        "file": OUT.name,
        "source_url": "https://web.archive.org/web/*/" + PREFIXES[0] + "*",
        "fetched_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "size_bytes": len(raw),
        "row_count": len(rows),
        "captures": len(dates),
        "years": f"{dates[0][:4]}-{dates[-1][:4]}" if dates else "",
        "note": ("the Senate's own per-senator pages, recovered from the Internet "
                 "Archive; each states the senator's caucus ('Bloque: ...'). One "
                 "row per page per capture, names exactly as printed, with the "
                 "address of the capture it rests on. A capture dates the page, "
                 "not the chamber."),
        "captured_on": dates,
    }
    manifest_path.write_text(json.dumps(manifest, indent=4, ensure_ascii=False) + "\n",
                             encoding="utf-8")

    print(f"\n{len(rows)} rows over {len(dates)} capture dates: {', '.join(dates)}")
    if party_only:
        years = sorted({s[:4] for s in party_only})
        print(f"{len(party_only)} captures ({', '.join(years)}) state the PARTY and not "
              f"the caucus, and are left out on purpose: the two are not the same")
    for label, items in (("carry neither line", unread),
                         ("could not be fetched — re-run to retry", failed)):
        if items:
            print(f"{len(items)} captures {label}:")
            for s in items[:10]:
                print(f"    {s}")
    print(f"Written: {OUT}")


if __name__ == "__main__":
    # no options, but --help must describe the script, not run it
    argparse.ArgumentParser(description=__doc__.strip().split("\n\n")[0]).parse_args()
    main()
