"""Privacy-preserving identity and prompt helpers."""

from __future__ import annotations

import hashlib
import hmac
import re

_EMAIL_PATTERN = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_PHONE_PATTERN = re.compile(r"(?<!\w)(?:\+?\d[\s().-]*){8,15}(?!\w)")


def hmac_fingerprint(secret: str, value: str, *, namespace: str) -> str:
    normalized = value.strip().casefold()
    payload = f"{namespace}:{normalized}".encode()
    return hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()


def redact_personal_data(value: str) -> tuple[str, bool]:
    redacted, email_count = _EMAIL_PATTERN.subn("[redacted email]", value)
    redacted, phone_count = _PHONE_PATTERN.subn("[redacted phone]", redacted)
    return redacted, bool(email_count or phone_count)
