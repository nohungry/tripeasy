"""P4 Task 5：整車建單、價格快照、取消舊單、summary 與逾時、應付金額單一來源。"""
import json
import subprocess
from concurrent.futures import ThreadPoolExecutor

from conftest import CART_API, CHECKOUT_API, ROOT, add_to_cart, auth_header, checkout, live_promotion
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
