"""P4 Task 9：管理員退款 API（R2 手動標記；歸還點數與優惠券、收回回饋；允許負餘額 Q2）。"""
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
import requests

from conftest import (
    API_BASE,
    auth_header,
    live_promotion,
    notify,
    order_status,
    ready_order,
    start_payment,
    success_notify,
    summary,
    travel_point,
)

ELIGIBILITY_API = "/api/v1/user/product/search/{}/eligibility"
REFUND_MSG = "只有已付款的訂單可以退款"


def refund_url(order_id):
    return f"/api/v1/admin/orders/{order_id}/refund"


def refund(api, admin, order_id):
    return api.post(refund_url(order_id), headers=auth_header(admin), timeout=10)


def paid_order(api, db, make_user, make_tour, discount=None, **kw):
    """建單、付款、成功 notify；回傳 (user, order_id, mon, amt)。"""
    user, order_id = ready_order(api, db, make_user, make_tour, discount, **kw)
    mon, amt, _ = start_payment(api, user, order_id)
    assert notify(api, success_notify(mon, amt)).status_code == 200
    assert order_status(db, order_id) == (1, {1})
    return user, order_id, mon, amt


def refund_rows(db, order_id, type_):
    return [r[0] for r in db.execute("SELECT point FROM point_record WHERE order_id = %s AND type = %s", (order_id, type_))]


def point_count(db, order_id):
    return db.execute("SELECT count(*) FROM point_record WHERE order_id = %s", (order_id,)).fetchone()[0]


def test_refund_point_order_restores_balance(api, db, make_user, make_tour):
    admin = make_user(role="admin")
    user = make_user()
    db.execute("UPDATE user_level SET travel_point = 100 WHERE user_id = %s", (user["user_id"],))
    user, order_id, _, amt = paid_order(
        api, db, make_user, make_tour, {"type": "point", "used_point": 100}, user=user, price=1000
    )
    assert amt == 920
    assert travel_point(db, user) == 92

    r = refund(api, admin, order_id)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["message"] == "退款成功"
    assert body["data"] == {"order_id": order_id, "payment_status": 3, "returned_point": 100, "clawed_back": 92}
    assert order_status(db, order_id) == (3, {3})
    assert travel_point(db, user) == 100
    assert refund_rows(db, order_id, "退款退回") == [100]
    assert refund_rows(db, order_id, "退款收回") == [-92]


def test_refund_coupon_order_releases_coupon(api, db, make_user, make_tour, make_coupon):
    admin = make_user(role="admin")
    user = make_user()
    coupon = make_coupon(user, discount=100)
    user, order_id, mon, amt = paid_order(
        api, db, make_user, make_tour, {"type": "coupon", "coupon_id": coupon["coupon_id"]}, user=user
    )
    assert amt == 900
    assert refund(api, admin, order_id).status_code == 200
    status, bound = db.execute(
        "SELECT status, order_id FROM user_coupon WHERE user_id = %s AND coupon_id = %s",
        (user["user_id"], coupon["coupon_id"]),
    ).fetchone()
    assert status == 0 and bound is None
    (pstatus,) = db.execute("SELECT payment_status FROM payment WHERE merchant_order_no = %s", (mon,)).fetchone()
    assert pstatus == 1
    assert refund_rows(db, order_id, "退款收回") == [-90]
    assert refund_rows(db, order_id, "退款退回") == []
    assert travel_point(db, user) == 0


def test_refund_allows_negative_balance(api, db, make_user, make_tour):
    admin = make_user(role="admin")
    user, order_id, _, _ = paid_order(api, db, make_user, make_tour)
    assert travel_point(db, user) == 100
    db.execute("UPDATE user_level SET travel_point = 0 WHERE user_id = %s", (user["user_id"],))
    assert refund(api, admin, order_id).status_code == 200
    assert travel_point(db, user) == -100


def test_refund_twice_is_409(api, db, make_user, make_tour):
    admin = make_user(role="admin")
    user, order_id, _, _ = paid_order(api, db, make_user, make_tour)
    assert refund(api, admin, order_id).status_code == 200
    r = refund(api, admin, order_id)
    assert r.status_code == 409
    assert r.json()["message"] == REFUND_MSG
    assert refund_rows(db, order_id, "退款收回") == [-100]
    assert travel_point(db, user) == 0


@pytest.mark.parametrize("status", [-1, 0, 2, 4])
def test_refund_non_paid_status_is_409(api, db, make_user, make_tour, status):
    admin = make_user(role="admin")
    user, order_id = ready_order(api, db, make_user, make_tour)
    db.execute("UPDATE orders SET payment_status = %s WHERE order_id = %s", (status, order_id))
    db.execute("UPDATE order_item SET payment_status = %s WHERE order_id = %s", (status, order_id))
    before = point_count(db, order_id)
    r = refund(api, admin, order_id)
    assert r.status_code == 409
    assert r.json()["message"] == REFUND_MSG
    assert point_count(db, order_id) == before
    assert order_status(db, order_id) == (status, {status})


def test_refund_unknown_order_is_404(api, make_user):
    admin = make_user(role="admin")
    r = refund(api, admin, str(uuid.uuid4()))
    assert r.status_code == 404
    assert r.json()["message"] == "查無此訂單項目"


def test_refund_bad_uuid_is_400(api, make_user):
    admin = make_user(role="admin")
    assert refund(api, admin, "not-a-uuid").status_code == 400


def test_refund_by_member_is_403(api, db, make_user, make_tour):
    user, order_id, _, _ = paid_order(api, db, make_user, make_tour)
    assert refund(api, user, order_id).status_code == 403
    assert order_status(db, order_id) == (1, {1})


def test_refund_without_token_is_401(api, db, make_user, make_tour):
    user, order_id, _, _ = paid_order(api, db, make_user, make_tour)
    assert api.post(refund_url(order_id), timeout=10).status_code == 401
    assert order_status(db, order_id) == (1, {1})


def test_refunded_order_revokes_review_eligibility(api, db, make_user, make_tour):
    admin = make_user(role="admin")
    tour = make_tour(price=1000)
    user, order_id, _, _ = paid_order(api, db, make_user, make_tour, tour=tour)
    url = ELIGIBILITY_API.format(tour["tour_id"])
    assert api.get(url, headers=auth_header(user)).json()["data"]["can_write"] is True
    assert refund(api, admin, order_id).status_code == 200
    assert api.get(url, headers=auth_header(user)).json()["data"]["can_write"] is False


def test_refunded_coupon_order_summary_shows_amount_paid(api, db, make_user, make_tour, make_coupon):
    """裁示 1：已退款訂單的應付金額取成功付款的實付額（券已釋放，不能退回未折抵金額）。"""
    admin = make_user(role="admin")
    user = make_user()
    coupon = make_coupon(user, discount=100)
    tour = live_promotion(db, make_tour)
    user, order_id, _, amt = paid_order(
        api, db, make_user, make_tour, {"type": "coupon", "coupon_id": coupon["coupon_id"]},
        user=user, tour=tour, people=2,
    )  # fmt: skip
    assert amt == 1700
    assert refund(api, admin, order_id).status_code == 200
    data = summary(api, user, order_id)
    assert data["payable"] == 1700, data


def test_refund_and_duplicate_notify_concurrently(api, db, make_user, make_tour):
    """裁示 2：退款與重複的成功 notify 同時送出，不 500、只退一次、點數一致。"""
    admin = make_user(role="admin")
    user, order_id = ready_order(api, db, make_user, make_tour)
    mon, amt, _ = start_payment(api, user, order_id)
    fields = success_notify(mon, amt)
    assert notify(api, fields).status_code == 200
    assert travel_point(db, user) == 100

    barrier = threading.Barrier(2, timeout=10)

    def do_refund():
        barrier.wait()
        return requests.post(f"{API_BASE}{refund_url(order_id)}", headers=auth_header(admin), timeout=15).status_code

    def do_notify():
        barrier.wait()
        return requests.post(f"{API_BASE}/api/v1/user/newebpay/notify", data=fields, timeout=15).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        f_refund, f_notify = pool.submit(do_refund), pool.submit(do_notify)
        codes = (f_refund.result(timeout=30), f_notify.result(timeout=30))
    assert codes == (200, 200), codes
    assert order_status(db, order_id) == (3, {3})
    assert refund_rows(db, order_id, "退款收回") == [-100]
    assert refund_rows(db, order_id, "新增") == [100]
    assert travel_point(db, user) == 0
