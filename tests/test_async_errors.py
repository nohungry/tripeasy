"""在 try 外面 reject 的 async handler，要回 500，而且 server 不能掛掉。

案例：POST /user/trade/cart/<hotel 行程> 的 room_type 含 NUL 字元，Joi 的 string() 接受，
middlewares/cart 的 post_userCart 在 try 外面 await pool.query（hotel_booking），Postgres 拒絕 NUL 而 reject。
（原案例是收藏 POST 的非 UUID tour_id；P5 Task 7 加了 UUID 驗證改回 400，見 test_member_favorites.py::
test_collection_bad_uuid_is_400，所以換成仍有此行為的路由。這裡只釘住「rejection 不得讓 server 掛掉並回 500」。）
"""
import datetime

from conftest import CART_API, auth_header


def test_rejection_outside_try_returns_500_and_server_survives(api, make_user, make_tour):
    user = make_user()
    tour = make_tour(item="hotel", with_detail=False)
    day = datetime.date.today() + datetime.timedelta(days=1)
    body = {
        "type": tour["type"],
        "item": "hotel",
        "people": 1,
        "options": {
            "start_date": day.isoformat(),
            "end_date": (day + datetime.timedelta(days=1)).isoformat(),
            "room_type": "bad\u0000room",
        },
    }

    r = api.post(f"{CART_API}/{tour['tour_id']}", headers=auth_header(user), json=body, timeout=5)

    assert r.status_code == 500, r.text
    assert r.json()["status"] == "error"
    assert api.get("/api/v1/health").status_code == 200
