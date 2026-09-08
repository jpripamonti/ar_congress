"""Build the frozen release bundle, its checksums and its archive.

What goes out is the dataset, the code that produces it, and what a stranger
needs to use, check and cite it — nothing else. The repository's own working
documents (TODO.md, the release process, the parse logs, the blind-read
records, the notebook) stay in the repository: they are how the corpus was
made, not part of what is being published.

Two things this does beyond copying. It keeps every file at the path the
repository gives it, so the relative links and the paths named in the shipped
documentation still resolve. And it walks every shipped Markdown file
afterwards, refusing to write the archive if any relative link points at a file
the bundle does not carry.

The bundle's README is docs/DEPOSIT_README.md, written for whoever unpacks the
archive. The repository's own README is not shipped: it is written for whoever
works in the repository, and it showed.
"""

import argparse
import hashlib
import re
import shutil
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PROCESSED = REPO_ROOT / "data" / "processed" / "senado"
RAW = REPO_ROOT / "data" / "raw" / "senado"
RELEASES = REPO_ROOT / "data" / "releases"

# (source, destination directory inside the bundle). A source may be a file, a
# glob, or a directory — a directory is copied whole and keeps its own name, so
# its destination here is the parent it should sit in.
# (source, destination directory inside the bundle[, name it takes there]).
# A source may be a file, a glob, or a directory — a directory is copied whole
# and keeps its own name, so its destination here is the parent it sits in.
PARTS = [
    # The corpus.
    (PROCESSED / "blocks", "data/processed/senado"),
    (PROCESSED / "speakers.parquet", "data/processed/senado"),
    (PROCESSED / "parse_stats.csv", "data/processed/senado"),
    # The one input that cannot be fetched again: captures of a dead page.
    (RAW / "bloques_archivados", "data/raw/senado"),
    # What the pipeline resolves against, and what the accuracy figure is
    # measured on.
    (REPO_ROOT / "reference" / "senado", "reference"),
    (REPO_ROOT / "reference" / "gold", "reference"),
    (REPO_ROOT / "raw_data_manifest.csv", ""),
    # The pipeline, and the environment it was calibrated in.
    (REPO_ROOT / "pyproject.toml", ""),
    (REPO_ROOT / "uv.lock", ""),
    # The documentation and the terms.
    (REPO_ROOT / "docs" / "DEPOSIT_README.md", "", "README.md"),
    (REPO_ROOT / "docs" / "DATA_DICTIONARY.md", "docs"),
    (REPO_ROOT / "LICENSE", ""),
    (REPO_ROOT / "LICENSE-DATA", ""),
    (REPO_ROOT / "CITATION.cff", ""),
]

# The pipeline, script by script, so that adding one to the repository is a
# decision about the release rather than an accident of a glob. Left out:
# make_release.py (this file — packaging, not the dataset), count_presiding.py
# (an analysis helper), check_blind_reads.py (its records stay in the
# repository, so the script would have nothing to read here).
SCRIPTS = [
    "download.py", "parse.py", "make_manifest.py",
    "fetch_roster.py", "fetch_blocs.py", "fetch_archived_blocs.py",
    "build_bloc_observations.py", "map_blocs.py", "extract_authorities.py",
    "resolve_speakers.py",
    "eval_gold.py", "check_gold.py", "audit_parse.py",
]

LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")


def parser_version():
    text = (REPO_ROOT / "scripts" / "parse.py").read_text(encoding="utf-8")
    match = re.search(r'^PARSER_VERSION = "([^"]+)"', text, re.M)
    if not match:
        raise SystemExit("Could not read PARSER_VERSION from scripts/parse.py")
    return match.group(1)


def copy_part(source, dest_dir, name=None):
    dest_dir.mkdir(parents=True, exist_ok=True)
    if "*" in source.name:
        sources = sorted(source.parent.glob(source.name))
        if not sources:
            raise SystemExit(f"Nothing matches {source}")
    else:
        sources = [source]
    for item in sources:
        if not item.exists():
            raise SystemExit(f"Missing: {item}")
        if item.is_dir():
            shutil.copytree(
                item, dest_dir / item.name, dirs_exist_ok=True,
                ignore=shutil.ignore_patterns(".DS_Store", "__pycache__"),
            )
        else:
            shutil.copy2(item, dest_dir / (name or item.name))


def broken_links(out_dir):
    broken = []
    for path in sorted(out_dir.rglob("*.md")):
        for target in LINK_RE.findall(path.read_text(encoding="utf-8")):
            target = target.split("#")[0].split(" ")[0].strip()
            if not target or target.startswith(("http://", "https://", "mailto:")):
                continue
            if not (path.parent / target).exists():
                broken.append(f"{path.relative_to(out_dir)} -> {target}")
    return broken


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_checksums(out_dir):
    checksums = out_dir / "CHECKSUMS.sha256"
    paths = sorted(
        "./" + str(p.relative_to(out_dir))
        for p in out_dir.rglob("*")
        if p.is_file() and p.name not in ("CHECKSUMS.sha256", ".DS_Store")
    )
    lines = [f"{sha256(out_dir / p)}  {p}\n" for p in paths]
    checksums.write_text("".join(lines), encoding="utf-8")
    return len(paths)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--force", action="store_true",
                    help="replace an existing bundle directory of this version")
    args = ap.parse_args()

    version = parser_version()
    name = f"ar_congress_senado_{version}"
    out_dir = RELEASES / name

    if out_dir.exists():
        if not args.force:
            raise SystemExit(f"{out_dir} exists. Pass --force to replace it.")
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)

    for source, dest, *rename in PARTS:
        copy_part(source, out_dir / dest if dest else out_dir,
                  rename[0] if rename else None)
    for script in SCRIPTS:
        copy_part(REPO_ROOT / "scripts" / script, out_dir / "scripts")

    broken = broken_links(out_dir)
    if broken:
        print(f"Broken links in the bundle: {len(broken)}")
        for line in broken:
            print(f"  {line}")
        raise SystemExit("Bundle not written to an archive. Fix the links first.")

    # Finder writes .DS_Store into any directory it is pointed at, including
    # this one between a build and the next. They are never part of a release.
    for junk in out_dir.rglob(".DS_Store"):
        junk.unlink()

    n_files = write_checksums(out_dir)

    archive = RELEASES / f"{name}.tar.gz"
    if archive.exists():
        archive.unlink()
    subprocess.run(
        ["tar", "--exclude", ".DS_Store", "-czf", archive.name, name],
        cwd=RELEASES, check=True,
    )
    digest = sha256(archive)
    (RELEASES / f"{name}.tar.gz.sha256").write_text(
        f"{digest}  {archive.name}\n", encoding="utf-8")

    unpacked = sum(p.stat().st_size for p in out_dir.rglob("*") if p.is_file())
    print(f"{out_dir.relative_to(REPO_ROOT)}")
    print(f"  {n_files + 1} files, {unpacked / 1e6:.0f} MB unpacked")
    print(f"  {archive.name}: {archive.stat().st_size / 1e6:.0f} MB")
    print(f"  sha256: {digest}")
    print("  every relative link in the shipped Markdown resolves")


if __name__ == "__main__":
    main()
