"""P5 Task 6：通知設定（GET /allnotifi-settings、PATCH /notifi-settings、PATCH /price-tracking、GET /regions）。"""
import collections
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest
from conftest import API_BASE, Api, auth_header
from dbfactory import insert

BASE = "/api/v1/user/automation"
ALL = f"{BASE}/allnotifi-settings"
EARLY = f"{BASE}/notifi-settings"
PRICE = f"{BASE}/price-tracking"
REGIONS = f"{BASE}/regions"

REGION_MSG = "「國家」與「地區」不是系統提供的選項"
PRICE_MSG = "「預算上限」必須是 0 以上的整數"
DEFAULTS = {
    "notifi_settings_enabled": False,
    "price_tracking": {"price_tracking_enabled": False, "country": None, "region": None, "max_price": None},
}


def price_body(country="Japan", region="Tokyo", max_price=30000, enabled=True):
    return {"price_tracking_enabled": enabled, "country": country, "region": region, "max_price": max_price}


def rows(db, user):
    return db.execute(
        "SELECT early_notify, flexible_notify, country, region, price FROM auto_setting WHERE user_id = %s",
        (user["user_id"],),
    ).fetchall()


def listed_tour(db, make_tour, country="p5land", region="p5city", status=1):
    tour = make_tour(status=status)
    db.execute("UPDATE tour SET country = %s, region = %s WHERE tour_id = %s", (country, region, tour["tour_id"]))
    return tour


def test_get_defaults_when_no_row(api, make_user):
    r = api.get(ALL, headers=auth_header(make_user()))
    assert r.status_code == 200, r.text
    assert r.json()["message"] == "查詢成功"
    data = r.json()["data"]
    assert data == DEFAULTS
    assert data["notifi_settings_enabled"] is False
    assert data["price_tracking"]["price_tracking_enabled"] is False


def test_get_returns_booleans(api, db, make_user):
    user = make_user()
    insert(db, "auto_setting", user_id=user["user_id"], early_notify=1, flexible_notify=0)
    data = api.get(ALL, headers=auth_header(user)).json()["data"]
    assert data["notifi_settings_enabled"] is True
    assert data["price_tracking"]["price_tracking_enabled"] is False
    db.execute("UPDATE auto_setting SET early_notify = 0, flexible_notify = 1 WHERE user_id = %s", (user["user_id"],))
    data = api.get(ALL, headers=auth_header(user)).json()["data"]
    assert data["notifi_settings_enabled"] is False
    assert data["price_tracking"]["price_tracking_enabled"] is True


def test_patch_early_upsert_idempotent(api, db, make_user):
    user = make_user()
    for _ in range(2):
        r = api.patch(EARLY, headers=auth_header(user), json={"notifi_settings_enabled": True})
        assert r.status_code == 200, r.text
        assert r.json()["message"] == "提醒設定已更新"
    assert rows(db, user) == [(1, 0, None, None, None)]


def test_patch_price_upsert_keeps_early(api, db, make_user):
    user = make_user()
    assert api.patch(EARLY, headers=auth_header(user), json={"notifi_settings_enabled": True}).status_code == 200
    r = api.patch(PRICE, headers=auth_header(user), json=price_body())
    assert r.status_code == 200, r.text
    assert r.json()["message"] == "彈性價格提醒狀態已更新"
    assert rows(db, user) == [(1, 1, "Japan", "Tokyo", 30000.0)]


def _concurrent_first_write(db, make_user, url, body, check_row):
    """8 條執行緒、各自 session、Barrier 帶 timeout：同一會員第一次寫入同時到。
    舊寫法（先查再 INSERT）會讓輸的請求撞 UNIQUE 回 500。"""
    user = make_user()
    n = 8
    barrier = threading.Barrier(n, timeout=10)
    headers = auth_header(user)

    def hit(_):
        session = Api(API_BASE)
        try:
            barrier.wait()
            return session.patch(url, headers=headers, json=body)
        finally:
            session.close()

    with ThreadPoolExecutor(max_workers=n) as pool:
        futures = [pool.submit(hit, i) for i in range(n)]
        results = [f.result(timeout=30) for f in futures]
    codes = [r.status_code for r in results]
    assert set(codes) == {200}, (collections.Counter(codes), [r.text for r in results if r.status_code != 200])
    assert rows(db, user) == [check_row]


def test_patch_concurrent_first_write_one_row(db, make_user):
    _concurrent_first_write(db, make_user, EARLY, {"notifi_settings_enabled": True}, (1, 0, None, None, None))


def test_price_tracking_concurrent_first_write_one_row(db, make_user):
    _concurrent_first_write(db, make_user, PRICE, price_body(), (0, 1, "Japan", "Tokyo", 30000.0))


def test_alice_like_row_resave_unchanged_is_200(api, db, make_user):
    # GC10：seed 帳號唯讀，改用 make_user 寫入與 alice 合併後相同的一列
    user = make_user()
    insert(db, "auto_setting", user_id=user["user_id"], early_notify=0, flexible_notify=1,
           country="Japan", region="Tokyo", price=1200.5)  # fmt: skip
    saved = api.get(ALL, headers=auth_header(user)).json()["data"]["price_tracking"]
    assert saved == {"price_tracking_enabled": True, "country": "Japan", "region": "Tokyo", "max_price": 1200.5}
    r = api.patch(PRICE, headers=auth_header(user), json=price_body(max_price=saved["max_price"]))
    assert r.status_code == 200, r.text
    assert rows(db, user) == [(0, 1, "Japan", "Tokyo", 1200.5)]


def test_price_tracking_non_integer_new_price_is_400(api, db, make_user):
    user = make_user()
    insert(db, "auto_setting", user_id=user["user_id"], early_notify=0, flexible_notify=1,
           country="Japan", region="Tokyo", price=1200.5)  # fmt: skip
    r = api.patch(PRICE, headers=auth_header(user), json=price_body(max_price=1300.5))
    assert r.status_code == 400, r.text
    assert r.json()["message"] == PRICE_MSG
    assert rows(db, user) == [(0, 1, "Japan", "Tokyo", 1200.5)]


def test_price_tracking_negative_price_is_400(api, make_user):
    r = api.patch(PRICE, headers=auth_header(make_user()), json=price_body(max_price=-1))
    assert r.status_code == 400, r.text
    assert r.json()["message"] == PRICE_MSG


def test_regions_lists_listed_tour_pairs(api, db, make_user, make_tour):
    listed_tour(db, make_tour, "p5land", "p5city")
    listed_tour(db, make_tour, "p5gone", "p5hidden", status=0)
    r = api.get(REGIONS, headers=auth_header(make_user()))
    assert r.status_code == 200, r.text
    data = r.json()["data"]
    assert isinstance(data, list)
    assert all(set(item) == {"country", "regions"} for item in data)
    by_country = {item["country"]: item["regions"] for item in data}
    assert "p5city" in by_country["p5land"]
    assert "p5gone" not in by_country
    assert "Japan" in by_country and "Tokyo" in by_country["Japan"]
    assert [i["country"] for i in data] == sorted(i["country"] for i in data)
    assert all(i["regions"] == sorted(i["regions"]) for i in data)


def test_regions_admin_is_403(api, make_user):
    r = api.get(REGIONS, headers=auth_header(make_user(role="admin")))
    assert r.status_code == 403, r.text
    assert r.json()["message"] == "您沒有權限進行此操作"


def test_regions_without_token_is_401(api):
    r = api.get(REGIONS)
    assert r.status_code == 401, r.text
    assert r.json()["message"] == "請先登入"


@pytest.mark.parametrize("country,region", [("Japan", "Paris"), ("日本", "東京")], ids=["mismatch", "chinese"])
def test_price_tracking_invalid_region_is_400(api, db, make_user, country, region):
    user = make_user()
    r = api.patch(PRICE, headers=auth_header(user), json=price_body(country, region))
    assert r.status_code == 400, r.text
    assert r.json()["message"] == REGION_MSG
    assert rows(db, user) == []


def test_price_tracking_accepts_listed_pair(api, db, make_user):
    user = make_user()
    r = api.patch(PRICE, headers=auth_header(user), json=price_body("France", "Paris", 5000))
    assert r.status_code == 200, r.text
    assert rows(db, user) == [(0, 1, "France", "Paris", 5000.0)]


def test_delisted_saved_region_kept_and_resavable(api, db, make_user, make_tour):
    user = make_user()
    tour = listed_tour(db, make_tour)
    assert api.patch(PRICE, headers=auth_header(user), json=price_body("p5land", "p5city", 1000)).status_code == 200
    db.execute("UPDATE tour SET status = 0 WHERE tour_id = %s", (tour["tour_id"],))
    saved = api.get(ALL, headers=auth_header(user)).json()["data"]["price_tracking"]
    assert (saved["country"], saved["region"]) == ("p5land", "p5city")
    r = api.patch(PRICE, headers=auth_header(user), json=price_body("p5land", "p5city", 1000))
    assert r.status_code == 200, r.text
    r = api.patch(PRICE, headers=auth_header(user), json=price_body("p5land", "p5other", 1000))
    assert r.status_code == 400, r.text
    assert r.json()["message"] == REGION_MSG
    assert rows(db, user) == [(0, 1, "p5land", "p5city", 1000.0)]


@pytest.mark.parametrize(
    "missing,label",
    [("country", "國家"), ("region", "地區"), ("max_price", "預算上限")],
)
def test_price_tracking_requires_fields(api, make_user, missing, label):
    body = price_body()
    del body[missing]
    r = api.patch(PRICE, headers=auth_header(make_user()), json=body)
    assert r.status_code == 400, r.text
    assert r.json()["message"] == f"開啟價格追蹤時「{label}」為必填欄位"


def test_early_not_boolean_is_400(api, make_user):
    r = api.patch(EARLY, headers=auth_header(make_user()), json={"notifi_settings_enabled": "abc"})
    assert r.status_code == 400, r.text
    assert r.json()["message"] == "「旅遊提醒」必須是 true 或 false"


def test_disable_price_tracking_clears_fields(api, db, make_user):
    user = make_user()
    assert api.patch(PRICE, headers=auth_header(user), json=price_body()).status_code == 200
    r = api.patch(PRICE, headers=auth_header(user), json={"price_tracking_enabled": False})
    assert r.status_code == 200, r.text
    assert rows(db, user) == [(0, 0, None, None, None)]


NOTIFY_CALLS = [
    ("get", ALL, None),
    ("patch", EARLY, {"notifi_settings_enabled": True}),
    ("patch", PRICE, price_body()),
]


@pytest.mark.parametrize("method,url,body", NOTIFY_CALLS, ids=["all", "early", "price"])
def test_notify_without_token_is_401(api, method, url, body):
    r = api.request(method.upper(), url, json=body)
    assert r.status_code == 401, r.text
    assert r.json()["message"] == "請先登入"


@pytest.mark.parametrize("method,url,body", NOTIFY_CALLS, ids=["all", "early", "price"])
def test_notify_admin_is_403(api, make_user, method, url, body):
    r = api.request(method.upper(), url, json=body, headers=auth_header(make_user(role="admin")))
    assert r.status_code == 403, r.text
    assert r.json()["message"] == "您沒有權限進行此操作"
