"""P3 Task 3：搜尋分頁、天數篩選、首頁促銷期間。"""
import datetime

import pytest
from conftest import auth_header

SEARCH = "/api/v1/user/product/search"
HOME = "/api/v1/user/home/search/products"
PAGING = {"sort_by": "date", "order": "asc", "lang": "zh-TW"}


def _all_pages(api, **params) -> list[dict]:
    """limit=10 從第 1 頁打到沒有 data 為止，回傳所有列。"""
    rows: list[dict] = []
    page = 1
    while True:
        r = api.get(SEARCH, params={**params, "page": page, "limit": 10})
        assert r.status_code == 200, r.text
        data = r.json().get("data")
        if not data:
            return rows
        rows.extend(data)
        page += 1
        assert page < 200, "分頁沒有結束"


def _db_ids(db, where: str = "status = 1", params=()) -> set[str]:
    return {str(r[0]) for r in db.execute(f"SELECT tour_id FROM tour WHERE {where}", params).fetchall()}


def test_search_pages_cover_every_listed_tour_once(api, db, make_tour):
    # 12 筆開始日皆 NULL（排序值相同）的行程，必須靠次要排序才不會在分頁間重複或遺漏
    fixtures = {make_tour()["tour_id"] for _ in range(12)}
    ids = [r["旅遊編號"] for r in _all_pages(api, **PAGING)]
    assert ids
    assert fixtures <= set(ids)
    assert len(ids) == len(set(ids))
    assert set(ids) == _db_ids(db)


def test_search_price_asc_pages_cover_every_listed_tour_once(api, db, make_tour):
    # 預設 price 1000，12 筆同價
    fixtures = {make_tour()["tour_id"] for _ in range(12)}
    rows = _all_pages(api, sort_by="price", order="asc", lang="zh-TW")
    ids = [r["旅遊編號"] for r in rows]
    assert ids
    assert fixtures <= set(ids)
    assert len(ids) == len(set(ids))
    assert set(ids) == _db_ids(db)
    prices = [r["價錢"] for r in rows]
    assert prices == sorted(prices)


def test_search_duration_filter(api, db):
    rows = _all_pages(api, duration=5, **PAGING)
    assert rows
    assert {r["旅遊天數"] for r in rows} == {5}
    assert {r["旅遊編號"] for r in rows} == _db_ids(db, "status = 1 AND days = 5")


def test_search_keyword_matches_title_or_slogan(api, db):
    # 既有行為的回歸測試
    rows = _all_pages(api, keyword="北海道", **PAGING)
    expected = _db_ids(db, "status = 1 AND (title ILIKE %s OR slogan ILIKE %s)", ("%北海道%", "%北海道%"))
    assert expected
    assert {r["旅遊編號"] for r in rows} == expected


@pytest.mark.parametrize(
    "params",
    [
        {"page": 0},
        {"order": "up"},
        {"sort_by": "name"},
        {"type": "x"},
        {"type": "tourgroup", "item": "hotel"},
        {"lang": None},
    ],
    ids=lambda p: str(p),
)
def test_search_validation_errors(api, params):
    # 既有行為的回歸測試
    query = {"page": 1, "limit": 10, **PAGING, **params}
    query = {k: v for k, v in query.items() if v is not None}
    r = api.get(SEARCH, params=query)
    assert r.status_code == 400, r.text


def _home_promotion_ids(api, headers=None) -> set[str]:
    ids: set[str] = set()
    page = 1
    while True:
        r = api.get(
            HOME,
            headers=headers,
            params={"type": "tourgroup", "item": "promotion", "page": page, "limit": 50, "lang": "zh-TW"},
        )
        assert r.status_code == 200, r.text
        data = r.json().get("data")
        if not data:
            return ids
        ids.update(row["旅遊編號"] for row in data)
        page += 1
        assert page < 50, "分頁沒有結束"


def test_home_promotion_excludes_delisted_and_out_of_period(api, db, make_user, make_tour):
    a = make_tour(status=2)
    b, c, d = make_tour(), make_tour(), make_tour()
    periods = [
        (a, "now() - interval '1 day'", "now() + interval '1 day'"),
        (b, "now() - interval '10 days'", "now() - interval '1 day'"),
        (c, "now() + interval '1 day'", "now() + interval '10 days'"),
        (d, "now() - interval '1 day'", "now() + interval '1 day'"),
    ]
    for t, start, end in periods:
        db.execute(
            "INSERT INTO notification (tour_id, type, start_date, end_date, discount, promo_price) "
            f"VALUES (%s, '促銷', {start}, {end}, 10, 900)",
            (t["tour_id"],),
        )
    names = {a["tour_id"]: "A(下架)", b["tour_id"]: "B(已過期)", c["tour_id"]: "C(未開始)"}
    for label, headers in (("訪客", None), ("會員", auth_header(make_user()))):
        ids = _home_promotion_ids(api, headers)
        assert d["tour_id"] in ids, label
        leaked = sorted(names[i] for i in names if i in ids)
        assert not leaked, f"{label}：不該出現的促銷行程 {leaked}"


# ----------------------------------------------------------------- Task 4：詳情 404、餐廳空項、隱藏玩法 title

TOUR = "/api/v1/user/product/search"


def _detail(api, tour_id):
    return api.get(f"{TOUR}/{tour_id}", params={"lang": "zh-TW"})


def test_detail_delisted_tour_is_404(api, make_tour):
    t = make_tour(status=2)
    r = _detail(api, t["tour_id"])
    assert r.status_code == 404, r.text
    assert r.json()["message"] == "查無此旅遊項目"


def test_detail_tour_without_detail_rows_is_404(api, make_tour):
    # tour_hotel 對 hotel 是 INNER JOIN，沒有 hotel 資料列 → function 回 0 列
    t = make_tour(item="hotel", with_detail=False)
    r = _detail(api, t["tour_id"])
    assert r.status_code == 404, r.text
    assert r.json()["message"] == "查無此旅遊項目"


def test_detail_food_has_no_empty_menu_or_opening(api, db, make_tour):
    from dbfactory import insert

    t = make_tour(item="food", with_detail=False)
    rs = insert(db, "restaurant", tour_id=t["tour_id"])
    for name in ("p3-菜甲", "p3-菜乙"):
        insert(db, "restaurant_menu", restaurant_id=rs["restaurant_id"], name=name)
    insert(db, "restaurant_business", restaurant_id=rs["restaurant_id"], week="p3-週一")
    r = _detail(api, t["tour_id"])
    assert r.status_code == 200, r.text
    data = r.json().get("data")
    assert data is not None, r.text
    feature = data["feature"]
    assert len(feature["menu"]) == 2
    assert sorted(m["name"] for m in feature["menu"]) == sorted(["p3-菜甲", "p3-菜乙"])
    assert len(feature["opening"]) == 1
    assert feature["opening"][0]["week"] == "p3-週一"


def test_detail_food_without_menu_or_opening_has_empty_lists(api, db, make_tour):
    from dbfactory import insert

    t = make_tour(item="food", with_detail=False)
    insert(db, "restaurant", tour_id=t["tour_id"])
    r = _detail(api, t["tour_id"])
    assert r.status_code == 200, r.text
    data = r.json().get("data")
    assert data is not None, r.text
    feature = data["feature"]
    assert feature["menu"] == []
    assert feature["opening"] == []


def test_detail_spot_without_detail_rows_stays_200(api, make_tour):
    # 既有行為的回歸測試（spec :134）：spot 對 tour_detail 是 LEFT JOIN，沒有明細仍回 200
    t = make_tour(item="spot", with_detail=False)
    r = _detail(api, t["tour_id"])
    assert r.status_code == 200, r.text


def test_hidden_shares_include_title(api, db, make_user, make_tour):
    from dbfactory import insert

    u, t = make_user(), make_tour()
    insert(db, "hidden_play", user_id=u["user_id"], tour_id=t["tour_id"], title="p3 標題", content="內容")
    r = api.get(
        f"{TOUR}/{t['tour_id']}/hidden-shares", params={"page": 1, "limit": 10, "lang": "zh-TW"}
    )
    assert r.status_code == 200, r.text
    rows = r.json().get("data")
    assert rows is not None, r.text
    assert rows
    assert rows[0]["title"] == "p3 標題"


def test_reviews_average_and_pagination(api, db, make_user, make_tour):
    # 既有行為的回歸測試
    from dbfactory import insert

    t = make_tour()
    for rating, age in ((5, "3 minutes"), (4, "2 minutes"), (4, "1 minute")):
        u = make_user()
        row = insert(db, "review", user_id=u["user_id"], tour_id=t["tour_id"], type="travel", rating=rating)
        db.execute(
            "UPDATE review SET created_at = now() - %s::interval WHERE review_id = %s",
            (age, row["review_id"]),
        )
    url = f"{TOUR}/{t['tour_id']}/reviews"
    r1 = api.get(url, params={"page": 1, "limit": 2, "lang": "zh-TW"})
    assert r1.status_code == 200, r1.text
    d1 = r1.json().get("data")
    assert d1 is not None, r1.text
    assert len(d1["reviews"]) == 2
    assert [x["rating"] for x in d1["reviews"]] == [4, 4]
    dates = [x["create_date"] for x in d1["reviews"]]
    assert dates == sorted(dates, reverse=True)
    assert d1["average_rating"] == 4.3
    r2 = api.get(url, params={"page": 2, "limit": 2, "lang": "zh-TW"})
    assert r2.status_code == 200, r2.text
    d2 = r2.json().get("data")
    assert d2 is not None, r2.text
    assert len(d2["reviews"]) == 1
    assert d2["reviews"][0]["rating"] == 5


def test_reviews_empty_tour(api, make_tour):
    # 既有行為的回歸測試
    t = make_tour()
    r = api.get(f"{TOUR}/{t['tour_id']}/reviews", params={"page": 1, "limit": 10, "lang": "zh-TW"})
    assert r.status_code == 200, r.text
    assert r.json()["message"] == "暫無此旅遊項目評論"
    assert "data" not in r.json()


HOKKAIDO = "北海道雪景 5 日深度遊"


def _hokkaido(db):
    """seed 北海道 5 日行程的 (tour_id, 開始日, 結束日)；seed 日期隨載入日平移，所以從 DB 讀。"""
    row = db.execute("SELECT tour_id, tour_start_date, tour_end_date FROM tour WHERE title = %s", (HOKKAIDO,)).fetchone()
    assert row, "seed 沒有北海道 5 日行程"
    return str(row[0]), row[1], row[2]


def _search(api, **params):
    r = api.get(SEARCH, params={**params, **PAGING, "page": 1, "limit": 50})
    return r


def test_search_wide_date_range_with_duration_ok(api, db, make_tour):
    _, start, _ = _hokkaido(db)
    lo, hi = start.date() - datetime.timedelta(days=30), start.date() + datetime.timedelta(days=300)
    # seed 只有一個 5 日行程，另建區間內與兩個越界的行程，才分辨得出日期條件有沒有作用
    one_day = datetime.timedelta(days=1)
    spans = {
        "inside": (lo + one_day, lo + one_day * 5),
        "starts_before": (lo - one_day, lo + one_day * 3),
        "ends_after": (hi - one_day * 3, hi + one_day),
    }
    ids = {}
    for name, (d1, d2) in spans.items():
        ids[name] = make_tour()["tour_id"]
        db.execute(
            "UPDATE tour SET days = 5, tour_start_date = %s, tour_end_date = %s::date + time '23:59:59' WHERE tour_id = %s",
            (d1, d2, ids[name]),
        )
    rows = _all_pages(api, start_date=lo.isoformat(), end_date=hi.isoformat(), duration=5, **PAGING)
    assert rows
    assert {r["旅遊天數"] for r in rows} == {5}
    assert HOKKAIDO in {r["旅遊名稱"] for r in rows}
    # 結果恰為「上架、5 天、開始日 ≥ lo 當天 00:00、結束日 < hi 隔天 00:00」的行程（每列都在區間內，區間內的也不漏）
    expected = _db_ids(
        db,
        "status = 1 AND days = 5 AND tour_start_date >= %s AND tour_end_date < %s::date + 1",
        (lo, hi),
    )
    got = {r["旅遊編號"] for r in rows}
    assert got == expected
    assert ids["inside"] in got
    assert ids["starts_before"] not in got and ids["ends_after"] not in got


def test_search_duration_equal_to_inclusive_range_ok(api, db):
    # 區間 start～start+4 涵蓋 5 天；end_date 含當天（行程結束於當天 23:59:59 也算）
    tour_id, start, end = _hokkaido(db)
    assert end.date() == start.date() + datetime.timedelta(days=4)
    r = _search(api, start_date=start.date().isoformat(), end_date=end.date().isoformat(), duration=5)
    assert r.status_code == 200, r.text
    assert tour_id in {x["旅遊編號"] for x in r.json().get("data", [])}


def test_search_end_date_before_tour_end_excludes_it(api, db):
    tour_id, start, end = _hokkaido(db)
    # 區間整體前移一天（仍涵蓋 5 天，通過驗證），結束日早於行程結束日
    lo, early = start.date() - datetime.timedelta(days=1), end.date() - datetime.timedelta(days=1)
    r = _search(api, start_date=lo.isoformat(), end_date=early.isoformat(), duration=5)
    assert r.status_code == 200, r.text
    assert tour_id not in {x["旅遊編號"] for x in r.json().get("data", [])}


def test_search_duration_exceeding_range_is_400(api):
    r = api.get(SEARCH, params={"start_date": "2027-01-01", "end_date": "2027-01-05", "duration": 6, **PAGING, "page": 1, "limit": 10})
    assert r.status_code == 400
    assert r.json()["message"] == "「天數」不可大於出發日期到結束日期涵蓋的天數（目前區間共 5 天）"


def test_search_impossible_date_is_400(api):
    r = _search(api, start_date="2027-02-30", end_date="2027-03-05")
    assert r.status_code == 400, r.text
    assert "出發日期" in r.json()["message"]
    r = _search(api, start_date="2027-02-01", end_date="2027-02-30")
    assert r.status_code == 400, r.text
    assert "結束日期" in r.json()["message"]


def test_search_offset_date_is_400(api):
    r = _search(api, start_date="2027-01-10T00:00:00+08:00", end_date="2027-01-12")
    assert r.status_code == 400, r.text
    assert "出發日期" in r.json()["message"]


@pytest.mark.parametrize(
    "params, expected",
    [
        ({"start_date": "2027-01-10", "end_date": "2027-01-01"}, "「出發日期」不可晚於「結束日期」"),
        ({"min_price": -1, "max_price": -5}, "「最低價格」不可大於「最高價格」"),
        ({"min_price": "abc"}, "「最低價格」必須是數字"),
        ({"duration": 99, "start_date": "2027-01-01", "end_date": "2027-01-05"},
         "「天數」不可大於出發日期到結束日期涵蓋的天數（目前區間共 5 天）"),
        ({"duration": "x"}, "「天數」必須是數字"),
        ({"limit": 0}, "「每頁筆數」必須大於等於 1"),
        ({"page": 0}, "「頁數」必須大於等於 1"),
        ({"sort_by": "zzz"}, "「排序欄位」僅能為 price 或 date"),
        ({"order": "zzz"}, "「排序方向」僅能為 asc 或 desc"),
    ],
    ids=lambda v: str(v),
)
def test_search_messages_have_no_param_names(api, params, expected):
    query = {"page": 1, "limit": 10, **PAGING, **params}
    r = api.get(SEARCH, params=query)
    assert r.status_code == 400, r.text
    message = r.json()["message"]
    assert message == expected
    for name in ("start_date", "end_date", "min_price", "max_price", "duration", "limit", "page", "sort_by", "order"):
        assert name not in message, (name, message)
