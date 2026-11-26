"""P4 Task 8：藍新付款表單、notify（簽章／冪等／金額）、結算、重付、return 與端到端（經 mock）。"""
import datetime
import os
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import psycopg
import pytest
import requests

import newebpay as nb
from conftest import (
    API_BASE,
    ROOT,
    _db_params,
    add_to_cart,
    auth_header,
    checkout,
    live_promotion,
    NOTIFY_API,
    PAYMENT_API,
    notify,
    order_status,
    preview,
    ready_order,
    start_payment,
    success_notify,
    summary,
    travel_point,
)

RETURN_API = "/api/v1/user/newebpay/return"
FRONTEND_PATH = os.getenv("FRONTEND_PATH", "http://localhost:5173")
MOCK_BASE = os.getenv("TEST_MOCK_NEWEBPAY_BASE", "http://localhost:8095")
MOCK_PAY = f"{MOCK_BASE}/MPG/pay"


# ------------------------------------------------------------------ helpers


def failure_notify(mon, amt):
    return nb.build_notify(mon, amt, status="MPG03009", message="交易失敗")


def payment_row(db, mon):
    return db.execute(
        "SELECT payment_status, result_info, result_time, return_data, return_time, discount_price "
        "FROM payment WHERE merchant_order_no = %s",
        (mon,),
    ).fetchone()


def reward_rows(db, order_id):
    return [r[0] for r in db.execute("SELECT point FROM point_record WHERE order_id = %s AND type = '新增'", (order_id,))]


def age_order(db, order_id, minutes):
    db.execute("UPDATE orders SET created_at = now() - make_interval(mins => %s) WHERE order_id = %s", (minutes, order_id))


def age_payments(db, order_id, seconds):
    db.execute(
        "UPDATE payment SET created_at = now() - make_interval(secs => %s) WHERE order_id = %s", (seconds, order_id)
    )


# ------------------------------------------------------------------ 付款表單


def test_payment_amount_from_backend(api, db, make_user, make_tour):
    user, order_id = ready_order(api, db, make_user, make_tour, price=1234)
    mon, amt, _ = start_payment(
        api, user, order_id,
        {"Amt": 1, "order_items": [{"title": "x", "price": 1}], "user": {"email": "x@example.com"}},
    )  # fmt: skip
    assert amt == 1234


def test_payment_trade_info_contains_required_fields(api, db, make_user, make_tour):
    user, order_id = ready_order(api, db, make_user, make_tour)
    r = api.post(PAYMENT_API, headers=auth_header(user), json={"order_id": order_id}, timeout=10)
    assert r.status_code == 200
    assert r.headers["Content-Type"].startswith("text/html")
    action, fields = nb.parse_payment_form(r.text)
    assert action == os.environ["PayGateWay"]
    assert set(fields) == {"MerchantID", "TradeInfo", "TradeSha", "Version"}
    assert len(re.findall(r'type="hidden"', r.text)) == 4
    assert fields["TradeSha"] == nb.trade_sha(fields["TradeInfo"])
    trade = nb.decode_trade_info(fields)
    for key in (
        "MerchantID", "RespondType", "TimeStamp", "Version", "MerchantOrderNo", "Amt", "ItemDesc",
        "Email", "ReturnURL", "NotifyURL", "TradeLimit",
    ):  # fmt: skip
        assert key in trade, key
    assert len(trade["MerchantOrderNo"]) <= 30
    assert trade["TradeLimit"] == os.environ["NEWEBPAY_TRADE_LIMIT_SECONDS"]
    assert trade["NotifyURL"] == os.environ["NotifyUrl"]
    assert trade["ReturnURL"] == os.environ["ReturnUrl"]
    assert trade["Email"] == user["email"]


def test_payment_form_never_contains_raw_item_desc(api, db, make_user, make_tour):
    title = "p3-<script>alert(1)</script>"
    user, order_id = ready_order(api, db, make_user, make_tour, tour=make_tour(title=title, price=1000))
    r = api.post(PAYMENT_API, headers=auth_header(user), json={"order_id": order_id}, timeout=10)
    assert r.status_code == 200
    assert "<script>alert(1)" not in r.text
    _, fields = nb.parse_payment_form(r.text)
    assert nb.decode_trade_info(fields)["ItemDesc"] == title


def test_payment_new_merchant_order_no_each_attempt(api, db, make_user, make_tour):
    user, order_id = ready_order(api, db, make_user, make_tour)
    first, _, _ = start_payment(api, user, order_id)
    second, _, _ = start_payment(api, user, order_id)
    assert first != second
    (n,) = db.execute("SELECT count(*) FROM payment WHERE order_id = %s", (order_id,)).fetchone()
    assert n == 2


def test_payment_other_users_order_is_404(api, db, make_user, make_tour):
    _, order_id = ready_order(api, db, make_user, make_tour)
    other = make_user()
    r = api.post(PAYMENT_API, headers=auth_header(other), json={"order_id": order_id}, timeout=10)
    assert r.status_code == 404
    assert r.json()["message"] == "查無此訂單項目"
    (n,) = db.execute("SELECT count(*) FROM payment WHERE order_id = %s", (order_id,)).fetchone()
    assert n == 0


def test_payment_requires_order_id(api, make_user):
    user = make_user()
    r = api.post(PAYMENT_API, headers=auth_header(user), json={}, timeout=10)
    assert r.status_code == 400


def test_payment_requires_pending_status(api, db, make_user, make_tour):
    user = make_user()
    order_id = checkout(api, user, [make_tour()])  # 狀態 -1（尚未 preview）
    r = api.post(PAYMENT_API, headers=auth_header(user), json={"order_id": order_id}, timeout=10)
    assert r.status_code == 409
    assert r.json()["message"] == "訂單狀態不允許此操作"


def test_payment_allowed_near_deadline_and_not_expired_while_in_progress(api, db, make_user, make_tour):
    user, order_id = ready_order(api, db, make_user, make_tour)
    age_order(db, order_id, 55)
    start_payment(api, user, order_id)  # 期限內即使剩不到一個 TradeLimit 也可付款
    age_order(db, order_id, 65)
    assert summary(api, user, order_id)["payment_status"] == 0  # 付款進行中不判逾時
    age_payments(db, order_id, 700)  # 超過 TradeLimit（600 秒）
    assert summary(api, user, order_id)["payment_status"] == 4


def test_payment_on_overdue_order_is_409(api, db, make_user, make_tour):
    user, order_id = ready_order(api, db, make_user, make_tour)
    age_order(db, order_id, 61)
    r = api.post(PAYMENT_API, headers=auth_header(user), json={"order_id": order_id}, timeout=10)
    assert r.status_code == 409
    assert r.json()["message"] == "訂單已逾時"
    assert order_status(db, order_id) == (4, {4})


# ------------------------------------------------------------------ notify 安全


def test_notify_bad_sha_changes_nothing(api, db, make_user, make_tour):
    user, order_id = ready_order(api, db, make_user, make_tour)
    mon, amt, _ = start_payment(api, user, order_id)
    fields = success_notify(mon, amt)
    sha = fields["TradeSha"]
    fields["TradeSha"] = ("0" if sha[0] != "0" else "1") + sha[1:]
    assert notify(api, fields).status_code == 400
    assert order_status(db, order_id) == (0, {0})
    status, info, result_time, *_ = payment_row(db, mon)
    assert status == 0 and info is None and result_time is None


def test_notify_missing_fields_is_400(api):
    assert api.post(NOTIFY_API, data={}, timeout=10).status_code == 400
    assert api.post(NOTIFY_API, data={"TradeInfo": "zz", "TradeSha": "zz"}, timeout=10).status_code == 400


def test_notify_undecryptable_trade_info_is_400(api):
    garbage = "ab" * 32
    r = api.post(NOTIFY_API, data={"TradeInfo": garbage, "TradeSha": nb.trade_sha(garbage)}, timeout=10)
    assert r.status_code == 400


def test_notify_amount_mismatch_rejected(api, db, make_user, make_tour):
    user, order_id = ready_order(api, db, make_user, make_tour)
    mon, amt, _ = start_payment(api, user, order_id)
    assert notify(api, success_notify(mon, amt + 1)).status_code == 400
    assert order_status(db, order_id) == (0, {0})
    status, info, *_ = payment_row(db, mon)
    assert status == 0
    assert info.startswith("金額不符")
    assert reward_rows(db, order_id) == []


def test_notify_unknown_merchant_order_no_is_400(api):
    assert notify(api, success_notify("T-no-such-order", 100)).status_code == 400


def test_notify_duplicate_settles_once(api, db, make_user, make_tour):
    user, order_id = ready_order(api, db, make_user, make_tour)
    mon, amt, _ = start_payment(api, user, order_id)
    fields = success_notify(mon, amt)
    assert notify(api, fields).status_code == 200
    assert notify(api, fields).status_code == 200
    assert reward_rows(db, order_id) == [100]
    assert travel_point(db, user) == 100


def test_notify_concurrent_duplicates_settle_once(api, db, make_user, make_tour):
    user, order_id = ready_order(api, db, make_user, make_tour)
    mon, amt, _ = start_payment(api, user, order_id)
    fields = success_notify(mon, amt)

    barrier = threading.Barrier(2)

    def send():
        barrier.wait(timeout=10)
        return requests.post(f"{API_BASE}{NOTIFY_API}", data=fields, timeout=10).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        codes = list(pool.map(lambda _: send(), range(2)))
    assert all(c != 500 for c in codes), codes
    assert codes == [200, 200], codes
    assert order_status(db, order_id) == (1, {1})
    assert reward_rows(db, order_id) == [100]
    assert travel_point(db, user) == 100


# ------------------------------------------------------------------ 結算


def test_notify_success_settles_coupon_order(api, db, make_user, make_tour, make_coupon):
    user = make_user()
    coupon = make_coupon(user, discount=100)
    tour = live_promotion(db, make_tour)
    user, order_id = ready_order(
        api, db, make_user, make_tour, {"type": "coupon", "coupon_id": coupon["coupon_id"]},
        user=user, tour=tour, people=2,
    )  # fmt: skip
    mon, amt, _ = start_payment(api, user, order_id)
    assert amt == 1700
    assert notify(api, success_notify(mon, amt)).status_code == 200
    assert order_status(db, order_id) == (1, {1})
    status, _, result_time, return_data, return_time, discount_price = payment_row(db, mon)
    assert status == 1
    assert return_data is not None and return_time is not None
    assert discount_price == 1700
    (cstatus,) = db.execute(
        "SELECT status FROM user_coupon WHERE user_id = %s AND coupon_id = %s", (user["user_id"], coupon["coupon_id"])
    ).fetchone()
    assert cstatus == 1
    assert reward_rows(db, order_id) == [170]
    assert travel_point(db, user) == 170
    (left,) = db.execute(
        "SELECT count(*) FROM cart_item ci JOIN cart c ON c.cart_id = ci.cart_id "
        "WHERE c.user_id = %s AND ci.tour_id = %s",
        (user["user_id"], tour["tour_id"]),
    ).fetchone()
    assert left == 0


def test_notify_success_settles_point_order(api, db, make_user, make_tour):
    user = make_user()
    db.execute("UPDATE user_level SET travel_point = 100 WHERE user_id = %s", (user["user_id"],))
    user, order_id = ready_order(
        api, db, make_user, make_tour, {"type": "point", "used_point": 100}, user=user, price=1000
    )
    mon, amt, _ = start_payment(api, user, order_id)
    assert amt == 920
    assert notify(api, success_notify(mon, amt)).status_code == 200
    rows = db.execute("SELECT type, point FROM point_record WHERE order_id = %s ORDER BY type", (order_id,)).fetchall()
    assert ("減少", -100) in rows
    assert ("新增", 92) in rows
    assert not [r for r in rows if r[0] == "減少_確認中"]
    assert travel_point(db, user) == 92


def test_notify_success_keeps_unrelated_cart_items(api, db, make_user, make_tour):
    user, order_id = ready_order(api, db, make_user, make_tour)
    other = make_tour()
    assert add_to_cart(api, user, other).status_code == 201
    mon, amt, _ = start_payment(api, user, order_id)
    assert notify(api, success_notify(mon, amt)).status_code == 200
    (n,) = db.execute(
        "SELECT count(*) FROM cart_item ci JOIN cart c ON c.cart_id = ci.cart_id "
        "WHERE c.user_id = %s AND ci.tour_id = %s",
        (user["user_id"], other["tour_id"]),
    ).fetchone()
    assert n == 1


def test_paid_order_item_enables_review(api, db, make_user, make_tour):
    tour = make_tour(price=1000)
    user, order_id = ready_order(api, db, make_user, make_tour, tour=tour)
    mon, amt, _ = start_payment(api, user, order_id)
    url = f"/api/v1/user/product/search/{tour['tour_id']}/eligibility"
    assert api.get(url, headers=auth_header(user)).json()["data"]["can_write"] is False
    assert notify(api, success_notify(mon, amt)).status_code == 200
    assert api.get(url, headers=auth_header(user)).json()["data"]["can_write"] is True


def test_reward_floors_non_multiple_of_ten(api, db, make_user, make_tour):
    user, order_id = ready_order(api, db, make_user, make_tour, price=995)
    mon, amt, _ = start_payment(api, user, order_id)
    assert amt == 995
    assert notify(api, success_notify(mon, amt)).status_code == 200
    assert reward_rows(db, order_id) == [99]
    assert travel_point(db, user) == 99


# ------------------------------------------------------------------ 失敗與重付


def test_notify_failure_keeps_order_pending(api, db, make_user, make_tour, make_coupon):
    user = make_user()
    coupon = make_coupon(user, discount=100)
    user, order_id = ready_order(
        api, db, make_user, make_tour, {"type": "coupon", "coupon_id": coupon["coupon_id"]}, user=user
    )
    mon, amt, _ = start_payment(api, user, order_id)
    assert notify(api, failure_notify(mon, amt)).status_code == 200
    assert order_status(db, order_id) == (0, {0})
    status, info, result_time, *_ = payment_row(db, mon)
    assert status == 0 and result_time is not None and info
    (cstatus,) = db.execute(
        "SELECT status FROM user_coupon WHERE user_id = %s AND coupon_id = %s", (user["user_id"], coupon["coupon_id"])
    ).fetchone()
    assert cstatus == -1


def test_retry_after_failure_settles(api, db, make_user, make_tour):
    user, order_id = ready_order(api, db, make_user, make_tour)
    first, amt, _ = start_payment(api, user, order_id)
    assert notify(api, failure_notify(first, amt)).status_code == 200
    second, amt2, _ = start_payment(api, user, order_id)
    assert second != first and amt2 == amt
    assert notify(api, success_notify(second, amt2)).status_code == 200
    assert order_status(db, order_id) == (1, {1})
    assert payment_row(db, first)[0] == 0
    assert payment_row(db, second)[0] == 1


# ------------------------------------------------------------------ 第 7 步與逾時


def test_success_on_expired_order_is_recorded_only(api, db, make_user, make_tour):
    user, order_id = ready_order(api, db, make_user, make_tour)
    mon, amt, _ = start_payment(api, user, order_id)
    db.execute("UPDATE orders SET payment_status = 4 WHERE order_id = %s", (order_id,))
    db.execute("UPDATE order_item SET payment_status = 4 WHERE order_id = %s", (order_id,))
    assert notify(api, success_notify(mon, amt)).status_code == 200
    assert order_status(db, order_id) == (4, {4})
    status, info, result_time, *_ = payment_row(db, mon)
    assert status == 0 and info and result_time is not None
    assert reward_rows(db, order_id) == []


def test_second_successful_attempt_is_recorded_not_settled(api, db, make_user, make_tour):
    user, order_id = ready_order(api, db, make_user, make_tour)
    first, amt, _ = start_payment(api, user, order_id)
    second, _, _ = start_payment(api, user, order_id)
    assert notify(api, success_notify(first, amt)).status_code == 200
    assert notify(api, success_notify(second, amt)).status_code == 200
    (paid,) = db.execute("SELECT count(*) FROM payment WHERE order_id = %s AND payment_status = 1", (order_id,)).fetchone()
    assert paid == 1
    status, info, *_ = payment_row(db, second)
    assert status == 0 and info
    assert len(reward_rows(db, order_id)) == 1


def test_success_after_cancel_is_recorded_only(api, db, make_user, make_tour):
    user, order_id = ready_order(api, db, make_user, make_tour)
    mon, amt, _ = start_payment(api, user, order_id)
    checkout(api, user, [make_tour()])  # 建新單，舊單被取消
    assert order_status(db, order_id) == (2, {2})
    assert notify(api, success_notify(mon, amt)).status_code == 200
    assert order_status(db, order_id) == (2, {2})
    assert payment_row(db, mon)[0] == 0


def test_order_expires_after_attempt_deadline(api, db, make_user, make_tour):
    user, order_id = ready_order(api, db, make_user, make_tour)
    start_payment(api, user, order_id)
    age_order(db, order_id, 61)
    age_payments(db, order_id, 300)
    assert summary(api, user, order_id)["payment_status"] == 0
    age_payments(db, order_id, 601)
    assert summary(api, user, order_id)["payment_status"] == 4


# ------------------------------------------------------------------ return


def test_return_redirects_to_result_page(api, db, make_user, make_tour):
    user, order_id = ready_order(api, db, make_user, make_tour)
    mon, amt, _ = start_payment(api, user, order_id)
    r = api.post(RETURN_API, data=success_notify(mon, amt), allow_redirects=False, timeout=10)
    assert r.status_code == 302
    assert r.headers["Location"] == f"{FRONTEND_PATH}/#/pay/result?order={order_id}"
    assert order_status(db, order_id) == (0, {0})
    assert payment_row(db, mon)[0] == 0


def test_return_bad_sha_redirects_without_order(api, db, make_user, make_tour):
    user, order_id = ready_order(api, db, make_user, make_tour)
    mon, amt, _ = start_payment(api, user, order_id)
    fields = success_notify(mon, amt)
    fields["TradeSha"] = "0" * 64
    r = api.post(RETURN_API, data=fields, allow_redirects=False, timeout=10)
    assert r.status_code == 302
    assert r.headers["Location"] == f"{FRONTEND_PATH}/#/pay/result"


# ------------------------------------------------------------------ 端到端（經 mock）


def _go_through_mock(api, user, order_id, result, headers=None):
    r = api.post(PAYMENT_API, headers=auth_header(user), json={"order_id": order_id}, timeout=10)
    assert r.status_code == 200, r.text
    action, fields = nb.parse_payment_form(r.text)
    page = requests.post(action, data=fields, timeout=10)
    assert page.status_code == 200, page.text
    session = re.search(r'name="session"\s+value="([^"]+)"', page.text).group(1)
    return requests.post(MOCK_PAY, data={"session": session, "result": result}, headers=headers or {}, timeout=15)


def _poll_status(api, user, order_id, want):
    for _ in range(10):
        if summary(api, user, order_id)["payment_status"] == want:
            return True
        time.sleep(0.5)
    return False


def test_payment_through_mock_gateway_settles(api, db, make_user, make_tour):
    user, order_id = ready_order(api, db, make_user, make_tour)
    resp = _go_through_mock(api, user, order_id, "success")
    assert resp.status_code == 200
    assert _poll_status(api, user, order_id, 1), "mock 的 notify 沒有讓訂單轉為已付款"
    (paid,) = db.execute("SELECT count(*) FROM payment WHERE order_id = %s AND payment_status = 1", (order_id,)).fetchone()
    assert paid == 1


def test_mock_timeout_sends_no_notify(api, db, make_user, make_tour):
    user, order_id = ready_order(api, db, make_user, make_tour)
    resp = _go_through_mock(api, user, order_id, "success", headers={"X-Mock-Now": str(time.time() + 3600)})
    assert "交易逾時" in resp.text
    assert order_status(db, order_id) == (0, {0})
    status, result_time = db.execute(
        "SELECT payment_status, result_time FROM payment WHERE order_id = %s", (order_id,)
    ).fetchone()
    assert status == 0 and result_time is None


# ------------------------------------------------------------------ 修正輪 1：F1 / F3 / M5 / M6


def _coupon_order(api, db, make_user, make_tour, make_coupon):
    user = make_user()
    coupon = make_coupon(user, discount=100)
    user, order_id = ready_order(
        api, db, make_user, make_tour, {"type": "coupon", "coupon_id": coupon["coupon_id"]}, user=user
    )
    mon, amt, _ = start_payment(api, user, order_id)
    assert amt == 900
    return user, order_id, mon, amt


def _assert_recorded_only(db, mon, order_id, status, amt):
    assert order_status(db, order_id) == (status, {status})
    pstatus, info, result_time, *_ = payment_row(db, mon)
    assert pstatus == 0 and result_time is not None
    assert info == f"訂單狀態 {status} 收到成功通知：notify={amt}"
    assert reward_rows(db, order_id) == []


def test_success_after_cancel_with_discount_is_recorded_only(api, db, make_user, make_tour, make_coupon):
    user, order_id, mon, amt = _coupon_order(api, db, make_user, make_tour, make_coupon)
    checkout(api, user, [make_tour()])  # 建新單 → 舊單取消並釋放保留
    assert order_status(db, order_id) == (2, {2})
    assert notify(api, success_notify(mon, amt)).status_code == 200
    _assert_recorded_only(db, mon, order_id, 2, amt)


def test_success_after_expiry_with_discount_is_recorded_only(api, db, make_user, make_tour, make_coupon):
    user, order_id, mon, amt = _coupon_order(api, db, make_user, make_tour, make_coupon)
    age_order(db, order_id, 65)
    age_payments(db, order_id, 700)
    assert summary(api, user, order_id)["payment_status"] == 4  # 真實路徑逾時並釋放保留
    assert notify(api, success_notify(mon, amt)).status_code == 200
    _assert_recorded_only(db, mon, order_id, 4, amt)


def test_payment_past_order_deadline_with_attempt_in_progress_is_409(api, db, make_user, make_tour):
    user, order_id = ready_order(api, db, make_user, make_tour)
    start_payment(api, user, order_id)
    age_order(db, order_id, 65)
    r = api.post(PAYMENT_API, headers=auth_header(user), json={"order_id": order_id}, timeout=10)
    assert r.status_code == 409
    assert r.json()["message"] == "訂單已逾時"
    (n,) = db.execute("SELECT count(*) FROM payment WHERE order_id = %s", (order_id,)).fetchone()
    assert n == 1
    assert order_status(db, order_id) == (0, {0})


@pytest.mark.parametrize("raw, expected", [("600", "600"), ("5", "60"), ("5000", "900"), ("0", "600")])
def test_trade_limit_seconds_is_clamped(raw, expected):
    import subprocess

    proc = subprocess.run(
        ["docker", "compose", "exec", "-T", "-e", f"NEWEBPAY_TRADE_LIMIT_SECONDS={raw}", "backend", "node", "-e",
         "console.log('RESULT' + require('./src/utils/trade').tradeLimitSeconds())"],
        cwd=ROOT, capture_output=True, text=True, timeout=60,
    )  # fmt: skip
    assert proc.returncode == 0, proc.stderr
    assert f"RESULT{expected}" in proc.stdout


def test_zero_reward_writes_no_point_record(api, db, make_user, make_tour, make_coupon):
    user = make_user()
    coupon = make_coupon(user, discount=95)
    user, order_id = ready_order(
        api, db, make_user, make_tour, {"type": "coupon", "coupon_id": coupon["coupon_id"]}, user=user, price=100
    )
    mon, amt, _ = start_payment(api, user, order_id)
    assert amt == 5
    assert notify(api, success_notify(mon, amt)).status_code == 200
    assert order_status(db, order_id) == (1, {1})
    assert reward_rows(db, order_id) == []
    assert travel_point(db, user) == 0


# ------------------------------------------------------------------ 修正輪 2：G1 / G2


def test_failure_notify_after_cancel_with_discount_is_recorded_only(api, db, make_user, make_tour, make_coupon):
    user, order_id, mon, amt = _coupon_order(api, db, make_user, make_tour, make_coupon)
    checkout(api, user, [make_tour()])
    assert order_status(db, order_id) == (2, {2})
    assert notify(api, failure_notify(mon, amt)).status_code == 200
    assert order_status(db, order_id) == (2, {2})
    pstatus, info, result_time, *_ = payment_row(db, mon)
    assert pstatus == 0 and result_time is not None
    assert info and not info.startswith("金額不符")


def _cart_item_id_of(db, user, tour):
    return str(
        db.execute(
            "SELECT ci.cart_item_id FROM cart_item ci JOIN cart c ON c.cart_id = ci.cart_id "
            "WHERE c.user_id = %s AND ci.tour_id = %s",
            (user["user_id"], tour["tour_id"]),
        ).fetchone()[0]
    )


def _wait_until_blocked_by(db, holder_pid: int, timeout: float = 10.0) -> None:
    """有期限地輪詢，直到有連線正在等 holder_pid 持有的鎖。"""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        row = db.execute(
            "SELECT count(*) FROM pg_stat_activity "
            "WHERE wait_event_type = 'Lock' AND %s = ANY(pg_blocking_pids(pid))",
            (holder_pid,),
        ).fetchone()
        if row[0] > 0:
            return
        time.sleep(0.05)
    pytest.fail("請求沒有在期限內被 holder 的 cart 鎖擋住")


def _assert_waits_on_cart_not_cart_item(db, user, cart_item_id, fire):
    """鎖順序（cart 先於 cart_item）的決定性檢查。

    測試自己的連線先鎖住該會員的 cart 列；請求在背景執行，必須卡在 cart 上、
    尚未持有 cart_item 的鎖（第二條連線 NOWAIT 鎖 cart_item 要成功）。回傳請求的 Response。
    """
    holder = psycopg.connect(**_db_params())
    probe = psycopg.connect(**_db_params())
    pool = ThreadPoolExecutor(max_workers=1)
    try:
        holder.execute("SELECT cart_id FROM cart WHERE user_id = %s FOR UPDATE", (user["user_id"],))
        future = pool.submit(fire)
        _wait_until_blocked_by(db, holder.info.backend_pid)  # 請求確實正在等 cart 的鎖
        assert not future.done()
        probe.execute("SELECT 1 FROM cart_item WHERE cart_item_id = %s FOR UPDATE NOWAIT", (cart_item_id,))
        probe.rollback()  # 立刻放掉
        holder.rollback()
        return future.result(timeout=15)
    finally:
        holder.rollback()
        probe.rollback()
        holder.close()
        probe.close()
        pool.shutdown(wait=False)


def test_cart_patch_locks_cart_before_cart_item(api, db, make_user, make_tour):
    user = make_user()
    tour = make_tour()
    assert add_to_cart(api, user, tour).status_code == 201
    item_id = _cart_item_id_of(db, user, tour)
    body = {
        "type": tour["type"],
        "item": tour["item"],
        "people": 3,
        "options": {
            "start_date": (datetime.date.today() + datetime.timedelta(days=1)).isoformat(),
            "end_date": (datetime.date.today() + datetime.timedelta(days=2)).isoformat(),
        },
    }
    r = _assert_waits_on_cart_not_cart_item(
        db,
        user,
        item_id,
        lambda: requests.patch(
            f"{API_BASE}/api/v1/user/trade/cart/{item_id}", json=body, headers=auth_header(user), timeout=15
        ),
    )
    assert r.status_code == 200, r.text
    assert db.execute("SELECT quantity FROM cart_item WHERE cart_item_id = %s", (item_id,)).fetchone()[0] == 3


def test_cart_delete_locks_cart_before_cart_item(api, db, make_user, make_tour):
    user = make_user()
    tour = make_tour()
    assert add_to_cart(api, user, tour).status_code == 201
    item_id = _cart_item_id_of(db, user, tour)
    r = _assert_waits_on_cart_not_cart_item(
        db,
        user,
        item_id,
        lambda: requests.delete(
            f"{API_BASE}/api/v1/user/trade/cart/{item_id}", headers=auth_header(user), timeout=15
        ),
    )
    assert r.status_code == 200, r.text
    assert db.execute("SELECT count(*) FROM cart_item WHERE cart_item_id = %s", (item_id,)).fetchone()[0] == 0


def test_settlement_locks_cart_before_cart_item(api, db, make_user, make_tour):
    tour = make_tour(price=1000)
    user, order_id = ready_order(api, db, make_user, make_tour, tour=tour)
    mon, amt, _ = start_payment(api, user, order_id)
    item_id = _cart_item_id_of(db, user, tour)
    fields = success_notify(mon, amt)
    r = _assert_waits_on_cart_not_cart_item(
        db,
        user, item_id, lambda: requests.post(f"{API_BASE}{NOTIFY_API}", data=fields, timeout=15)
    )
    assert r.status_code == 200, r.text
    assert order_status(db, order_id) == (1, {1})
    assert db.execute("SELECT count(*) FROM cart_item WHERE cart_item_id = %s", (item_id,)).fetchone()[0] == 0


# ------------------------------------------------------------------ 反目標


BYPASS_RE = re.compile(r"(skip|bypass|disable|no)[_-]?(sha|sign|signature|verify|check)", re.IGNORECASE)
FORBIDDEN_RE = re.compile(r"MOCK_NEWEBPAY|FAKE_PAY")


def test_no_signature_bypass_switch():
    src = ROOT / "backend" / "src"
    files = list(src.rglob("*.js"))
    assert files
    offenders = []
    for path in files:
        text = path.read_text(encoding="utf-8")
        rel = path.relative_to(src).as_posix()
        for match in BYPASS_RE.finditer(text):
            offenders.append(f"{rel}: {match.group(0)}")
        for match in FORBIDDEN_RE.finditer(text):
            offenders.append(f"{rel}: {match.group(0)}")
        if "createDecipheriv" in text and rel != "utils/newebpay.js":
            offenders.append(f"{rel}: createDecipheriv")
    assert not offenders, offenders


# ---- F5：/payment 參數訊息走共用格式化

@pytest.mark.parametrize("body", [[], {}, {"order_id": ""}, {"order_id": "x"}, {"order_id": 5}], ids=["array", "missing", "empty", "not-uuid", "number"])
def test_payment_bad_body_is_400_without_raw_names(api, make_user, body):
    user = make_user()
    r = api.post(PAYMENT_API, headers=auth_header(user), json=body, timeout=5)
    assert r.status_code == 400, r.text
    message = r.json()["message"]
    assert "order_id" not in message and '"' not in message
