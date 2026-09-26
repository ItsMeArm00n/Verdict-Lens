"""Local SQLite case store. One row per audit run so the case library is real, not seeded.

The database is a convenience for browsing past runs. It never influences a decision:
every stored case carries the frozen, complete audit result exactly as the auditor
returned it, and re-running an applicant always reproduces the same numbers.
"""
import json
import os
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(os.environ.get("VERDICTLENS_DB", Path(__file__).resolve().parent / "verdictlens.db"))
CASE_PREFIX = "VL"
_lock = threading.Lock()

_SCHEMA = """
CREATE TABLE IF NOT EXISTS cases (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    case_ref      TEXT    NOT NULL UNIQUE,
    created_at    TEXT    NOT NULL,
    stage         TEXT    NOT NULL,
    applicant     TEXT    NOT NULL,
    primary_json  TEXT,
    audit_json    TEXT
);
CREATE INDEX IF NOT EXISTS cases_created_at ON cases (created_at DESC);
"""


def _connect():
    connection = sqlite3.connect(DB_PATH, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    return connection


def initialize():
    with _lock, _connect() as connection:
        connection.executescript(_SCHEMA)


def _next_ref(connection):
    """Allocate the next VL-#### reference inside the same write transaction."""
    row = connection.execute("SELECT COALESCE(MAX(id), 0) AS top FROM cases").fetchone()
    return f"{CASE_PREFIX}-{int(row['top']) + 1:04d}"


def create_case(applicant, primary=None):
    """Persist an applicant and, when available, its primary prediction or full audit."""
    created_at = datetime.now(timezone.utc).isoformat()
    stage = "audit" if primary is None else "decision"
    with _lock, _connect() as connection:
        case_ref = _next_ref(connection)
        connection.execute(
            "INSERT INTO cases (case_ref, created_at, stage, applicant, primary_json, audit_json)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (
                case_ref,
                created_at,
                stage,
                json.dumps(applicant, allow_nan=False),
                json.dumps(primary, allow_nan=False) if primary else None,
                None,
            ),
        )
    return {"case_ref": case_ref, "created_at": created_at, "stage": stage}


def save_audit(case_ref, primary, audit):
    """Attach the frozen audit result to an existing case, upgrading its stage."""
    with _lock, _connect() as connection:
        result = connection.execute(
            "UPDATE cases SET stage = 'audit', primary_json = ?, audit_json = ? WHERE case_ref = ?",
            (json.dumps(primary, allow_nan=False), json.dumps(audit, allow_nan=False), case_ref),
        )
        if result.rowcount == 0:
            raise KeyError(case_ref)
    return get_case(case_ref)


def _summary(row):
    audit = json.loads(row["audit_json"]) if row["audit_json"] else None
    primary = json.loads(row["primary_json"]) if row["primary_json"] else None
    return {
        "case_ref": row["case_ref"],
        "created_at": row["created_at"],
        "stage": row["stage"],
        "decision": primary["decision"] if primary else None,
        "risk_estimate": primary["risk_estimate"] if primary else None,
        "threshold": primary["threshold"] if primary else None,
        "signed_margin": primary["signed_margin"] if primary else None,
        "status": audit["status"] if audit else None,
        "flags": audit["flags"] if audit else [],
        "flag_count": len(audit["flags"]) if audit else 0,
    }


def list_cases(search="", status="all", decision="all", limit=200, offset=0):
    rows = _connect().execute(
        "SELECT case_ref, created_at, stage, applicant, primary_json, audit_json"
        " FROM cases ORDER BY id DESC"
    ).fetchall()
    cases = [_summary(row) for row in rows]
    if search:
        needle = search.strip().lower()
        cases = [c for c in cases if needle in c["case_ref"].lower()]
    if status != "all":
        cases = [c for c in cases if (c["status"] == "REVIEW") == (status == "review")]
    if decision != "all":
        cases = [c for c in cases if c["decision"] == decision.upper()]
    return {"total": len(cases), "cases": cases[offset : offset + limit]}


def get_case(case_ref):
    row = _connect().execute("SELECT * FROM cases WHERE case_ref = ?", (case_ref,)).fetchone()
    if row is None:
        raise KeyError(case_ref)
    return {
        "case_ref": row["case_ref"],
        "created_at": row["created_at"],
        "stage": row["stage"],
        "applicant": json.loads(row["applicant"]),
        "primary": json.loads(row["primary_json"]) if row["primary_json"] else None,
        "audit": json.loads(row["audit_json"]) if row["audit_json"] else None,
    }


def delete_case(case_ref):
    with _lock, _connect() as connection:
        result = connection.execute("DELETE FROM cases WHERE case_ref = ?", (case_ref,))
    if result.rowcount == 0:
        raise KeyError(case_ref)
    return {"deleted": case_ref}
