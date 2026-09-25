"""Recover which caucus each senator sat with before 2005, from the Senate's
own bloc-roster page as the Internet Archive captured it.

WHY THIS EXISTS. The Senate's roll-call records give the caucus beside every
senator's name, but they begin in 2005. Five years of this corpus sit before
that. The Senate itself published a page listing every senator under their
caucus throughout those years; the page is long dead and the Senate keeps no
archive of it, but the Internet Archive captured it every few months. Those
captures are primary evidence — the chamber's own statement of its own
composition — and they close the gap almost exactly, running to June 2004
against roll-call records that start in February 2005.

WHAT A CAPTURE IS AND IS NOT. It says what the page said on the day it was
captured. The page lags the chamber: of the 1,112 senator-rows recovered here,
two are provably stale against the roster's own mandate dates — one senator
still listed four days after his term ended, one listed a month before his
began. So a capture brackets a change between two dates; it never dates one to
the day. Every row carries its capture date and the URL it came from, so the
distance is always visible.

TWO PAGE LAYOUTS, one rule. The 2000-2001 page marks a caucus with bold and
underline; the 2002-2004 page uses a coloured table band with white text. In
both, a senator is normally a link to their own profile page. So the parse
walks the document in order, remembering the last heading it saw and attaching
each senator to it. A name before any heading is reported, never guessed at.

The pages are hand-written HTML and are broken in three ways that each cost a
row or a whole caucus if the parse is strict about markup, so each is handled
by name rather than by loosening everything: a link closed with "<a>" instead
of "</a>", which would otherwise swallow the senator after it; a heading whose
"</u>" is missing, which would drop the caucus and orphan its members; and two
senators printed as plain text with no link at all. Accents arrive both as
Latin-1 bytes and as HTML entities, sometimes in the same name.

Raw HTML is archived under data/raw/senado/bloques_archivados/ so a re-run
neither refetches nor depends on the archive still answering. Names are left
exactly as the page printed them; resolving them to people is
build_bloc_observations.py's job, against the roster's mandate dates.

    http://web.archive.org/cdx/search/cdx      which captures exist
    https://web.archive.org/web/<ts>id_/<url>  one capture, without the
                                               archive's own toolbar injected
"""

import argparse
import csv
import hashlib
import json
import re
import sys
import time
from html import unescape
from datetime import datetime, timezone
from pathlib import Path

import requests

REPO_ROOT = Path(__file__).resolve().parents[1]
CACHE_DIR = REPO_ROOT / "data" / "raw" / "senado" / "bloques_archivados"
OUT = REPO_ROOT / "reference" / "senado" / "bloque_por_foto.csv"

CDX = "http://web.archive.org/cdx/search/cdx"
RAW = "https://web.archive.org/web/{ts}id_/{url}"
# The two addresses the roster lived at. A third page at .../bloques/cuerpo1
# lists caucus NAMES with no members and is deliberately not fetched.
SOURCES = [
    "http://www.senado.gov.ar/web/senadores/m_bloques.html",
    "http://proyectos.senado.gov.ar/web/owa/lbloques.paginabloq",
    "http://proyectos.senado.gov.ar/web/owa/webnueva.senbloque",
]
FIRST_YEAR, LAST_YEAR = 2000, 2005
FETCH_TIMEOUT = (10, 120)
MAX_RETRIES = 4
FETCH_DELAY = 3  # the archive rate-limits hard; 503 is its way of saying slow down

TAG = re.compile(r"<[^>]+>")
# A caucus heading: bold+underline in either order (old page), or white text in
# the coloured band (new page). The closing </u> is optional because the old
# page sometimes omits it ("<b><u> Partido Justicialista Federal de Senadores
# Nacionales</b>"), which would otherwise drop a whole caucus and orphan its
# members.
HEAD_RE = re.compile(
    r"<b>\s*<u>(.*?)(?:</u>\s*)?</b>|<u>\s*<b>(.*?)</b>(?:\s*</u>)?"
    r"|<font[^>]*color=\"#FFFFFF\"[^>]*>(.*?)</font>", re.I | re.S)
# A senator: a link to their own profile page. The capture stops at the first
# </a> OR at the next tag that opens a link or a paragraph, because the old page
# sometimes closes a link with "<a>" instead of "</a>" ("RAIJER , BEATRIZ
# IRMA<a><p>") and a plain non-greedy match would then swallow the next senator.
NAME_RE = re.compile(
    r"<a\s[^>]*href=\"[^\"]*?cuerpo1\.html?\"[^>]*>(.*?)(?:</a>|<a[ >]|<p[ >])",
    re.I | re.S)
# Two senators on the old page are printed as plain text with no link at all.
# Matched on shape — SURNAME in capitals, comma, given name — inside a paragraph
# that holds no link, which no caucus heading looks like (they are title case
# and carry no comma).
PLAIN_RE = re.compile(
    r"<p[^>]*>((?:(?!<a[ >])[^<])*?[A-ZÁÉÍÓÚÑÜ]{2,}[A-ZÁÉÍÓÚÑÜ .'-]*,"
    r"\s*[A-ZÁÉÍÓÚÑÜ][^<]*?)</p>", re.I | re.S)


def text_of(fragment):
    # the page writes accents both as bytes and as entities ("&Aacute;NGEL")
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
    """Every capture of every roster address, one per month at most."""
    found = []
    for url in SOURCES:
        print(f"  index: {url}")
        r = get(CDX, {"url": url, "from": FIRST_YEAR, "to": LAST_YEAR,
                      "fl": "timestamp,original,statuscode",
                      "collapse": "timestamp:6", "filter": "statuscode:200"})
        if r is None:
            print("    index unavailable — falling back to whatever is cached")
            continue
        for line in r.text.splitlines():
            parts = line.split()
            if len(parts) >= 2:
                found.append((parts[0], parts[1]))
        time.sleep(FETCH_DELAY)
    return sorted(set(found))


def fetch(ts, url):
    """One capture, from the cache if it is already there."""
    path = CACHE_DIR / f"snap_{ts}.html"
    if path.exists():
        remember_source(ts, url)
        return path.read_bytes()
    r = get(RAW.format(ts=ts, url=url))
    if r is None:
        return None
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path.write_bytes(r.content)
    remember_source(ts, url)
    time.sleep(FETCH_DELAY)
    return r.content


def remember_source(ts, url):
    """Keep the address a capture came from beside the capture itself.

    The roster lived at three addresses over the years and the capture file is
    named only for its timestamp, so a later offline re-run has no way to
    rebuild the link back to the archive. Without this the URL column comes out
    unusable, which is what it was until now.
    """
    side = CACHE_DIR / f"snap_{ts}.url"
    if side.exists() and side.read_text(encoding="utf-8").strip() == url:
        return
    if side.exists():
        print(f"    {ts}: recorded address replaced\n"
              f"      was {side.read_text(encoding='utf-8').strip()}\n"
              f"      now {url}")
    side.write_text(url + "\n", encoding="utf-8")


def cached_source(ts):
    """The address a cached capture came from, or None if it was never kept."""
    side = CACHE_DIR / f"snap_{ts}.url"
    return side.read_text(encoding="utf-8").strip() if side.exists() else None


def parse(html, ts, url):
    """Walk the page in order, attaching each senator to the last heading seen."""
    # these pages are Latin-1; decoding them as UTF-8 mangles every accent
    if isinstance(html, bytes):
        html = html.decode("cp1252", errors="replace")
    events = []
    for m in HEAD_RE.finditer(html):
        events.append((m.start(), "bloc", text_of(next(g for g in m.groups() if g))))
    for m in NAME_RE.finditer(html):
        events.append((m.start(), "name", text_of(m.group(1))))
    linked = {e[2] for e in events if e[1] == "name"}
    for m in PLAIN_RE.finditer(html):
        txt = text_of(m.group(1))
        if txt and txt not in linked:
            events.append((m.start(), "name", txt))
    events.sort()

    date = f"{ts[0:4]}-{ts[4:6]}-{ts[6:8]}"
    rows, bloc, orphans = [], None, []
    for _, kind, txt in events:
        if not txt:
            continue
        if kind == "bloc":
            bloc = txt
        elif bloc is None:
            orphans.append(txt)
        else:
            rows.append({"snapshot_date": date,
                         "snapshot_url": RAW.format(ts=ts, url=url),
                         "bloque_impreso": bloc, "senador_impreso": txt})
    return rows, orphans


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true",
                    help="parse the cached captures only; never touch the network")
    args = ap.parse_args()

    if args.offline:
        captures = []
        for p in sorted(CACHE_DIR.glob("snap_*.html")):
            ts = p.stem.removeprefix("snap_")
            url = cached_source(ts)
            if url is None:
                sys.exit(f"{p.name} has no recorded source address; run once "
                         f"online so every capture keeps the address it came from")
            captures.append((ts, url))
        print(f"{len(captures)} cached captures")
    else:
        captures = list_captures()
        print(f"{len(captures)} captures listed")

    all_rows, total_orphans = [], 0
    for ts, url in captures:
        html = fetch(ts, url)
        if html is None:
            print(f"  {ts}  FETCH FAILED")
            continue
        rows, orphans = parse(html, ts, url)
        total_orphans += len(orphans)
        blocs = len({r["bloque_impreso"] for r in rows})
        note = "" if rows else "   <- no members; probably the names-only page"
        print(f"  {ts[0:4]}-{ts[4:6]}-{ts[6:8]}  {len(rows):3d} senators  "
              f"{blocs:2d} caucuses{note}")
        if orphans:
            print(f"      {len(orphans)} names before any caucus heading: {orphans[:4]}")
        all_rows += rows

    if not all_rows:
        sys.exit("nothing parsed")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["snapshot_date", "snapshot_url",
                                          "bloque_impreso", "senador_impreso"])
        w.writeheader()
        w.writerows(all_rows)
    dates = sorted({r["snapshot_date"] for r in all_rows})

    raw = OUT.read_bytes()
    manifest_path = OUT.parent / "manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        manifest = {"datasets": {}}
    # An offline re-run that reproduces the table fetched nothing: it keeps
    # the time the captures were fetched, so a rebuild leaves the shipped
    # manifest, and its checksum, as they were.
    previous = manifest["datasets"].get(OUT.name, {})
    digest = hashlib.sha256(raw).hexdigest()
    fetched = (previous["fetched_at_utc"] if args.offline and previous.get("sha256") == digest
               else datetime.now(timezone.utc).isoformat(timespec="seconds"))
    manifest["datasets"][OUT.name] = {
        "file": OUT.name,
        "source_url": "https://web.archive.org/web/*/" + SOURCES[0],
        "fetched_at_utc": fetched,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "size_bytes": len(raw),
        "row_count": len(all_rows),
        "captures": len(dates),
        "years": f"{dates[0][:4]}-{dates[-1][:4]}",
        "note": ("the Senate's own bloc-roster page, recovered from the Internet "
                 "Archive because the page no longer exists and the Senate keeps "
                 "no copy; one row per senator per capture, names exactly as "
                 "printed. A capture dates the page, not the chamber."),
        "captured_on": dates,
    }
    manifest_path.write_text(json.dumps(manifest, indent=4, ensure_ascii=False) + "\n",
                             encoding="utf-8")

    print(f"\n{len(all_rows)} rows over {len(dates)} captures, "
          f"{dates[0]} to {dates[-1]}")
    print(f"names that could not be attached to a caucus: {total_orphans}")
    print(f"Written: {OUT}   ({datetime.now(timezone.utc):%Y-%m-%d %H:%M UTC})")


if __name__ == "__main__":
    main()
