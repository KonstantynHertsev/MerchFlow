import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(os.getenv("DATA_DIR", ".")) / "merchflow.db"

FREE_LIMIT = 50

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id                     INTEGER PRIMARY KEY AUTOINCREMENT,
    email                  TEXT    UNIQUE NOT NULL,
    password_hash          TEXT    NOT NULL,
    created_at             TEXT    NOT NULL DEFAULT (datetime('now')),
    tier                   TEXT    NOT NULL DEFAULT 'free',
    usage_month            TEXT    NOT NULL DEFAULT '',
    usage_count            INTEGER NOT NULL DEFAULT 0,
    paddle_subscription_id TEXT    NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS waitlist (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    email      TEXT    UNIQUE NOT NULL,
    created_at TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS feedback (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL,
    email      TEXT    NOT NULL,
    rating     INTEGER NOT NULL,
    comment    TEXT    NOT NULL DEFAULT '',
    created_at TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS password_reset_tokens (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL,
    token      TEXT    UNIQUE NOT NULL,
    expires_at TEXT    NOT NULL,
    used       INTEGER NOT NULL DEFAULT 0,
    created_at TEXT    NOT NULL DEFAULT (datetime('now'))
);
"""


def init_db():
    with _conn() as con:
        con.executescript(SCHEMA)
        # Migrate existing users table if columns are missing
        cols = {r[1] for r in con.execute("PRAGMA table_info(users)").fetchall()}
        if "usage_month" not in cols:
            con.execute("ALTER TABLE users ADD COLUMN usage_month TEXT NOT NULL DEFAULT ''")
        if "usage_count" not in cols:
            con.execute("ALTER TABLE users ADD COLUMN usage_count INTEGER NOT NULL DEFAULT 0")
        if "paddle_subscription_id" not in cols:
            con.execute("ALTER TABLE users ADD COLUMN paddle_subscription_id TEXT NOT NULL DEFAULT ''")


@contextmanager
def _conn():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    finally:
        con.close()


def create_user(email: str, password_hash: str) -> int:
    with _conn() as con:
        cur = con.execute(
            "INSERT INTO users (email, password_hash) VALUES (?, ?)",
            (email.lower().strip(), password_hash),
        )
        return cur.lastrowid


def get_user_by_email(email: str) -> dict | None:
    with _conn() as con:
        row = con.execute(
            "SELECT * FROM users WHERE email = ?", (email.lower().strip(),)
        ).fetchone()
        return dict(row) if row else None


def get_user_by_id(user_id: int) -> dict | None:
    with _conn() as con:
        row = con.execute(
            "SELECT * FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        return dict(row) if row else None


def get_usage(user_id: int, current_month: str) -> int:
    """Return images processed this month, resetting counter if month changed."""
    with _conn() as con:
        row = con.execute(
            "SELECT usage_month, usage_count, tier FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        if not row:
            return 0
        if row["tier"] == "pro":
            return 0  # unlimited
        if row["usage_month"] != current_month:
            con.execute(
                "UPDATE users SET usage_month = ?, usage_count = 0 WHERE id = ?",
                (current_month, user_id),
            )
            return 0
        return row["usage_count"]


def increment_usage(user_id: int, current_month: str, count: int):
    with _conn() as con:
        con.execute(
            """UPDATE users
               SET usage_month = ?, usage_count = usage_count + ?
               WHERE id = ?""",
            (current_month, count, user_id),
        )


def add_to_waitlist(email: str) -> bool:
    """Returns True if added, False if already on list."""
    try:
        with _conn() as con:
            con.execute(
                "INSERT INTO waitlist (email) VALUES (?)", (email.lower().strip(),)
            )
        return True
    except sqlite3.IntegrityError:
        return False


def get_waitlist() -> list[dict]:
    with _conn() as con:
        rows = con.execute(
            "SELECT email, created_at FROM waitlist ORDER BY created_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]


def add_feedback(user_id: int, email: str, rating: int, comment: str):
    with _conn() as con:
        con.execute(
            "INSERT INTO feedback (user_id, email, rating, comment) VALUES (?, ?, ?, ?)",
            (user_id, email, rating, comment),
        )


def get_all_feedback() -> list[dict]:
    with _conn() as con:
        rows = con.execute(
            "SELECT email, rating, comment, created_at FROM feedback ORDER BY created_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]


def create_reset_token(user_id: int, token: str, expires_at: str):
    with _conn() as con:
        con.execute(
            "UPDATE password_reset_tokens SET used = 1 WHERE user_id = ?", (user_id,)
        )
        con.execute(
            "INSERT INTO password_reset_tokens (user_id, token, expires_at) VALUES (?, ?, ?)",
            (user_id, token, expires_at),
        )


def get_reset_token(token: str) -> dict | None:
    with _conn() as con:
        row = con.execute(
            "SELECT * FROM password_reset_tokens WHERE token = ? AND used = 0", (token,)
        ).fetchone()
        return dict(row) if row else None


def use_reset_token(token: str, new_password_hash: str) -> bool:
    with _conn() as con:
        row = con.execute(
            "SELECT user_id FROM password_reset_tokens WHERE token = ? AND used = 0", (token,)
        ).fetchone()
        if not row:
            return False
        con.execute("UPDATE password_reset_tokens SET used = 1 WHERE token = ?", (token,))
        con.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?", (new_password_hash, row["user_id"])
        )
        return True


def set_user_tier(user_id: int, tier: str, subscription_id: str = ""):
    with _conn() as con:
        con.execute(
            "UPDATE users SET tier = ?, paddle_subscription_id = ? WHERE id = ?",
            (tier, subscription_id, user_id),
        )


def set_user_tier_by_subscription(subscription_id: str, tier: str):
    with _conn() as con:
        con.execute(
            "UPDATE users SET tier = ? WHERE paddle_subscription_id = ?",
            (tier, subscription_id),
        )


def get_all_users() -> list[dict]:
    with _conn() as con:
        rows = con.execute(
            "SELECT id, email, tier, usage_month, usage_count, created_at FROM users ORDER BY created_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]
