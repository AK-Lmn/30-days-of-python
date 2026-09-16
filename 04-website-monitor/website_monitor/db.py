from datetime import datetime, timezone, timedelta
import json
from pathlib import Path
import sqlite3
from typing import Any, Dict, List, Optional

from website_monitor.config import get_default_db_path, DEFAULT_RETENTION_DAYS
from website_monitor.models import MonitorTarget, CheckResult, Incident, TargetStats


def get_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    target_path = db_path or get_default_db_path()
    target_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(target_path))
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    return conn


def init_db(db_path: Optional[Path] = None) -> None:
    with get_connection(db_path) as conn:
        conn.execute(
            'CREATE TABLE IF NOT EXISTS targets ('
            'id INTEGER PRIMARY KEY AUTOINCREMENT, '
            'url TEXT NOT NULL UNIQUE, '
            'name TEXT NOT NULL, '
            'method TEXT NOT NULL DEFAULT \'GET\', '
            'expected_status INTEGER NOT NULL DEFAULT 200, '
            'keyword TEXT, '
            'timeout_seconds REAL NOT NULL DEFAULT 10.0, '
            'check_interval_seconds INTEGER NOT NULL DEFAULT 60, '
            'headers TEXT NOT NULL DEFAULT \'{}\', '
            'request_body TEXT, '
            'tags TEXT NOT NULL DEFAULT \'[]\', '
            'is_active INTEGER NOT NULL DEFAULT 1, '
            'created_at TEXT NOT NULL)'
        )
        conn.execute(
            'CREATE TABLE IF NOT EXISTS check_logs ('
            'id INTEGER PRIMARY KEY AUTOINCREMENT, '
            'target_id INTEGER NOT NULL REFERENCES targets(id) ON DELETE CASCADE, '
            'is_up INTEGER NOT NULL, '
            'status_code INTEGER, '
            'response_time_ms REAL NOT NULL, '
            'error_message TEXT, '
            'ssl_days_left INTEGER, '
            'checked_at TEXT NOT NULL)'
        )
        conn.execute(
            'CREATE TABLE IF NOT EXISTS incidents ('
            'id INTEGER PRIMARY KEY AUTOINCREMENT, '
            'target_id INTEGER NOT NULL REFERENCES targets(id) ON DELETE CASCADE, '
            'reason TEXT NOT NULL, '
            'started_at TEXT NOT NULL, '
            'ended_at TEXT, '
            'duration_seconds REAL, '
            'resolved INTEGER NOT NULL DEFAULT 0)'
        )
        conn.execute('CREATE INDEX IF NOT EXISTS idx_check_logs_target_time ON check_logs(target_id, checked_at)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_incidents_target_resolved ON incidents(target_id, resolved)')
        conn.commit()


def add_target(target: MonitorTarget, db_path: Optional[Path] = None) -> MonitorTarget:
    init_db(db_path)
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO targets ('
            'url, name, method, expected_status, keyword, '
            'timeout_seconds, check_interval_seconds, headers, '
            'request_body, tags, is_active, created_at) '
            'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (
                target.url,
                target.name,
                target.method,
                target.expected_status,
                target.keyword,
                target.timeout_seconds,
                target.check_interval_seconds,
                json.dumps(target.headers),
                target.request_body,
                json.dumps(target.tags),
                1 if target.is_active else 0,
                target.created_at,
            ),
        )
        target.id = cursor.lastrowid
        conn.commit()
    return target


def get_target(target_id: int, db_path: Optional[Path] = None) -> Optional[MonitorTarget]:
    init_db(db_path)
    with get_connection(db_path) as conn:
        row = conn.execute('SELECT * FROM targets WHERE id = ?', (target_id,)).fetchone()
        if row:
            return MonitorTarget.from_row(row)
    return None


def get_target_by_url(url: str, db_path: Optional[Path] = None) -> Optional[MonitorTarget]:
    init_db(db_path)
    with get_connection(db_path) as conn:
        row = conn.execute('SELECT * FROM targets WHERE url = ?', (url.strip(),)).fetchone()
        if row:
            return MonitorTarget.from_row(row)
    return None


def list_targets(
    active_only: bool = False, tag: Optional[str] = None, db_path: Optional[Path] = None
) -> List[MonitorTarget]:
    init_db(db_path)
    query = 'SELECT * FROM targets WHERE 1=1'
    params: List[Any] = []
    if active_only:
        query += ' AND is_active = 1'
    query += ' ORDER BY id ASC'

    with get_connection(db_path) as conn:
        rows = conn.execute(query, params).fetchall()
        results = [MonitorTarget.from_row(r) for r in rows]

    if tag:
        clean_tag = tag.strip().lower()
        results = [t for t in results if clean_tag in [x.lower() for x in t.tags]]

    return results


def update_target(target: MonitorTarget, db_path: Optional[Path] = None) -> bool:
    if target.id is None:
        return False
    init_db(db_path)
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            'UPDATE targets SET '
            'url = ?, name = ?, method = ?, expected_status = ?, '
            'keyword = ?, timeout_seconds = ?, check_interval_seconds = ?, '
            'headers = ?, request_body = ?, tags = ?, is_active = ? '
            'WHERE id = ?',
            (
                target.url,
                target.name,
                target.method,
                target.expected_status,
                target.keyword,
                target.timeout_seconds,
                target.check_interval_seconds,
                json.dumps(target.headers),
                target.request_body,
                json.dumps(target.tags),
                1 if target.is_active else 0,
                target.id,
            ),
        )
        conn.commit()
        return cursor.rowcount > 0


def delete_target(target_id: int, db_path: Optional[Path] = None) -> bool:
    init_db(db_path)
    with get_connection(db_path) as conn:
        cursor = conn.execute('DELETE FROM targets WHERE id = ?', (target_id,))
        conn.commit()
        return cursor.rowcount > 0


def record_check(result: CheckResult, db_path: Optional[Path] = None) -> int:
    init_db(db_path)
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            'INSERT INTO check_logs ('
            'target_id, is_up, status_code, response_time_ms, '
            'error_message, ssl_days_left, checked_at) '
            'VALUES (?, ?, ?, ?, ?, ?, ?)',
            (
                result.target_id,
                1 if result.is_up else 0,
                result.status_code,
                result.response_time_ms,
                result.error_message,
                result.ssl_days_left,
                result.checked_at,
            ),
        )
        result.id = cursor.lastrowid
        conn.commit()
        return result.id


def get_recent_checks(
    target_id: Optional[int] = None, limit: int = 50, db_path: Optional[Path] = None
) -> List[CheckResult]:
    init_db(db_path)
    with get_connection(db_path) as conn:
        if target_id is not None:
            query = (
                'SELECT c.*, t.name as target_name, t.url as target_url '
                'FROM check_logs c '
                'JOIN targets t ON c.target_id = t.id '
                'WHERE c.target_id = ? '
                'ORDER BY c.checked_at DESC, c.id DESC '
                'LIMIT ?'
            )
            rows = conn.execute(query, (target_id, limit)).fetchall()
        else:
            query = (
                'SELECT c.*, t.name as target_name, t.url as target_url '
                'FROM check_logs c '
                'JOIN targets t ON c.target_id = t.id '
                'ORDER BY c.checked_at DESC, c.id DESC '
                'LIMIT ?'
            )
            rows = conn.execute(query, (limit,)).fetchall()
        return [CheckResult.from_row(r) for r in rows]


def get_active_incident(target_id: int, db_path: Optional[Path] = None) -> Optional[Incident]:
    init_db(db_path)
    with get_connection(db_path) as conn:
        query = (
            'SELECT i.*, t.name as target_name, t.url as target_url '
            'FROM incidents i '
            'JOIN targets t ON i.target_id = t.id '
            'WHERE i.target_id = ? AND i.resolved = 0 '
            'ORDER BY i.id DESC '
            'LIMIT 1'
        )
        row = conn.execute(query, (target_id,)).fetchone()
        if row:
            return Incident.from_row(row)
    return None


def open_incident(
    target_id: int, reason: str, started_at: Optional[str] = None, db_path: Optional[Path] = None
) -> Incident:
    init_db(db_path)
    existing = get_active_incident(target_id, db_path)
    if existing:
        return existing

    ts = started_at or datetime.now(timezone.utc).isoformat()
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            'INSERT INTO incidents (target_id, reason, started_at, resolved) '
            'VALUES (?, ?, ?, 0)',
            (target_id, reason, ts),
        )
        incident_id = cursor.lastrowid
        conn.commit()

    target = get_target(target_id, db_path)
    return Incident(
        id=incident_id,
        target_id=target_id,
        target_name=target.name if target else None,
        target_url=target.url if target else None,
        reason=reason,
        started_at=ts,
        resolved=False,
    )


def resolve_incident(
    incident_id: int, ended_at: Optional[str] = None, db_path: Optional[Path] = None
) -> Optional[Incident]:
    init_db(db_path)
    ts = ended_at or datetime.now(timezone.utc).isoformat()
    with get_connection(db_path) as conn:
        row = conn.execute('SELECT * FROM incidents WHERE id = ?', (incident_id,)).fetchone()
        if not row:
            return None

        incident = Incident.from_row(row)
        try:
            st = datetime.fromisoformat(incident.started_at)
            et = datetime.fromisoformat(ts)
            duration = max(0.0, (et - st).total_seconds())
        except Exception:
            duration = 0.0

        conn.execute(
            'UPDATE incidents SET ended_at = ?, duration_seconds = ?, resolved = 1 WHERE id = ?',
            (ts, duration, incident_id),
        )
        conn.commit()

        updated_row = conn.execute(
            'SELECT i.*, t.name as target_name, t.url as target_url '
            'FROM incidents i '
            'JOIN targets t ON i.target_id = t.id '
            'WHERE i.id = ?',
            (incident_id,),
        ).fetchone()
        if updated_row:
            return Incident.from_row(updated_row)
    return None


def list_incidents(
    target_id: Optional[int] = None,
    limit: int = 50,
    unresolved_only: bool = False,
    db_path: Optional[Path] = None,
) -> List[Incident]:
    init_db(db_path)
    query = (
        'SELECT i.*, t.name as target_name, t.url as target_url '
        'FROM incidents i '
        'JOIN targets t ON i.target_id = t.id '
        'WHERE 1=1'
    )
    params: List[Any] = []
    if target_id is not None:
        query += ' AND i.target_id = ?'
        params.append(target_id)
    if unresolved_only:
        query += ' AND i.resolved = 0'
    query += ' ORDER BY i.id DESC LIMIT ?'
    params.append(limit)

    with get_connection(db_path) as conn:
        rows = conn.execute(query, params).fetchall()
        return [Incident.from_row(r) for r in rows]


def get_target_stats(
    target_id: int, hours: Optional[int] = None, db_path: Optional[Path] = None
) -> Optional[TargetStats]:
    init_db(db_path)
    target = get_target(target_id, db_path)
    if not target:
        return None

    query = 'SELECT is_up, status_code, response_time_ms, checked_at, ssl_days_left FROM check_logs WHERE target_id = ?'
    params: List[Any] = [target_id]
    if hours is not None and hours > 0:
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
        query += ' AND checked_at >= ?'
        params.append(cutoff)
    query += ' ORDER BY checked_at ASC'

    with get_connection(db_path) as conn:
        rows = conn.execute(query, params).fetchall()

    active_inc = get_active_incident(target_id, db_path) is not None

    if not rows:
        return TargetStats(
            target_id=target.id or 0,
            target_name=target.name,
            target_url=target.url,
            total_checks=0,
            up_checks=0,
            down_checks=0,
            uptime_percentage=100.0,
            avg_latency_ms=0.0,
            min_latency_ms=0.0,
            p95_latency_ms=0.0,
            max_latency_ms=0.0,
            active_incident=active_inc,
        )

    total_checks = len(rows)
    up_checks = sum(1 for r in rows if r['is_up'])
    down_checks = total_checks - up_checks
    uptime_percentage = (up_checks / total_checks) * 100.0 if total_checks > 0 else 100.0

    latencies = [float(r['response_time_ms']) for r in rows]
    latencies.sort()
    avg_latency = sum(latencies) / len(latencies)
    min_latency = latencies[0]
    max_latency = latencies[-1]
    p95_idx = int(0.95 * (len(latencies) - 1))
    p95_latency = latencies[p95_idx]

    last_row = rows[-1]
    return TargetStats(
        target_id=target.id or 0,
        target_name=target.name,
        target_url=target.url,
        total_checks=total_checks,
        up_checks=up_checks,
        down_checks=down_checks,
        uptime_percentage=uptime_percentage,
        avg_latency_ms=avg_latency,
        min_latency_ms=min_latency,
        p95_latency_ms=p95_latency,
        max_latency_ms=max_latency,
        active_incident=active_inc,
        last_status_code=last_row['status_code'],
        last_latency_ms=float(last_row['response_time_ms']),
        last_checked_at=last_row['checked_at'],
        last_is_up=bool(last_row['is_up']),
        ssl_days_left=last_row['ssl_days_left'],
    )


def get_all_target_stats(
    hours: Optional[int] = None, db_path: Optional[Path] = None
) -> List[TargetStats]:
    init_db(db_path)
    targets = list_targets(db_path=db_path)
    stats_list = []
    for t in targets:
        if t.id is not None:
            st = get_target_stats(t.id, hours=hours, db_path=db_path)
            if st:
                stats_list.append(st)
    return stats_list


def get_latency_history(
    target_id: int, limit: int = 60, db_path: Optional[Path] = None
) -> List[float]:
    init_db(db_path)
    with get_connection(db_path) as conn:
        rows = conn.execute(
            'SELECT response_time_ms FROM check_logs '
            'WHERE target_id = ? '
            'ORDER BY checked_at DESC, id DESC '
            'LIMIT ?',
            (target_id, limit),
        ).fetchall()
        res = [float(r['response_time_ms']) for r in rows]
        res.reverse()
        return res


def prune_logs(retention_days: int = DEFAULT_RETENTION_DAYS, db_path: Optional[Path] = None) -> int:
    init_db(db_path)
    cutoff = (datetime.now(timezone.utc) - timedelta(days=retention_days)).isoformat()
    with get_connection(db_path) as conn:
        cursor = conn.execute('DELETE FROM check_logs WHERE checked_at < ?', (cutoff,))
        conn.commit()
        return cursor.rowcount


def get_consecutive_failures(target_id: int, db_path: Optional[Path] = None) -> int:
    init_db(db_path)
    with get_connection(db_path) as conn:
        rows = conn.execute(
            'SELECT is_up FROM check_logs WHERE target_id = ? ORDER BY checked_at DESC, id DESC LIMIT 20',
            (target_id,),
        ).fetchall()
        count = 0
        for r in rows:
            if not r['is_up']:
                count += 1
            else:
                break
        return count

