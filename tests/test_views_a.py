"""A 組 view／function（商品與首頁）的行為。

每個測試在 tx 裡自己塞資料、只查自己的列，不依賴 seed；結束時 tx 會 rollback。
"""
import uuid
from datetime import datetime, timedelta

from psycopg.rows import dict_row

from dbfactory import insert


def rows(tx, query: str, params=()) -> list[dict]:
    with tx.cursor(row_factory=dict_row) as cur:
        cur.execute(query, params)
        return cur.fetchall()


def make_user(tx, **kw) -> dict:
    return insert(tx, "user", **kw)


def make_tour(tx, **kw) -> dict:
    return insert(tx, "tour", **kw)


def days(n: int) -> datetime:
    return datetime.now() + timedelta(days=n)


def unique_group() -> tuple[str, str]:
    """獨一無二的 (大分類, 小分類)，讓排行 function 只看到本測試的行程。"""
    token = uuid.uuid4().hex[:10]
    return f"t-{token}", f"i-{token}"


# ---------- tour_base ----------

def test_tour_base_includes_inactive_tours(tx):
    tour = make_tour(tx, status=2)
    (row,) = rows(tx, 'SELECT * FROM tour_base WHERE "旅遊編號" = %s', (tour["tour_id"],))
    assert row["上下架狀態"] == 2


def test_tour_base_without_notification_has_null_notice(tx):
    tour = make_tour(tx)
    (row,) = rows(tx, 'SELECT * FROM tour_base WHERE "旅遊編號" = %s', (tour["tour_id"],))
    assert row["通知狀態"] is None
    assert row["促銷價錢"] is None


def test_tour_base_promo_price_only_in_period(tx):
    ended = make_tour(tx)
    insert(tx, "notification", tour_id=ended["tour_id"], type="促銷",
           start_date=days(-10), end_date=days(-5), promo_price=700.0)
    active = make_tour(tx)
    insert(tx, "notification", tour_id=active["tour_id"], type="促銷",
           start_date=days(-2), end_date=days(2), promo_price=800.0)
    by_id = {
        r["旅遊編號"]: r
        for r in rows(tx, 'SELECT * FROM tour_base WHERE "旅遊編號" = ANY(%s)',
                      ([ended["tour_id"], active["tour_id"]],))
    }
    assert by_id[ended["tour_id"]]["通知狀態"] == "促銷"
    assert by_id[ended["tour_id"]]["促銷價錢"] is None
    assert by_id[active["tour_id"]]["通知狀態"] == "促銷"
    assert by_id[active["tour_id"]]["促銷價錢"] == 800.0


def test_tour_base_promo_and_change_in_one_row(tx):
    tour = make_tour(tx)
    insert(tx, "notification", tour_id=tour["tour_id"], type="異動", change_desc="班機異動")
    insert(tx, "notification", tour_id=tour["tour_id"], type="促銷",
           start_date=days(-1), end_date=days(1), promo_price=900.0)
    (row,) = rows(tx, 'SELECT * FROM tour_base WHERE "旅遊編號" = %s', (tour["tour_id"],))
    assert row["通知狀態"] == "促銷"
    assert row["異動通知內容"] == "班機異動"
    assert row["促銷價錢"] == 900.0


# ---------- tour_travel ----------

def test_tour_travel_active_only_with_favorite_flag(tx):
    active = make_tour(tx)
    inactive = make_tour(tx, status=2)
    fan = make_user(tx)
    other = make_user(tx)
    insert(tx, "favorite", user_id=fan["user_id"], tour_id=active["tour_id"])
    ids = [active["tour_id"], inactive["tour_id"]]
    query = 'SELECT * FROM tour_travel(%s) WHERE "旅遊編號" = ANY(%s)'

    (as_fan,) = rows(tx, query, (fan["user_id"], ids))
    assert as_fan["旅遊編號"] == active["tour_id"]
    assert as_fan["收藏狀態"] is True
    (as_other,) = rows(tx, query, (other["user_id"], ids))
    assert as_other["收藏狀態"] is False
    (as_anon,) = rows(tx, "SELECT * FROM tour_travel(NULL::uuid) WHERE \"旅遊編號\" = ANY(%s)", (ids,))
    assert as_anon["收藏狀態"] is False  # 契約 #28：未登入為 false


# ---------- 排行 ----------

def test_popular_counts_paid_only_and_breaks_ties(tx):
    big, small = unique_group()
    user = make_user(tx)
    order = insert(tx, "orders", user_id=user["user_id"])

    def buy(tour, status, quantity=1):
        insert(tx, "order_item", order_id=order["order_id"], tour_id=tour["tour_id"],
               payment_status=status, quantity=quantity)

    two_paid = make_tour(tx, type=big, item=small)      # 2 筆已付款（quantity 各 1）
    one_big = make_tour(tx, type=big, item=small)       # 1 筆已付款但 quantity 5：按列數數，所以排第 2
    unpaid = make_tour(tx, type=big, item=small)        # 只有未付款／已取消
    none_a = make_tour(tx, type=big, item=small)
    none_b = make_tour(tx, type=big, item=small)
    inactive = make_tour(tx, type=big, item=small, status=2)
    buy(two_paid, 1); buy(two_paid, 1); buy(two_paid, 0)
    buy(one_big, 1, quantity=5)
    buy(unpaid, 0); buy(unpaid, -1); buy(unpaid, 2)
    buy(inactive, 1)

    result = rows(tx, "SELECT tour_id, 購買排行 FROM tour_travel_popular(%s, %s) ORDER BY 購買排行",
                  (big, small))
    tail = sorted([unpaid["tour_id"], none_a["tour_id"], none_b["tour_id"]])
    assert [r["tour_id"] for r in result] == [two_paid["tour_id"], one_big["tour_id"]] + tail
    assert [r["購買排行"] for r in result] == [1, 2, 3, 4, 5]
    assert inactive["tour_id"] not in {r["tour_id"] for r in result}


def test_most_favorited_ranks_and_breaks_ties(tx):
    big, small = unique_group()
    fans = [make_user(tx) for _ in range(3)]
    top = make_tour(tx, type=big, item=small)
    mid = make_tour(tx, type=big, item=small)
    none_a = make_tour(tx, type=big, item=small)
    none_b = make_tour(tx, type=big, item=small)
    inactive = make_tour(tx, type=big, item=small, status=2)
    for fan in fans[:3]:
        insert(tx, "favorite", user_id=fan["user_id"], tour_id=top["tour_id"])
    insert(tx, "favorite", user_id=fans[0]["user_id"], tour_id=mid["tour_id"])
    for fan in fans:
        insert(tx, "favorite", user_id=fan["user_id"], tour_id=inactive["tour_id"])

    result = rows(tx, "SELECT tour_id, 收藏排行 FROM tour_travel_most_favorited(%s, %s) ORDER BY 收藏排行",
                  (big, small))
    tail = sorted([none_a["tour_id"], none_b["tour_id"]])
    assert [r["tour_id"] for r in result] == [top["tour_id"], mid["tour_id"]] + tail
    assert [r["收藏排行"] for r in result] == [1, 2, 3, 4]


# ---------- 詳情 ----------

def test_tour_detail_one_row_active_only(tx):
    active = make_tour(tx)
    insert(tx, "tour_detail", tour_id=active["tour_id"], itinerary="第一天")
    inactive = make_tour(tx, status=2)
    insert(tx, "tour_detail", tour_id=inactive["tour_id"])
    query = 'SELECT * FROM tour_tour_detail(NULL::uuid) WHERE "旅遊編號" = %s'

    (row,) = rows(tx, query, (active["tour_id"],))
    assert row["行程規劃"] == "第一天"
    assert rows(tx, query, (inactive["tour_id"],)) == []


def test_tour_hotel_one_row_per_room(tx):
    tour = make_tour(tx, type="backpacker", item="hotel")
    hotel = insert(tx, "hotel", tour_id=tour["tour_id"], facility_desc="泳池")
    insert(tx, "hotel_room", hotel_id=hotel["hotel_id"], title="雙人房")
    insert(tx, "hotel_room", hotel_id=hotel["hotel_id"], title="四人房")

    result = rows(tx, 'SELECT * FROM tour_hotel(NULL::uuid) WHERE "旅遊編號" = %s', (tour["tour_id"],))
    assert sorted(r["房型名稱"] for r in result) == ["四人房", "雙人房"]
    assert {r["旅遊名稱"] for r in result} == {tour["title"]}
    assert {r["基本設施與服務"] for r in result} == {"泳池"}


def test_tour_restaurant_rows_are_menu_xor_opening(tx):
    tour = make_tour(tx, type="backpacker", item="food")
    restaurant = insert(tx, "restaurant", tour_id=tour["tour_id"])
    for _ in range(3):
        insert(tx, "restaurant_menu", restaurant_id=restaurant["restaurant_id"])
    for week in ("週一", "週二"):
        insert(tx, "restaurant_business", restaurant_id=restaurant["restaurant_id"], week=week)

    result = rows(tx, 'SELECT * FROM tour_restaurant(NULL::uuid) WHERE "旅遊編號" = %s', (tour["tour_id"],))
    assert len(result) == 3 + 2
    for r in result:
        has_menu = r["菜單名稱"] is not None
        has_opening = r["營業星期"] is not None
        assert has_menu != has_opening


# ---------- user_user_level、首頁好評 ----------

def test_user_user_level_one_row_per_user(tx):
    user = make_user(tx)
    insert(tx, "user_level", user_id=user["user_id"], level="1", name="舊等級",
           updated_at=days(-3))
    insert(tx, "user_level", user_id=user["user_id"], level="2", name="新等級",
           updated_at=days(-1))
    (row,) = rows(tx, 'SELECT * FROM user_user_level WHERE "使用者編號" = %s', (user["user_id"],))
    assert row["旅遊等級名稱"] == "新等級"  # 契約 #22：多筆取最新


def test_review_for_home_only_web(tx):
    user = make_user(tx)
    tour = make_tour(tx)
    web = insert(tx, "review", user_id=user["user_id"], type="web")
    travel = insert(tx, "review", user_id=user["user_id"], type="travel", tour_id=tour["tour_id"])
    result = rows(tx, 'SELECT * FROM "user_level_review_forHome" WHERE "評論編號" = ANY(%s)',
                  ([web["review_id"], travel["review_id"]],))
    assert [r["評論編號"] for r in result] == [web["review_id"]]


# ---------- 補強：期間邊界、同類型多筆通知、LEFT JOIN／保留列規則 ----------

def test_tour_base_promo_not_started_has_null_price(tx):
    tour = make_tour(tx)
    insert(tx, "notification", tour_id=tour["tour_id"], type="促銷",
           start_date=days(5), end_date=days(10), promo_price=600.0)
    (row,) = rows(tx, 'SELECT * FROM tour_base WHERE "旅遊編號" = %s', (tour["tour_id"],))
    assert row["通知狀態"] == "促銷"  # #9：不判斷期間
    assert row["促銷價錢"] is None  # #10：期間外為 NULL


def test_tour_base_promo_period_bounds_are_inclusive(tx):
    """tx 內 now() 固定，所以把起日或訖日設成 now()::timestamp 能精確測出 BETWEEN 含邊界。"""
    starts_now = make_tour(tx)
    n1 = insert(tx, "notification", tour_id=starts_now["tour_id"], type="促銷",
                start_date=days(-1), end_date=days(1), promo_price=111.0)
    ends_now = make_tour(tx)
    n2 = insert(tx, "notification", tour_id=ends_now["tour_id"], type="促銷",
                start_date=days(-1), end_date=days(1), promo_price=222.0)
    tx.execute("UPDATE notification SET start_date = now()::timestamp WHERE notification_id = %s",
               (n1["notification_id"],))
    tx.execute("UPDATE notification SET end_date = now()::timestamp WHERE notification_id = %s",
               (n2["notification_id"],))
    by_id = {
        r["旅遊編號"]: r["促銷價錢"]
        for r in rows(tx, 'SELECT "旅遊編號", "促銷價錢" FROM tour_base WHERE "旅遊編號" = ANY(%s)',
                      ([starts_now["tour_id"], ends_now["tour_id"]],))
    }
    assert by_id[starts_now["tour_id"]] == 111.0
    assert by_id[ends_now["tour_id"]] == 222.0


def test_tour_base_latest_notification_of_same_type_wins(tx):
    tour = make_tour(tx)
    insert(tx, "notification", tour_id=tour["tour_id"], type="促銷", promo_price=700.0,
           start_date=days(-1), end_date=days(1), updated_at=days(-3))
    insert(tx, "notification", tour_id=tour["tour_id"], type="促銷", promo_price=900.0,
           start_date=days(-1), end_date=days(1), updated_at=days(-1))
    insert(tx, "notification", tour_id=tour["tour_id"], type="異動", change_desc="舊", updated_at=days(-4))
    insert(tx, "notification", tour_id=tour["tour_id"], type="異動", change_desc="新", updated_at=days(-2))
    (row,) = rows(tx, 'SELECT * FROM tour_base WHERE "旅遊編號" = %s', (tour["tour_id"],))
    assert row["促銷價錢"] == 900.0  # #8：同類型取 updated_at 最大
    assert row["異動通知內容"] == "新"


def test_tour_travel_matches_tour_base_columns(tx):
    """tour_travel 的欄位 ＝ tour_base ＋ 收藏狀態，值也要一致（防欄位位置錯位）。"""
    tour = make_tour(tx)
    insert(tx, "notification", tour_id=tour["tour_id"], type="促銷", promo_price=500.0,
           start_date=days(-1), end_date=days(1))
    (base,) = rows(tx, 'SELECT * FROM tour_base WHERE "旅遊編號" = %s', (tour["tour_id"],))
    (travel,) = rows(tx, 'SELECT * FROM tour_travel(NULL::uuid) WHERE "旅遊編號" = %s', (tour["tour_id"],))
    assert {k: v for k, v in travel.items() if k != "收藏狀態"} == base


def test_tour_detail_without_tour_detail_row_still_one_row(tx):
    tour = make_tour(tx)  # 沒有 tour_detail
    (row,) = rows(tx, 'SELECT * FROM tour_tour_detail(NULL::uuid) WHERE "旅遊編號" = %s', (tour["tour_id"],))
    assert row["行程規劃"] is None  # #30
    assert row["特色圖1 url"] is None and row["特色圖1 描述"] is None


def test_tour_hotel_without_rooms_one_null_row(tx):
    tour = make_tour(tx, type="backpacker", item="hotel")
    insert(tx, "hotel", tour_id=tour["tour_id"], facility_desc="泳池")
    (row,) = rows(tx, 'SELECT * FROM tour_hotel(NULL::uuid) WHERE "旅遊編號" = %s', (tour["tour_id"],))
    assert row["房型名稱"] is None  # #33
    assert row["基本設施與服務"] == "泳池"


def test_tour_restaurant_without_menu_or_opening_one_row(tx):
    tour = make_tour(tx, type="backpacker", item="food")
    insert(tx, "restaurant", tour_id=tour["tour_id"])
    (row,) = rows(tx, 'SELECT * FROM tour_restaurant(NULL::uuid) WHERE "旅遊編號" = %s', (tour["tour_id"],))
    for col in ("菜單名稱", "菜單描述", "菜單價錢", "營業星期", "營業時間"):
        assert row[col] is None  # #33
    assert row["官網介紹"] == "測試官網介紹"


def test_tour_restaurant_menu_only_has_no_placeholder_row(tx):
    tour = make_tour(tx, type="backpacker", item="food")
    restaurant = insert(tx, "restaurant", tour_id=tour["tour_id"])
    for _ in range(2):
        insert(tx, "restaurant_menu", restaurant_id=restaurant["restaurant_id"])
    result = rows(tx, 'SELECT * FROM tour_restaurant(NULL::uuid) WHERE "旅遊編號" = %s', (tour["tour_id"],))
    assert len(result) == 2
    assert all(r["菜單名稱"] is not None and r["營業星期"] is None for r in result)


def test_user_user_level_without_level_still_one_row(tx):
    user = make_user(tx)  # 沒有 user_level
    (row,) = rows(tx, 'SELECT * FROM user_user_level WHERE "使用者編號" = %s', (user["user_id"],))
    assert row["名稱"] == user["name"]
    assert row["旅遊等級"] is None and row["旅遊等級名稱"] is None  # #22
