import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import bcrypt
from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException
from starlette.requests import Request

from app.services import crypto_service
from app.services.auth_service import (
    check_session,
    create_session,
    destroy_session,
    validate_password,
    verify_password,
)
from app.services.rate_limit_service import client_ip, rate_limit


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.counts: dict[str, int] = {}

    async def set(self, key, value, ex=None):
        self.values[key] = value

    async def exists(self, key):
        return int(key in self.values)

    async def delete(self, *keys):
        for key in keys:
            self.values.pop(key, None)

    async def incr(self, key):
        self.counts[key] = self.counts.get(key, 0) + 1
        return self.counts[key]

    async def expire(self, key, seconds):
        return True


def request(headers=()):
    return Request({"type": "http", "headers": headers, "client": ("127.0.0.1", 1234)})


class SecurityServiceTests(unittest.IsolatedAsyncioTestCase):
    def test_password_policy_and_verification(self):
        validate_password("correct horse battery staple 9!")
        with self.assertRaises(ValueError):
            validate_password("short 1!")  # under 12 characters
        with self.assertRaises(ValueError):
            validate_password("x1!" + "x" * 70)  # over 72 bytes
        with self.assertRaises(ValueError):
            validate_password("no digits here!!")  # missing number
        with self.assertRaises(ValueError):
            validate_password("NoSpecials12345")  # missing special character
        hashed = bcrypt.hashpw(
            b"correct horse battery staple 9!", bcrypt.gensalt()
        ).decode()
        self.assertTrue(verify_password("correct horse battery staple 9!", hashed))
        self.assertFalse(verify_password("incorrect password", hashed))

    def test_crypto_round_trip_and_wrong_key(self):
        with (
            tempfile.TemporaryDirectory() as directory,
            patch.object(crypto_service, "KEY_PATH", Path(directory) / "fernet.key"),
            patch.object(crypto_service.settings, "token_encryption_key", None),
        ):
            crypto_service.initialise_crypto()
            encrypted = crypto_service.encrypt("secret")
            self.assertEqual(crypto_service.decrypt(encrypted), "secret")
            self.assertEqual(crypto_service.KEY_PATH.stat().st_mode & 0o777, 0o600)
            crypto_service._fernet = Fernet(Fernet.generate_key())
            with self.assertRaises(InvalidToken):
                crypto_service.decrypt(encrypted)

    async def test_session_lifecycle(self):
        redis = FakeRedis()
        token = await create_session(redis)
        self.assertTrue(await check_session(redis, token))
        await destroy_session(redis, token)
        self.assertFalse(await check_session(redis, token))

    async def test_rate_limit_and_forwarded_ip(self):
        redis = FakeRedis()
        req = request(((b"x-forwarded-for", b"192.0.2.10"),))
        self.assertEqual(client_ip(req), "192.0.2.10")
        dependency = rate_limit("test", 2, 60)
        with patch("app.services.rate_limit_service.time.time", return_value=120):
            await dependency(req, redis)
            await dependency(req, redis)
            with self.assertRaises(HTTPException) as raised:
                await dependency(req, redis)
        self.assertEqual(raised.exception.status_code, 429)
        self.assertEqual(raised.exception.headers, {"Retry-After": "60"})


if __name__ == "__main__":
    unittest.main()
