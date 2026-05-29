from dataclasses import dataclass
from time import time
from urllib.request import urlopen
import json

from authlib.jose import JsonWebKey, jwt


APPLE_ISSUER = "https://appleid.apple.com"
APPLE_KEYS_URL = "https://appleid.apple.com/auth/keys"
_JWKS_CACHE_SECONDS = 60 * 60
_cached_jwks: dict | None = None
_cached_jwks_expires_at = 0.0


@dataclass(frozen=True)
class AppleIdentity:
    sub: str
    email: str | None
    email_verified: bool


def verify_apple_identity_token(identity_token: str, *, audience: str, nonce: str | None = None) -> AppleIdentity:
    key_set = JsonWebKey.import_key_set(_get_apple_jwks())
    claims = jwt.decode(
        identity_token,
        key_set,
        claims_options={
            "iss": {"essential": True, "values": [APPLE_ISSUER]},
            "aud": {"essential": True, "values": [audience]},
            "sub": {"essential": True},
            "exp": {"essential": True},
            "iat": {"essential": True},
        },
    )
    claims.validate()

    if nonce is not None and claims.get("nonce") != nonce:
        raise ValueError("Apple identity token nonce did not match.")

    sub = str(claims.get("sub") or "").strip()
    if not sub:
        raise ValueError("Apple identity token did not include a subject.")

    email = str(claims.get("email") or "").strip().lower() or None
    raw_email_verified = claims.get("email_verified")
    email_verified = raw_email_verified is True or str(raw_email_verified).lower() == "true"
    return AppleIdentity(sub=sub, email=email, email_verified=email_verified)


def _get_apple_jwks() -> dict:
    global _cached_jwks, _cached_jwks_expires_at

    now = time()
    if _cached_jwks is not None and now < _cached_jwks_expires_at:
        return _cached_jwks

    with urlopen(APPLE_KEYS_URL, timeout=10) as response:
        payload = json.loads(response.read().decode("utf-8"))

    if not isinstance(payload, dict) or not payload.get("keys"):
        raise ValueError("Apple JWKS response did not include signing keys.")

    _cached_jwks = payload
    _cached_jwks_expires_at = now + _JWKS_CACHE_SECONDS
    return payload
