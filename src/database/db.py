"""Thread-safe SQLite store for tracking data (restart-proof).

- WAL mode: dashboard can read while tracker writes.
- Commits every flush (15s) -> a crash loses at most 15s of data.
- Crash recovery: sessions left with end_time NULL are closed as CRASH
  on the next boot.
"""

import sqlite3
import threading
from datetime import datetime
from pathlib import Path

APP_DIR = Path.home() / "AppData" / "Roaming" / "DigitalWellbeing"
DB_PATH = APP_DIR / "wellbeing.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    boot_time TEXT NOT NULL,
    end_time TEXT,
    end_reason TEXT NOT NULL DEFAULT 'RUNNING',
    active_sec INTEGER NOT NULL DEFAULT 0,
    idle_sec INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_sessions_date ON sessions(date);

CREATE TABLE IF NOT EXISTS app_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    hour INTEGER NOT NULL,
    app_name TEXT NOT NULL,
    exe_path TEXT,
    window_title TEXT,
    active_sec INTEGER NOT NULL DEFAULT 0,
    UNIQUE(date, hour, app_name)
);
CREATE INDEX IF NOT EXISTS idx_app_date ON app_usage(date);

CREATE TABLE IF NOT EXISTS hourly (
    date TEXT NOT NULL,
    hour INTEGER NOT NULL,
    active_sec INTEGER NOT NULL DEFAULT 0,
    idle_sec INTEGER NOT NULL DEFAULT 0,
    UNIQUE(date, hour)
);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    type TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_events_ts ON events(timestamp);
"""


class Store:
    def __init__(self, path: Path = DB_PATH):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._con = sqlite3.connect(str(path), check_same_thread=False)
        self._con.execute("PRAGMA journal_mode=WAL")
        self._con.execute("PRAGMA synchronous=NORMAL")
        self._con.executescript(SCHEMA)
        self._con.commit()

    def _exec(self, sql: str, params=()) -> None:
        with self._lock:
            self._con.execute(sql, params)
            self._con.commit()

    def _query(self, sql: str, params=()) -> list:
        with self._lock:
            cur = self._con.execute(sql, params)
            return cur.fetchall()

    def close(self) -> None:
        with self._lock:
            self._con.commit()
            self._con.close()

    def log_event(self, etype: str, ts: datetime | None = None) -> None:
        self._exec("INSERT INTO events(timestamp, type) VALUES(?, ?)",
                   ((ts or datetime.now()).strftime("%Y-%m-%d %H:%M:%S"),
                    etype))

    # ------------------------------------------------------------ sessions --
    def open_session(self, date_str: str, boot_iso: str) -> int:
        self._exec(
            "INSERT INTO sessions(date, boot_time, end_reason) "
            "VALUES(?, ?, 'RUNNING')", (date_str, boot_iso))
        return self._query("SELECT last_insert_rowid()")[0][0]

    def recover_crashed(self, now_iso: str) -> int:
        """Close sessions left RUNNING by a crash/previous run. Returns count."""
        with self._lock:
            cur = self._con.execute(
                "UPDATE sessions SET end_time = ?, end_reason = 'CRASH' "
                "WHERE end_time IS NULL", (now_iso,))
            self._con.commit()
            return cur.rowcount

    def close_session(self, sid: int, end_iso: str, reason: str) -> None:
        self._exec(
            "UPDATE sessions SET end_time = ?, end_reason = ? "
            "WHERE id = ?", (end_iso, reason, sid))

    def update_session_time(self, sid: int, active: int, idle: int) -> None:
        self._exec(
            "UPDATE sessions SET active_sec = active_sec + ?, "
            "idle_sec = idle_sec + ? WHERE id = ?", (active, idle, sid))

    def get_session(self, sid: int):
        rows = self._query(
            "SELECT date, boot_time, end_time, end_reason, active_sec, "
            "idle_sec FROM sessions WHERE id = ?", (sid,))
        return rows[0] if rows else None

    # ----------------------------------------------------------- app usage --
    def add_app_time(self, date_str: str, hour: int, app_name: str,
                     exe_path: str, title: str, seconds: int) -> None:
        self._exec(
            "INSERT INTO app_usage(date, hour, app_name, exe_path, "
            "window_title, active_sec) VALUES(?,?,?,?,?,?) "
            "ON CONFLICT(date, hour, app_name) DO UPDATE SET "
            "window_title = excluded.window_title, "
            "active_sec = active_sec + excluded.active_sec",
            (date_str, hour, app_name, exe_path, title, seconds))

    def add_hourly(self, date_str: str, hour: int, active: int,
                   idle: int) -> None:
        self._exec(
            "INSERT INTO hourly(date, hour, active_sec, idle_sec) "
            "VALUES(?,?,?,?) ON CONFLICT(date, hour) DO UPDATE SET "
            "active_sec = active_sec + excluded.active_sec, "
            "idle_sec = idle_sec + excluded.idle_sec",
            (date_str, hour, active, idle))

    # ------------------------------------------------------------- queries --
    def sessions_for_day(self, date_str: str):
        return self._query(
            "SELECT boot_time, end_time, end_reason, active_sec, idle_sec "
            "FROM sessions WHERE date = ? ORDER BY boot_time", (date_str,))

    def hourly_for_day(self, date_str: str):
        rows = self._query(
            "SELECT hour, active_sec, idle_sec FROM hourly WHERE date = ?",
            (date_str,))
        active = [0] * 24
        idle = [0] * 24
        for hour, a, i in rows:
            active[hour] = a
            idle[hour] = i
        return active, idle

    def apps_for_day(self, date_str: str):
        return self._query(
            "SELECT app_name, MAX(window_title), SUM(active_sec) "
            "FROM app_usage WHERE date = ? GROUP BY app_name "
            "ORDER BY SUM(active_sec) DESC", (date_str,))

    def unlocks_for_day(self, date_str: str) -> int:
        row = self._query(
            "SELECT COUNT(*) FROM events WHERE type = 'UNLOCK' "
            "AND substr(timestamp, 1, 10) = ?", (date_str,))
        return row[0][0] if row else 0
