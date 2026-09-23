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

EVIDENCE_PATH = REPO_ROOT / "reference" / "senado" / "session_convened_as.csv"

_map_cache = None
_rows_cache = None
_evidence_cache = None


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


# `session_kind` holds two dimensions in one column: how a sitting was called
# (ordinaria, especial, extraordinaria, ...) and whether it reached a quorum
# (en_minoria, sin_quorum). A sitting that failed to reach quorum was still
# called as something, and one column cannot say both. The two functions
# below split them. `session_kind` itself is left as it was, so nothing that
# already groups by it changes.


def _rows():
    global _rows_cache
    if _rows_cache is None:
        with open(MAP_PATH, encoding="utf-8") as fh:
            _rows_cache = {r["session_type"].strip(): r for r in csv.DictReader(fh)}
    return _rows_cache


def _evidence():
    global _evidence_cache
    if _evidence_cache is None:
        with open(EVIDENCE_PATH, encoding="utf-8") as fh:
            _evidence_cache = {r["session_id"]: r["convened_as"] for r in csv.DictReader(fh)}
    return _evidence_cache


def quorum_failed_for(session_type):
    """True where the chamber's own label says the sitting had no quorum.

    Read from the label alone, never inferred. False means the label records
    no failure, not that a quorum was counted. None for an unmapped label.
    """
    row = _rows().get((session_type or "").strip())
    return None if row is None else row["quorum_failed"] == "true"


def convened_as_for(session_type, session_id):
    """How the sitting was called, or None where the record does not say.

    For most labels it is the label's own kind. A sitting without quorum is
    labelled only as that ("EN MINORÍA"), and what it had been called as is
    taken from the sitting itself — its cover or the words spoken in it —
    one sitting at a time, in session_convened_as.csv with the quote. The
    running header some of these print ("Versión provisional - sesión
    ordinaria") is a template: on 8 December 1998 it says "ordinaria" over
    a sitting the chair calls "la otra sesión especial prevista para hoy",
    so it is never read. Where nothing says, the answer is None, not a
    default.
    """
    row = _rows().get((session_type or "").strip())
    if row is None:
        return None
    if row["convened_as"]:
        return row["convened_as"]
    return _evidence().get(session_id)
