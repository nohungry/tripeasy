"""藍新的 notify／return 是由藍新伺服器或瀏覽器表單從別的網域送來，不受前端來源白名單限制；其餘路由維持白名單。"""
import os

import requests

from conftest import (
    API_BASE,
    NOTIFY_API,
    PAYMENT_API,
    auth_header,
    order_status,
    ready_order,
    start_payment,
    success_notify,
)

RETURN_API = "/api/v1/user/newebpay/return"
FRONTEND_PATH = os.getenv("FRONTEND_PATH", "http://localhost:5173")
FOREIGN = {"Origin": os.getenv("TEST_MOCK_NEWEBPAY_BASE", "http://localhost:8095")}


def test_return_accepts_gateway_origin(api, db, make_user, make_tour):
    user, order_id = ready_order(api, db, make_user, make_tour)
    mon, amt, _ = start_payment(api, user, order_id)
    r = requests.post(
        f"{API_BASE}{RETURN_API}", data=success_notify(mon, amt), headers=FOREIGN, allow_redirects=False, timeout=10
    )
    assert r.status_code == 302
    assert r.headers["Location"] == f"{FRONTEND_PATH}/#/pay/result?order={order_id}"


def test_notify_accepts_gateway_origin(api, db, make_user, make_tour):
    user, order_id = ready_order(api, db, make_user, make_tour)
    mon, amt, _ = start_payment(api, user, order_id)
    r = requests.post(f"{API_BASE}{NOTIFY_API}", data=success_notify(mon, amt), headers=FOREIGN, timeout=10)
    assert r.status_code == 200
    assert order_status(db, order_id) == (1, {1})


def test_other_routes_still_reject_foreign_origin(api, make_user):
    user = make_user()
    headers = {**auth_header(user), **FOREIGN}
    r = requests.get(f"{API_BASE}/api/v1/user/trade/cart/list", headers=headers, timeout=10)
    # 現況：cors 丟「不允許的來源」，全域錯誤處理把沒有 status 的錯誤轉成 500 與通用訊息「伺服器錯誤」
    assert r.status_code == 500
    assert r.json()["message"] == "伺服器錯誤"
    allowed = requests.get(
        f"{API_BASE}/api/v1/user/trade/cart/list", headers={**auth_header(user), "Origin": FRONTEND_PATH}, timeout=10
    )
    assert allowed.status_code == 200  # 對照：白名單內的來源正常
    r = requests.post(f"{API_BASE}{PAYMENT_API}", headers=headers, json={}, timeout=10)
    assert r.status_code == 500  # /payment 與 notify／return 同一個 router，仍受白名單限制
    assert r.json()["message"] == "伺服器錯誤"
    ok = requests.post(f"{API_BASE}{PAYMENT_API}", headers={**auth_header(user), "Origin": FRONTEND_PATH}, json={}, timeout=10)
    assert ok.status_code == 400  # 對照：白名單內的來源會進到驗證（缺 order_id），不是 CORS 拒絕
