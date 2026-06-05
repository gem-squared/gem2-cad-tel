"""U2: AuditContext — context manager + emission API + CLI entrypoint shell.

Stdlib only. Failure-soft: insert errors warnings.warn() and continue,
NEVER abort the pipeline. The audit subsystem must not change pipeline
delivery semantics — its role is observation, not gating.
"""
from __future__ import annotations

import contextlib
import json
import os
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


# ── CLI subcommands ─────────────────────────────────────────────────────────


def _resolve_db_path(arg: str | None) -> Path:
    if arg:
        return Path(arg)
    env = os.environ.get("GEM2_VISION_AUDIT_DB")
    if env:
        return Path(env)
    return DEFAULT_DB_PATH


def _open_for_read(db_path: Path) -> sqlite3.Connection:
    if not db_path.exists():
        raise FileNotFoundError(f"audit DB not found: {db_path}")
    c = sqlite3.connect(str(db_path))
    c.row_factory = sqlite3.Row
    return c


def _print_table(rows: list[sqlite3.Row], cols: list[str]) -> None:
    if not rows:
        print("(no rows)")
        return
    widths = {c: max(len(c), max(len(str(r[c] if r[c] is not None else "")) for r in rows)) for c in cols}
    sep = "  "
    header = sep.join(c.ljust(widths[c]) for c in cols)
    print(header)
    print(sep.join("-" * widths[c] for c in cols))
    for r in rows:
        print(sep.join(str(r[c] if r[c] is not None else "").ljust(widths[c]) for c in cols))


def cmd_list_runs(args) -> int:
    db = _resolve_db_path(args.db)
    conn = _open_for_read(db)
    try:
        sql = (
            "SELECT run_id, drawing_id, started_at, duration_ms, exit_state "
            "FROM runs WHERE 1=1"
        )
        params: list[Any] = []
        if args.drawing_id:
            sql += " AND drawing_id = ?"
            params.append(args.drawing_id)
        sql += " ORDER BY started_at DESC LIMIT ?"
        params.append(args.limit)
        rows = conn.execute(sql, params).fetchall()
        _print_table(rows, ["run_id", "drawing_id", "started_at", "duration_ms", "exit_state"])
        return 0
    finally:
        conn.close()


def cmd_show_run(args) -> int:
    db = _resolve_db_path(args.db)
    conn = _open_for_read(db)
    try:
        run = conn.execute("SELECT * FROM runs WHERE run_id = ?", (args.run_id,)).fetchone()
        if run is None:
            print(f"run_id {args.run_id!r} not found", file=sys.stderr)
            return 1
        print(f"=== run_id: {run['run_id']} ===")
        for k in run.keys():
            print(f"  {k}: {run[k]}")
        print("\n--- stage_events ---")
        events = conn.execute(
            "SELECT timestamp, stage, level, message, payload_json "
            "FROM stage_events WHERE run_id = ? ORDER BY event_id",
            (args.run_id,),
        ).fetchall()
        _print_table(events, ["timestamp", "stage", "level", "message"])
        print("\n--- refusals_log ---")
        refs = conn.execute(
            "SELECT attempted_type, why FROM refusals_log WHERE run_id = ?",
            (args.run_id,),
        ).fetchall()
        _print_table(refs, ["attempted_type", "why"])
        print("\n--- policy_fires ---")
        pol = conn.execute(
            "SELECT policy_name, detail_json, timestamp FROM policy_fires WHERE run_id = ?",
            (args.run_id,),
        ).fetchall()
        _print_table(pol, ["timestamp", "policy_name", "detail_json"])
        print("\n--- epistemic_counts ---")
        eps = conn.execute(
            "SELECT stage, field, tag, count FROM epistemic_counts WHERE run_id = ? "
            "ORDER BY field, tag",
            (args.run_id,),
        ).fetchall()
        _print_table(eps, ["stage", "field", "tag", "count"])
        return 0
    finally:
        conn.close()


def cmd_refusals(args) -> int:
    db = _resolve_db_path(args.db)
    conn = _open_for_read(db)
    try:
        sql_parts = ["SELECT r.attempted_type, COUNT(*) AS cnt, runs.drawing_id "
                     "FROM refusals_log r JOIN runs ON r.run_id = runs.run_id WHERE 1=1"]
        params: list[Any] = []
        if args.drawing_id:
            sql_parts.append("AND runs.drawing_id = ?")
            params.append(args.drawing_id)
        if args.attempted_type:
            sql_parts.append("AND r.attempted_type = ?")
            params.append(args.attempted_type)
        sql_parts.append("GROUP BY r.attempted_type, runs.drawing_id ORDER BY cnt DESC")
        sql = " ".join(sql_parts)
        rows = conn.execute(sql, params).fetchall()
        if not rows:
            print("(no refusals match)")
            return 0
        _print_table(rows, ["attempted_type", "cnt", "drawing_id"])
        return 0
    finally:
        conn.close()


def cmd_stats(args) -> int:
    db = _resolve_db_path(args.db)
    conn = _open_for_read(db)
    try:
        total_runs = conn.execute("SELECT COUNT(*) AS c FROM runs").fetchone()["c"]
        success_runs = conn.execute(
            "SELECT COUNT(*) AS c FROM runs WHERE exit_state = 'SUCCESS'"
        ).fetchone()["c"]
        total_refusals = conn.execute("SELECT COUNT(*) AS c FROM refusals_log").fetchone()["c"]
        total_policy_fires = conn.execute(
            "SELECT COUNT(*) AS c FROM policy_fires"
        ).fetchone()["c"]
        print(f"runs:           {total_runs}  (SUCCESS: {success_runs})")
        print(f"refusals:       {total_refusals}")
        print(f"policy_fires:   {total_policy_fires}")
        print("\n--- epistemic distribution (across all runs) ---")
        dist = conn.execute(
            "SELECT field, tag, SUM(count) AS total FROM epistemic_counts "
            "GROUP BY field, tag ORDER BY field, tag"
        ).fetchall()
        _print_table(dist, ["field", "tag", "total"])
        print("\n--- top attempted_types for refusals ---")
        tops = conn.execute(
            "SELECT attempted_type, COUNT(*) AS cnt FROM refusals_log "
            "GROUP BY attempted_type ORDER BY cnt DESC LIMIT 10"
        ).fetchall()
        _print_table(tops, ["attempted_type", "cnt"])
        return 0
    finally:
        conn.close()


def _build_parser() -> "argparse.ArgumentParser":
    import argparse
    p = argparse.ArgumentParser(
        prog="cad_trust.audit",
        description="Audit DB query CLI for the CAD Trust Engine",
    )
    p.add_argument("--db", help=f"audit DB path (default: env GEM2_VISION_AUDIT_DB or {DEFAULT_DB_PATH})")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_list = sub.add_parser("list-runs", help="list recent pipeline runs")
    p_list.add_argument("--limit", type=int, default=20)
    p_list.add_argument("--drawing-id", default=None)
    p_list.set_defaults(func=cmd_list_runs)

    p_show = sub.add_parser("show-run", help="show events / refusals / policy fires for one run")
    p_show.add_argument("run_id")
    p_show.set_defaults(func=cmd_show_run)

    p_ref = sub.add_parser("refusals", help="aggregate refusal counts")
    p_ref.add_argument("--drawing-id", default=None)
    p_ref.add_argument("--attempted-type", default=None)
    p_ref.set_defaults(func=cmd_refusals)

    p_stats = sub.add_parser("stats", help="epistemic distribution + refusal rollup across all runs")
    p_stats.set_defaults(func=cmd_stats)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"error: {exc.__class__.__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
