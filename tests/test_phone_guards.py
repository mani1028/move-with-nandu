import unittest
from types import SimpleNamespace

from fastapi import HTTPException

from backend.routers.auth import DriverRegisterIn, driver_register
from backend.routers.drivers import PrefPatch, patch_me as patch_driver_me
from backend.routers.users import PatchUserIn, patch_me as patch_user_me


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
            return _ScalarResult(None)
        return _ScalarResult(self._execute_results.pop(0))

    async def commit(self):
        return None

    async def refresh(self, _obj):
        return None

    def add(self, _obj):
        return None


class PhoneGuardTests(unittest.IsolatedAsyncioTestCase):
    async def test_user_patch_rejects_duplicate_phone(self):
        db = _FakeDB([SimpleNamespace(id="USR-2")])
        user = SimpleNamespace(id="USR-1", name="One", phone="9000000001")

        with self.assertRaises(HTTPException) as ctx:
            await patch_user_me(PatchUserIn(phone="9000000002"), user, db)  # type: ignore

        self.assertEqual(ctx.exception.status_code, 400)

    async def test_driver_patch_rejects_duplicate_phone(self):
        db = _FakeDB([SimpleNamespace(id="DRV-2")])
        driver = SimpleNamespace(
            id="DRV-1",
            name="Driver One",
            email="d1@example.com",
            phone="9111111111",
            route_pref="Karimnagar",
            ac_pref=True,
            address="",
            vehicle_type="7 Seater",
            plate="TS09AA1111",
            license_url="",
            aadhar_url="",
            rc_url="",
            insurance_url="",
            status="offline",
            jobs_done=0,
            filled_seats=0,
            doc_status="pending",
        )

        with self.assertRaises(HTTPException) as ctx:
            await patch_driver_me(PrefPatch(phone="9222222222"), driver, db)  # type: ignore

        self.assertEqual(ctx.exception.status_code, 400)

    async def test_driver_register_rejects_empty_phone(self):
        db = _FakeDB([])

        with self.assertRaises(HTTPException) as ctx:
            await driver_register(
                DriverRegisterIn(
                    name="Driver",
                    email="driver@example.com",
                    phone="",
                    password="pass1234",
                    plate="TS09AA1111",
                ),
                db,  # type: ignore
            )

        self.assertEqual(ctx.exception.status_code, 400)


if __name__ == "__main__":
    unittest.main()
