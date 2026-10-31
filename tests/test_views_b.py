"""B 組 view／function（購物車、訂位、折扣、結帳）的行為。

每個測試在 tx 裡自己塞資料、只查自己的列，不依賴 seed；結束時 tx 會 rollback。
tx 內 now() 是固定的，所以 `x = now()::timestamp` 可以構成精確的邊界。
"""
import uuid
from datetime import datetime, time, timedelta

from psycopg.rows import dict_row

from dbfactory import insert


def rows(tx, query: str, params=()) -> list[dict]:
    with tx.cursor(row_factory=dict_row) as cur:
        cur.execute(query, params)
        return cur.fetchall()


def days(n: int) -> datetime:
    return datetime.now() + timedelta(days=n)


def make_user(tx, **kw) -> dict:
    return insert(tx, "user", **kw)


def make_tour(tx, **kw) -> dict:
    return insert(tx, "tour", **kw)


def make_order_item(tx, user, tour, **kw) -> dict:
    """為 user 建一張新訂單並放一個 order_item；kw 傳給 order_item。"""
    order = kw.pop("order", None) or insert(tx, "orders", user_id=user["user_id"])
    return insert(tx, "order_item", order_id=order["order_id"], tour_id=tour["tour_id"], **kw)


def make_hotel_room(tx, tour, title, room_count) -> dict:
    hotel = insert(tx, "hotel", tour_id=tour["tour_id"])
    return insert(tx, "hotel_room", hotel_id=hotel["hotel_id"], title=title, room_count=room_count)


def make_restaurant(tx, tour, limit=10) -> dict:
    return insert(tx, "restaurant", tour_id=tour["tour_id"], reservation_limit=limit)


# ---------- user_cartList ----------

def test_cartlist_row_per_item_with_owner(tx):
    alice, bob = make_user(tx), make_user(tx)
    tour1 = make_tour(tx, price=1000)
    tour2 = make_tour(tx, price=2000)
    cart_a = insert(tx, "cart", user_id=alice["user_id"])
    cart_b = insert(tx, "cart", user_id=bob["user_id"])
    start = days(5)
    item1 = insert(tx, "cart_item", cart_id=cart_a["cart_id"], tour_id=tour1["tour_id"], quantity=2,
                   start_date=start)
    item2 = insert(tx, "cart_item", cart_id=cart_a["cart_id"], tour_id=tour2["tour_id"], quantity=3,
                   start_date=start, end_date=days(8), room_type="雙人房")
    item3 = insert(tx, "cart_item", cart_id=cart_b["cart_id"], tour_id=tour1["tour_id"], quantity=1,
                   start_date=start)
    result = rows(tx, 'SELECT * FROM "user_cartList" WHERE cart_id = ANY(%s)',
                  ([cart_a["cart_id"], cart_b["cart_id"]],))
    by_item = {r["cart_item_id"]: r for r in result}
    assert set(by_item) == {item1["cart_item_id"], item2["cart_item_id"], item3["cart_item_id"]}
    assert by_item[item1["cart_item_id"]]["user_id"] == alice["user_id"]
    assert by_item[item2["cart_item_id"]]["user_id"] == alice["user_id"]
    assert by_item[item3["cart_item_id"]]["user_id"] == bob["user_id"]
    assert by_item[item3["cart_item_id"]]["cart_id"] == cart_b["cart_id"]
    r2 = by_item[item2["cart_item_id"]]
    assert (r2["tour_id"], r2["quantity"], r2["room_type"], r2["價錢"]) == (tour2["tour_id"], 3, "雙人房", 2000)
    assert r2["旅遊名稱"] == tour2["title"]
    assert r2["大分類"] == tour2["type"] and r2["小分類"] == tour2["item"]
    assert r2["旅遊代表圖 Url"] == tour2["cover_image"]
    r1 = by_item[item1["cart_item_id"]]
    assert r1["end_date"] is None and r1["room_type"] is None


def test_cartlist_promo_price_only_in_period(tx):
    user = make_user(tx)
    cart = insert(tx, "cart", user_id=user["user_id"])
    expectations = {}
    # 三種促銷：進行中、已結束、尚未開始；都 price=1000、promo=600、quantity=3
    for label, (s, e) in {"active": (days(-1), days(1)), "ended": (days(-9), days(-5)),
                          "future": (days(5), days(9))}.items():
        tour = make_tour(tx, price=1000)
        insert(tx, "notification", tour_id=tour["tour_id"], type="促銷",
               start_date=s, end_date=e, promo_price=600.0)
        item = insert(tx, "cart_item", cart_id=cart["cart_id"], tour_id=tour["tour_id"], quantity=3)
        expectations[item["cart_item_id"]] = label
    plain = make_tour(tx, price=1000)
    plain_item = insert(tx, "cart_item", cart_id=cart["cart_id"], tour_id=plain["tour_id"], quantity=3)
    expectations[plain_item["cart_item_id"]] = "plain"
    by_label = {expectations[r["cart_item_id"]]: r
                for r in rows(tx, 'SELECT * FROM "user_cartList" WHERE cart_id = %s', (cart["cart_id"],))}
    assert by_label["active"]["促銷價錢"] == 600.0
    assert by_label["active"]["singleTotal_Price"] == 1800.0
    for label in ("ended", "future", "plain"):
        assert by_label[label]["促銷價錢"] is None, label
        assert by_label[label]["singleTotal_Price"] == 3000.0, label
    assert isinstance(by_label["active"]["singleTotal_Price"], float)


# ---------- hotel_booking ----------

def test_hotel_booking_always_one_row(tx):
    user = make_user(tx)
    tour = make_tour(tx)
    other_tour = make_tour(tx)
    make_hotel_room(tx, tour, "設計雙人房", 4)
    # 房型拼錯：即使有同名 room_type 的訂單，仍然是 0／0
    make_order_item(tx, user, tour, room_type="拼錯的房型", payment_status=1,
                    start_date=days(10), end_date=days(12))
    q = "SELECT * FROM hotel_booking(%s, %s, %s, %s)"
    assert rows(tx, q, ("拼錯的房型", days(10), days(12), tour["tour_id"])) == [
        {"booking_count": 0, "room_count": 0}]
    # 行程不存在
    assert rows(tx, q, ("設計雙人房", days(10), days(12), uuid.uuid4())) == [
        {"booking_count": 0, "room_count": 0}]
    # 房型屬於另一個行程
    assert rows(tx, q, ("設計雙人房", days(10), days(12), other_tour["tour_id"])) == [
        {"booking_count": 0, "room_count": 0}]
    # 找得到房型但沒有任何訂單：1 列，booking_count 0、room_count 4
    assert rows(tx, q, ("設計雙人房", days(10), days(12), tour["tour_id"])) == [
        {"booking_count": 0, "room_count": 4}]
    # 參數為 NULL 也不能變成 0 列
    assert len(rows(tx, q, (None, None, None, None))) == 1


def test_hotel_booking_counts_only_open_payment_statuses(tx):
    user = make_user(tx)
    tour = make_tour(tx)
    make_hotel_room(tx, tour, "房A", 9)
    make_hotel_room(tx, tour, "房B", 9)
    start, end = days(10), days(12)
    for status in (-1, 0, 1, 2, 3, 4):
        make_order_item(tx, user, tour, room_type="房A", payment_status=status,
                        start_date=start, end_date=end)
    # 其他房型、其他行程的訂單不計
    make_order_item(tx, user, tour, room_type="房B", payment_status=1, start_date=start, end_date=end)
    make_order_item(tx, user, make_tour(tx), room_type="房A", payment_status=1,
                    start_date=start, end_date=end)
    (row,) = rows(tx, "SELECT * FROM hotel_booking(%s, %s, %s, %s)", ("房A", start, end, tour["tour_id"]))
    assert row == {"booking_count": 3, "room_count": 9}
    assert isinstance(row["booking_count"], int)


def test_hotel_booking_date_range_is_half_open(tx):
    user = make_user(tx)
    tour = make_tour(tx)
    make_hotel_room(tx, tour, "房A", 5)
    d = lambda n: datetime(2031, 6, 1) + timedelta(days=n)  # noqa: E731
    make_order_item(tx, user, tour, room_type="房A", payment_status=1, start_date=d(2), end_date=d(5))
    q = "SELECT booking_count FROM hotel_booking('房A', %s, %s, %s)"

    def count(a, b):
        return rows(tx, q, (a, b, tour["tour_id"]))[0]["booking_count"]

    assert count(d(5), d(7)) == 0, "既有訂單的退房日當天，下一位可入住"
    assert count(d(0), d(2)) == 0, "新訂單的退房日是既有訂單的入住日，不衝突"
    assert count(d(4), d(6)) == 1, "重疊最後一晚"
    assert count(d(0), d(3)) == 1, "重疊第一晚"
    assert count(d(3), d(4)) == 1, "包在既有訂單裡"
    assert count(d(0), d(9)) == 1, "包住既有訂單"
    assert count(d(2), d(5)) == 1, "完全相同"


def test_hotel_booking_room_count_from_the_right_tour(tx):
    tour1, tour2 = make_tour(tx), make_tour(tx)
    make_hotel_room(tx, tour1, "同名房", 2)
    make_hotel_room(tx, tour2, "同名房", 7)
    q = "SELECT room_count FROM hotel_booking('同名房', %s, %s, %s)"
    assert rows(tx, q, (days(1), days(2), tour1["tour_id"])) == [{"room_count": 2}]
    assert rows(tx, q, (days(1), days(2), tour2["tour_id"])) == [{"room_count": 7}]


# ---------- restaurant_booking ----------

def test_restaurant_booking_counts_by_status(tx):
    user = make_user(tx)
    tour = make_tour(tx, item="food")
    make_restaurant(tx, tour, limit=25)
    # quantity 各不同，加總才分得出哪幾個狀態被算進去：-1,0,1 → 1+2+4 = 7
    for status, qty in {-1: 1, 0: 2, 1: 4, 2: 8, 3: 16, 4: 32}.items():
        make_order_item(tx, user, tour, payment_status=status, quantity=qty, total_price=100.0)
    make_order_item(tx, user, make_tour(tx, item="food"), payment_status=1, quantity=64)  # 其他行程
    q = "SELECT * FROM restaurant_booking(%s, %s)"
    (row,) = rows(tx, q, (days(3), tour["tour_id"]))
    assert row == {"booking_count": 7, "reservation_limit": 25}
    assert isinstance(row["booking_count"], int)


def test_restaurant_booking_ignores_time_parameter(tx):
    """#16：參數 1（controller 恆傳 NULL）被忽略，不分時段。"""
    user = make_user(tx)
    tour = make_tour(tx, item="food")
    make_restaurant(tx, tour, limit=10)
    make_order_item(tx, user, tour, payment_status=1, quantity=3, start_date=days(1))
    make_order_item(tx, user, tour, payment_status=1, quantity=4, start_date=days(40))
    q = "SELECT booking_count FROM restaurant_booking(%s, %s)"
    assert rows(tx, q, (None, tour["tour_id"])) == [{"booking_count": 7}]
    assert rows(tx, q, (days(1), tour["tour_id"])) == [{"booking_count": 7}]


def test_restaurant_booking_no_orders_and_no_restaurant(tx):
    tour = make_tour(tx, item="food")
    make_restaurant(tx, tour, limit=12)
    assert rows(tx, "SELECT * FROM restaurant_booking(NULL, %s)", (tour["tour_id"],)) == [
        {"booking_count": 0, "reservation_limit": 12}]
    # 沒有 restaurant 列的行程回 0 列（契約：找得到才回 1 列）
    assert rows(tx, "SELECT * FROM restaurant_booking(NULL, %s)", (make_tour(tx)["tour_id"],)) == []


# ---------- restaurant_isClosed ----------

def _weekday(dt: datetime) -> str:
    return ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"][dt.weekday()]


def test_restaurant_isclosed_always_one_row(tx):
    """#19：只看 restaurant_business 有無對應星期的列；預約時間 NULL／餐廳不存在 → false。"""
    tour = make_tour(tx, item="food")
    rest = make_restaurant(tx, tour)
    open_day = datetime(2031, 6, 2, 12, 0)   # 星期一
    closed_day = datetime(2031, 6, 3, 12, 0)  # 星期二：沒有營業列
    insert(tx, "restaurant_business", restaurant_id=rest["restaurant_id"],
           week=_weekday(open_day), business_hours="11:00~14:00")
    q = "SELECT * FROM restaurant_isclosed(%s, %s)"
    assert rows(tx, q, (open_day, tour["tour_id"])) == [{"isclosed": False}]
    assert rows(tx, q, (closed_day, tour["tour_id"])) == [{"isclosed": True}]
    # 該星期有營業列時，不看時段（時段由 restaurant_business_parsed 負責）
    assert rows(tx, q, (open_day.replace(hour=22), tour["tour_id"])) == [{"isclosed": False}]
    assert rows(tx, q, (None, tour["tour_id"])) == [{"isclosed": False}]
    assert rows(tx, q, (open_day, uuid.uuid4())) == [{"isclosed": False}]
    assert rows(tx, q, (open_day, make_tour(tx)["tour_id"])) == [{"isclosed": False}]  # 有行程沒餐廳


# ---------- restaurant_business_parsed ----------

def test_business_hours_split_per_slot(tx):
    tour = make_tour(tx, item="food")
    rest = make_restaurant(tx, tour)
    insert(tx, "restaurant_business", restaurant_id=rest["restaurant_id"], week="Monday",
           business_hours="11:00~14:00, 17:00~21:00")
    insert(tx, "restaurant_business", restaurant_id=rest["restaurant_id"], week="Tuesday",
           business_hours="17:00~23:00")
    result = rows(tx, "SELECT * FROM restaurant_business_parsed WHERE tour_id = %s ORDER BY week, start_time",
                  (tour["tour_id"],))
    assert [(r["week"], r["start_time"], r["end_time"]) for r in result] == [
        ("Monday", time(11, 0), time(14, 0)),
        ("Monday", time(17, 0), time(21, 0)),
        ("Tuesday", time(17, 0), time(23, 0)),
    ]
    assert all(isinstance(r["start_time"], time) and isinstance(r["end_time"], time) for r in result)


def test_business_hours_midnight_end_becomes_2359(tx):
    """#20：'17:00~00:00' 的 00:00 視為 24:00，end_time = 23:59:59。"""
    tour = make_tour(tx, item="food")
    rest = make_restaurant(tx, tour)
    insert(tx, "restaurant_business", restaurant_id=rest["restaurant_id"], week="Friday",
           business_hours="17:00~00:00")
    (row,) = rows(tx, "SELECT * FROM restaurant_business_parsed WHERE tour_id = %s", (tour["tour_id"],))
    assert (row["start_time"], row["end_time"]) == (time(17, 0), time(23, 59, 59))


def test_business_hours_unparsable_slots_are_ignored(tx):
    """#21：無法解析的時段由 view 忽略，不丟例外、也不影響同列其他時段。"""
    tour = make_tour(tx, item="food")
    rest = make_restaurant(tx, tour)
    insert(tx, "restaurant_business", restaurant_id=rest["restaurant_id"], week="Monday",
           business_hours="公休, 10:00~12:00, 99:00~25:00, abc")
    insert(tx, "restaurant_business", restaurant_id=rest["restaurant_id"], week="Tuesday",
           business_hours="全天營業")
    result = rows(tx, "SELECT * FROM restaurant_business_parsed WHERE tour_id = %s", (tour["tour_id"],))
    assert [(r["week"], r["start_time"], r["end_time"]) for r in result] == [
        ("Monday", time(10, 0), time(12, 0))]


def test_business_parsed_has_no_row_for_tour_without_restaurant(tx):
    tour = make_tour(tx, item="food")
    assert rows(tx, "SELECT * FROM restaurant_business_parsed WHERE tour_id = %s", (tour["tour_id"],)) == []


# ---------- user_couponList ----------

def test_couponlist_keeps_used_and_expired(tx):
    user = make_user(tx)
    other = make_user(tx)
    order = insert(tx, "orders", user_id=user["user_id"])
    specs = {
        "unused": dict(status=0, expire=days(10)),
        "used": dict(status=1, expire=days(10)),
        "previewing": dict(status=-1, expire=days(10), order_id=order["order_id"]),
        "expired": dict(status=0, expire=days(-10)),
    }
    coupons = {}
    for label, spec in specs.items():
        c = insert(tx, "coupon", description=f"desc-{label}", discount=50.0, expire_date=spec["expire"])
        extra = {"order_id": spec["order_id"]} if "order_id" in spec else {}
        insert(tx, "user_coupon", user_id=user["user_id"], coupon_id=c["coupon_id"],
               status=spec["status"], **extra)
        coupons[c["coupon_id"]] = (label, c)
    insert(tx, "user_coupon", user_id=other["user_id"], coupon_id=next(iter(coupons)), status=0)
    result = rows(tx, 'SELECT * FROM "user_couponList" WHERE user_id = %s', (user["user_id"],))
    assert len(result) == 4
    by_label = {coupons[r["coupon_id"]][0]: r for r in result}
    assert {k: v["status"] for k, v in by_label.items()} == {
        "unused": 0, "used": 1, "previewing": -1, "expired": 0}
    prev = by_label["previewing"]
    assert prev["order_id"] == order["order_id"]
    assert by_label["unused"]["order_id"] is None
    exp = by_label["expired"]
    c = coupons[exp["coupon_id"]][1]
    assert (exp["code"], exp["discount"], exp["description"]) == (c["code"], 50.0, "desc-expired")
    assert exp["expire_date"] == c["expire_date"] and exp["expired_date"] == c["expire_date"]


# ---------- user_level_point_coupon ----------

def _bind(tx, user, status, expire, **coupon_kw):
    c = insert(tx, "coupon", expire_date=expire, **coupon_kw)
    insert(tx, "user_coupon", user_id=user["user_id"], coupon_id=c["coupon_id"], status=status)
    return c


def test_point_coupon_only_usable_and_keeps_user(tx):
    user = make_user(tx)
    insert(tx, "user_level", user_id=user["user_id"], level="Lv1", name="探險家",
           badge_url="https://img.example.com/b.png", travel_point=1500)
    usable = _bind(tx, user, 0, days(5), discount=70.0, description="可用")
    on_boundary = _bind(tx, user, 0, datetime.now().replace(microsecond=0), description="邊界")
    # 以 now()::timestamp 精確等於「現在」：到期時刻本身仍算未過期（controller：now > expire 才過期）
    tx.execute("UPDATE coupon SET expire_date = now()::timestamp WHERE coupon_id = %s", (on_boundary["coupon_id"],))
    _bind(tx, user, 1, days(5))                                    # 已使用
    _bind(tx, user, -1, days(5))                                   # 預覽占用
    _bind(tx, user, 0, days(-1))                                   # 已過期
    just_expired = _bind(tx, user, 0, days(5))                     # 剛過期一秒
    tx.execute("UPDATE coupon SET expire_date = now()::timestamp - interval '1 second' WHERE coupon_id = %s",
               (just_expired["coupon_id"],))
    result = rows(tx, 'SELECT * FROM "user_level_point_coupon" WHERE 使用者編號 = %s', (user["user_id"],))
    assert {r["優惠卷編號"] for r in result} == {usable["coupon_id"], on_boundary["coupon_id"]}
    r = next(r for r in result if r["優惠卷編號"] == usable["coupon_id"])
    assert (r["優惠卷代碼"], r["優惠卷折扣"], r["優惠卷描述"], r["優惠卷期限"]) == (
        usable["code"], 70.0, "可用", usable["expire_date"])
    for row in result:  # 使用者與等級欄位每列都相同
        assert (row["名稱"], row["信箱"], row["角色"]) == (user["name"], user["email"], "User")
        assert (row["個人偏好 1"], row["個人偏好 2"], row["個人偏好 3"]) == (1, 2, 3)
        assert (row["旅遊等級"], row["旅遊等級名稱"], row["使用者旅遊積分"]) == ("Lv1", "探險家", 1500)
        assert row["旅遊徽章 Url"] == "https://img.example.com/b.png"


def test_point_coupon_user_without_usable_coupon_keeps_one_row(tx):
    """#40：沒有可用優惠卷（含完全沒有綁定）的使用者仍有 1 列，優惠卷欄位全為 NULL。"""
    only_used = make_user(tx)
    insert(tx, "user_level", user_id=only_used["user_id"], travel_point=300)
    _bind(tx, only_used, 1, days(5))
    _bind(tx, only_used, 0, days(-5))
    none_at_all = make_user(tx)
    insert(tx, "user_level", user_id=none_at_all["user_id"], travel_point=800)
    for user, point in ((only_used, 300), (none_at_all, 800)):
        (row,) = rows(tx, 'SELECT * FROM "user_level_point_coupon" WHERE 使用者編號 = %s', (user["user_id"],))
        assert row["使用者旅遊積分"] == point and row["名稱"] == user["name"]
        for col in ("優惠卷編號", "優惠卷代碼", "優惠卷折扣", "優惠卷描述", "優惠卷期限"):
            assert row[col] is None, col


def test_point_coupon_user_without_level_and_latest_level_wins(tx):
    no_level = make_user(tx)
    (row,) = rows(tx, 'SELECT * FROM "user_level_point_coupon" WHERE 使用者編號 = %s', (no_level["user_id"],))
    assert row["旅遊等級"] is None and row["使用者旅遊積分"] is None and row["名稱"] == no_level["name"]

    two_levels = make_user(tx)
    insert(tx, "user_level", user_id=two_levels["user_id"], level="舊", travel_point=1, updated_at=days(-5))
    insert(tx, "user_level", user_id=two_levels["user_id"], level="新", travel_point=2, updated_at=days(-1))
    insert(tx, "user_level", user_id=two_levels["user_id"], level="更舊", travel_point=3, updated_at=days(-9))
    (row,) = rows(tx, 'SELECT * FROM "user_level_point_coupon" WHERE 使用者編號 = %s', (two_levels["user_id"],))
    assert (row["旅遊等級"], row["使用者旅遊積分"]) == ("新", 2)


def test_point_coupon_two_usable_coupons_two_rows_same_points(tx):
    user = make_user(tx)
    insert(tx, "user_level", user_id=user["user_id"], travel_point=42)
    _bind(tx, user, 0, days(3))
    _bind(tx, user, 0, days(4))
    result = rows(tx, 'SELECT * FROM "user_level_point_coupon" WHERE 使用者編號 = %s', (user["user_id"],))
    assert len(result) == 2 and {r["使用者旅遊積分"] for r in result} == {42}
    assert isinstance(result[0]["使用者旅遊積分"], int)


# ---------- user_orderList ----------

def test_orderlist_total_count_and_unit_promo(tx):
    user = make_user(tx)
    tour_a = make_tour(tx, price=1000)
    tour_b = make_tour(tx, price=500)
    order1 = insert(tx, "orders", user_id=user["user_id"])
    order2 = insert(tx, "orders", user_id=user["user_id"])
    # order1 兩個項目（不同 payment_status，都要出現）：#13 的各種 discount_price
    promo = make_order_item(tx, user, tour_a, order=order1, quantity=3, total_price=3000.0,
                            discount_price=2400.0, payment_status=-1)
    zero = make_order_item(tx, user, tour_b, order=order1, quantity=2, total_price=1000.0,
                           discount_price=0.0, payment_status=2,
                           room_type="雙人房", end_date=days(9))
    single = make_order_item(tx, user, tour_a, order=order2, quantity=1, total_price=1000.0,
                             discount_price=None, payment_status=1)
    result = rows(tx, 'SELECT * FROM "user_orderList" WHERE order_id = ANY(%s)',
                  ([order1["order_id"], order2["order_id"]],))
    assert len(result) == 3
    by_tour_order = {(r["order_id"], r["tour_id"]): r for r in result}
    r_promo = by_tour_order[(order1["order_id"], tour_a["tour_id"])]
    r_zero = by_tour_order[(order1["order_id"], tour_b["tour_id"])]
    r_single = by_tour_order[(order2["order_id"], tour_a["tour_id"])]
    assert (r_promo["total_count"], r_zero["total_count"], r_single["total_count"]) == (2, 2, 1)
    assert isinstance(r_promo["total_count"], int)
    assert (r_promo["價錢"], r_promo["促銷價錢"], r_promo["singleTotal_Price"]) == (1000.0, 800.0, 3000.0)
    assert (r_zero["價錢"], r_zero["促銷價錢"], r_zero["singleTotal_Price"]) == (500.0, None, 1000.0)
    assert (r_single["價錢"], r_single["促銷價錢"], r_single["singleTotal_Price"]) == (1000.0, None, 1000.0)
    assert (r_zero["room_type"], r_zero["end_date"]) == ("雙人房", zero["end_date"])
    assert r_promo["room_type"] is None
    assert (r_promo["quantity"], r_promo["start_date"]) == (3, promo["start_date"])
    assert r_promo["旅遊名稱"] == tour_a["title"] and r_promo["大分類"] == tour_a["type"]
    assert r_promo["小分類"] == tour_a["item"] and r_promo["旅遊代表圖 Url"] == tour_a["cover_image"]


def test_orderlist_price_is_historical_not_current_tour_price(tx):
    """#13：價錢取下單當時（order_item），不是現在的 tour.price／促銷。"""
    user = make_user(tx)
    tour = make_tour(tx, price=9999)
    insert(tx, "notification", tour_id=tour["tour_id"], type="促銷",
           start_date=days(-1), end_date=days(1), promo_price=1.0)
    item = make_order_item(tx, user, tour, quantity=2, total_price=2000.0, discount_price=1600.0)
    (row,) = rows(tx, 'SELECT * FROM "user_orderList" WHERE order_id = %s', (item["order_id"],))
    assert (row["價錢"], row["促銷價錢"]) == (1000.0, 800.0)


def test_orderlist_zero_quantity_gives_null_prices(tx):
    user = make_user(tx)
    tour = make_tour(tx)
    item = make_order_item(tx, user, tour, quantity=0, total_price=0.0, discount_price=100.0)
    (row,) = rows(tx, 'SELECT * FROM "user_orderList" WHERE order_id = %s', (item["order_id"],))
    assert row["價錢"] is None and row["促銷價錢"] is None
