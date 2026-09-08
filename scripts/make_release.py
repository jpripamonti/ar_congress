"""Build the frozen release bundle, its checksums and its archive.

What goes in is listed in docs/RELEASE.md; PARTS below is that table in code.
Three things this does that a hand-run copy did not. It keeps each file at the
path the repository gives it, so the relative links inside the shipped Markdown
still resolve. It rewrites the one link that cannot survive the move — the
README's pointer to DATA.md, which is about the author's working copy and has
no place in a bundle — and stops if that link is no longer there to rewrite.
And it walks every shipped Markdown file afterwards, asking of each relative
link whether the file it names is actually in the bundle: the 0.4.37 bundle
went out with eight links that pointed at nothing.
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
PARTS = [
    # The corpus and the working data, at the paths the documentation names.
    (PROCESSED / "blocks", "data/processed/senado"),
    (PROCESSED / "logs", "data/processed/senado"),
    (PROCESSED / "speakers.parquet", "data/processed/senado"),
    (PROCESSED / "parse_stats.csv", "data/processed/senado"),
    (PROCESSED / "gold_eval.csv", "data/processed/senado"),
    (PROCESSED / "blind_read_check.csv", "data/processed/senado"),
    (PROCESSED / "audit_source.csv", "data/processed/senado"),
    (PROCESSED / "review_sheet.csv", "data/processed/senado"),
    (RAW / "bloques_archivados", "data/raw/senado"),
    (RAW / "listings", "data/raw/senado"),
    # The pipeline that produced it, and the environment it was pinned to.
    (REPO_ROOT / "scripts" / "*.py", "scripts"),
    (REPO_ROOT / "pyproject.toml", ""),
    (REPO_ROOT / "uv.lock", ""),
    (REPO_ROOT / "notebooks" / "analysis.ipynb", "notebooks"),
    (REPO_ROOT / "figures" / "*.png", "figures"),
    # The reference tables and the verification records.
    (REPO_ROOT / "reference" / "senado", "reference"),
    (REPO_ROOT / "reference" / "gold", "reference"),
    (REPO_ROOT / "reference" / "verification", "reference"),
    (REPO_ROOT / "raw_data_manifest.csv", ""),
    # The documentation and the terms.
    (REPO_ROOT / "README.md", ""),
    (REPO_ROOT / "SOURCES.md", ""),
    (REPO_ROOT / "TODO.md", ""),
    (REPO_ROOT / "LICENSE", ""),
    (REPO_ROOT / "LICENSE-DATA", ""),
    (REPO_ROOT / "CITATION.cff", ""),
    (REPO_ROOT / "docs" / "DATA_DICTIONARY.md", "docs"),
    (REPO_ROOT / "docs" / "RELEASE.md", "docs"),
]

# The release notes of every version, at the path the repository gives them, so
# that their own links to ../RELEASE.md and ../../SOURCES.md still resolve.
NOTES_GLOB = (REPO_ROOT / "docs" / "releases" / "*.md", "docs/releases")

# Links that cannot come along, and what the bundle's copy should say instead.
# Each must match exactly once, or the build stops: a rewrite that silently
# matches nothing is how the links rotted in the first place.
REWRITES = [
    # The two places the README speaks to whoever works in the repository
    # rather than to whoever unpacks the bundle. Each must match exactly once,
    # or the build stops: a rewrite that silently matches nothing is how the
    # links rotted in the first place.
    ("README.md",
     "- `data/` — symlink to the working copy kept outside Git (see\n"
     "  [DATA.md](DATA.md)).",
     "- `data/` — the parsed corpus, the per-sitting logs, the archived\n"
     "  bloc-roster pages and the portal listings. In the repository this is a\n"
     "  symlink to a working copy kept outside Git; here it is a real directory."),
    ("README.md",
     "On a new machine, re-create the working-data symlink first (see DATA.md).",
     "The corpus is already under `data/` in this bundle. Only the steps that\n"
     "read the source PDFs need `download.py` run first: the PDFs are not\n"
     "redistributed here, and `raw_data_manifest.csv` says which ones they are."),
]

LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")


def parser_version():
    text = (REPO_ROOT / "scripts" / "parse.py").read_text(encoding="utf-8")
    match = re.search(r'^PARSER_VERSION = "([^"]+)"', text, re.M)
    if not match:
        raise SystemExit("Could not read PARSER_VERSION from scripts/parse.py")
    return match.group(1)


def copy_part(source, dest_dir):
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
            shutil.copy2(item, dest_dir / item.name)


def apply_rewrites(out_dir):
    for relative, old, new in REWRITES:
        path = out_dir / relative
        text = path.read_text(encoding="utf-8")
        if text.count(old) != 1:
            raise SystemExit(
                f"{relative}: expected exactly one occurrence of {old!r}, "
                f"found {text.count(old)}. Update REWRITES in this script."
            )
        path.write_text(text.replace(old, new), encoding="utf-8")


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

    notes = REPO_ROOT / "docs" / "releases" / f"{version}.md"
    if not notes.exists():
        raise SystemExit(f"No release notes at {notes.relative_to(REPO_ROOT)}")

    if out_dir.exists():
        if not args.force:
            raise SystemExit(f"{out_dir} exists. Pass --force to replace it.")
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)

    for source, dest in PARTS:
        copy_part(source, out_dir / dest if dest else out_dir)
    copy_part(NOTES_GLOB[0], out_dir / NOTES_GLOB[1])

    apply_rewrites(out_dir)

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
