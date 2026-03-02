from __future__ import annotations

import json
from datetime import datetime
from typing import Any

import aiosqlite
from .security import hash_password, verify_password


class Database:
    def __init__(self, path: str) -> None:
        self.path = path

    async def init(self) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute("PRAGMA foreign_keys = ON")
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER UNIQUE,
                    username TEXT,
                    full_name TEXT,
                    role TEXT CHECK(role IN ('intern', 'seller', 'admin')) NOT NULL,
                    password_hash TEXT UNIQUE NOT NULL,
                    is_used BOOLEAN DEFAULT FALSE,
                    is_active BOOLEAN DEFAULT TRUE,
                    warnings INTEGER DEFAULT 0,
                    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_warning_reset TIMESTAMP
                )
                """
            )
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS sales (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL REFERENCES users(id),
                    amount REAL NOT NULL,
                    screenshots TEXT NOT NULL,
                    status TEXT CHECK(status IN ('pending', 'need_more', 'approved', 'rejected')) DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    confirmed_by INTEGER REFERENCES users(id),
                    confirmed_at TIMESTAMP
                )
                """
            )
            await db.commit()

        await self.ensure_default_admin()

    async def ensure_default_admin(self) -> None:
        default_admin_tg_id = 7510792565
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("SELECT id FROM users WHERE user_id = ?", (default_admin_tg_id,))
            existing = await cur.fetchone()
            if existing:
                await db.execute(
                    "UPDATE users SET role = 'admin', is_active = TRUE, is_used = TRUE WHERE user_id = ?",
                    (default_admin_tg_id,),
                )
            else:
                placeholder_hash = hash_password("ALTShop-admin-seed")
                await db.execute(
                    """
                    INSERT INTO users(user_id, username, full_name, role, password_hash, is_used, is_active)
                    VALUES(?, ?, ?, 'admin', ?, TRUE, TRUE)
                    """,
                    (default_admin_tg_id, None, "Default Admin", placeholder_hash),
                )
            await db.commit()

    async def create_member(self, role: str, full_name: str, raw_password: str) -> None:
        password_hash = hash_password(raw_password)
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "INSERT INTO users(role, full_name, password_hash, is_used) VALUES(?, ?, ?, FALSE)",
                (role, full_name, password_hash),
            )
            await db.commit()

    async def get_user_by_telegram_id(self, tg_id: int) -> dict[str, Any] | None:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("SELECT * FROM users WHERE user_id = ?", (tg_id,))
            row = await cur.fetchone()
            return dict(row) if row else None

    async def bind_user_with_password(self, tg_id: int, username: str | None, full_name: str, raw_password: str) -> dict[str, Any] | None:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("SELECT * FROM users WHERE is_used = FALSE")
            candidates = await cur.fetchall()

            matched = None
            for row in candidates:
                if verify_password(raw_password, row["password_hash"]):
                    matched = row
                    break

            if not matched:
                return None

            await db.execute(
                """
                UPDATE users
                SET user_id = ?, username = ?, full_name = ?, is_used = TRUE, registered_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (tg_id, username, full_name, matched["id"]),
            )
            await db.commit()

            cur = await db.execute("SELECT * FROM users WHERE id = ?", (matched["id"],))
            row = await cur.fetchone()
            return dict(row) if row else None

    async def all_staff(self) -> list[dict[str, Any]]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("SELECT * FROM users WHERE is_used = TRUE ORDER BY role, full_name")
            rows = await cur.fetchall()
            return [dict(r) for r in rows]

    async def list_users_for_warning(self) -> list[dict[str, Any]]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute(
                "SELECT * FROM users WHERE is_used = TRUE AND role IN ('intern', 'seller') ORDER BY full_name"
            )
            rows = await cur.fetchall()
            return [dict(r) for r in rows]

    async def issue_warning(self, user_db_id: int) -> dict[str, Any] | None:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("SELECT * FROM users WHERE id = ?", (user_db_id,))
            row = await cur.fetchone()
            if not row or not row["is_active"]:
                return None
            new_warnings = row["warnings"] + 1
            is_active = new_warnings < 3
            await db.execute("UPDATE users SET warnings = ?, is_active = ? WHERE id = ?", (new_warnings, is_active, user_db_id))
            await db.commit()
            cur = await db.execute("SELECT * FROM users WHERE id = ?", (user_db_id,))
            updated = await cur.fetchone()
            return dict(updated) if updated else None

    async def set_block_status(self, user_db_id: int, is_active: bool) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute("UPDATE users SET is_active = ? WHERE id = ?", (is_active, user_db_id))
            await db.commit()

    async def list_users(self, role: str | None = None) -> list[dict[str, Any]]:
        query = "SELECT * FROM users WHERE is_used = TRUE"
        params: tuple[Any, ...] = ()
        if role:
            query += " AND role = ?"
            params = (role,)
        query += " ORDER BY role, full_name"

        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute(query, params)
            rows = await cur.fetchall()
            return [dict(r) for r in rows]

    async def get_admins(self) -> list[dict[str, Any]]:
        return await self.list_users(role="admin")

    async def create_sale(self, user_db_id: int, amount: float, screenshots: list[str]) -> int:
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute(
                "INSERT INTO sales(user_id, amount, screenshots, status) VALUES(?, ?, ?, 'pending')",
                (user_db_id, amount, json.dumps(screenshots)),
            )
            await db.commit()
            return cur.lastrowid

    async def get_sale(self, sale_id: int) -> dict[str, Any] | None:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("SELECT * FROM sales WHERE id = ?", (sale_id,))
            row = await cur.fetchone()
            if not row:
                return None
            obj = dict(row)
            obj["screenshots"] = json.loads(obj["screenshots"])
            return obj

    async def update_sale_status(self, sale_id: int, status: str, admin_db_id: int | None = None) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "UPDATE sales SET status = ?, confirmed_by = ?, confirmed_at = CURRENT_TIMESTAMP WHERE id = ?",
                (status, admin_db_id, sale_id),
            )
            await db.commit()

    async def month_sales(self, user_db_id: int) -> float:
        now = datetime.now()
        start = datetime(now.year, now.month, 1).strftime("%Y-%m-%d %H:%M:%S")
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute(
                "SELECT COALESCE(SUM(amount), 0) FROM sales WHERE user_id = ? AND status = 'approved' AND created_at >= ?",
                (user_db_id, start),
            )
            row = await cur.fetchone()
            return float(row[0]) if row else 0.0

    async def month_stats(self, user_db_id: int) -> tuple[float, int]:
        now = datetime.now()
        start = datetime(now.year, now.month, 1).strftime("%Y-%m-%d %H:%M:%S")
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute(
                "SELECT COALESCE(SUM(amount), 0), COUNT(*) FROM sales WHERE user_id = ? AND status = 'approved' AND created_at >= ?",
                (user_db_id, start),
            )
            row = await cur.fetchone()
            return (float(row[0]), int(row[1])) if row else (0.0, 0)

    async def month_sales_for_user_id(self, user_db_id: int) -> list[dict[str, Any]]:
        now = datetime.now()
        start = datetime(now.year, now.month, 1).strftime("%Y-%m-%d %H:%M:%S")
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute(
                "SELECT * FROM sales WHERE user_id = ? AND created_at >= ? ORDER BY created_at DESC",
                (user_db_id, start),
            )
            rows = await cur.fetchall()
            return [dict(r) for r in rows]

    async def reset_warnings(self) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "UPDATE users SET warnings = 0, last_warning_reset = CURRENT_TIMESTAMP WHERE is_used = TRUE"
            )
            await db.commit()
