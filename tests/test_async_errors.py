"""在 try 外面 reject 的 async handler，要回 500，而且 server 不能掛掉。

案例：POST /user/collection/info/<非 UUID> 通過 middleware 的 Joi 檢查後，
middlewares/collection 的 postCollection 在 try 外面 await pool.query，Postgres 拒絕非 UUID 而 reject。
（原案例 /newebpay/payment 在 P4 Task 8 改成 try 內處理，換成仍有此行為的路由；
這條路由的 500 本身可視為驗證缺陷，這裡只釘住「rejection 不得讓 server 掛掉並回 500」。）
"""
from conftest import auth_header


def test_rejection_outside_try_returns_500_and_server_survives(api, make_user):
    user = make_user()

    r = api.post("/api/v1/user/collection/info/not-a-uuid", headers=auth_header(user), json={}, timeout=5)

    assert r.status_code == 500
    assert r.json()["status"] == "error"
    assert api.get("/api/v1/health").status_code == 200
