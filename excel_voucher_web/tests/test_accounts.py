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


def test_admin_upsert_does_not_overwrite_existing_password(tmp_path):
    store = AccountStore(tmp_path / "accounts.sqlite3", initial_password="wowjd12!@")
    store.upsert_admin_user(
        user_id="rlckd9646",
        name="김기창",
        password="legacy-pass-1",
        email="rlckd9646@dae-seung.co.kr",
        must_change_password=False,
    )
    store.change_password("rlckd9646", "legacy-pass-1", "already-changed-1")

    store.upsert_admin_user(
        user_id="rlckd9646",
        name="김기창",
        password="eotmd12!@",
        email="rlckd9646@dae-seung.co.kr",
        must_change_password=True,
    )

    assert store.authenticate("rlckd9646", "eotmd12!@") is None
    user = store.authenticate("rlckd9646", "already-changed-1")
    assert user is not None
    assert user.is_admin is True


def test_admin_legacy_sync_can_update_password(tmp_path):
    store = AccountStore(tmp_path / "accounts.sqlite3", initial_password="wowjd12!@")
    store.upsert_admin_user(
        user_id="rlckd9646",
        name="김기창",
        password="old-legacy-pass",
        email="rlckd9646@dae-seung.co.kr",
        must_change_password=False,
    )

    store.upsert_admin_user(
        user_id="rlckd9646",
        name="김기창",
        password="new-legacy-pass",
        email="rlckd9646@dae-seung.co.kr",
        must_change_password=False,
        overwrite_password=True,
    )

    assert store.authenticate("rlckd9646", "old-legacy-pass") is None
    user = store.authenticate("rlckd9646", "new-legacy-pass")
    assert user is not None
    assert user.is_admin is True
