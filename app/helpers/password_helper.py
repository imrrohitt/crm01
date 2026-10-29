"""
Password hashing with bcrypt.
"""

import bcrypt

MAX_PASSWORD_BYTES = 72  # bcrypt ignores/rejects anything longer

# Hash used to keep login timing similar when the email does not exist.
_DUMMY_HASH = bcrypt.hashpw(b"not-a-real-password", bcrypt.gensalt()).decode()


class PasswordHelper:
    @staticmethod
    def hash(password: str) -> str:
        raw = password.encode("utf-8")
        if len(raw) > MAX_PASSWORD_BYTES:
            raise ValueError("Password is too long (max 72 bytes)")
        return bcrypt.hashpw(raw, bcrypt.gensalt()).decode()

    @staticmethod
    def verify(password: str, password_hash: str | None) -> bool:
        """Constant-ish time check; runs a dummy comparison when there is no hash."""
        raw = password.encode("utf-8")
        if len(raw) > MAX_PASSWORD_BYTES:
            return False
        try:
            if not password_hash:
                bcrypt.checkpw(raw, _DUMMY_HASH.encode())
                return False
            return bcrypt.checkpw(raw, password_hash.encode())
        except ValueError:
            return False
