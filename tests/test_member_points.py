"""P5 Task 5：點數紀錄 API（GET /user/points/records）與 pointslevel 的負點數、無券顯示。"""
import datetime

from conftest import auth_header, negative_points_via_refund
from dbfactory import insert

RECORDS = "/api/v1/user/points/records"
POINTSLEVEL = "/api/v1/user/userinfo/pointslevel"


def records(api, user, **params):
    r = api.get(RECORDS, headers=auth_header(user), params=params)
    assert r.status_code == 200, r.text
    return r.json()["data"]


def add(db, user, type_, point, minutes_ago, order_id=None):
    return insert(
        db, "point_record", user_id=user["user_id"], type=type_, point=point, order_id=order_id,
        created_at=datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=minutes_ago),
    )  # fmt: skip


def test_point_records_reasons_and_order(api, db, make_user, make_order, make_tour):
    user = make_user()
    tour = make_tour(price=1000)
    order = make_order(user, tour["tour_id"], payment_status=1)
    oid = order["order_id"]
    add(db, user, "新增", 170, 5, oid)
    add(db, user, "減少", -100, 4, oid)
    add(db, user, "退款收回", -170, 3, oid)
    add(db, user, "退款退回", 100, 2, oid)
    add(db, user, "其他類型", 5, 1)
    data = records(api, user)
    assert data["total"] == 5
    assert [(r["type"], r["point"], r["reason"]) for r in data["data"]] == [
        ("其他類型", 5, "其他類型"),
        ("退款退回", 100, "退款退還折抵"),
        ("退款收回", -170, "退款收回回饋"),
        ("減少", -100, "點數折抵"),
        ("新增", 170, "購物回饋"),
    ]
    assert set(data["data"][0]) == {"created_at", "point", "type", "reason", "order_id"}
    assert data["data"][0]["order_id"] is None
    assert data["data"][1]["order_id"] == oid


def test_point_records_hide_pending_deduction(api, db, make_user):
    user = make_user()
    add(db, user, "減少_確認中", -50, 2)
    add(db, user, "新增", 30, 1)
    data = records(api, user)
    assert data["total"] == 1
    assert [r["point"] for r in data["data"]] == [30]


def test_point_records_paging(api, db, make_user):
    user = make_user()
    for i in range(6):
        add(db, user, "新增", i + 1, 10 - i)  # point 6 最新
    first = records(api, user, page=1, limit=4)
    second = records(api, user, page=2, limit=4)
    assert first["total"] == second["total"] == 6
    assert [r["point"] for r in first["data"]] == [6, 5, 4, 3]
    assert [r["point"] for r in second["data"]] == [2, 1]


def test_point_records_default_limit_is_4(api, db, make_user):
    user = make_user()
    for i in range(5):
        add(db, user, "新增", i + 1, 10 - i)
    assert len(records(api, user)["data"]) == 4


def test_point_records_empty(api, make_user):
    assert records(api, make_user()) == {"data": [], "total": 0}


def test_point_records_other_user_not_visible(api, db, make_user):
    a = make_user()
    b = make_user()
    add(db, b, "新增", 77, 1)
    assert records(api, a) == {"data": [], "total": 0}
    assert [r["point"] for r in records(api, b)["data"]] == [77]


def test_point_records_without_token_is_401(api):
    r = api.get(RECORDS)
    assert r.status_code == 401
    assert r.json()["message"] == "請先登入"


def test_point_records_admin_is_403(api, make_user):
    r = api.get(RECORDS, headers=auth_header(make_user(role="admin")))
    assert r.status_code == 403
    assert r.json()["message"] == "您沒有權限進行此操作"


def test_point_records_limit_over_50_is_400(api, make_user):
    r = api.get(RECORDS, headers=auth_header(make_user()), params={"limit": 51})
    assert r.status_code == 400
    assert r.json()["message"] == "「每頁筆數」不可超過 50"


def test_pointslevel_negative_shows_zero(api, db, make_user, make_tour):
    user = negative_points_via_refund(api, db, make_user, make_tour)
    r = api.get(POINTSLEVEL, headers=auth_header(user))
    assert r.status_code == 200, r.text
    assert r.json()["data"][0]["travel_point"] == 0
    assert db.execute("SELECT travel_point FROM user_level WHERE user_id = %s", (user["user_id"],)).fetchone()[0] == -8


def test_pointslevel_without_coupon_is_empty_list(api, make_user):
    r = api.get(POINTSLEVEL, headers=auth_header(make_user()))
    assert r.status_code == 200, r.text
    assert r.json()["data"][0]["coupon"] == []
