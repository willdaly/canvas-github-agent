"""SQLite-backed users, encrypted credentials, and session tokens."""

from __future__ import annotations

import hashlib
import os
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from threading import RLock
from typing import Optional

from app.credential_crypto import CredentialCryptoError, decrypt_secret, encrypt_secret

DEFAULT_USER_DB_PATH = ".data/users.sqlite3"
SESSION_COOKIE_NAME = "cga_session"
SESSION_TTL_DAYS = int(os.getenv("SESSION_TTL_DAYS", "30") or "30")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class UserStore:
    def __init__(self, db_path: str | None = None):
        configured = (db_path or os.getenv("USER_STORE_PATH", DEFAULT_USER_DB_PATH)).strip()
        self.db_path = configured or DEFAULT_USER_DB_PATH
        self._lock = RLock()
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _ensure_schema(self) -> None:
        directory = os.path.dirname(self.db_path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS user_credentials (
                    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
                    canvas_token_cipher BLOB NOT NULL,
                    github_token_cipher BLOB NOT NULL,
                    github_username TEXT NOT NULL DEFAULT '',
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS sessions (
                    token_hash TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    expires_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
                """
            )
            conn.commit()

    def create_session_with_credentials(
        self,
        *,
        canvas_token: str,
        github_token: str,
        github_username: str,
    ) -> tuple[str, int]:
        """Create user, store encrypted tokens, return (raw_session_token, user_id)."""
        canvas_cipher = encrypt_secret(canvas_token)
        github_cipher = encrypt_secret(github_token)
        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        expires = (_utcnow() + timedelta(days=SESSION_TTL_DAYS)).isoformat()

        with self._lock, self._connect() as conn:
            cur = conn.execute("INSERT INTO users DEFAULT VALUES")
            user_id = int(cur.lastrowid)
            conn.execute(
                """
                INSERT INTO user_credentials (user_id, canvas_token_cipher, github_token_cipher, github_username)
                VALUES (?, ?, ?, ?)
                """,
                (user_id, canvas_cipher, github_cipher, github_username.strip()),
            )
            conn.execute(
                "INSERT INTO sessions (token_hash, user_id, expires_at) VALUES (?, ?, ?)",
                (token_hash, user_id, expires),
            )
            conn.commit()

        return raw_token, user_id

    def update_credentials_for_session(self, raw_token: str, *, canvas_token: str, github_token: str, github_username: str) -> None:
        user_id = self.validate_session(raw_token)
        if user_id is None:
            raise ValueError("Invalid session")
        canvas_cipher = encrypt_secret(canvas_token)
        github_cipher = encrypt_secret(github_token)
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                UPDATE user_credentials
                SET canvas_token_cipher = ?, github_token_cipher = ?, github_username = ?, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
                """,
                (canvas_cipher, github_cipher, github_username.strip(), user_id),
            )
            conn.commit()

    def validate_session(self, raw_token: Optional[str]) -> Optional[int]:
        if not raw_token:
            return None
        token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        now_iso = _utcnow().isoformat()
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT user_id, expires_at FROM sessions WHERE token_hash = ?",
                (token_hash,),
            ).fetchone()
        if not row:
            return None
        user_id, expires_at = int(row[0]), row[1]
        if expires_at:
            try:
                exp = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
                if exp.tzinfo is None:
                    exp = exp.replace(tzinfo=timezone.utc)
                if exp < _utcnow():
                    self.delete_session(raw_token)
                    return None
            except ValueError:
                pass
        return user_id

    def delete_session(self, raw_token: Optional[str]) -> None:
        if not raw_token:
            return
        token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        with self._lock, self._connect() as conn:
            conn.execute("DELETE FROM sessions WHERE token_hash = ?", (token_hash,))
            conn.commit()

    def load_credentials_blob(self, user_id: int) -> Optional[tuple[bytes, bytes, str]]:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT canvas_token_cipher, github_token_cipher, github_username FROM user_credentials WHERE user_id = ?",
                (user_id,),
            ).fetchone()
        if not row:
            return None
        return row[0], row[1], row[2] or ""

    def decrypt_workflow_tokens(self, user_id: int) -> tuple[str, str, str]:
        row = self.load_credentials_blob(user_id)
        if not row:
            raise CredentialCryptoError("No credentials for user")
        c_blob, g_blob, gh_user = row
        return decrypt_secret(c_blob), decrypt_secret(g_blob), gh_user


def encryption_configured() -> bool:
    return bool((os.getenv("CREDENTIAL_ENCRYPTION_KEY") or "").strip())
