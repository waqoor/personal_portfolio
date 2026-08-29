from __future__ import annotations

import hashlib
import hmac
import re
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def generate_token(bytes_count: int = 32) -> str:
    return secrets.token_urlsafe(bytes_count)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def keyed_digest(value: str, secret: str) -> str:
    return hmac.new(secret.encode("utf-8"), value.encode("utf-8"), hashlib.sha256).hexdigest()


def safe_request_id(candidate: str | None) -> str:
    if candidate and _REQUEST_ID_PATTERN.fullmatch(candidate):
        return candidate
    return secrets.token_hex(16)


class PasswordService:
    def __init__(self) -> None:
        self._hasher = PasswordHasher(time_cost=3, memory_cost=65_536, parallelism=4)
        self._dummy_hash = self._hasher.hash(generate_token())

    def hash(self, password: str) -> str:
        return self._hasher.hash(password)

    def verify(self, encoded_hash: str | None, password: str) -> bool:
        candidate = encoded_hash or self._dummy_hash
        try:
            valid = self._hasher.verify(candidate, password)
        except (VerifyMismatchError, InvalidHashError):
            return False
        return bool(valid and encoded_hash is not None)

    def needs_rehash(self, encoded_hash: str) -> bool:
        return self._hasher.check_needs_rehash(encoded_hash)
