"""
Symmetric encryption for secrets stored in the database (Instagram access tokens).
Fernet (AES-128-CBC + HMAC). The Fernet key is derived from ENCRYPTION_KEY, so any
long random string works.
"""

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from config.settings import get_settings

KEY_VERSION = 1  # stored next to each token so the key can be rotated later


class CryptoError(Exception):
    pass


def _fernet() -> Fernet:
    secret = get_settings().ENCRYPTION_KEY
    if not secret:
        raise CryptoError("ENCRYPTION_KEY is not set")
    key = base64.urlsafe_b64encode(hashlib.sha256(secret.encode("utf-8")).digest())
    return Fernet(key)


class CryptoHelper:
    @staticmethod
    def encrypt(plaintext: str) -> bytes:
        return _fernet().encrypt(plaintext.encode("utf-8"))

    @staticmethod
    def decrypt(token: bytes) -> str:
        try:
            return _fernet().decrypt(bytes(token)).decode("utf-8")
        except InvalidToken as e:
            raise CryptoError("Could not decrypt value (wrong ENCRYPTION_KEY?)") from e
