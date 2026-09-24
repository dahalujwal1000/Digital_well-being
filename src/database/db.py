"""Thread-safe SQLite store for tracking data (restart-proof).

- WAL mode: dashboard can read while tracker writes.
- Commits every flush (15s) -> a crash loses at most 15s of data.
- Crash recovery: sessions left with end_time NULL are closed as CRASH
  on the next boot.
"""

import sqlite3
import threading
from datetime import datetime, timedelta
from pathlib import Path

from src.utils.log import get_logger
from src.utils.paths import get_data_dir

APP_DIR = get_data_dir()
DB_PATH = APP_DIR / "wellbeing.db"

log = get_logger("db")

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

CREATE TABLE IF NOT EXISTS web_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    hour INTEGER NOT NULL,
    site TEXT NOT NULL,
    active_sec INTEGER NOT NULL DEFAULT 0,
    UNIQUE(date, hour, site)
);
CREATE INDEX IF NOT EXISTS idx_web_date ON web_usage(date);
"""


class Store:
    def _connect(self) -> None:
        self._con = sqlite3.connect(str(self.path), check_same_thread=False)
        self._con.execute("PRAGMA journal_mode=WAL")
        self._con.execute("PRAGMA synchronous=NORMAL")
        self._con.executescript(SCHEMA)
        self._con.commit()

    def __init__(self, path: Path = DB_PATH):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._connect()

    # ------------------------------------------------------- resilience --
    # A locked/disk-busy DB or a closed connection must not kill the tracker:
    # reopen once and retry. The thread lock serializes access, so the retry
    # is safe from any caller thread.
    def _reconnect(self) -> None:
        try:
            self._con.close()
        except Exception:
            pass
        self._connect()
        log.info("SQLite reconnected")

    def _exec(self, sql: str, params=()) -> None:
        with self._lock:
            try:
                self._con.execute(sql, params)
                self._con.commit()
            except (sqlite3.OperationalError, sqlite3.ProgrammingError) as exc:
                log.warning("SQLite write error (%s) - reconnecting", exc)
                self._reconnect()
                self._con.execute(sql, params)
                self._con.commit()

    def _query(self, sql: str, params=()) -> list:
        with self._lock:
            try:
                cur = self._con.execute(sql, params)
                return cur.fetchall()
            except (sqlite3.OperationalError,
                    sqlite3.ProgrammingError) as exc:
                log.warning("SQLite read error (%s) - reconnecting", exc)
                self._reconnect()
                cur = self._con.execute(sql, params)
                return cur.fetchall()

    def close(self) -> None:
        with self._lock:
            try:
                self._con.commit()
                self._con.close()
            except sqlite3.ProgrammingError:
                pass          # already closed (e.g. after reconnect test)
            except sqlite3.Error:
                log.exception("error while closing SQLite connection")

    def log_event(self, etype: str, ts: datetime | None = None) -> None:
        self._exec("INSERT INTO events(timestamp, type) VALUES(?, ?)",
                   ((ts or datetime.now()).strftime("%Y-%m-%d %H:%M:%S"),
                    etype))

    # ------------------------------------------------------------ sessions --
    def open_session(self, date_str: str, boot_iso: str) -> int:
        sql = ("INSERT INTO sessions(date, boot_time, end_reason) "
               "VALUES(?, ?, 'RUNNING')")
        params = (date_str, boot_iso)
        with self._lock:
            try:
                cursor = self._con.execute(sql, params)
                self._con.commit()
            except (sqlite3.OperationalError,
                    sqlite3.ProgrammingError) as exc:
                log.warning("SQLite session insert error (%s) - "
                            "reconnecting", exc)
                self._reconnect()
                cursor = self._con.execute(sql, params)
                self._con.commit()
            return cursor.lastrowid

    def recover_crashed(self, now_iso: str) -> int:
        """Close sessions left RUNNING by a crash/previous run. Returns count.

        end_time is clamped to boot_time + tracked seconds (never past the
        recovery time), so an overnight crash doesn't count the whole
        offline night as open time."""
        with self._lock:
            rows = self._con.execute(
                "SELECT id, boot_time, active_sec, idle_sec FROM sessions "
                "WHERE end_time IS NULL").fetchall()
            count = 0
            for sid, boot_iso, active, idle in rows:
                try:
                    dt = datetime.strptime(
                        boot_iso, "%Y-%m-%d %H:%M:%S") + timedelta(
                            seconds=int(active) + int(idle))
                    end_iso = dt.strftime("%Y-%m-%d %H:%M:%S")
                except (ValueError, TypeError, OverflowError):
                    end_iso = now_iso
                # never credit time beyond the actual recovery moment
                if end_iso > now_iso:
                    end_iso = now_iso
                self._con.execute(
                    "UPDATE sessions SET end_time = ?, end_reason = 'CRASH' "
                    "WHERE id = ?", (end_iso, sid))
                count += 1
            self._con.commit()
            return count

    def day_totals(self, date_str: str) -> tuple[int, int]:
        """(SUM(active_sec), SUM(idle_sec)) across ALL sessions of a day.

        A single day can hold several sessions (boot/sleep/wake splits)."""
        rows = self._query(
            "SELECT COALESCE(SUM(active_sec), 0), COALESCE(SUM(idle_sec), 0) "
            "FROM sessions WHERE date = ?", (date_str,))
        return (rows[0][0], rows[0][1]) if rows else (0, 0)

    def close_session(self, sid: int, end_iso: str, reason: str) -> None:
        self._exec(
            "UPDATE sessions SET end_time = ?, end_reason = ? "
            "WHERE id = ?", (end_iso, reason, sid))

    def update_session_time(self, sid: int, active: int, idle: int) -> None:
        self._exec(
            "UPDATE sessions SET active_sec = active_sec + ?, "
            "idle_sec = idle_sec + ? WHERE id = ?", (active, idle, sid))

    def apply_flush(self, sid: int, app_rows: list, hourly_rows: list,
                    web_rows: list, active: int, idle: int) -> None:
        """Persist one tracker snapshot atomically."""
        with self._lock:
            for attempt in range(2):
                try:
                    for date_str, hour, app_name, exe, title, sec in app_rows:
                        self._con.execute(
                            "INSERT INTO app_usage(date, hour, app_name, "
                            "exe_path, window_title, active_sec) "
                            "VALUES(?,?,?,?,?,?) "
                            "ON CONFLICT(date, hour, app_name) DO UPDATE SET "
                            "exe_path = excluded.exe_path, "
                            "window_title = excluded.window_title, "
                            "active_sec = active_sec + excluded.active_sec",
                            (date_str, hour, app_name, exe, title, sec))
                    for date_str, hour, act, idle_sec in hourly_rows:
                        self._con.execute(
                            "INSERT INTO hourly(date, hour, active_sec, "
                            "idle_sec) VALUES(?,?,?,?) "
                            "ON CONFLICT(date, hour) DO UPDATE SET "
                            "active_sec = active_sec + excluded.active_sec, "
                            "idle_sec = idle_sec + excluded.idle_sec",
                            (date_str, hour, act, idle_sec))
                    for date_str, hour, site, sec in web_rows:
                        self._con.execute(
                            "INSERT INTO web_usage(date, hour, site, "
                            "active_sec) VALUES(?,?,?,?) "
                            "ON CONFLICT(date, hour, site) DO UPDATE SET "
                            "active_sec = active_sec + excluded.active_sec",
                            (date_str, hour, site, sec))
                    if active or idle:
                        self._con.execute(
                            "UPDATE sessions SET active_sec = active_sec + ?, "
                            "idle_sec = idle_sec + ? WHERE id = ?",
                            (active, idle, sid))
                    self._con.commit()
                    return
                except (sqlite3.OperationalError,
                        sqlite3.ProgrammingError) as exc:
                    try:
                        self._con.rollback()
                    except sqlite3.Error:
                        pass
                    if attempt:
                        raise
                    log.warning("SQLite flush error (%s) - reconnecting", exc)
                    self._reconnect()
                except Exception:
                    try:
                        self._con.rollback()
                    except sqlite3.Error:
                        pass
                    raise

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

    def add_web_time(self, date_str: str, hour: int, site: str,
                     seconds: int) -> None:
        self._exec(
            "INSERT INTO web_usage(date, hour, site, active_sec) "
            "VALUES(?,?,?,?) ON CONFLICT(date, hour, site) DO UPDATE SET "
            "active_sec = active_sec + excluded.active_sec",
            (date_str, hour, site, seconds))

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
            "SELECT app_name, MAX(window_title), SUM(active_sec), "
            "MAX(exe_path) "
            "FROM app_usage WHERE date = ? GROUP BY app_name "
            "ORDER BY SUM(active_sec) DESC", (date_str,))

    def web_for_day(self, date_str: str):
        return self._query(
            "SELECT site, SUM(active_sec) FROM web_usage WHERE date = ? "
            "GROUP BY site ORDER BY SUM(active_sec) DESC", (date_str,))

    def unlocks_for_day(self, date_str: str) -> int:
        row = self._query(
            "SELECT COUNT(*) FROM events WHERE type = 'UNLOCK' "
            "AND substr(timestamp, 1, 10) = ?", (date_str,))
        return row[0][0] if row else 0
