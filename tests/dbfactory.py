"""在測試交易裡塞資料的小工具：只填必要欄位，其餘用 DEFAULTS 補 NOT NULL 欄位。

外鍵欄位（user_id、tour_id…）沒有預設，一定要由呼叫端給。
DEFAULTS 的值若是 callable，每次 insert 呼叫一次（用於要唯一的欄位）。
"""
import uuid
from datetime import datetime

from psycopg import sql
from psycopg.rows import dict_row


def _uid() -> str:
    return uuid.uuid4().hex[:12]


def _now() -> datetime:
    return datetime.now()


DEFAULTS: dict[str, dict] = {
    "user": {
        "name": lambda: f"測試-{_uid()}",
        "email": lambda: f"factory-{uuid.uuid4().hex}@example.com",
        "role": "User",
        "password": "not-a-real-hash",
        "preference1": 1,
        "preference2": 2,
        "preference3": 3,
    },
    "socialLogin": {},
    "user_level": {},
    "coupon": {
        "code": lambda: f"T{_uid()}",
        "discount": 0.9,
        "description": "測試優惠卷",
        "expire_date": _now,
    },
    "user_coupon": {"status": 0},
    "point_record": {"type": "earn", "point": 10},
    "tour": {
        "type": "tourgroup",
        "item": "travel",
        "status": 1,
        "title": lambda: f"測試行程-{_uid()}",
        "slogan": "測試標語",
        "days": 3,
        "price": 1000,
        "country": "測試國",
        "region": "測試區",
        "address": "測試地址",
        "google_map_url": "https://maps.example.com/x",
        "calendar_url": "https://calendar.example.com/x",
        "preference1": 1,
        "preference2": 2,
        "preference3": 3,
        "description": "測試描述",
        "cover_image": "https://img.example.com/cover.jpg",
        **{f"img{i}": f"https://img.example.com/{i}.jpg" for i in range(1, 7)},
        **{f"img{i}_desc": f"圖{i}" for i in range(1, 7)},
    },
    "tour_detail": {
        **{f"feature_img{i}": f"https://img.example.com/f{i}.jpg" for i in range(1, 4)},
        **{f"feature_desc{i}": f"特色{i}" for i in range(1, 4)},
        "itinerary": "測試行程規劃",
    },
    "restaurant": {
        "reservation_limit": 4,
        "website_info": "測試官網介紹",
        "website_url": "https://restaurant.example.com",
    },
    "restaurant_business": {"week": "週一", "business_hours": "11:00~14:00"},
    "restaurant_menu": {"name": lambda: f"菜-{_uid()}", "price": 100.0},
    "hotel": {},
    "hotel_room": {
        "title": lambda: f"房型-{_uid()}",
        "capacity": 2,
        "room_count": 5,
        "image": "https://img.example.com/room.jpg",
        "image_desc": "房型圖",
    },
    "notification": {"type": "異動"},
    "country": {"name": lambda: f"國-{_uid()}"},
    "region": {"name": lambda: f"區-{_uid()}"},
    "cart": {"total_price": 0.0},
    "cart_item": {"quantity": 1, "start_date": _now},
    "orders": {"total_price": 1000.0},
    "order_item": {"total_price": 1000.0, "quantity": 1, "start_date": _now},
    "payment": {"payment_method": "credit_card"},
    "review": {"type": "web", "rating": 5, "content": "測試評論"},
    "hidden_play": {"title": lambda: f"玩法-{_uid()}"},
    "auto_setting": {},
    "favorite": {},
}


def insert(conn, table: str, **cols) -> dict:
    """INSERT 一列並回傳整列（RETURNING *，dict）。"""
    values = dict(cols)
    for name, default in DEFAULTS[table].items():
        if name not in values:
            values[name] = default() if callable(default) else default
    stmt = sql.SQL("INSERT INTO {} ({}) VALUES ({}) RETURNING *").format(
        sql.Identifier(table),
        sql.SQL(", ").join(sql.Identifier(c) for c in values),
        sql.SQL(", ").join(sql.Placeholder() for _ in values),
    )
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(stmt, list(values.values()))
        return cur.fetchone()
