import base64
import hashlib
import hmac
import json
import os
import time
from typing import Any

from .config import JWT_SECRET, JWT_TTL_SECONDS


def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 120_000)
    return f"{base64.b64encode(salt).decode()}${base64.b64encode(digest).decode()}"


def verify_password(password: str, stored: str) -> bool:
    salt_text, digest_text = stored.split("$", 1)
    salt = base64.b64decode(salt_text)
    expected = hash_password(password, salt).split("$", 1)[1]
    return hmac.compare_digest(expected, digest_text)


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _unb64url(data: str) -> bytes:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))


def create_token(subject: str) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {"sub": subject, "iat": int(time.time()), "exp": int(time.time()) + JWT_TTL_SECONDS}
    signing_input = ".".join(
        [_b64url(json.dumps(header, separators=(",", ":")).encode()), _b64url(json.dumps(payload).encode())]
    )
    signature = hmac.new(JWT_SECRET.encode(), signing_input.encode(), hashlib.sha256).digest()
    return f"{signing_input}.{_b64url(signature)}"


def decode_token(token: str) -> dict[str, Any]:
    try:
        header, payload, signature = token.split(".")
        signing_input = f"{header}.{payload}"
        expected = _b64url(hmac.new(JWT_SECRET.encode(), signing_input.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(signature, expected):
            raise ValueError("Invalid signature")
        claims = json.loads(_unb64url(payload))
        if int(claims["exp"]) < int(time.time()):
            raise ValueError("Token expired")
        return claims
    except Exception as exc:
        raise ValueError("Invalid token") from exc
