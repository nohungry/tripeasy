"""P3 Task 6：購買資格查詢與寫評論 API（只限購買過的會員）。"""
import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
import requests
from conftest import API_BASE, DEFAULT_TIMEOUT, auth_header

SEARCH = "/api/v1/user/product/search"
NO_PERMISSION = "您沒有權限進行此操作"
NOT_BOUGHT = "購買過此行程的會員才能評論"
DUPLICATE = "你已評論過此行程"
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
    assert _review_count(db, t["tour_id"]) == 0


def test_post_review_order_for_other_tour_does_not_count(api, db, make_user, make_order, make_tour):
    x, y = make_tour(), make_tour()
    u = _buyer(make_user, make_order, x)
    r = api.post(_url(y["tour_id"]), headers=auth_header(u), json=BODY)
    assert r.status_code == 403, r.text
    assert _review_count(db, y["tour_id"]) == 0


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


def test_eligibility_admin_is_403(api, make_user, make_tour):
    t = make_tour()
    admin = make_user(role="admin")
    r = api.get(_url(t["tour_id"], "eligibility"), headers=auth_header(admin))
    assert r.status_code == 403, r.text
    assert r.json()["message"] == NO_PERMISSION


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
