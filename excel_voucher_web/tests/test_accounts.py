from __future__ import annotations

from app.accounts import AccountStore


def test_groupware_user_starts_with_forced_initial_password(tmp_path):
    store = AccountStore(tmp_path / "accounts.sqlite3", initial_password="wowjd12!@")
    store.upsert_groupware_user(
        {
            "user_id": "finance01",
            "emp_no": "1001",
            "name": "재정담당",
            "dept_code": "HQ22111000",
            "dept_name": "(재정)1파트",
            "email": "finance01@example.com",
            "company_key": "daeseung",
            "active": True,
        }
    )

    user = store.authenticate("finance01", "wowjd12!@")

    assert user is not None
    assert user.must_change_password is True
    assert user.company_key == "daeseung"


def test_password_change_clears_force_flag(tmp_path):
    store = AccountStore(tmp_path / "accounts.sqlite3", initial_password="wowjd12!@")
    store.upsert_groupware_user({"user_id": "finance01", "name": "재정담당", "active": True})

    assert store.change_password("finance01", "wowjd12!@", "changed-pass-1") is True
    user = store.authenticate("finance01", "changed-pass-1")

    assert user is not None
    assert user.must_change_password is False


def test_temporary_password_forces_change_again(tmp_path):
    store = AccountStore(tmp_path / "accounts.sqlite3", initial_password="wowjd12!@")
    store.upsert_groupware_user({"user_id": "finance01", "name": "재정담당", "active": True})
    store.change_password("finance01", "wowjd12!@", "changed-pass-1")

    store.set_temporary_password("finance01", "Temp-pass-1")
    user = store.authenticate("finance01", "Temp-pass-1")

    assert user is not None
    assert user.must_change_password is True
