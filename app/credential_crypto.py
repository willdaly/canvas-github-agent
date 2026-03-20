"""Symmetric encryption for tokens at rest (Fernet)."""

from __future__ import annotations

import os
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken


class CredentialCryptoError(Exception):
    pass


@lru_cache
def _fernet() -> Fernet:
    raw = (os.getenv("CREDENTIAL_ENCRYPTION_KEY") or "").strip()
    if not raw:
        raise CredentialCryptoError("CREDENTIAL_ENCRYPTION_KEY is not set")
    try:
        return Fernet(raw.encode() if isinstance(raw, str) else raw)
    except Exception as exc:
        raise CredentialCryptoError("Invalid CREDENTIAL_ENCRYPTION_KEY (must be Fernet key)") from exc


def encrypt_secret(plain: str) -> bytes:
    if not plain:
        return b""
    return _fernet().encrypt(plain.encode("utf-8"))


def decrypt_secret(blob: bytes) -> str:
    if not blob:
        return ""
    try:
        return _fernet().decrypt(blob).decode("utf-8")
    except InvalidToken as exc:
        raise CredentialCryptoError("Failed to decrypt credential") from exc
