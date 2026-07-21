# Data notes

`data/` contains the Senate transcript corpus — raw session PDFs and the
processed per-session Parquet tables. Keep it outside Git. Its canonical
working copy is `OneDrive/_working-data/ar_congress/data`, linked here (as a
relative symlink) through `~/PARA/_working-data` so that project code can
keep using `data/...`.

Before working on a new computer, confirm that `~/PARA/_working-data` links
to that computer's local OneDrive sync folder, and that the `data` symlink
resolves from the project root.
