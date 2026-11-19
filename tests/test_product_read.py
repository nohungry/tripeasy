"""P3 Task 3：搜尋分頁、天數篩選、首頁促銷期間。"""
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


def test_search_pages_cover_every_listed_tour_once(api, db):
    ids = [r["旅遊編號"] for r in _all_pages(api, **PAGING)]
    assert ids
    assert len(ids) == len(set(ids))
    assert set(ids) == _db_ids(db)


def test_search_price_desc_pages_cover_every_listed_tour_once(api, db):
    rows = _all_pages(api, sort_by="price", order="desc", lang="zh-TW")
    ids = [r["旅遊編號"] for r in rows]
    assert ids
    assert len(ids) == len(set(ids))
    assert set(ids) == _db_ids(db)
    prices = [r["價錢"] for r in rows]
    assert prices == sorted(prices, reverse=True)


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
    for headers in (None, auth_header(make_user())):
        ids = _home_promotion_ids(api, headers)
        assert d["tour_id"] in ids
        for t in (a, b, c):
            assert t["tour_id"] not in ids, t
