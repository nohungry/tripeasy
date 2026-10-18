"""在 try 外面 reject 的 async handler，要回 500，而且 server 不能掛掉。

案例：POST /user/newebpay/payment 帶空的 body，
newebpay.js:59 在 try 外面執行 order_items.reduce，會拋出 TypeError。
"""
from conftest import auth_header


def test_rejection_outside_try_returns_500_and_server_survives(api, make_user):
    user = make_user()

    r = api.post(
        "/api/v1/user/newebpay/payment", headers=auth_header(user), json={}, timeout=5
    )

    assert r.status_code == 500
    assert r.json()["status"] == "error"
    assert api.get("/api/v1/health").status_code == 200
