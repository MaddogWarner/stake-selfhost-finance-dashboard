import logging
import os
from pathlib import Path

from cryptography.fernet import Fernet

from app.config import settings

logger = logging.getLogger(__name__)
KEY_PATH = Path("/data/fernet.key")
_fernet: Fernet | None = None


def initialise_crypto() -> None:
    global _fernet
    raw_key: bytes
    if settings.token_encryption_key:
        raw_key = settings.token_encryption_key.encode()
    elif KEY_PATH.exists():
        raw_key = KEY_PATH.read_bytes().strip()
    else:
        KEY_PATH.parent.mkdir(parents=True, exist_ok=True)
        raw_key = Fernet.generate_key()
        fd = os.open(KEY_PATH, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as key_file:
            key_file.write(raw_key + b"\n")
        logger.info("Generated token encryption key at %s", KEY_PATH)
    try:
        _fernet = Fernet(raw_key)
    except (TypeError, ValueError) as exc:
        raise RuntimeError(
            "TOKEN_ENCRYPTION_KEY or /data/fernet.key is not a valid Fernet key."
        ) from exc


def _cipher() -> Fernet:
    if _fernet is None:
        raise RuntimeError("Token encryption has not been initialised.")
    return _fernet


def encrypt(value: str) -> str:
    return _cipher().encrypt(value.encode()).decode()


def decrypt(value: str) -> str:
    return _cipher().decrypt(value.encode()).decode()
