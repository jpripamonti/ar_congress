"""Map the chamber's own `session_type` label to a small set of canonical kinds.

`session_type` is the Senate's own wording for what kind of sitting a
transcript records ("TIPO DE SESION" in the portal listing). Several distinct
labels name the same kind of sitting under different spellings or procedural
detail -- `EN MINORÍA` and `ESPECIAL EN MINORÍA` are the chamber's own example
of this (see TODO.md). `session_type` is never overwritten: the chamber's
wording is evidence about the chamber and has to survive. This module only
adds a second, derived field, `session_kind`, alongside it.

The mapping itself is reference/senado/session_type_map.csv, one row per raw
label, with a `note` explaining the grouping and an `ambiguous` flag for
labels that mix two dimensions (e.g. a calling procedure and a period) and
were grouped by judgment call rather than a clean identity.
"""

import csv
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MAP_PATH = REPO_ROOT / "reference" / "senado" / "session_type_map.csv"

_map_cache = None


def _load_map():
    global _map_cache
    if _map_cache is None:
        mapping = {}
        with open(MAP_PATH, encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                mapping[row["session_type"].strip()] = row["session_kind"].strip()
        _map_cache = mapping
    return _map_cache


def session_kind_for(session_type):
    """Canonical kind for a raw session_type, or None if the label is unmapped.

    None (rather than a guess) is deliberate: an unmapped label means the
    portal has started using wording session_type_map.csv does not yet cover,
    and that should surface as a gap to fix in the reference table, not be
    silently absorbed into some existing bucket.
    """
    if not session_type:
        return None
    return _load_map().get(session_type.strip())
