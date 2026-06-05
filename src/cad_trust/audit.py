"""U2: AuditContext — context manager + emission API + CLI entrypoint shell.

Stdlib only. Failure-soft: insert errors warnings.warn() and continue,
NEVER abort the pipeline. The audit subsystem must not change pipeline
delivery semantics — its role is observation, not gating.
"""
from __future__ import annotations

import contextlib
import json
import sqlite3
import sys
import time
import uuid
import warnings
from datetime import datetime, timezone
from pathlib import Path
from types import TracebackType
from typing import Any

from cad_trust.audit_schema import init_audit_db

DEFAULT_DB_PATH = Path(".gem-squared") / "audit.sqlite"


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _json_dumps(payload: Any) -> str:
    """JSON serializer that handles most pipeline types without raising."""
    try:
        return json.dumps(payload, ensure_ascii=False, default=str)
    except Exception as exc:  # truly unserializable → soft-fail
        warnings.warn(f"audit: json_dumps fell back to repr ({exc})", stacklevel=3)
        return repr(payload)


class AuditContext:
    """Context manager that records one pipeline run into the audit DB.

    Usage:
        with AuditContext(db_path, drawing_id) as ctx:
            ctx.emit_stage_event("ingest", "INFO", "starting", {"path": str(p)})
            ...
    """

    def __init__(self, db_path: Path | str, drawing_id: str) -> None:
        self._db_path = db_path
        self._drawing_id = drawing_id
        self._run_id = uuid.uuid4().hex
        self._conn: sqlite3.Connection | None = None
        self._t0: float | None = None

    @property
    def run_id(self) -> str:
        return self._run_id

    @property
    def db_path(self) -> Path | str:
        return self._db_path

    # ── lifecycle ───────────────────────────────────────────────────────────

    def __enter__(self) -> "AuditContext":
        init_audit_db(self._db_path)  # idempotent
        self._conn = sqlite3.connect(str(self._db_path))
        self._conn.row_factory = sqlite3.Row
        self._t0 = time.perf_counter()
        try:
            self._conn.execute(
                "INSERT INTO runs(run_id, drawing_id, started_at, exit_state) "
                "VALUES (?, ?, ?, 'in_progress')",
                (self._run_id, self._drawing_id, _now_iso()),
            )
            self._conn.commit()
        except sqlite3.Error as exc:
            warnings.warn(f"audit: failed to insert runs row ({exc})", stacklevel=2)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if self._conn is None:
            return
        if self._t0 is not None:
            duration_ms = int((time.perf_counter() - self._t0) * 1000)
        else:
            duration_ms = 0
        if exc_type is None:
            exit_state = "SUCCESS"
            error_msg: str | None = None
        else:
            exit_state = "FAILURE"
            error_msg = f"{exc_type.__name__}: {exc_val}"
        try:
            self._conn.execute(
                "UPDATE runs SET completed_at = ?, duration_ms = ?, exit_state = ?, error_msg = ? "
                "WHERE run_id = ?",
                (_now_iso(), duration_ms, exit_state, error_msg, self._run_id),
            )
            self._conn.commit()
        except sqlite3.Error as exc:
            warnings.warn(f"audit: failed to update runs row on exit ({exc})", stacklevel=2)
        finally:
            with contextlib.suppress(Exception):
                self._conn.close()
            self._conn = None
        # Re-raise: never swallow user exceptions
        return None

    # ── emission API ────────────────────────────────────────────────────────

    def emit_stage_event(
        self,
        stage: str,
        level: str,
        message: str,
        payload: Any = None,
    ) -> None:
        if self._conn is None:
            warnings.warn("audit: emit_stage_event called outside of context", stacklevel=2)
            return
        payload_json = _json_dumps(payload) if payload is not None else None
        try:
            self._conn.execute(
                "INSERT INTO stage_events(run_id, stage, level, message, payload_json, timestamp) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (self._run_id, stage, level, message, payload_json, _now_iso()),
            )
            self._conn.commit()
        except sqlite3.Error as exc:
            warnings.warn(
                f"audit: emit_stage_event({stage!r}, {message!r}) failed: {exc}",
                stacklevel=2,
            )

    def record_policy_fire(self, policy_name: str, detail: Any = None) -> None:
        if self._conn is None:
            warnings.warn("audit: record_policy_fire called outside of context", stacklevel=2)
            return
        detail_json = _json_dumps(detail) if detail is not None else None
        try:
            self._conn.execute(
                "INSERT INTO policy_fires(run_id, policy_name, detail_json, timestamp) "
                "VALUES (?, ?, ?, ?)",
                (self._run_id, policy_name, detail_json, _now_iso()),
            )
            self._conn.commit()
        except sqlite3.Error as exc:
            warnings.warn(
                f"audit: record_policy_fire({policy_name!r}) failed: {exc}",
                stacklevel=2,
            )

    def record_refusal(
        self,
        region: Any,
        attempted_type: str,
        why: str,
    ) -> None:
        if self._conn is None:
            warnings.warn("audit: record_refusal called outside of context", stacklevel=2)
            return
        region_json = _json_dumps(region)
        try:
            self._conn.execute(
                "INSERT INTO refusals_log(run_id, region_json, attempted_type, why, recorded_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (self._run_id, region_json, attempted_type, why, _now_iso()),
            )
            self._conn.commit()
        except sqlite3.Error as exc:
            warnings.warn(
                f"audit: record_refusal({attempted_type!r}) failed: {exc}",
                stacklevel=2,
            )

    def record_epistemic_count(
        self,
        stage: str,
        tag: str,
        field: str,
        count: int,
    ) -> None:
        """UPSERT — (run_id, stage, tag, field) composite key."""
        if self._conn is None:
            warnings.warn("audit: record_epistemic_count called outside of context", stacklevel=2)
            return
        try:
            self._conn.execute(
                "INSERT INTO epistemic_counts(run_id, stage, tag, field, count) "
                "VALUES (?, ?, ?, ?, ?) "
                "ON CONFLICT(run_id, stage, tag, field) DO UPDATE SET count = excluded.count",
                (self._run_id, stage, tag, field, count),
            )
            self._conn.commit()
        except sqlite3.Error as exc:
            warnings.warn(
                f"audit: record_epistemic_count({stage!r}, {tag!r}, {field!r}) failed: {exc}",
                stacklevel=2,
            )

    def record_error(self, error_msg: str) -> None:
        """Record an error mid-run. exit_state will be set to FAILURE by __exit__."""
        self.emit_stage_event("pipeline", "ERROR", "error recorded", {"message": error_msg})


# ── convenience entrypoint ──────────────────────────────────────────────────


def audit_run(db_path: Path | str, drawing_id: str) -> AuditContext:
    """Construct an AuditContext. Use as `with audit_run(...) as ctx: ...`."""
    return AuditContext(db_path, drawing_id)


# ── CLI shell — U4 fills in subcommands ─────────────────────────────────────


def main(argv: list[str] | None = None) -> int:
    """U4 owns the real argparse routing. Provide a stub here so
    `python -m cad_trust.audit` doesn't 500 between U2 and U4."""
    print("cad_trust.audit CLI — U2 stub; subcommands land in U4", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
