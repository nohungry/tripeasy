"""P4 Task 5：整車建單、價格快照、取消舊單、summary 與逾時、應付金額單一來源。"""
import json
import subprocess
from concurrent.futures import ThreadPoolExecutor

from conftest import (
    CART_API,
    CHECKOUT_API,
    ROOT,
    add_to_cart,
    auth_header,
    cancel_discount,
    checkout,
    live_promotion,
    notify,
    preview,
    ready_order,
    refund,
    start_payment,
    success_notify,
    trial_discount,
)
from test_seed import EMAIL, _paid_by_order


def _cart_id(db, user) -> str:
    return str(db.execute("SELECT cart_id FROM cart WHERE user_id = %s", (user["user_id"],)).fetchone()[0])


def _summary(api, user, order_id):
    return api.get(f"{CHECKOUT_API}/summary/{order_id}", headers=auth_header(user), timeout=5)


def _statuses(db, order_id):
    order = db.execute("SELECT payment_status FROM orders WHERE order_id = %s", (order_id,)).fetchone()[0]
    items = {r[0] for r in db.execute("SELECT payment_status FROM order_item WHERE order_id = %s", (order_id,))}
    return order, items


def _age_order(db, order_id, minutes=61):
    db.execute(
        "UPDATE orders SET created_at = now() - make_interval(mins => %s) WHERE order_id = %s", (minutes, order_id)
    )


def test_create_order_includes_every_cart_item(api, db, make_user, make_tour):
    user = make_user()
    order_id = checkout(api, user, [make_tour(price=1000), make_tour(price=2000)])
    assert db.execute("SELECT count(*) FROM order_item WHERE order_id = %s", (order_id,)).fetchone()[0] == 2
    assert db.execute("SELECT total_price FROM orders WHERE order_id = %s", (order_id,)).fetchone()[0] == 3000


def test_create_order_snapshots_promo_price(api, db, make_user, make_tour):
    user = make_user()
    promo, plain = live_promotion(db, make_tour), make_tour(price=1000)
    assert add_to_cart(api, user, promo, people=2).status_code == 201
    order_id = checkout(api, user, [plain])
    rows = dict(
        db.execute("SELECT tour_id::text, discount_price FROM order_item WHERE order_id = %s", (order_id,)).fetchall()
    )
    assert rows[promo["tour_id"]] == 1800
    assert rows[plain["tour_id"]] is None
    summary = _summary(api, user, order_id).json()["data"]["summary"]
    assert summary["promo_subtotal"] == 2800
    assert summary["payable"] == 2800


def test_create_order_empty_cart_is_400(api, db, make_user, make_tour):
    user = make_user()
    tour = make_tour()
    assert add_to_cart(api, user, tour).status_code == 201
    item_id = db.execute(
        "SELECT cart_item_id FROM cart_item WHERE cart_id = %s", (_cart_id(db, user),)
    ).fetchone()[0]
    r = api.delete(f"{CART_API}/{item_id}", headers=auth_header(user), timeout=5)
    assert r.status_code == 200, r.text
    r = api.post(f"{CHECKOUT_API}/order/{_cart_id(db, user)}", headers=auth_header(user), timeout=5)
    assert r.status_code == 400
    assert r.json()["message"] == "購物車沒有項目"


def test_create_order_cancels_previous_pending(api, db, make_user, make_tour):
    user = make_user()
    first = checkout(api, user, [make_tour()])
    r = api.post(f"{CHECKOUT_API}/order/{_cart_id(db, user)}", headers=auth_header(user), timeout=5)
    assert r.status_code == 200, r.text
    second = r.json()["data"]["order_id"]
    assert _statuses(db, first) == (2, {2})
    assert _statuses(db, second) == (-1, {-1})


def test_create_order_concurrently_leaves_one_pending(api, db, make_user, make_tour):
    user = make_user()
    assert add_to_cart(api, user, make_tour()).status_code == 201
    url = f"{CHECKOUT_API}/order/{_cart_id(db, user)}"
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(api.post, url, headers=auth_header(user), timeout=10) for _ in range(2)]
        codes = [f.result().status_code for f in futures]
    assert codes == [200, 200]
    pending = db.execute(
        "SELECT count(*) FROM orders WHERE user_id = %s AND payment_status IN (-1, 0)", (user["user_id"],)
    ).fetchone()[0]
    assert pending == 1


def test_create_order_keeps_cart(api, db, make_user, make_tour):
    user = make_user()
    checkout(api, user, [make_tour(), make_tour()])
    count = db.execute("SELECT count(*) FROM cart_item WHERE cart_id = %s", (_cart_id(db, user),)).fetchone()[0]
    assert count == 2


def test_other_users_cart_is_404(api, db, make_user, make_tour):
    owner, other = make_user(), make_user()
    assert add_to_cart(api, owner, make_tour()).status_code == 201
    r = api.post(f"{CHECKOUT_API}/order/{_cart_id(db, owner)}", headers=auth_header(other), timeout=5)
    assert r.status_code == 404
    assert r.json()["message"] == "查無此購物車項目"
    assert db.execute("SELECT count(*) FROM orders WHERE user_id = %s", (owner["user_id"],)).fetchone()[0] == 0


def test_other_users_summary_is_404(api, make_user, make_tour):
    owner, other = make_user(), make_user()
    order_id = checkout(api, owner, [make_tour()])
    r = _summary(api, other, order_id)
    assert r.status_code == 404
    assert r.json()["message"] == "查無此訂單項目"


def test_other_users_userinfo_is_404(api, make_user, make_tour):
    owner, other = make_user(), make_user()
    order_id = checkout(api, owner, [make_tour()])
    r = api.get(f"{CHECKOUT_API}/userinfo/{order_id}", headers=auth_header(other), timeout=5)
    assert r.status_code == 404
    assert r.json()["message"] == "查無此訂單項目"


def test_summary_expires_overdue_order(api, db, make_user, make_tour):
    user = make_user()
    order_id = checkout(api, user, [make_tour()])
    _age_order(db, order_id)
    r = _summary(api, user, order_id)
    assert r.status_code == 200, r.text
    assert r.json()["data"]["summary"]["payment_status"] == 4
    assert _statuses(db, order_id) == (4, {4})


def test_summary_does_not_expire_order_with_payment_in_progress(api, db, make_user, make_tour):
    user = make_user()
    order_id = checkout(api, user, [make_tour()])
    _age_order(db, order_id)
    db.execute(
        "INSERT INTO payment (user_id, order_id, payment_method, payment_status, result_time, created_at) "
        "VALUES (%s, %s, 'credit_card', 0, NULL, now())",
        (user["user_id"], order_id),
    )
    r = _summary(api, user, order_id)
    assert r.status_code == 200, r.text
    assert r.json()["data"]["summary"]["payment_status"] == -1
    assert _statuses(db, order_id) == (-1, {-1})


def test_summary_get_point_is_floor_of_payable(api, make_user, make_tour):
    user = make_user()
    order_id = checkout(api, user, [make_tour(price=1005)])
    summary = _summary(api, user, order_id).json()["data"]["summary"]
    assert summary["payable"] == 1005
    assert summary["get_point"] == 100


def test_payable_treats_zero_discount_price_as_no_promo(api, db, make_user, make_tour):
    user = make_user()
    order_id = checkout(api, user, [make_tour(price=1000)])
    db.execute("UPDATE order_item SET discount_price = 0 WHERE order_id = %s", (order_id,))
    summary = _summary(api, user, order_id).json()["data"]["summary"]
    assert summary["total_price"] == 1000
    assert summary["promo_subtotal"] == summary["total_price"]
    assert summary["payable"] == summary["total_price"]


def _insert_attempt(db, user, order_id, *, result_time_sql, age_seconds):
    db.execute(
        "INSERT INTO payment (user_id, order_id, payment_method, payment_status, result_time, created_at) "
        f"VALUES (%s, %s, 'credit_card', 0, {result_time_sql}, now() - make_interval(secs => %s))",
        (user["user_id"], order_id, age_seconds),
    )


def test_summary_expires_when_payment_attempt_has_result(api, db, make_user, make_tour):
    user = make_user()
    order_id = checkout(api, user, [make_tour()])
    _age_order(db, order_id)
    _insert_attempt(db, user, order_id, result_time_sql="now()", age_seconds=0)
    assert _summary(api, user, order_id).json()["data"]["summary"]["payment_status"] == 4
    assert _statuses(db, order_id) == (4, {4})


def test_summary_expires_when_payment_attempt_past_trade_limit(api, db, make_user, make_tour):
    user = make_user()
    order_id = checkout(api, user, [make_tour()])
    _age_order(db, order_id)
    _insert_attempt(db, user, order_id, result_time_sql="NULL", age_seconds=11 * 60)
    assert _summary(api, user, order_id).json()["data"]["summary"]["payment_status"] == 4
    assert _statuses(db, order_id) == (4, {4})


def test_summary_does_not_expire_before_deadline(api, db, make_user, make_tour):
    user = make_user()
    order_id = checkout(api, user, [make_tour()])
    _age_order(db, order_id, minutes=59)
    assert _summary(api, user, order_id).json()["data"]["summary"]["payment_status"] == -1
    assert _statuses(db, order_id) == (-1, {-1})


def test_create_order_and_preview_points_concurrently_no_500(api, db, make_user, make_tour):
    user = make_user()
    db.execute("UPDATE user_level SET travel_point = 1000 WHERE user_id = %s", (user["user_id"],))
    tour = make_tour()
    body = {
        "user": {"name": "測試用戶", "email": user["email"], "address": "台北市測試路1號", "phone_number": "0912345678"},
        "payment_method": "atm",
        "discount": {"type": "point", "used_point": 50},
    }
    headers = auth_header(user)
    for round_no in range(8):
        order_id = checkout(api, user, [tour])
        cart = _cart_id(db, user)
        with ThreadPoolExecutor(max_workers=2) as pool:
            preview = pool.submit(
                api.patch, f"{CHECKOUT_API}/preview/{order_id}", json=body, headers=headers, timeout=15
            )
            create = pool.submit(api.post, f"{CHECKOUT_API}/order/{cart}", headers=headers, timeout=15)
            codes = (preview.result().status_code, create.result().status_code)
        assert 500 not in codes, (round_no, codes)


NODE_PAYABLE = """
const { pool } = require('./src/config/database');
const { computePayable } = require('./src/utils/trade');
(async () => {
  const ids = JSON.parse(process.argv[1]);
  const client = await pool.connect();
  const out = {};
  try {
    await client.query('BEGIN');
    for (const id of ids) out[id] = (await computePayable(client, id)).payable;
  } finally {
    await client.query('ROLLBACK');
    client.release();
  }
  console.log('RESULT' + JSON.stringify(out));
  process.exit(0);
})().catch((e) => { console.error(e); process.exit(1); });
"""


def test_payable_matches_seed_paid_orders(db):
    """唯讀：在 backend 容器內以 ROLLBACK 交易呼叫 computePayable，與 test_seed 的實付定義比對。"""
    seed_emails = set(EMAIL.values())
    expected = {(email, title): int(paid) for email, title, paid, _, _ in _paid_by_order(db) if email in seed_emails}
    assert len(expected) == 15
    order_ids = {}
    for order_id, email, title in db.execute(
        'SELECT o.order_id::text, u.email, t.title FROM orders o JOIN "user" u USING (user_id) '
        "JOIN order_item oi USING (order_id) JOIN tour t ON t.tour_id = oi.tour_id "
        "WHERE o.payment_status = 1 AND u.email = ANY(%s)",
        (list(EMAIL.values()),),
    ).fetchall():
        order_ids[order_id] = (email, title)
    assert len(order_ids) == 15
    proc = subprocess.run(
        ["docker", "compose", "exec", "-T", "backend", "node", "-e", NODE_PAYABLE, json.dumps(list(order_ids))],
        cwd=ROOT, capture_output=True, text=True, timeout=60,
    )  # fmt: skip
    assert proc.returncode == 0, proc.stderr
    line = next(l for l in proc.stdout.splitlines() if l.startswith("RESULT"))
    actual = {order_ids[oid]: payable for oid, payable in json.loads(line[len("RESULT"):]).items()}
    assert actual == expected


# ------------------------------------------------------------------ P4 Task 6：折扣試算與保留

NOT_OWNER = "查無此訂單項目"


def _set_points(db, user, points):
    db.execute("UPDATE user_level SET travel_point = %s WHERE user_id = %s", (points, user["user_id"]))


def _user_coupon(db, user, coupon):
    """回傳 (status, order_id 或 None)。"""
    row = db.execute(
        "SELECT status, order_id::text FROM user_coupon WHERE user_id = %s AND coupon_id = %s",
        (user["user_id"], coupon["coupon_id"]),
    ).fetchone()
    return row[0], row[1]


def _reserved_points(db, order_id):
    return [
        r[0]
        for r in db.execute(
            "SELECT point FROM point_record WHERE order_id = %s AND type = '減少_確認中'", (order_id,)
        ).fetchall()
    ]


def _order_discount(db, order_id):
    return db.execute(
        "SELECT discount_type, discount_price FROM orders WHERE order_id = %s", (order_id,)
    ).fetchone()


def _coupon_body(coupon):
    return {"type": "coupon", "discount": {"coupon": coupon["code"]}}


def _promo_order(api, db, make_tour, user, people=2):
    """促銷行程 900 × people 的訂單（2 人 = 1800）。"""
    assert add_to_cart(api, user, live_promotion(db, make_tour), people=people).status_code == 201
    return checkout(api, user, [])


def test_coupon_subtracts_amount_on_promo_subtotal(api, db, make_user, make_tour, make_coupon):
    user = make_user()
    coupon = make_coupon(user, discount=100)
    order_id = _promo_order(api, db, make_tour, user)
    r = preview(api, user, order_id, {"type": "coupon", "coupon_id": coupon["coupon_id"]})
    assert r.status_code == 200, r.text
    assert r.json()["data"]["payable"] == 1700
    assert db.execute("SELECT discount_price FROM orders WHERE order_id = %s", (order_id,)).fetchone()[0] == 1700
    assert _summary(api, user, order_id).json()["data"]["summary"]["payable"] == 1700
    assert _user_coupon(db, user, coupon) == (-1, order_id)


def test_trial_discount_does_not_write(api, db, make_user, make_tour, make_coupon):
    user = make_user()
    coupon = make_coupon(user, discount=100)
    order_id = _promo_order(api, db, make_tour, user)
    r = trial_discount(api, user, order_id, _coupon_body(coupon))
    assert r.status_code == 200, r.text
    summary = r.json()["data"]["summary"]
    assert summary["payable"] == 1700
    assert summary["discount_amount"] == 100
    assert summary["promo_subtotal"] == 1800
    assert _user_coupon(db, user, coupon) == (0, None)
    assert _order_discount(db, order_id) == (None, None)


def test_point_must_be_multiple_of_five(api, db, make_user, make_tour):
    user = make_user()
    _set_points(db, user, 100)
    order_id = checkout(api, user, [make_tour(price=1000)])
    r = preview(api, user, order_id, {"type": "point", "used_point": 12})
    assert (r.status_code, r.json()["message"]) == (400, "旅遊積分必須是 5 的倍數")
    r = trial_discount(api, user, order_id, {"type": "point", "discount": {"point": 12}})
    assert (r.status_code, r.json()["message"]) == (400, "旅遊積分必須是 5 的倍數")
    assert _reserved_points(db, order_id) == []


def test_point_reserves_and_limits_balance(api, db, make_user, make_tour, make_order):
    user = make_user()
    _set_points(db, user, 100)
    tour = make_tour(price=1000)
    order_a = checkout(api, user, [tour])
    r = preview(api, user, order_a, {"type": "point", "used_point": 100})
    assert r.status_code == 200, r.text
    assert _reserved_points(db, order_a) == [-100]
    assert r.json()["data"]["payable"] == 1000 - 80
    # API 不允許同一會員同時有兩張未付款訂單，B 單以 DB 直接建立
    order_b = make_order(user, tour["tour_id"], payment_status=-1)["order_id"]
    r = trial_discount(api, user, order_b, {"type": "point", "discount": {"point": 5}})
    assert (r.status_code, r.json()["message"]) == (409, "超出可使用的點數")


def test_discount_must_leave_one_dollar(api, db, make_user, make_tour, make_coupon):
    user = make_user()
    big, small = make_coupon(user, discount=300), make_coupon(user, discount=299)
    order_id = checkout(api, user, [make_tour(price=300)])
    r = preview(api, user, order_id, {"type": "coupon", "coupon_id": big["coupon_id"]})
    assert (r.status_code, r.json()["message"]) == (400, "折抵後金額至少需 1 元")
    assert _user_coupon(db, user, big) == (0, None)
    r = preview(api, user, order_id, {"type": "coupon", "coupon_id": small["coupon_id"]})
    assert r.status_code == 200, r.text
    assert r.json()["data"]["payable"] == 1
    assert _summary(api, user, order_id).json()["data"]["summary"]["payable"] == 1


def test_coupon_reserved_by_other_order_is_409(api, db, make_user, make_tour, make_order, make_coupon):
    user = make_user()
    first, second = make_coupon(user), make_coupon(user)
    tour = make_tour(price=1000)
    order_a = checkout(api, user, [tour])
    assert preview(api, user, order_a, {"type": "coupon", "coupon_id": first["coupon_id"]}).status_code == 200
    assert _user_coupon(db, user, first) == (-1, order_a)
    order_b = checkout(api, user, [])  # 建 B 單時 A 被取消、券被釋放
    assert _user_coupon(db, user, first) == (0, None)
    r = preview(api, user, order_b, {"type": "coupon", "coupon_id": first["coupon_id"]})
    assert r.status_code == 200, r.text
    # 另一張券被別的訂單保留（DB 直接設定）
    other = make_order(user, tour["tour_id"], payment_status=-1)["order_id"]
    db.execute(
        "UPDATE user_coupon SET status = -1, order_id = %s WHERE user_id = %s AND coupon_id = %s",
        (other, user["user_id"], second["coupon_id"]),
    )
    r = preview(api, user, order_b, {"type": "coupon", "coupon_id": second["coupon_id"]})
    assert (r.status_code, r.json()["message"]) == (409, "優惠券已被其他訂單保留")
    assert _user_coupon(db, user, second) == (-1, other)


def test_preview_change_discount_releases_previous(api, db, make_user, make_tour, make_coupon):
    user = make_user()
    _set_points(db, user, 100)
    coupon = make_coupon(user)
    order_id = checkout(api, user, [make_tour(price=1000)])
    assert preview(api, user, order_id, {"type": "coupon", "coupon_id": coupon["coupon_id"]}).status_code == 200
    assert preview(api, user, order_id, {"type": "point", "used_point": 50}).status_code == 200
    assert _user_coupon(db, user, coupon) == (0, None)
    assert _reserved_points(db, order_id) == [-50]
    assert _order_discount(db, order_id) == ("point", 960)


def test_cancel_discount_releases_coupon(api, db, make_user, make_tour, make_coupon):
    user = make_user()
    coupon = make_coupon(user)
    order_id = checkout(api, user, [make_tour(price=1000)])
    assert preview(api, user, order_id, {"type": "coupon", "coupon_id": coupon["coupon_id"]}).status_code == 200
    r = cancel_discount(api, user, order_id)
    assert r.status_code == 200, r.text
    assert r.json()["data"]["summary"]["payable"] == 1000
    assert _user_coupon(db, user, coupon) == (0, None)
    assert _order_discount(db, order_id) == ("none", None)


def test_cancel_discount_releases_points(api, db, make_user, make_tour):
    user = make_user()
    _set_points(db, user, 100)
    order_id = checkout(api, user, [make_tour(price=1000)])
    assert preview(api, user, order_id, {"type": "point", "used_point": 50}).status_code == 200
    assert _reserved_points(db, order_id) == [-50]
    assert cancel_discount(api, user, order_id).status_code == 200
    assert _reserved_points(db, order_id) == []


def test_negative_balance_means_zero_available_points(api, db, make_user, make_tour, make_coupon):
    user = make_user()
    _set_points(db, user, -50)
    coupon = make_coupon(user)
    order_id = checkout(api, user, [make_tour(price=1000)])
    r = trial_discount(api, user, order_id, {"type": "point", "discount": {"point": 5}})
    assert (r.status_code, r.json()["message"]) == (409, "超出可使用的點數")
    assert trial_discount(api, user, order_id, _coupon_body(coupon)).status_code == 200


def test_preview_other_users_order_is_404(api, db, make_user, make_tour, make_coupon):
    owner, other = make_user(), make_user()
    coupon = make_coupon(owner)
    order_id = checkout(api, owner, [make_tour(price=1000)])
    assert preview(api, owner, order_id, {"type": "coupon", "coupon_id": coupon["coupon_id"]}).status_code == 200
    r = preview(api, other, order_id, None)
    assert (r.status_code, r.json()["message"]) == (404, NOT_OWNER)
    assert _statuses(db, order_id) == (0, {0})
    assert _user_coupon(db, owner, coupon) == (-1, order_id)


def test_trial_discount_other_users_order_is_404(api, db, make_user, make_tour, make_coupon):
    owner, other = make_user(), make_user()
    coupon = make_coupon(owner)
    order_id = checkout(api, owner, [make_tour(price=1000)])
    assert preview(api, owner, order_id, {"type": "coupon", "coupon_id": coupon["coupon_id"]}).status_code == 200
    r = trial_discount(api, other, order_id, _coupon_body(coupon))
    assert (r.status_code, r.json()["message"]) == (404, NOT_OWNER)
    assert _user_coupon(db, owner, coupon) == (-1, order_id)


def test_cancel_discount_other_users_order_is_404(api, db, make_user, make_tour, make_coupon):
    owner, other = make_user(), make_user()
    coupon = make_coupon(owner)
    order_id = checkout(api, owner, [make_tour(price=1000)])
    assert preview(api, owner, order_id, {"type": "coupon", "coupon_id": coupon["coupon_id"]}).status_code == 200
    r = cancel_discount(api, other, order_id)
    assert (r.status_code, r.json()["message"]) == (404, NOT_OWNER)
    assert _user_coupon(db, owner, coupon) == (-1, order_id)
    assert _order_discount(db, order_id)[0] == "coupon"


def test_used_and_expired_coupon_rejected(api, db, make_user, make_tour, make_coupon):
    user = make_user()
    used, expired = make_coupon(user, status=1), make_coupon(user, expire_in_days=-1)
    order_id = checkout(api, user, [make_tour(price=1000)])
    r = preview(api, user, order_id, {"type": "coupon", "coupon_id": used["coupon_id"]})
    assert (r.status_code, r.json()["message"]) == (409, "優惠券已使用")
    r = preview(api, user, order_id, {"type": "coupon", "coupon_id": expired["coupon_id"]})
    assert (r.status_code, r.json()["message"]) == (409, "優惠券已過期")
    r = trial_discount(api, user, order_id, _coupon_body(used))
    assert (r.status_code, r.json()["message"]) == (409, "優惠券已使用")
    r = trial_discount(api, user, order_id, _coupon_body(expired))
    assert (r.status_code, r.json()["message"]) == (409, "優惠券已過期")


def test_other_users_coupon_is_404(api, make_user, make_tour, make_coupon):
    user, other = make_user(), make_user()
    coupon = make_coupon(other)
    order_id = checkout(api, user, [make_tour(price=1000)])
    r = preview(api, user, order_id, {"type": "coupon", "coupon_id": coupon["coupon_id"]})
    assert (r.status_code, r.json()["message"]) == (404, "查無此優惠卷")
    r = trial_discount(api, user, order_id, _coupon_body(coupon))
    assert (r.status_code, r.json()["message"]) == (404, "查無此優惠卷")


def _wait_until(predicate, timeout=10.0, interval=0.05):
    import time

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(interval)
    return False


def test_preview_same_coupon_concurrently_reserves_once(api, db, make_user, make_tour, make_order, make_coupon):
    """決定性：先用另一條連線鎖住 user_coupon 列，兩個 preview 都卡在鎖上後才放行。"""
    import psycopg

    from conftest import _db_params

    user = make_user()
    coupon = make_coupon(user)
    tour = make_tour(price=1000)
    # API 不會讓同一會員同時有兩張未付款訂單，兩張 -1 訂單以 DB 直接建立
    orders = [make_order(user, tour["tour_id"], payment_status=-1)["order_id"] for _ in range(2)]
    before = {order_id: _order_discount(db, order_id) for order_id in orders}
    discount = {"type": "coupon", "coupon_id": coupon["coupon_id"]}

    def waiting_on_coupon_lock():
        (n,) = db.execute(
            "SELECT count(*) FROM pg_stat_activity WHERE wait_event_type = 'Lock' "
            "AND query ILIKE '%%user_coupon%%FOR UPDATE%%' AND pid <> pg_backend_pid()"
        ).fetchone()
        return n

    locker = psycopg.connect(**_db_params())
    try:
        locker.execute(
            "SELECT user_coupon_id FROM user_coupon WHERE user_id = %s AND coupon_id = %s FOR UPDATE",
            (user["user_id"], coupon["coupon_id"]),
        )
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = {order_id: pool.submit(preview, api, user, order_id, discount) for order_id in orders}
            both_waiting = _wait_until(lambda: waiting_on_coupon_lock() >= 2)
            locker.rollback()
            results = {order_id: f.result() for order_id, f in futures.items()}
    finally:
        locker.close()
    assert both_waiting, "兩個 preview 沒有同時卡在 user_coupon 的列鎖上"
    codes = sorted(r.status_code for r in results.values())
    assert codes == [200, 409], [r.text for r in results.values()]
    winner = next(o for o, r in results.items() if r.status_code == 200)
    loser = next(o for o, r in results.items() if r.status_code == 409)
    assert results[loser].json()["message"] == "優惠券已被其他訂單保留"
    assert _user_coupon(db, user, coupon) == (-1, winner)
    assert _order_discount(db, loser) == before[loser]


def test_preview_resend_same_coupon_same_order_is_200(api, db, make_user, make_tour, make_coupon):
    user = make_user()
    coupon = make_coupon(user)
    order_id = checkout(api, user, [make_tour(price=1000)])
    discount = {"type": "coupon", "coupon_id": coupon["coupon_id"]}
    assert preview(api, user, order_id, discount).status_code == 200
    r = preview(api, user, order_id, discount)
    assert r.status_code == 200, r.text
    assert _user_coupon(db, user, coupon) == (-1, order_id)
    r = preview(api, user, order_id.upper(), discount)
    assert r.status_code == 200, r.text
    assert r.json()["data"]["discount_price"] == r.json()["data"]["payable"] == 900
    assert _user_coupon(db, user, coupon) == (-1, order_id)


def test_preview_without_discount_releases_reservation(api, db, make_user, make_tour, make_coupon):
    user = make_user()
    coupon = make_coupon(user)
    order_id = checkout(api, user, [make_tour(price=1000)])
    assert preview(api, user, order_id, {"type": "coupon", "coupon_id": coupon["coupon_id"]}).status_code == 200
    r = preview(api, user, order_id, None)
    assert r.status_code == 200, r.text
    assert r.json()["data"]["discount_price"] is None
    assert r.json()["data"]["payable"] == 1000
    assert _user_coupon(db, user, coupon) == (0, None)
    assert _order_discount(db, order_id) == ("none", None)


def test_preview_on_expired_order_is_409(api, db, make_user, make_tour, make_coupon):
    user = make_user()
    coupon = make_coupon(user)
    order_id = checkout(api, user, [make_tour(price=1000)])
    discount = {"type": "coupon", "coupon_id": coupon["coupon_id"]}
    assert preview(api, user, order_id, discount).status_code == 200
    _age_order(db, order_id)
    r = preview(api, user, order_id, discount)
    assert (r.status_code, r.json()["message"]) == (409, "訂單已逾時")
    assert _statuses(db, order_id) == (4, {4})
    assert _user_coupon(db, user, coupon) == (0, None)


def test_preview_on_paid_order_is_409(api, db, make_user, make_tour):
    user = make_user()
    order_id = checkout(api, user, [make_tour(price=1000)])
    db.execute("UPDATE orders SET payment_status = 1 WHERE order_id = %s", (order_id,))
    r = preview(api, user, order_id, None)
    assert (r.status_code, r.json()["message"]) == (409, "訂單狀態不允許此操作")
    assert _statuses(db, order_id)[0] == 1


# 以下三支原屬 Task 5，因需要 make_coupon 與新的保留邏輯而移到本 Task


def test_expire_releases_point_reservation(api, db, make_user, make_tour):
    user = make_user()
    _set_points(db, user, 100)
    order_id = checkout(api, user, [make_tour(price=1000)])
    assert preview(api, user, order_id, {"type": "point", "used_point": 50}).status_code == 200
    assert _reserved_points(db, order_id) == [-50]
    _age_order(db, order_id)
    assert _summary(api, user, order_id).json()["data"]["summary"]["payment_status"] == 4
    assert _reserved_points(db, order_id) == []


def test_create_new_order_releases_point_reservation(api, db, make_user, make_tour):
    user = make_user()
    _set_points(db, user, 100)
    order_a = checkout(api, user, [make_tour(price=1000)])
    assert preview(api, user, order_a, {"type": "point", "used_point": 50}).status_code == 200
    assert _reserved_points(db, order_a) == [-50]
    r = api.post(f"{CHECKOUT_API}/order/{_cart_id(db, user)}", headers=auth_header(user), timeout=5)
    assert r.status_code == 200, r.text
    assert _reserved_points(db, order_a) == []
    assert _statuses(db, order_a) == (2, {2})


def test_create_new_order_releases_coupon_reservation(api, db, make_user, make_tour, make_coupon):
    user = make_user()
    coupon = make_coupon(user)
    order_a = checkout(api, user, [make_tour(price=1000)])
    assert preview(api, user, order_a, {"type": "coupon", "coupon_id": coupon["coupon_id"]}).status_code == 200
    assert _user_coupon(db, user, coupon) == (-1, order_a)
    r = api.post(f"{CHECKOUT_API}/order/{_cart_id(db, user)}", headers=auth_header(user), timeout=5)
    assert r.status_code == 200, r.text
    assert _user_coupon(db, user, coupon) == (0, None)


def test_summary_expires_overdue_order_releases_coupon(api, db, make_user, make_tour, make_coupon):
    user = make_user()
    coupon = make_coupon(user)
    order_id = checkout(api, user, [make_tour(price=1000)])
    assert preview(api, user, order_id, {"type": "coupon", "coupon_id": coupon["coupon_id"]}).status_code == 200
    _age_order(db, order_id)
    assert _summary(api, user, order_id).json()["data"]["summary"]["payment_status"] == 4
    assert _statuses(db, order_id) == (4, {4})
    assert _user_coupon(db, user, coupon) == (0, None)


# ---- 已付款與付款進行中不得改折扣

IN_PROGRESS = "付款進行中，請稍後再試"


def _start_payment(db, user, order_id):
    db.execute(
        "INSERT INTO payment (user_id, order_id, payment_method, payment_status, result_time, created_at) "
        "VALUES (%s, %s, 'credit_card', 0, NULL, now())",
        (user["user_id"], order_id),
    )


def test_cancel_discount_on_paid_order_is_409(api, db, make_user, make_tour, make_coupon):
    user = make_user()
    coupon = make_coupon(user)
    order_id = checkout(api, user, [make_tour(price=1000)])
    assert preview(api, user, order_id, {"type": "coupon", "coupon_id": coupon["coupon_id"]}).status_code == 200
    before = _order_discount(db, order_id)
    db.execute("UPDATE orders SET payment_status = 1 WHERE order_id = %s", (order_id,))
    r = cancel_discount(api, user, order_id)
    assert (r.status_code, r.json()["message"]) == (409, "訂單狀態不允許此操作")
    assert _order_discount(db, order_id) == before
    assert _user_coupon(db, user, coupon) == (-1, order_id)


def test_cancel_discount_on_expired_order_is_409(api, db, make_user, make_tour):
    user = make_user()
    order_id = checkout(api, user, [make_tour(price=1000)])
    _age_order(db, order_id)
    r = cancel_discount(api, user, order_id)
    assert (r.status_code, r.json()["message"]) == (409, "訂單已逾時")
    assert _statuses(db, order_id) == (4, {4})


def test_preview_while_payment_in_progress_is_409(api, db, make_user, make_tour, make_coupon):
    user = make_user()
    first, second = make_coupon(user), make_coupon(user)
    order_id = checkout(api, user, [make_tour(price=1000)])
    assert preview(api, user, order_id, {"type": "coupon", "coupon_id": first["coupon_id"]}).status_code == 200
    before = _order_discount(db, order_id)
    _start_payment(db, user, order_id)
    r = preview(api, user, order_id, {"type": "coupon", "coupon_id": second["coupon_id"]})
    assert (r.status_code, r.json()["message"]) == (409, IN_PROGRESS)
    assert _user_coupon(db, user, first) == (-1, order_id)
    assert _user_coupon(db, user, second) == (0, None)
    assert _order_discount(db, order_id) == before


def test_cancel_discount_while_payment_in_progress_is_409(api, db, make_user, make_tour, make_coupon):
    user = make_user()
    coupon = make_coupon(user)
    order_id = checkout(api, user, [make_tour(price=1000)])
    assert preview(api, user, order_id, {"type": "coupon", "coupon_id": coupon["coupon_id"]}).status_code == 200
    before = _order_discount(db, order_id)
    _start_payment(db, user, order_id)
    r = cancel_discount(api, user, order_id)
    assert (r.status_code, r.json()["message"]) == (409, IN_PROGRESS)
    assert _user_coupon(db, user, coupon) == (-1, order_id)
    assert _order_discount(db, order_id) == before


# ---- 最終審查修正 F1：建單重驗購物車項目

CART_STALE = "購物車中有已下架或已過出發日的項目，請移除後再結帳"


def _post_order(api, db, user):
    return api.post(f"{CHECKOUT_API}/order/{_cart_id(db, user)}", headers=auth_header(user), timeout=5)


def _order_count(db, user):
    return db.execute("SELECT count(*) FROM orders WHERE user_id = %s", (user["user_id"],)).fetchone()[0]


def test_create_order_rejects_taken_down_tour(api, db, make_user, make_tour):
    user = make_user()
    tour = make_tour(price=1000)
    assert add_to_cart(api, user, tour).status_code == 201
    db.execute("UPDATE tour SET status = 0 WHERE tour_id = %s", (tour["tour_id"],))
    r = _post_order(api, db, user)
    assert (r.status_code, r.json()["message"]) == (409, CART_STALE)
    assert _order_count(db, user) == 0


def test_create_order_rejects_past_start_date(api, db, make_user, make_tour):
    user = make_user()
    tour = make_tour(price=1000)
    assert add_to_cart(api, user, tour).status_code == 201
    db.execute(
        "UPDATE cart_item SET start_date = now() - interval '3 days' WHERE cart_id = %s", (_cart_id(db, user),)
    )
    r = _post_order(api, db, user)
    assert (r.status_code, r.json()["message"]) == (409, CART_STALE)
    assert _order_count(db, user) == 0


def test_create_order_stale_item_keeps_previous_pending_order(api, db, make_user, make_tour):
    user = make_user()
    first = checkout(api, user, [make_tour(price=1000)])
    stale = make_tour(price=1000)
    assert add_to_cart(api, user, stale).status_code == 201
    db.execute("UPDATE tour SET status = 0 WHERE tour_id = %s", (stale["tour_id"],))
    assert _post_order(api, db, user).status_code == 409
    assert db.execute("SELECT payment_status FROM orders WHERE order_id = %s", (first,)).fetchone()[0] == -1


def test_create_order_valid_cart_still_ok(api, db, make_user, make_tour):
    user = make_user()
    tour = make_tour(price=1000)
    assert add_to_cart(api, user, tour).status_code == 201
    assert _post_order(api, db, user).status_code == 200


# ---- F4：付款進行中，同折扣的預覽可通過且不動保留

def test_preview_same_coupon_while_payment_in_progress_is_ok(api, db, make_user, make_tour, make_coupon):
    user = make_user()
    coupon = make_coupon(user)
    order_id = checkout(api, user, [make_tour(price=1000)])
    assert preview(api, user, order_id, {"type": "coupon", "coupon_id": coupon["coupon_id"]}).status_code == 200
    before = _order_discount(db, order_id)
    _start_payment(db, user, order_id)
    r = preview(api, user, order_id, {"type": "coupon", "coupon_id": coupon["coupon_id"]})
    assert r.status_code == 200, r.text
    assert _user_coupon(db, user, coupon) == (-1, order_id)
    assert _order_discount(db, order_id) == before


def test_preview_same_points_while_payment_in_progress_is_ok(api, db, make_user, make_tour):
    user = make_user()
    db.execute("UPDATE user_level SET travel_point = 100 WHERE user_id = %s", (user["user_id"],))
    order_id = checkout(api, user, [make_tour(price=1000)])
    assert preview(api, user, order_id, {"type": "point", "used_point": 50}).status_code == 200
    rows = lambda: db.execute(
        "SELECT point_id, point FROM point_record WHERE order_id = %s AND type = '減少_確認中'", (order_id,)
    ).fetchall()
    before = rows()
    _start_payment(db, user, order_id)
    r = preview(api, user, order_id, {"type": "point", "used_point": 50})
    assert r.status_code == 200, r.text
    assert rows() == before
    r = preview(api, user, order_id, {"type": "point", "used_point": 55})
    assert (r.status_code, r.json()["message"]) == (409, IN_PROGRESS)
    assert rows() == before


def test_preview_same_none_while_payment_in_progress_updates_contact_only(api, db, make_user, make_tour):
    user = make_user()
    order_id = checkout(api, user, [make_tour(price=1000)])
    assert preview(api, user, order_id).status_code == 200
    _start_payment(db, user, order_id)
    r = preview(api, user, order_id)
    assert r.status_code == 200, r.text
    assert _order_discount(db, order_id) == ("none", None)


def test_preview_other_discount_while_payment_in_progress_still_409(api, db, make_user, make_tour, make_coupon):
    user = make_user()
    coupon = make_coupon(user)
    order_id = checkout(api, user, [make_tour(price=1000)])
    assert preview(api, user, order_id).status_code == 200
    _start_payment(db, user, order_id)
    r = preview(api, user, order_id, {"type": "coupon", "coupon_id": coupon["coupon_id"]})
    assert (r.status_code, r.json()["message"]) == (409, IN_PROGRESS)
    assert _user_coupon(db, user, coupon) == (0, None)


# ---- P5 Task 9（spec §7）：逾時與取消清空訂單折扣欄位


def test_expire_clears_discount_columns(api, db, make_user, make_tour, make_coupon):
    user = make_user()
    coupon = make_coupon(user)
    order_id = checkout(api, user, [make_tour(price=1000)])
    assert preview(api, user, order_id, {"type": "coupon", "coupon_id": coupon["coupon_id"]}).status_code == 200
    assert _order_discount(db, order_id)[0] == "coupon"
    _age_order(db, order_id)
    data = _summary(api, user, order_id).json()["data"]
    assert data["summary"]["payment_status"] == 4
    assert data["discount"]["type"] is None  # 回應與 DB 一致
    assert data["summary"]["discount_price"] is None
    assert _order_discount(db, order_id) == (None, None)
    assert _user_coupon(db, user, coupon) == (0, None)


def test_expire_point_order_clears_discount_columns(api, db, make_user, make_tour):
    user = make_user()
    _set_points(db, user, 100)
    order_id = checkout(api, user, [make_tour(price=1000)])
    assert preview(api, user, order_id, {"type": "point", "used_point": 50}).status_code == 200
    assert _order_discount(db, order_id)[0] == "point"
    _age_order(db, order_id)
    assert _summary(api, user, order_id).json()["data"]["summary"]["payment_status"] == 4
    assert _order_discount(db, order_id) == (None, None)
    assert _reserved_points(db, order_id) == []


def test_cancel_previous_order_clears_discount_columns(api, db, make_user, make_tour, make_coupon):
    user = make_user()
    coupon = make_coupon(user)
    order_a = checkout(api, user, [make_tour(price=1000)])
    assert preview(api, user, order_a, {"type": "coupon", "coupon_id": coupon["coupon_id"]}).status_code == 200
    assert _order_discount(db, order_a)[0] == "coupon"
    r = api.post(f"{CHECKOUT_API}/order/{_cart_id(db, user)}", headers=auth_header(user), timeout=5)
    assert r.status_code == 200, r.text
    assert _statuses(db, order_a) == (2, {2})
    assert _order_discount(db, order_a) == (None, None)
    assert _user_coupon(db, user, coupon) == (0, None)


def test_refund_keeps_discount_columns(api, db, make_user, make_tour, make_coupon):
    """回歸測試（一開始就綠）：退款不清折扣欄位，computePayable 的已退款分支仍讀 discount_type。"""
    admin, user = make_user(role="admin"), make_user()
    coupon = make_coupon(user, discount=100)
    tour = live_promotion(db, make_tour)
    user, order_id = ready_order(
        api, db, make_user, make_tour, {"type": "coupon", "coupon_id": coupon["coupon_id"]}, user=user, tour=tour, people=2
    )  # fmt: skip
    mon, amt, _ = start_payment(api, user, order_id)
    assert notify(api, success_notify(mon, amt)).status_code == 200
    before = _order_discount(db, order_id)
    assert before[0] == "coupon"
    assert refund(api, admin, order_id).status_code == 200
    assert _statuses(db, order_id) == (3, {3})
    assert _order_discount(db, order_id) == before


def test_paid_order_keeps_discount_columns_after_deadline_and_new_order(api, db, make_user, make_tour, make_coupon):
    """回歸測試（一開始就綠）：已付款訂單超過期限後，summary 與建立新單都不清折扣欄位。"""
    user = make_user()
    coupon = make_coupon(user, discount=100)
    tour = live_promotion(db, make_tour)
    user, order_id = ready_order(
        api, db, make_user, make_tour, {"type": "coupon", "coupon_id": coupon["coupon_id"]}, user=user, tour=tour, people=2
    )  # fmt: skip
    mon, amt, _ = start_payment(api, user, order_id)
    assert notify(api, success_notify(mon, amt)).status_code == 200
    before = _order_discount(db, order_id)
    assert before[0] == "coupon" and before[1] is not None
    _age_order(db, order_id)
    assert _summary(api, user, order_id).json()["data"]["summary"]["payment_status"] == 1
    assert _order_discount(db, order_id) == before
    checkout(api, user, [make_tour(price=1000)])  # 建立新單會取消其他未付款單，不得動已付款單
    assert _statuses(db, order_id) == (1, {1})
    assert _order_discount(db, order_id) == before
