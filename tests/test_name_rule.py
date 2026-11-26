"""P5 Task 2：註冊、會員資料、結帳共用姓名規則（去頭尾空白後 2 到 20 個 Unicode 字元，拒絕控制字元）。"""
import uuid

import pytest

from conftest import auth_header, checkout
from test_member_auth import PROFILE_INFO, SIGNUP, _count_email, _signup_body, cleanup_email  # noqa: F401

LEN_MSG = "「姓名」需為 2 到 20 個字"
BLANK_MSG = "「姓名」不得為空白"
CTRL_MSG = "「姓名」不得包含控制字元"


def _email() -> str:
    return f"val.{uuid.uuid4().hex[:8]}@example.com"


def _stored_name(db, email: str):
    return db.execute('SELECT name FROM "user" WHERE lower(email) = lower(%s)', (email,)).fetchone()[0]


def _signup(api, cleanup_email, name):
    email = _email()
    cleanup_email(email)
    return email, api.post(SIGNUP, json=_signup_body(email, name=name))


def test_signup_accepts_20_chars_and_spaces(api, cleanup_email):
    _, r = _signup(api, cleanup_email, "王" * 18 + " A")
    assert r.status_code == 201, r.text


def test_signup_rejects_21_chars(api, db, cleanup_email):
    email, r = _signup(api, cleanup_email, "王" * 21)
    assert r.status_code == 400, r.text
    assert r.json()["message"] == LEN_MSG
    assert _count_email(db, email) == 0


def test_signup_trims_name(api, db, cleanup_email):
    email, r = _signup(api, cleanup_email, "  小明  ")
    assert r.status_code == 201, r.text
    assert _stored_name(db, email) == "小明"


def test_signup_blank_name(api, cleanup_email):
    _, r = _signup(api, cleanup_email, "   ")
    assert r.status_code == 400, r.text
    assert r.json()["message"] == BLANK_MSG


def test_signup_counts_code_points(api, cleanup_email):
    _, r = _signup(api, cleanup_email, "😀" * 10)
    assert r.status_code == 201, r.text
    _, r = _signup(api, cleanup_email, "😀" * 21)
    assert r.status_code == 400, r.text
    assert r.json()["message"] == LEN_MSG


def test_signup_allows_symbols_and_spaces(api, cleanup_email):
    _, r = _signup(api, cleanup_email, "Mary-Jane O'Neil")
    assert r.status_code == 201, r.text


@pytest.mark.parametrize("name", ["小明\u0007", "小\n明"], ids=["bell", "newline"])
def test_signup_rejects_control_chars(api, cleanup_email, name):
    _, r = _signup(api, cleanup_email, name)
    assert r.status_code == 400, r.text
    assert r.json()["message"] == CTRL_MSG


@pytest.mark.parametrize("name", ["小明\u0007", "小\n明"], ids=["bell", "newline"])
def test_profile_rejects_control_chars(api, make_user, name):
    r = api.patch(PROFILE_INFO, headers=auth_header(make_user()), json={"name": name})
    assert r.status_code == 400, r.text
    assert r.json()["message"] == CTRL_MSG


@pytest.mark.parametrize("name", ["小明\u0007", "小\n明"], ids=["bell", "newline"])
def test_checkout_rejects_control_chars(api, make_user, make_tour, name):
    user = make_user()
    order_id = checkout(api, user, [make_tour()])
    body = {
        "user": {"name": name, "email": user["email"], "address": "台北市", "phone_number": "0912345678"},
        "payment_method": "credit_card",
    }
    r = api.patch(f"/api/v1/user/checkout/preview/{order_id}", json=body, headers=auth_header(user), timeout=10)
    assert r.status_code == 400, r.text
    assert r.json()["message"] == CTRL_MSG


def test_profile_name_rules(api, make_user):
    h = auth_header(make_user())
    for name, status, msg in [("王", 400, LEN_MSG), ("王" * 20, 200, None), ("王" * 21, 400, LEN_MSG)]:
        r = api.patch(PROFILE_INFO, headers=h, json={"name": name})
        assert r.status_code == status, (name, r.text)
        if msg:
            assert r.json()["message"] == msg


def test_profile_blank_name(api, make_user):
    r = api.patch(PROFILE_INFO, headers=auth_header(make_user()), json={"name": "   "})
    assert r.status_code == 400, r.text
    assert r.json()["message"] == BLANK_MSG


# 回歸測試：現行 schema 已有 .trim()，預期一開始就綠。
def test_profile_saves_trimmed_name(api, db, make_user):
    user = make_user()
    r = api.patch(PROFILE_INFO, headers=auth_header(user), json={"name": "  新名字  "})
    assert r.status_code == 200, r.text
    assert db.execute('SELECT name FROM "user" WHERE user_id = %s', (user["user_id"],)).fetchone()[0] == "新名字"


def test_control_char_check_is_stateless(api, make_user):
    h = auth_header(make_user())
    for _ in range(3):
        r = api.patch(PROFILE_INFO, headers=h, json={"name": "小明\u0007"})
        assert r.status_code == 400, r.text
        assert r.json()["message"] == CTRL_MSG


def test_checkout_name_rules(api, make_user, make_tour):
    user = make_user()
    order_id = checkout(api, user, [make_tour()])

    def go(name):
        body = {
            "user": {"name": name, "email": user["email"], "address": "台北市", "phone_number": "0912345678"},
            "payment_method": "credit_card",
        }
        return api.patch(f"/api/v1/user/checkout/preview/{order_id}", json=body, headers=auth_header(user), timeout=10)

    assert go("Google 測試員").status_code == 200
    r = go("王" * 21)
    assert r.status_code == 400, r.text
    assert r.json()["message"] == LEN_MSG
