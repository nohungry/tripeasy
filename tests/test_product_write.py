"""P3 Task 6／7：購買資格查詢、寫評論、分享隱藏玩法 API（只限購買過的會員）。"""
import datetime
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

import psycopg
import pytest
import requests
from conftest import API_BASE, DEFAULT_TIMEOUT, _db_params, auth_header

SEARCH = "/api/v1/user/product/search"
NO_PERMISSION = "您沒有權限進行此操作"
NOT_BOUGHT = "購買過此行程的會員才能評論"
DUPLICATE = "你已評論過此行程"
NOT_BOUGHT_SHARE = "購買過此行程的會員才能分享隱藏玩法"
URL_MSG = "「url」必須是 http 或 https 網址"
SHARE_BODY = {"title": "清晨的魚市", "content": "六點前到"}
RATING_MSG = "「rating」必須是 1 到 5 的整數"
BODY = {"rating": 4, "content": "很棒的行程"}


def _url(tour_id, suffix="reviews") -> str:
    return f"{SEARCH}/{tour_id}/{suffix}"


def _buyer(make_user, make_order, tour, status=1) -> dict:
    user = make_user()
    make_order(user, tour["tour_id"], payment_status=status)
    return user


def _review_count(db, tour_id) -> int:
    return db.execute("SELECT count(*) FROM review WHERE tour_id = %s", (tour_id,)).fetchone()[0]


def test_post_review_requires_login(api, make_tour):
    t = make_tour()
    r = api.post(_url(t["tour_id"]), json=BODY)
    assert r.status_code == 401, r.text
    assert r.json()["message"] == "請先登入"


def test_post_review_admin_is_403(api, make_user, make_tour):
    t = make_tour()
    admin = make_user(role="admin")
    r = api.post(_url(t["tour_id"]), headers=auth_header(admin), json=BODY)
    assert r.status_code == 403, r.text
    assert r.json()["message"] == NO_PERMISSION


def test_post_review_admin_with_invalid_body_is_403(api, make_user, make_tour):
    t = make_tour()
    admin = make_user(role="admin")
    r = api.post(_url(t["tour_id"]), headers=auth_header(admin), json={"rating": 9})
    assert r.status_code == 403, r.text
    assert r.json()["message"] == NO_PERMISSION


def test_post_review_without_order_is_403(api, db, make_user, make_tour):
    t = make_tour()
    u = make_user()
    r = api.post(_url(t["tour_id"]), headers=auth_header(u), json=BODY)
    assert r.status_code == 403, r.text
    assert r.json()["message"] == NOT_BOUGHT
    assert _review_count(db, t["tour_id"]) == 0


@pytest.mark.parametrize("status", [-1, 0, 2, 3, 4])
def test_post_review_unpaid_status_is_403(api, db, make_user, make_order, make_tour, status):
    t = make_tour()
    u = _buyer(make_user, make_order, t, status=status)
    r = api.post(_url(t["tour_id"]), headers=auth_header(u), json=BODY)
    assert r.status_code == 403, r.text
    assert r.json()["message"] == NOT_BOUGHT
    assert _review_count(db, t["tour_id"]) == 0


def test_post_review_other_users_order_does_not_count(api, db, make_user, make_order, make_tour):
    t = make_tour()
    _buyer(make_user, make_order, t)  # B 已付款
    a = make_user()
    r = api.post(_url(t["tour_id"]), headers=auth_header(a), json=BODY)
    assert r.status_code == 403, r.text
    assert r.json()["message"] == NOT_BOUGHT
    assert _review_count(db, t["tour_id"]) == 0


def test_post_review_order_for_other_tour_does_not_count(api, db, make_user, make_order, make_tour):
    x, y = make_tour(), make_tour()
    u = _buyer(make_user, make_order, x)
    r = api.post(_url(y["tour_id"]), headers=auth_header(u), json=BODY)
    assert r.status_code == 403, r.text
    assert r.json()["message"] == NOT_BOUGHT
    assert _review_count(db, y["tour_id"]) == 0


def test_post_review_order_paid_but_item_unpaid_is_403(api, db, make_user, make_order, make_tour):
    t = make_tour()
    u = make_user()
    make_order(u, t["tour_id"], payment_status=0, order_payment_status=1)
    r = api.post(_url(t["tour_id"]), headers=auth_header(u), json=BODY)
    assert r.status_code == 403, r.text
    assert r.json()["message"] == NOT_BOUGHT
    assert _review_count(db, t["tour_id"]) == 0


def test_post_review_item_paid_but_order_unpaid_is_201(api, make_user, make_order, make_tour):
    t = make_tour()
    u = make_user()
    make_order(u, t["tour_id"], payment_status=1, order_payment_status=0)
    r = api.post(_url(t["tour_id"]), headers=auth_header(u), json=BODY)
    assert r.status_code == 201, r.text


def test_post_review_unpaid_item_in_same_order_as_paid_item_is_403(api, db, make_user, make_order, make_tour):
    from dbfactory import insert

    x, y = make_tour(), make_tour()
    u = make_user()
    order = make_order(u, x["tour_id"], payment_status=1)  # X 已付款
    insert(
        db, "order_item", order_id=order["order_id"], tour_id=y["tour_id"], payment_status=0,
        total_price=1000, quantity=1, start_date=datetime.datetime.now(),
    )  # Y 同一張訂單、未付款；會員的 teardown（delete_user）會清掉該訂單的所有品項
    r = api.post(_url(y["tour_id"]), headers=auth_header(u), json=BODY)
    assert r.status_code == 403, r.text
    assert r.json()["message"] == NOT_BOUGHT
    assert _review_count(db, y["tour_id"]) == 0
    r = api.post(_url(x["tour_id"]), headers=auth_header(u), json=BODY)
    assert r.status_code == 201, r.text


def _wait_until_insert_blocked(db, blocker_pid, timeout=10.0) -> None:
    """有期限地輪詢，直到後端的 review INSERT 被 blocker_pid 的交易擋住。"""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        row = db.execute(
            "SELECT count(*) FROM pg_stat_activity "
            "WHERE wait_event_type = 'Lock' AND %s = ANY(pg_blocking_pids(pid)) "
            "AND query LIKE 'INSERT INTO public.\"review\"%%'",
            (blocker_pid,),
        ).fetchone()
        if row[0] > 0:
            return
        time.sleep(0.05)
    pytest.fail("後端的 INSERT 沒有在期限內被未提交的交易擋住")


@pytest.mark.parametrize("finish, expected", [("commit", 409), ("rollback", 201)])
def test_post_review_insert_unique_violation_is_409(
    api, db, make_user, make_order, make_tour, finish, expected
):
    # 另一條連線先 INSERT 同一組 (user, tour) 但不 commit：READ COMMITTED 下 middleware 的
    # hasReviewed 看不到它而放行，後端的 INSERT 卡在唯一索引上；commit 後撞 23505 → 409，
    # rollback 則正常 201（對照組）
    t = make_tour()
    u = _buyer(make_user, make_order, t)
    holder = psycopg.connect(**_db_params())  # 非 autocommit
    try:
        holder.execute(
            "INSERT INTO review (user_id, tour_id, type, rating, content) VALUES (%s, %s, 'travel', 5, 'holder')",
            (u["user_id"], t["tour_id"]),
        )
        blocker_pid = holder.info.backend_pid
        with ThreadPoolExecutor(1) as pool:
            fut = pool.submit(
                lambda: requests.post(
                    f"{API_BASE}{_url(t['tour_id'])}", headers=auth_header(u), json=BODY, timeout=DEFAULT_TIMEOUT
                )
            )
            try:
                _wait_until_insert_blocked(db, blocker_pid)
            finally:
                getattr(holder, finish)()
            r = fut.result(timeout=DEFAULT_TIMEOUT)
    finally:
        holder.close()
    assert r.status_code == expected, r.text
    if expected == 409:
        assert r.json()["message"] == DUPLICATE
        # 留下的是 holder 那一則；會員／行程的 teardown 會清掉 review
        assert db.execute(
            "SELECT content FROM review WHERE tour_id = %s", (t["tour_id"],)
        ).fetchall() == [("holder",)]
    assert _review_count(db, t["tour_id"]) == 1


def test_post_review_validation_before_purchase_check(api, make_user, make_tour):
    t = make_tour()
    u = make_user()  # 未購買
    r = api.post(_url(t["tour_id"]), headers=auth_header(u), json={"rating": 0, "content": "x"})
    assert r.status_code == 400, r.text


def test_post_review_unknown_tour_is_404(api, make_user):
    u = make_user()
    r = api.post(_url(uuid.uuid4()), headers=auth_header(u), json=BODY)
    assert r.status_code == 404, r.text
    assert r.json()["message"] == "查無此旅遊項目"


def test_post_review_delisted_tour_is_404(api, make_user, make_order, make_tour):
    t = make_tour(status=2)
    u = _buyer(make_user, make_order, t)
    r = api.post(_url(t["tour_id"]), headers=auth_header(u), json=BODY)
    assert r.status_code == 404, r.text
    assert r.json()["message"] == "查無此旅遊項目"


def test_post_review_invalid_tour_id_is_400(api, make_user):
    u = make_user()
    r = api.post(_url("not-a-uuid"), headers=auth_header(u), json=BODY)
    assert r.status_code == 400, r.text


def test_post_review_success_201(api, db, make_user, make_order, make_tour):
    t = make_tour()
    u = _buyer(make_user, make_order, t)
    r = api.post(
        _url(t["tour_id"]), headers=auth_header(u), json={"rating": 4, "content": "  很棒的行程  "}
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["message"] == "評論成功"
    data = body["data"]
    assert set(data) == {"review_id", "review_type", "rating", "content", "create_date"}
    assert data["review_type"] == "travel"
    assert data["rating"] == 4
    assert data["content"] == "很棒的行程"
    row = db.execute(
        "SELECT user_id, tour_id, type, rating, content, hashtag IS NULL FROM review WHERE review_id = %s",
        (data["review_id"],),
    ).fetchone()
    assert row is not None
    assert (str(row[0]), str(row[1]), row[2], row[3], row[4], row[5]) == (
        u["user_id"], t["tour_id"], "travel", 4, "很棒的行程", True,
    )  # fmt: skip


def test_post_review_type_follows_tour_item(api, db, make_user, make_order, make_tour):
    t = make_tour(item="spot")
    u = _buyer(make_user, make_order, t)
    r = api.post(_url(t["tour_id"]), headers=auth_header(u), json=BODY)
    assert r.status_code == 201, r.text
    rows = db.execute("SELECT type FROM review WHERE tour_id = %s", (t["tour_id"],)).fetchall()
    assert rows == [("spot",)]


def test_post_review_appears_in_list_with_average(api, make_user, make_order, make_tour):
    t = make_tour()
    u = _buyer(make_user, make_order, t)
    assert api.post(_url(t["tour_id"]), headers=auth_header(u), json=BODY).status_code == 201
    r = api.get(_url(t["tour_id"]), params={"page": 1, "limit": 5, "lang": "zh-TW"})
    assert r.status_code == 200, r.text
    d = r.json()["data"]
    assert len(d["reviews"]) == 1
    assert d["reviews"][0]["content"] == BODY["content"]
    assert d["average_rating"] == 4.0


def test_post_review_twice_is_409(api, db, make_user, make_order, make_tour):
    t = make_tour()
    u = _buyer(make_user, make_order, t)
    h = auth_header(u)
    assert api.post(_url(t["tour_id"]), headers=h, json=BODY).status_code == 201
    r = api.post(_url(t["tour_id"]), headers=h, json=BODY)
    assert r.status_code == 409, r.text
    assert r.json()["message"] == DUPLICATE
    assert _review_count(db, t["tour_id"]) == 1


def test_post_review_concurrent_only_one_succeeds(db, make_user, make_order, make_tour):
    # 5 個請求同時送出：middleware 的 hasReviewed 檢查會被同時通過，
    # 其中一個 INSERT 成功，其餘撞 review_user_tour_key（23505）→ 必須是 409 而不是 500
    t = make_tour()
    u = _buyer(make_user, make_order, t)
    h = auth_header(u)
    url = f"{API_BASE}{_url(t['tour_id'])}"

    def _post(_):
        return requests.post(url, headers=h, json=BODY, timeout=DEFAULT_TIMEOUT).status_code

    with ThreadPoolExecutor(5) as pool:
        codes = sorted(pool.map(_post, range(5)))
    assert codes == [201, 409, 409, 409, 409]
    assert _review_count(db, t["tour_id"]) == 1


def test_post_review_multiple_paid_orders_ok(api, make_user, make_order, make_tour):
    t = make_tour()
    u = _buyer(make_user, make_order, t)
    make_order(u, t["tour_id"], payment_status=1)
    r = api.post(_url(t["tour_id"]), headers=auth_header(u), json=BODY)
    assert r.status_code == 201, r.text


@pytest.mark.parametrize(
    "body, message",
    [
        ({"rating": 0, "content": "x"}, RATING_MSG),
        ({"rating": 6, "content": "x"}, RATING_MSG),
        ({"rating": 4.5, "content": "x"}, RATING_MSG),
        ({"rating": "5", "content": "x"}, RATING_MSG),
        ({"content": "x"}, "請輸入「rating」"),
        ({"rating": 4, "content": ""}, "「content」不得為空白"),
        ({"rating": 4, "content": "   "}, "「content」不得為空白"),
        ({"rating": 4, "content": "字" * 501}, "「content」不可超過 500 字"),
        ({"rating": 4}, "請輸入「content」"),
        ({"rating": 4, "content": "x", "hashtag": "x"}, "不支援的欄位「hashtag」"),
    ],
    ids=[
        "rating-0", "rating-6", "rating-4.5", "rating-str", "rating-missing",
        "content-empty", "content-blank", "content-501", "content-missing", "unknown-field",
    ],
)  # fmt: skip
def test_post_review_validation(api, db, make_user, make_order, make_tour, body, message):
    t = make_tour()
    u = _buyer(make_user, make_order, t)
    r = api.post(_url(t["tour_id"]), headers=auth_header(u), json=body)
    assert r.status_code == 400, r.text
    assert r.json()["message"] == message
    assert _review_count(db, t["tour_id"]) == 0


def test_post_review_content_500_chars_ok(api, make_user, make_order, make_tour):
    t = make_tour()
    u = _buyer(make_user, make_order, t)
    r = api.post(_url(t["tour_id"]), headers=auth_header(u), json={"rating": 5, "content": "字" * 500})
    assert r.status_code == 201, r.text


def test_post_review_html_stored_verbatim(api, db, make_user, make_order, make_tour):
    t = make_tour()
    u = _buyer(make_user, make_order, t)
    html = "<script>alert(1)</script>"
    r = api.post(_url(t["tour_id"]), headers=auth_header(u), json={"rating": 5, "content": html})
    assert r.status_code == 201, r.text
    assert db.execute("SELECT content FROM review WHERE tour_id = %s", (t["tour_id"],)).fetchone()[0] == html
    lst = api.get(_url(t["tour_id"]), params={"page": 1, "limit": 5, "lang": "zh-TW"})
    assert lst.status_code == 200, lst.text
    reviews = lst.json()["data"]["reviews"]
    assert len(reviews) == 1
    assert reviews[0]["content"] == html


def test_eligibility_requires_login(api, make_tour):
    t = make_tour()
    r = api.get(_url(t["tour_id"], "eligibility"))
    assert r.status_code == 401, r.text
    assert r.json()["message"] == "請先登入"


def test_eligibility_admin_is_403(api, make_user, make_tour):
    t = make_tour()
    admin = make_user(role="admin")
    r = api.get(_url(t["tour_id"], "eligibility"), headers=auth_header(admin))
    assert r.status_code == 403, r.text
    assert r.json()["message"] == NO_PERMISSION


def test_eligibility_invalid_tour_id_is_400(api, make_user):
    u = make_user()
    r = api.get(_url("not-a-uuid", "eligibility"), headers=auth_header(u))
    assert r.status_code == 400, r.text


def test_eligibility_delisted_tour_is_404(api, make_user, make_tour):
    t = make_tour(status=2)
    u = make_user()
    r = api.get(_url(t["tour_id"], "eligibility"), headers=auth_header(u))
    assert r.status_code == 404, r.text
    assert r.json()["message"] == "查無此旅遊項目"


def test_eligibility_unknown_tour_is_404(api, make_user):
    u = make_user()
    r = api.get(_url(uuid.uuid4(), "eligibility"), headers=auth_header(u))
    assert r.status_code == 404, r.text
    assert r.json()["message"] == "查無此旅遊項目"


def _eligibility(api, user, tour_id) -> dict:
    r = api.get(_url(tour_id, "eligibility"), headers=auth_header(user))
    assert r.status_code == 200, r.text
    assert r.json()["message"] == "查詢成功"
    return r.json()["data"]


def test_eligibility_states(api, make_user, make_order, make_tour):
    t = make_tour()
    u = make_user()
    assert _eligibility(api, u, t["tour_id"]) == {"can_write": False, "has_reviewed": False}
    make_order(u, t["tour_id"])
    assert _eligibility(api, u, t["tour_id"]) == {"can_write": True, "has_reviewed": False}
    assert api.post(_url(t["tour_id"]), headers=auth_header(u), json=BODY).status_code == 201
    assert _eligibility(api, u, t["tour_id"]) == {"can_write": True, "has_reviewed": True}


def test_eligibility_seed_alice(api, db):
    # 唯讀 GET：不寫入任何 seed 資料
    def _uid(email):
        row = db.execute('SELECT user_id FROM "user" WHERE email = %s', (email,)).fetchone()
        assert row is not None, email
        return str(row[0])

    def _tid(title):
        row = db.execute("SELECT tour_id FROM tour WHERE title = %s", (title,)).fetchone()
        assert row is not None, title
        return str(row[0])

    alice = {"user_id": _uid("alice@example.com"), "role": "User"}
    carol = {"user_id": _uid("carol@example.com"), "role": "User"}
    hokkaido = _tid("北海道雪景 5 日深度遊")
    italy = _tid("義大利深度文化之旅")
    assert _eligibility(api, alice, hokkaido) == {"can_write": True, "has_reviewed": True}
    assert _eligibility(api, alice, italy) == {"can_write": False, "has_reviewed": False}
    assert _eligibility(api, carol, hokkaido) == {"can_write": True, "has_reviewed": False}


# ---------- Task 7：分享隱藏玩法 ----------


def _share_count(db, tour_id) -> int:
    return db.execute("SELECT count(*) FROM hidden_play WHERE tour_id = %s", (tour_id,)).fetchone()[0]


def _share_url(tour_id) -> str:
    return _url(tour_id, "hidden-shares")


def test_post_hidden_share_requires_login(api, make_tour):
    t = make_tour()
    r = api.post(_share_url(t["tour_id"]), json=SHARE_BODY)
    assert r.status_code == 401, r.text
    assert r.json()["message"] == "請先登入"


def test_post_hidden_share_admin_is_403(api, make_user, make_tour):
    t = make_tour()
    admin = make_user(role="admin")
    r = api.post(_share_url(t["tour_id"]), headers=auth_header(admin), json=SHARE_BODY)
    assert r.status_code == 403, r.text
    assert r.json()["message"] == NO_PERMISSION


def test_post_hidden_share_admin_with_invalid_body_is_403(api, make_user, make_tour):
    t = make_tour()
    admin = make_user(role="admin")
    r = api.post(_share_url(t["tour_id"]), headers=auth_header(admin), json={"title": ""})
    assert r.status_code == 403, r.text
    assert r.json()["message"] == NO_PERMISSION


def test_post_hidden_share_without_order_is_403(api, db, make_user, make_tour):
    t = make_tour()
    u = make_user()
    r = api.post(_share_url(t["tour_id"]), headers=auth_header(u), json=SHARE_BODY)
    assert r.status_code == 403, r.text
    assert r.json()["message"] == NOT_BOUGHT_SHARE
    assert _share_count(db, t["tour_id"]) == 0


@pytest.mark.parametrize("status", [-1, 0, 2, 3, 4])
def test_post_hidden_share_unpaid_status_is_403(api, db, make_user, make_order, make_tour, status):
    t = make_tour()
    u = _buyer(make_user, make_order, t, status=status)
    r = api.post(_share_url(t["tour_id"]), headers=auth_header(u), json=SHARE_BODY)
    assert r.status_code == 403, r.text
    assert r.json()["message"] == NOT_BOUGHT_SHARE
    assert _share_count(db, t["tour_id"]) == 0


def test_post_hidden_share_other_users_order_does_not_count(api, db, make_user, make_order, make_tour):
    t = make_tour()
    _buyer(make_user, make_order, t)  # B 已付款
    a = make_user()
    r = api.post(_share_url(t["tour_id"]), headers=auth_header(a), json=SHARE_BODY)
    assert r.status_code == 403, r.text
    assert r.json()["message"] == NOT_BOUGHT_SHARE
    assert _share_count(db, t["tour_id"]) == 0


def test_post_hidden_share_order_for_other_tour_does_not_count(api, db, make_user, make_order, make_tour):
    x, y = make_tour(), make_tour()
    u = _buyer(make_user, make_order, x)
    r = api.post(_share_url(y["tour_id"]), headers=auth_header(u), json=SHARE_BODY)
    assert r.status_code == 403, r.text
    assert r.json()["message"] == NOT_BOUGHT_SHARE
    assert _share_count(db, y["tour_id"]) == 0


def test_post_hidden_share_order_paid_but_item_unpaid_is_403(api, db, make_user, make_order, make_tour):
    t = make_tour()
    u = make_user()
    make_order(u, t["tour_id"], payment_status=0, order_payment_status=1)
    r = api.post(_share_url(t["tour_id"]), headers=auth_header(u), json=SHARE_BODY)
    assert r.status_code == 403, r.text
    assert r.json()["message"] == NOT_BOUGHT_SHARE
    assert _share_count(db, t["tour_id"]) == 0


def test_post_hidden_share_item_paid_but_order_unpaid_is_201(api, make_user, make_order, make_tour):
    t = make_tour()
    u = make_user()
    make_order(u, t["tour_id"], payment_status=1, order_payment_status=0)
    r = api.post(_share_url(t["tour_id"]), headers=auth_header(u), json=SHARE_BODY)
    assert r.status_code == 201, r.text


def test_post_hidden_share_validation_before_purchase_check(api, make_user, make_tour):
    t = make_tour()
    u = make_user()  # 未購買
    r = api.post(_share_url(t["tour_id"]), headers=auth_header(u), json={"title": "", "content": "x"})
    assert r.status_code == 400, r.text
    assert r.json()["message"] == "「title」不得為空白"


def test_post_hidden_share_invalid_tour_id_is_400(api, make_user):
    u = make_user()
    r = api.post(_share_url("not-a-uuid"), headers=auth_header(u), json=SHARE_BODY)
    assert r.status_code == 400, r.text
    assert r.json()["message"]


def test_post_hidden_share_success_201(api, db, make_user, make_order, make_tour):
    t = make_tour()
    u = _buyer(make_user, make_order, t)
    r = api.post(
        _share_url(t["tour_id"]),
        headers=auth_header(u),
        json={"title": " 清晨的魚市 ", "content": " 六點前到 ", "url": "https://example.com/tip"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["message"] == "分享成功"
    data = body["data"]
    assert set(data) == {"shares_id", "title", "content", "url", "create_date"}
    assert data["title"] == "清晨的魚市"
    assert data["content"] == "六點前到"
    assert data["url"] == "https://example.com/tip"
    row = db.execute(
        "SELECT user_id, tour_id, title, content, share_url FROM hidden_play WHERE hidden_play_id = %s",
        (data["shares_id"],),
    ).fetchone()
    assert row is not None
    assert (str(row[0]), str(row[1]), row[2], row[3], row[4]) == (
        u["user_id"], t["tour_id"], "清晨的魚市", "六點前到", "https://example.com/tip",
    )  # fmt: skip


def test_post_hidden_share_without_url(api, db, make_user, make_order, make_tour):
    t = make_tour()
    u = _buyer(make_user, make_order, t)
    r = api.post(_share_url(t["tour_id"]), headers=auth_header(u), json=SHARE_BODY)
    assert r.status_code == 201, r.text
    data = r.json()["data"]
    assert data["url"] is None
    row = db.execute(
        "SELECT share_url IS NULL FROM hidden_play WHERE hidden_play_id = %s", (data["shares_id"],)
    ).fetchone()
    assert row is not None
    assert row[0] is True


def test_post_hidden_share_multiple_allowed(api, db, make_user, make_order, make_tour):
    t = make_tour()
    u = _buyer(make_user, make_order, t)
    h = auth_header(u)
    assert api.post(_share_url(t["tour_id"]), headers=h, json=SHARE_BODY).status_code == 201
    assert api.post(_share_url(t["tour_id"]), headers=h, json=SHARE_BODY).status_code == 201
    assert _share_count(db, t["tour_id"]) == 2


def test_post_hidden_share_appears_in_list(api, make_user, make_order, make_tour):
    t = make_tour()
    u = _buyer(make_user, make_order, t)
    body = {"title": "清晨的魚市", "content": "六點前到", "url": "https://example.com/tip"}
    assert api.post(_share_url(t["tour_id"]), headers=auth_header(u), json=body).status_code == 201
    r = api.get(_share_url(t["tour_id"]), params={"page": 1, "limit": 5, "lang": "zh-TW"})
    assert r.status_code == 200, r.text
    rows = r.json()["data"]
    assert len(rows) >= 1
    assert rows[0]["title"] == body["title"]
    assert rows[0]["url"] == body["url"]


@pytest.mark.parametrize(
    "body, message",
    [
        ({"title": "", "content": "x"}, "「title」不得為空白"),
        ({"title": "   ", "content": "x"}, "「title」不得為空白"),
        ({"title": "字" * 51, "content": "x"}, "「title」不可超過 50 字"),
        ({"content": "x"}, "請輸入「title」"),
        ({"title": "t"}, "請輸入「content」"),
        ({"title": "t", "content": ""}, "「content」不得為空白"),
        ({"title": "t", "content": "字" * 1001}, "「content」不可超過 1000 字"),
        ({"title": "t", "content": "x", "url": "javascript:alert(1)"}, URL_MSG),
        ({"title": "t", "content": "x", "url": "data:text/html,x"}, URL_MSG),
        ({"title": "t", "content": "x", "url": "ftp://example.com/a"}, URL_MSG),
        ({"title": "t", "content": "x", "url": ""}, URL_MSG),
        ({"title": "t", "content": "x", "url": "https://example.com/" + "a" * 236}, "「url」不可超過 255 字"),
        ({"title": "t", "content": "x", "rating": 5}, "不支援的欄位「rating」"),
    ],
)
def test_post_hidden_share_validation(api, db, make_user, make_order, make_tour, body, message):
    t = make_tour()
    u = _buyer(make_user, make_order, t)
    r = api.post(_share_url(t["tour_id"]), headers=auth_header(u), json=body)
    assert r.status_code == 400, r.text
    assert r.json()["message"] == message
    assert _share_count(db, t["tour_id"]) == 0


def test_post_hidden_share_boundaries_ok(api, db, make_user, make_order, make_tour):
    t = make_tour()
    u = _buyer(make_user, make_order, t)
    body = {"title": "字" * 50, "content": "字" * 1000, "url": "https://example.com/" + "a" * 235}
    assert len(body["url"]) == 255
    r = api.post(_share_url(t["tour_id"]), headers=auth_header(u), json=body)
    assert r.status_code == 201, r.text
    assert _share_count(db, t["tour_id"]) == 1


def test_post_hidden_share_delisted_tour_is_404(api, make_user, make_order, make_tour):
    t = make_tour(status=2)
    u = _buyer(make_user, make_order, t)
    r = api.post(_share_url(t["tour_id"]), headers=auth_header(u), json=SHARE_BODY)
    assert r.status_code == 404, r.text
    assert r.json()["message"] == "查無此旅遊項目"


def test_post_hidden_share_unknown_tour_is_404(api, make_user):
    u = make_user()
    r = api.post(_share_url(uuid.uuid4()), headers=auth_header(u), json=SHARE_BODY)
    assert r.status_code == 404, r.text
    assert r.json()["message"] == "查無此旅遊項目"


def test_post_hidden_share_html_stored_verbatim(api, db, make_user, make_order, make_tour):
    t = make_tour()
    u = _buyer(make_user, make_order, t)
    content = "<img src=x onerror=alert(1)>"
    r = api.post(
        _share_url(t["tour_id"]), headers=auth_header(u), json={"title": "t", "content": content}
    )
    assert r.status_code == 201, r.text
    row = db.execute(
        "SELECT content FROM hidden_play WHERE hidden_play_id = %s", (r.json()["data"]["shares_id"],)
    ).fetchone()
    assert row is not None
    assert row[0] == content
