# Data notes

`data/` contains the Senate transcript corpus — raw session files and the
processed per-sitting Parquet tables. It is kept outside Git. Put it in
`data/` at the project root, or make `data` a symlink to wherever it lives,
so the scripts can keep using `data/...`. `scripts/download.py` fetches the
sources again from the manifest.
