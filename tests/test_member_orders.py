"""P5 Task 3：我的訂單 API（GET /user/orders、/user/orders/:order_id）與已購買明細的越權讀取。"""
import datetime
import uuid

import newebpay as nb
import pytest
from conftest import (
    auth_header,
    live_promotion,
    notify,
    ready_order,
    start_payment,
    success_notify,
)

ORDERS = "/api/v1/user/orders"
PURCHASES = "/api/v1/user/purchases/info"
NOT_FOUND = "查無此訂單項目"


def list_orders(api, user, **params):
    return api.get(ORDERS, headers=auth_header(user), params=params)


def listed(api, user, **params):
    r = list_orders(api, user, **params)
    assert r.status_code == 200, r.text
    return r.json()["data"]


def detail(api, user, order_id):
    return api.get(f"{ORDERS}/{order_id}", headers=auth_header(user))


def age(db, order_id, minutes):
    db.execute("UPDATE orders SET created_at = now() - make_interval(mins => %s) WHERE order_id = %s", (minutes, order_id))


def parse(ts):
    return datetime.datetime.fromisoformat(ts.replace("Z", "+00:00"))


def row_of(api, user, order_id):
    return next(o for o in listed(api, user, limit=50)["data"] if o["order_id"] == order_id)


# ------------------------------------------------------------------ 列表


def test_orders_list_all_statuses(api, db, make_user, make_tour, make_order):
    user, tour = make_user(), make_tour()
    for status in (-1, 0, 1, 2, 3, 4):
        make_order(user, tour["tour_id"], payment_status=status)
    data = listed(api, user, limit=50)
    assert data["total"] == 6
    assert {o["status_label"] for o in data["data"]} == {"待付款", "已付款", "已取消", "已退款", "已逾時"}
    assert {o["payment_status"] for o in data["data"]} == {-1, 0, 1, 2, 3, 4}


def test_orders_list_item_fields(api, db, make_user, make_tour, make_order):
    user, tour = make_user(), make_tour()
    order = make_order(user, tour["tour_id"], payment_status=1)
    o = listed(api, user)["data"][0]
    assert o["order_id"] == order["order_id"]
    assert o["item_count"] == 1
    assert o["first_item"]["title"] == tour["title"]
    assert o["first_item"]["cover_image"]
    for key in ("created_at", "deadline", "total_price", "promo_subtotal", "payable", "discount_type", "discount_amount",
                "payment_in_progress", "can_continue_payment", "is_overdue"):  # fmt: skip
        assert key in o, key


def test_orders_list_newest_first_and_paging(api, db, make_user, make_tour, make_order):
    user, tour = make_user(), make_tour()
    for _ in range(3):
        make_order(user, tour["tour_id"], payment_status=1)
    first = listed(api, user, limit=2, page=1)
    second = listed(api, user, limit=2, page=2)
    assert len(first["data"]) == 2 and len(second["data"]) == 1
    assert first["total"] == second["total"] == 3
    times = [parse(o["created_at"]) for o in first["data"] + second["data"]]
    assert times == sorted(times, reverse=True)


def test_orders_list_default_limit_is_4(api, db, make_user, make_tour, make_order):
    user, tour = make_user(), make_tour()
    for _ in range(5):
        make_order(user, tour["tour_id"], payment_status=1)
    data = listed(api, user)
    assert len(data["data"]) == 4 and data["total"] == 5


def test_orders_limit_over_50_is_400(api, make_user):
    r = list_orders(api, make_user(), limit=51)
    assert r.status_code == 400
    assert r.json()["message"] == "「每頁筆數」不可超過 50"


def test_orders_list_empty(api, make_user):
    r = list_orders(api, make_user())
    assert r.status_code == 200, r.text
    assert r.json()["data"] == {"data": [], "total": 0}


# ------------------------------------------------------------------ 金額


def test_orders_payable_from_compute_payable(api, db, make_user, make_tour, make_coupon):
    user = make_user()
    coupon = make_coupon(user, discount=100)
    tour = live_promotion(db, make_tour)
    user, order_id = ready_order(
        api, db, make_user, make_tour, {"type": "coupon", "coupon_id": coupon["coupon_id"]}, user=user, tour=tour, people=2
    )  # fmt: skip
    o = row_of(api, user, order_id)
    assert (o["payable"], o["discount_type"], o["discount_amount"]) == (1700, "coupon", 100)
    db.execute("UPDATE orders SET discount_price = 1 WHERE order_id = %s", (order_id,))
    assert row_of(api, user, order_id)["payable"] == 1700
    assert detail(api, user, order_id).json()["data"]["money"]["payable"] == 1700


# ------------------------------------------------------------------ 期限與進行中


def test_order_deadline_is_created_at_plus_timeout(api, db, make_user, make_tour, make_order):
    user, tour = make_user(), make_tour()
    make_order(user, tour["tour_id"], payment_status=-1)
    o = listed(api, user)["data"][0]
    assert parse(o["deadline"]) - parse(o["created_at"]) == datetime.timedelta(minutes=60)


def test_order_list_in_progress_label(api, db, make_user, make_tour):
    user, order_id = ready_order(api, db, make_user, make_tour)
    start_payment(api, user, order_id)
    o = row_of(api, user, order_id)
    assert o["status_label"] == "付款處理中"
    assert o["payment_in_progress"] is True
    assert o["can_continue_payment"] is False
    assert o["is_overdue"] is False


def test_order_can_continue_payment_flags(api, db, make_user, make_tour, make_order):
    user, tour = make_user(), make_tour()
    pending = make_order(user, tour["tour_id"], payment_status=-1)["order_id"]
    paid = make_order(user, tour["tour_id"], payment_status=1)["order_id"]
    for order_id, expected in ((pending, (True, False)), (paid, (False, False))):
        o = row_of(api, user, order_id)
        assert (o["can_continue_payment"], o["is_overdue"]) == expected
        d = detail(api, user, order_id).json()["data"]
        assert (d["can_continue_payment"], d["is_overdue"]) == expected


def test_order_list_in_progress_wins_over_deadline(api, db, make_user, make_tour):
    """Review Focus 2：付款進行中的訂單即使超過期限，仍是付款處理中，不被讀取轉成 4。"""
    user, order_id = ready_order(api, db, make_user, make_tour)
    start_payment(api, user, order_id)
    age(db, order_id, 61)
    o = row_of(api, user, order_id)
    assert o["status_label"] == "付款處理中"
    assert (o["can_continue_payment"], o["is_overdue"]) == (False, False)
    d = detail(api, user, order_id).json()["data"]
    assert (d["can_continue_payment"], d["is_overdue"]) == (False, False)
    assert db.execute("SELECT payment_status FROM orders WHERE order_id = %s", (order_id,)).fetchone()[0] == 0


def test_order_list_does_not_expire_overdue(api, db, make_user, make_tour, make_order):
    user, tour = make_user(), make_tour()
    order_id = make_order(user, tour["tour_id"], payment_status=-1)["order_id"]
    age(db, order_id, 61)
    o = row_of(api, user, order_id)
    assert o["status_label"] == "待付款"
    assert (o["is_overdue"], o["can_continue_payment"]) == (True, False)
    assert db.execute("SELECT payment_status FROM orders WHERE order_id = %s", (order_id,)).fetchone()[0] == -1
    assert db.execute("SELECT payment_status FROM order_item WHERE order_id = %s", (order_id,)).fetchone()[0] == -1


# ------------------------------------------------------------------ 明細


def test_order_detail_fields(api, db, make_user, make_tour):
    user, order_id = ready_order(api, db, make_user, make_tour, people=2)
    mon, amt, _ = start_payment(api, user, order_id)
    assert notify(api, success_notify(mon, amt)).status_code == 200
    r = detail(api, user, order_id)
    assert r.status_code == 200, r.text
    d = r.json()["data"]
    assert d["order_id"] == order_id
    assert d["status_label"] == "已付款"
    assert len(d["items"]) == 1
    item = d["items"][0]
    for key in ("order_item_id", "tour_id", "title", "cover_image", "quantity", "start_date", "end_date", "room_type",
                "total_price", "discount_price"):  # fmt: skip
        assert key in item, key
    assert item["quantity"] == 2
    assert d["shipping"]["address"] == "台北市測試路1號"
    assert d["shipping"]["phone"] == "0912345678"
    assert d["shipping"]["payment_type"]
    assert set(d["money"]) == {"total_price", "promo_subtotal", "payable", "discount_type", "discount_amount"}
    assert d["payments"][0]["result"] == "成功"
    assert set(d["payments"][0]) == {"created_at", "result_time", "result"}
    for leaked in ("return_data", "TradeInfo", "result_info", "merchant_order_no", mon):
        assert leaked not in r.text


def test_order_detail_failed_payment_result(api, db, make_user, make_tour):
    user, order_id = ready_order(api, db, make_user, make_tour)
    mon, amt, _ = start_payment(api, user, order_id)
    assert notify(api, nb.build_notify(mon, amt, status="MPG03009", message="交易失敗")).status_code == 200
    d = detail(api, user, order_id).json()["data"]
    assert d["payments"][0]["result"] == "失敗"


# ------------------------------------------------------------------ 越權與權限


def test_other_users_order_detail_is_404(api, make_user, make_tour, make_order):
    owner, other, tour = make_user(), make_user(), make_tour()
    order_id = make_order(owner, tour["tour_id"], payment_status=1)["order_id"]
    r = detail(api, other, order_id)
    assert r.status_code == 404
    assert r.json()["message"] == NOT_FOUND
    assert detail(api, owner, order_id).status_code == 200


def test_other_users_purchase_item_is_404(api, make_user, make_tour, make_order):
    """越權讀取：B 讀 A 已付款的 order_item_id；改前會 200。"""
    owner, other, tour = make_user(), make_user(), make_tour()
    item_id = make_order(owner, tour["tour_id"], payment_status=1)["order_item_id"]
    r = api.get(f"{PURCHASES}/{item_id}", headers=auth_header(other))
    assert r.status_code == 404, r.text
    assert r.json()["message"] == NOT_FOUND


def test_purchase_item_unknown_is_404(api, make_user):
    r = api.get(f"{PURCHASES}/{uuid.uuid4()}", headers=auth_header(make_user()))
    assert r.status_code == 404, r.text
    assert r.json()["message"] == NOT_FOUND


def test_own_unpaid_purchase_item_unchanged(api, make_user, make_tour, make_order):
    """回歸測試（F3）：本人未付款的項目維持 200 查無資料。"""
    user, tour = make_user(), make_tour()
    item_id = make_order(user, tour["tour_id"], payment_status=-1)["order_item_id"]
    r = api.get(f"{PURCHASES}/{item_id}", headers=auth_header(user))
    assert r.status_code == 200, r.text
    assert r.json()["message"] == "查無資料"


def test_orders_without_token_is_401(api):
    r = api.get(ORDERS)
    assert r.status_code == 401
    assert r.json()["message"] == "請先登入"


def test_orders_admin_is_403(api, make_user):
    admin = make_user(role="admin")
    for url in (ORDERS, f"{ORDERS}/{uuid.uuid4()}"):
        r = api.get(url, headers=auth_header(admin))
        assert r.status_code == 403
        assert r.json()["message"] == "您沒有權限進行此操作"


def test_order_detail_bad_uuid_is_400(api, make_user):
    r = api.get(f"{ORDERS}/not-a-uuid", headers=auth_header(make_user()))
    assert r.status_code == 400
    assert r.json()["message"] == "「訂單編號」必須是有效的 UUID 格式"
