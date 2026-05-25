import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiosqlite

from app.config import get_settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS sites (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT NOT NULL,
    email TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    company_json TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS registrations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    site_id INTEGER NOT NULL,
    catalog_id TEXT NOT NULL,
    catalog_name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    login TEXT,
    password TEXT,
    profile_url TEXT,
    backlink_url TEXT,
    error_message TEXT,
    log_json TEXT,
    started_at TEXT,
    finished_at TEXT,
    FOREIGN KEY (site_id) REFERENCES sites(id),
    UNIQUE(site_id, catalog_id)
);

CREATE TABLE IF NOT EXISTS email_codes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    site_id INTEGER,
    catalog_id TEXT,
    from_addr TEXT,
    subject TEXT,
    code TEXT,
    raw_snippet TEXT,
    received_at TEXT NOT NULL,
    FOREIGN KEY (site_id) REFERENCES sites(id)
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def init_db() -> None:
    settings = get_settings()
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(settings.db_path) as db:
        await db.executescript(SCHEMA)
        await db.commit()


async def create_site(url: str, email: str) -> int:
    now = _now()
    async with aiosqlite.connect(get_settings().db_path) as db:
        cur = await db.execute(
            "INSERT INTO sites (url, email, status, created_at, updated_at) VALUES (?, ?, 'pending', ?, ?)",
            (url, email, now, now),
        )
        await db.commit()
        return cur.lastrowid


async def update_site(site_id: int, **fields: Any) -> None:
    allowed = {"status", "company_json", "url", "email"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return
    updates["updated_at"] = _now()
    cols = ", ".join(f"{k} = ?" for k in updates)
    vals = list(updates.values()) + [site_id]
    async with aiosqlite.connect(get_settings().db_path) as db:
        await db.execute(f"UPDATE sites SET {cols} WHERE id = ?", vals)
        await db.commit()


async def get_site(site_id: int) -> dict | None:
    async with aiosqlite.connect(get_settings().db_path) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM sites WHERE id = ?", (site_id,))
        row = await cur.fetchone()
        return dict(row) if row else None


async def list_sites() -> list[dict]:
    async with aiosqlite.connect(get_settings().db_path) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM sites ORDER BY id DESC")
        rows = await cur.fetchall()
        return [dict(r) for r in rows]


async def create_registration(
    site_id: int, catalog_id: str, catalog_name: str
) -> int:
    now = _now()
    async with aiosqlite.connect(get_settings().db_path) as db:
        cur = await db.execute(
            """INSERT OR IGNORE INTO registrations
               (site_id, catalog_id, catalog_name, status, started_at)
               VALUES (?, ?, ?, 'pending', ?)""",
            (site_id, catalog_id, catalog_name, now),
        )
        await db.commit()
        if cur.lastrowid:
            return cur.lastrowid
        cur = await db.execute(
            "SELECT id FROM registrations WHERE site_id = ? AND catalog_id = ?",
            (site_id, catalog_id),
        )
        row = await cur.fetchone()
        return row[0]


async def update_registration(reg_id: int, **fields: Any) -> None:
    allowed = {
        "status",
        "login",
        "password",
        "profile_url",
        "backlink_url",
        "error_message",
        "log_json",
        "finished_at",
    }
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return
    cols = ", ".join(f"{k} = ?" for k in updates)
    vals = list(updates.values()) + [reg_id]
    async with aiosqlite.connect(get_settings().db_path) as db:
        await db.execute(f"UPDATE registrations SET {cols} WHERE id = ?", vals)
        await db.commit()


async def get_registrations_for_site(site_id: int) -> list[dict]:
    async with aiosqlite.connect(get_settings().db_path) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM registrations WHERE site_id = ? ORDER BY catalog_name",
            (site_id,),
        )
        return [dict(r) for r in await cur.fetchall()]


async def list_all_registrations() -> list[dict]:
    async with aiosqlite.connect(get_settings().db_path) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            """SELECT r.*, s.url as site_url, s.email as site_email
               FROM registrations r
               JOIN sites s ON s.id = r.site_id
               ORDER BY r.id DESC"""
        )
        return [dict(r) for r in await cur.fetchall()]


async def save_email_code(
    code: str,
    from_addr: str,
    subject: str,
    raw_snippet: str,
    site_id: int | None = None,
    catalog_id: str | None = None,
) -> None:
    async with aiosqlite.connect(get_settings().db_path) as db:
        await db.execute(
            """INSERT INTO email_codes
               (site_id, catalog_id, from_addr, subject, code, raw_snippet, received_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (site_id, catalog_id, from_addr, subject, code, raw_snippet, _now()),
        )
        await db.commit()


def parse_company_json(site_row: dict) -> dict:
    raw = site_row.get("company_json")
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}
