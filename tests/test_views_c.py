"""C 組 view（會員與後台）的行為。

每個測試在 tx 裡自己塞資料、只查自己的列，不依賴 seed；結束時 tx 會 rollback。
tx 內 CURRENT_TIMESTAMP 是固定的，所以凡是順序或「最新」有關的資料都明確給時間。
"""
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from psycopg.rows import dict_row

from dbfactory import insert

BASE = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)


def rows(tx, query: str, params=()) -> list[dict]:
    with tx.cursor(row_factory=dict_row) as cur:
        cur.execute(query, params)
        return cur.fetchall()


def make_user(tx, **kw) -> dict:
    return insert(tx, "user", **kw)


def make_tour(tx, **kw) -> dict:
    return insert(tx, "tour", **kw)


def make_item(tx, user, tour, order_created_at=None, order_status=-1, **kw) -> dict:
    """為 user 建一張新訂單並放一個 order_item；kw 傳給 order_item。"""
    order_cols = {"user_id": user["user_id"], "payment_status": order_status}
    if order_created_at is not None:
        order_cols["created_at"] = order_created_at
    order = insert(tx, "orders", **order_cols)
    item = insert(tx, "order_item", order_id=order["order_id"], tour_id=tour["tour_id"], **kw)
    return item


# ---------- user_favorite ----------

def test_favorite_keeps_inactive_and_uses_favorite_time(tx):
    user, other = make_user(tx), make_user(tx)
    active = make_tour(tx, status=1, preference1=4, preference2=5, preference3=6, title="上架行程")
    inactive = make_tour(tx, status=2, preference1=7, preference2=8, preference3=9, title="下架行程")
    t_inactive = BASE + timedelta(days=2)
    t_active = BASE + timedelta(days=1)
    fav_inactive = insert(tx, "favorite", user_id=user["user_id"], tour_id=inactive["tour_id"],
                          created_at=t_inactive)
    fav_active = insert(tx, "favorite", user_id=user["user_id"], tour_id=active["tour_id"],
                        created_at=t_active)
    insert(tx, "favorite", user_id=other["user_id"], tour_id=active["tour_id"], created_at=BASE)

    got = {r["旅遊編號"]: r for r in rows(
        tx, 'SELECT * FROM "user_favorite" WHERE "收藏人員編號" = %s', (user["user_id"],))}

    assert set(got) == {active["tour_id"], inactive["tour_id"]}  # #41 下架行程的收藏也出現
    r = got[inactive["tour_id"]]
    assert r["上下架狀態"] == 2
    assert r["旅遊名稱"] == "下架行程"
    assert r["favorite_id"] == fav_inactive["favorite_id"]
    assert r["建立時間"] == t_inactive  # #43 收藏時間，不是 tour.created_at
    assert r["建立時間"] != inactive["created_at"]
    assert (r["偏好分類1"], r["偏好分類2"], r["偏好分類3"]) == (7, 8, 9)  # #42 行程的偏好
    assert got[active["tour_id"]]["建立時間"] == t_active
    assert got[active["tour_id"]]["favorite_id"] == fav_active["favorite_id"]


def test_favorite_one_row_per_favorite_even_with_many_notifications(tx):
    """每筆 favorite 一列：行程有多筆促銷／異動通知也不會讓收藏重複（tour_base 已各取最新一筆）。"""
    user = make_user(tx)
    tour = make_tour(tx)
    for i in range(2):
        insert(tx, "notification", tour_id=tour["tour_id"], type="促銷", updated_at=BASE + timedelta(days=i))
        insert(tx, "notification", tour_id=tour["tour_id"], type="異動", updated_at=BASE + timedelta(days=i))
    insert(tx, "favorite", user_id=user["user_id"], tour_id=tour["tour_id"])
    got = rows(tx, 'SELECT * FROM "user_favorite" WHERE "收藏人員編號" = %s', (user["user_id"],))
    assert len(got) == 1


# ---------- user_orders ----------

def test_orders_paid_only_newest_first(tx):
    user, other = make_user(tx), make_user(tx)
    tour = make_tour(tx, status=1)
    inactive = make_tour(tx, status=2, title="下架行程")

    # 依「最舊 → 最新」之外的順序插入，且 order_item.created_at 與 orders.created_at 順序相反，
    # 才能分辨「依 orders.created_at 排序」和「依插入順序／order_item.created_at 排序」
    mid = make_item(tx, user, tour, order_created_at=BASE + timedelta(days=5), order_status=0,
                    payment_status=1, created_at=BASE + timedelta(days=3), total_price=500.0,
                    discount_price=450.0, quantity=2)
    oldest = make_item(tx, user, inactive, order_created_at=BASE + timedelta(days=1), order_status=0,
                       payment_status=1, created_at=BASE + timedelta(days=9))
    newest = make_item(tx, user, tour, order_created_at=BASE + timedelta(days=8), order_status=0,
                       payment_status=1, created_at=BASE + timedelta(days=1))
    # 其餘 payment_status 全不出現（訂單層級狀態故意設成 1，確認篩選看的是 order_item）
    unpaid = {}
    for status in (-1, 0, 2, 3, 4):
        unpaid[status] = make_item(tx, user, tour, order_created_at=BASE + timedelta(days=20 + status),
                                   order_status=1, payment_status=status)
    make_item(tx, other, tour, order_created_at=BASE + timedelta(days=30), payment_status=1)

    got = rows(tx, 'SELECT * FROM "user_orders" WHERE "使用者編號" = %s', (user["user_id"],))

    assert [r["order_item_id"] for r in got] == [
        newest["order_item_id"], mid["order_item_id"], oldest["order_item_id"]]
    assert {r["付款狀態"] for r in got} == {1}
    assert got[2]["上下架狀態"] == 2  # #41 下架行程的購買紀錄也出現
    r = got[1]
    assert (r["數量"], r["小計"], r["促銷小計"]) == (2, 500.0, 450.0)
    assert r["出發日期"] == mid["start_date"]
    assert r["旅遊編號"] == tour["tour_id"]
    assert r["旅遊名稱"] == tour["title"]
    assert (r["偏好分類1"], r["偏好分類2"], r["偏好分類3"]) == (1, 2, 3)  # #42


# ---------- user_order_item ----------

def test_order_item_exactly_one_row_with_owner(tx):
    user = make_user(tx)
    tour = make_tour(tx, title="明細行程", preference1=3, preference2=4, preference3=5)
    # 讓一對多的表都有多列：若 view 誤 JOIN 它們，就會變成多列（#46）
    insert(tx, "tour_detail", tour_id=tour["tour_id"])
    insert(tx, "tour_detail", tour_id=tour["tour_id"])
    for i in range(2):
        insert(tx, "notification", tour_id=tour["tour_id"], type="促銷", updated_at=BASE + timedelta(days=i))
        insert(tx, "notification", tour_id=tour["tour_id"], type="異動", updated_at=BASE + timedelta(days=i))
        hotel = insert(tx, "hotel", tour_id=tour["tour_id"])
        insert(tx, "hotel_room", hotel_id=hotel["hotel_id"])
    item = make_item(tx, user, tour, payment_status=1, total_price=900.0, discount_price=800.0,
                     quantity=3, room_type="雙人房")
    # 同一張訂單的另一個項目與別人的項目不應混進來
    insert(tx, "order_item", order_id=item["order_id"], tour_id=tour["tour_id"], payment_status=1)

    got = rows(tx, 'SELECT * FROM "user_order_item" WHERE order_item_id = %s', (item["order_item_id"],))

    assert len(got) == 1
    r = got[0]
    assert r["使用者編號"] == user["user_id"]  # #47
    assert r["order_id"] == item["order_id"]
    assert r["tour_id"] == tour["tour_id"]
    assert (r["total_price"], r["discount_price"], r["quantity"], r["room_type"]) == (900.0, 800.0, 3, "雙人房")
    assert r["title"] == "明細行程"
    assert (r["preference1"], r["preference2"], r["preference3"]) == (3, 4, 5)  # #42
    assert "address" in r and r["address"] == tour["address"]  # tour.address，不是 orders.address
    assert "phone" not in r and "payment_type" not in r  # #47 不帶 orders 的地址電話


@pytest.mark.parametrize("status", [-1, 0, 2, 3, 4])
def test_order_item_not_paid_has_no_row(tx, status):
    """#6：明細與清單同一個篩選，只有 order_item.payment_status = 1。"""
    user = make_user(tx)
    tour = make_tour(tx)
    item = make_item(tx, user, tour, order_status=1, payment_status=status)  # 訂單層級是 1 也不算
    got = rows(tx, 'SELECT * FROM "user_order_item" WHERE order_item_id = %s', (item["order_item_id"],))
    assert got == []


def test_order_item_inactive_tour_still_appears(tx):
    user = make_user(tx)
    tour = make_tour(tx, status=2)
    item = make_item(tx, user, tour, payment_status=1)
    got = rows(tx, 'SELECT * FROM "user_order_item" WHERE order_item_id = %s', (item["order_item_id"],))
    assert len(got) == 1  # #41
    assert got[0]["status"] == 2


# ---------- user_adminList ----------

def test_adminlist_one_row_latest_level(tx):
    user = make_user(tx, role="admin", preference1=6, preference2=7, preference3=8)
    other = make_user(tx)
    # 最新的那筆 level_id 較大、最舊的那筆 level_id 較小，且先插入最新的：
    # 若 view 改成只用 level_id／插入順序決勝，會選到舊的
    newest_id = uuid.UUID("ffffffff-0000-4000-8000-000000000001")
    oldest_id = uuid.UUID("00000000-0000-4000-8000-000000000001")
    middle_id = uuid.UUID("88888888-0000-4000-8000-000000000001")
    insert(tx, "user_level", level_id=str(newest_id), user_id=user["user_id"], level="Level 3",
           name="最新", badge_url="https://b/3", travel_point=300, updated_at=BASE + timedelta(days=10))
    insert(tx, "user_level", level_id=str(oldest_id), user_id=user["user_id"], level="Level 1",
           name="最舊", badge_url="https://b/1", travel_point=100, updated_at=BASE)
    insert(tx, "user_level", level_id=str(middle_id), user_id=user["user_id"], level="Level 2",
           name="中間", badge_url="https://b/2", travel_point=200, updated_at=BASE + timedelta(days=5))
    insert(tx, "user_level", user_id=other["user_id"], level="Other", name="別人", travel_point=1)

    got = rows(tx, 'SELECT * FROM "user_adminList" WHERE "使用者編號" = %s', (user["user_id"],))

    assert len(got) == 1  # #22 恰好一列
    r = got[0]
    assert (r["旅遊等級"], r["旅遊等級名稱"], r["旅遊徽章 Url"], r["使用者旅遊積分"]) == (
        "Level 3", "最新", "https://b/3", 300)
    assert r["名稱"] == user["name"]
    assert r["信箱"] == user["email"]
    assert r["角色"] == "admin"
    assert r["個人照片 Url"] == user["avatar_url"]
    assert (r["個人偏好 1"], r["個人偏好 2"], r["個人偏好 3"]) == (6, 7, 8)  # #49 數字


def test_adminlist_user_without_level_still_one_row(tx):
    """#22 LEFT JOIN：沒有 user_level 的使用者仍有一列，等級欄位為 NULL。"""
    user = make_user(tx)
    got = rows(tx, 'SELECT * FROM "user_adminList" WHERE "使用者編號" = %s', (user["user_id"],))
    assert len(got) == 1
    r = got[0]
    assert r["名稱"] == user["name"]
    assert (r["旅遊等級"], r["旅遊等級名稱"], r["旅遊徽章 Url"], r["使用者旅遊積分"]) == (None,) * 4
