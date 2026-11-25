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
FOREIGN = {"Origin": "http://localhost:8095"}


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
    assert r.status_code == 500  # 現況：cors 回「不允許的來源」，由全域錯誤處理轉成 500
    r = requests.post(f"{API_BASE}{PAYMENT_API}", headers=headers, json={}, timeout=10)
    assert r.status_code == 500  # /payment 與 notify／return 同一個 router，仍受白名單限制
