import unittest
from types import SimpleNamespace
from unittest.mock import patch

from backend.routers.google_auth import GoogleTokenIn, google_login


class _ScalarResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class _FakeDB:
    def __init__(self, execute_results):
        self._execute_results = list(execute_results)

    async def execute(self, _query):
        if not self._execute_results:
            raise AssertionError("No execute result queued")
        return _ScalarResult(self._execute_results.pop(0))

    async def commit(self):
        return None

    async def rollback(self):
        return None

    async def refresh(self, _obj):
        return None


class GoogleAuthPhoneResponseTests(unittest.IsolatedAsyncioTestCase):
    async def test_existing_user_by_email_returns_phone(self):
        existing_user = SimpleNamespace(
            id="USR-1",
            name="Book Nandu",
            email="booknandu@gmail.com",
            phone="89198166410",
            picture="",
            role="admin",
            provider="local",
            provider_id=None,
            email_verified=True,
        )

        # 1st query: no user by provider_id, 2nd query: user found by email
        db = _FakeDB([None, existing_user])

        with patch("backend.routers.google_auth.verify_google_id_token", return_value={
            "sub": "google-sub-1",
            "email": "booknandu@gmail.com",
            "name": "Book Nandu",
            "email_verified": True,
        }), patch("backend.routers.google_auth.create_access_token", return_value="token-1"):
            res = await google_login(GoogleTokenIn(id_token="fake"), db)  # type: ignore

        self.assertEqual(res.user["email"], "booknandu@gmail.com")
        self.assertEqual(res.user["phone"], "89198166410")
        self.assertEqual(res.user["role"], "admin")


if __name__ == "__main__":
    unittest.main()
