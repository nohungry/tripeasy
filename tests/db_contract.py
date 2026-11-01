"""docs/db-contract.md 的 21 個 view／function 的機器可讀版。

key 是 CREATE 時的識別字（等於 pg_class.relname／pg_proc.proname，所以
restaurant_isClosed 的 key 是小寫的 restaurant_isclosed）。
型別用契約寫法；args 只比型別與順序，名稱僅供閱讀。
Task 4 放 A 組，Task 5 加 B 組，Task 6 加 C 組。
"""

_TOUR_LIST_COLUMNS = [
    ("旅遊編號", "uuid"),
    ("上下架狀態", "smallint"),
    ("通知狀態", "varchar"),
    ("旅遊名稱", "varchar"),
    ("旅遊標語", "varchar"),
    ("旅遊描述", "text"),
    ("大分類", "varchar"),
    ("小分類", "varchar"),
    ("所屬國家", "varchar"),
    ("所屬地區", "varchar"),
    ("建立時間", "timestamptz"),
    ("更新時間", "timestamptz"),
    ("價錢", "integer"),
    ("促銷價錢", "double precision"),
    ("促銷開始日期", "timestamp"),
    ("促銷結束日期", "timestamp"),
    ("旅遊開始日期", "timestamp"),
    ("旅遊結束日期", "timestamp"),
    ("旅遊天數", "integer"),
    ("旅遊代表圖 Url", "text"),
    ("偏好分類1", "smallint"),
    ("偏好分類2", "smallint"),
    ("偏好分類3", "smallint"),
    ("異動通知內容", "text"),  # 旅遊標語、旅遊結束日期、旅遊天數、異動通知內容 為 #26 加入
]

# tour_tour_detail／tour_hotel／tour_restaurant 共用的行程與通知欄位（契約：「同 tour_tour_detail」）
_TOUR_PAGE_COLUMNS = (
    [
        ("旅遊編號", "uuid"),
        ("旅遊名稱", "varchar"),
        ("旅遊標語", "varchar"),
        ("大分類", "varchar"),
        ("小分類", "varchar"),
        ("旅遊代表圖 Url", "text"),
    ]
    + [(f"旅遊圖{i} 描述", "varchar") for i in range(1, 7)]
    + [(f"旅遊圖{i} Url", "text") for i in range(1, 7)]
    + [
        ("價錢", "integer"),
        ("旅遊開始日期", "timestamp"),
        ("旅遊結束日期", "timestamp"),
        ("所屬國家", "varchar"),
        ("所屬地區", "varchar"),
        ("地址", "text"),
        ("Google Map Url", "varchar"),
        ("旅遊描述", "text"),
        ("偏好設定分類 1", "smallint"),
        ("偏好設定分類 2", "smallint"),
        ("偏好設定分類 3", "smallint"),
        ("收藏狀態", "boolean"),
        ("異動通知內容", "text"),
        ("促銷價錢", "double precision"),
        ("通知狀態", "varchar"),
        ("促銷開始日期", "timestamp"),
        ("促銷結束日期", "timestamp"),
    ]
)

_USER_ARG = [("使用者編號", "uuid")]

OBJECTS: dict[str, dict] = {
    "tour_base": {"kind": "view", "args": [], "columns": _TOUR_LIST_COLUMNS},
    "tour_travel": {
        "kind": "function",
        "args": _USER_ARG,
        "columns": _TOUR_LIST_COLUMNS + [("收藏狀態", "boolean")],
    },
    "tour_travel_popular": {
        "kind": "function",
        "args": [("大分類", "text"), ("小分類", "text")],
        "columns": [("tour_id", "uuid"), ("購買排行", "integer")],
    },
    "tour_travel_most_favorited": {
        "kind": "function",
        "args": [("大分類", "text"), ("小分類", "text")],
        "columns": [("tour_id", "uuid"), ("收藏排行", "integer")],
    },
    "tour_tour_detail": {
        "kind": "function",
        "args": _USER_ARG,
        "columns": _TOUR_PAGE_COLUMNS
        + [(f"特色圖{i} 描述", "varchar") for i in range(1, 4)]
        + [(f"特色圖{i} url", "text") for i in range(1, 4)]
        + [("行程規劃", "text")],
    },
    "tour_hotel": {
        "kind": "function",
        "args": _USER_ARG,
        "columns": _TOUR_PAGE_COLUMNS
        + [
            ("房型名稱", "varchar"),
            ("房型描述", "varchar"),
            ("房型容納人數", "integer"),
            ("房型數量", "integer"),
            ("房型代表圖 url", "text"),
            ("基本設施與服務", "text"),
            ("餐飲相關服務", "text"),
            ("客房與設施", "text"),
            ("交通與停車", "text"),
            ("其他便利服務", "text"),
        ],
    },
    "tour_restaurant": {
        "kind": "function",
        "args": _USER_ARG,
        "columns": _TOUR_PAGE_COLUMNS
        + [
            ("餐廳人員限制", "integer"),
            ("官網介紹", "text"),
            ("官網 url", "varchar"),
            ("菜單名稱", "varchar"),
            ("菜單描述", "text"),
            ("菜單價錢", "double precision"),
            ("營業星期", "varchar"),
            ("營業時間", "text"),
        ],
    },
    "user_user_level": {
        "kind": "view",
        "args": [],
        "columns": [
            ("使用者編號", "uuid"),
            ("名稱", "varchar"),
            ("個人照片 Url", "varchar"),
            ("旅遊等級", "varchar"),
            ("旅遊等級名稱", "varchar"),
            ("旅遊徽章 Url", "varchar"),
        ],
    },
    "user_level_review_forHome": {
        "kind": "view",
        "args": [],
        "columns": [
            ("評論編號", "uuid"),
            ("評論時間", "timestamptz"),
            ("名稱", "varchar"),
            ("個人照片 Url", "varchar"),
            ("旅遊等級", "varchar"),
            ("旅遊等級名稱", "varchar"),
            ("旅遊徽章 Url", "varchar"),
            ("評分", "integer"),
            ("評論內容", "text"),
        ],
    },
    # ---------- B 組：購物車、訂位、折扣、結帳 ----------
    "user_cartList": {
        "kind": "view",
        "args": [],
        "columns": [
            ("user_id", "uuid"),
            ("cart_id", "uuid"),
            ("tour_id", "uuid"),
            ("大分類", "varchar"),
            ("小分類", "varchar"),
            ("旅遊名稱", "varchar"),
            ("旅遊代表圖 Url", "text"),
            ("價錢", "integer"),
            ("促銷價錢", "double precision"),
            ("quantity", "integer"),
            ("start_date", "timestamp"),
            ("end_date", "timestamp"),
            ("room_type", "varchar"),
            ("singleTotal_Price", "double precision"),
            ("cart_item_id", "uuid"),  # #35 多帶
        ],
    },
    "hotel_booking": {
        "kind": "function",
        "args": [("房型", "varchar"), ("入住日期", "timestamp"), ("退房日期", "timestamp"), ("旅遊編號", "uuid")],
        "columns": [("booking_count", "integer"), ("room_count", "integer")],
    },
    "restaurant_booking": {
        "kind": "function",
        "args": [("預約時間", "timestamp"), ("旅遊編號", "uuid")],
        "columns": [("booking_count", "integer"), ("reservation_limit", "integer")],
    },
    "restaurant_isclosed": {
        "kind": "function",
        "args": [("預約時間", "timestamp"), ("旅遊編號", "uuid")],
        "columns": [("isclosed", "boolean")],
    },
    "restaurant_business_parsed": {
        "kind": "view",
        "args": [],
        "columns": [
            ("tour_id", "uuid"),
            ("week", "varchar"),
            ("start_time", "time"),
            ("end_time", "time"),
        ],
    },
    "user_couponList": {
        "kind": "view",
        "args": [],
        "columns": [
            ("user_id", "uuid"),
            ("coupon_id", "uuid"),
            ("code", "varchar"),
            ("discount", "double precision"),
            ("description", "text"),
            ("expire_date", "timestamp"),
            ("expired_date", "timestamp"),  # #36 同值多帶
            ("status", "smallint"),
            ("order_id", "uuid"),
        ],
    },
    "user_level_point_coupon": {
        "kind": "view",
        "args": [],
        "columns": [
            ("使用者編號", "uuid"),
            ("名稱", "varchar"),
            ("信箱", "varchar"),
            ("角色", "varchar"),
            ("個人照片 Url", "varchar"),
            ("個人偏好 1", "smallint"),
            ("個人偏好 2", "smallint"),
            ("個人偏好 3", "smallint"),
            ("旅遊等級", "varchar"),
            ("旅遊等級名稱", "varchar"),
            ("旅遊徽章 Url", "varchar"),
            ("使用者旅遊積分", "integer"),
            ("優惠卷編號", "uuid"),
            ("優惠卷代碼", "varchar"),
            ("優惠卷折扣", "double precision"),
            ("優惠卷描述", "text"),
            ("優惠卷期限", "timestamp"),
        ],
    },
    "user_orderList": {
        "kind": "view",
        "args": [],
        "columns": [
            ("order_id", "uuid"),
            ("tour_id", "uuid"),
            ("大分類", "varchar"),
            ("小分類", "varchar"),
            ("旅遊名稱", "varchar"),
            ("旅遊代表圖 Url", "text"),
            ("價錢", "double precision"),
            ("促銷價錢", "double precision"),
            ("quantity", "integer"),
            ("start_date", "timestamp"),
            ("end_date", "timestamp"),
            ("room_type", "varchar"),
            ("singleTotal_Price", "double precision"),
            ("total_count", "integer"),
        ],
    },
    # ---------- C 組：會員與後台 ----------
    "user_favorite": {
        "kind": "view",
        "args": [],
        # #11 A：favorite ＋ tour_base 的欄位（不含 tour_base 的 建立時間／更新時間）＋ favorite_id；
        # 建立時間 ＝ favorite.created_at（#43）
        "columns": [
            ("收藏人員編號", "uuid"),
            ("建立時間", "timestamptz"),
            ("favorite_id", "uuid"),
        ]
        + [c for c in _TOUR_LIST_COLUMNS if c[0] not in ("建立時間", "更新時間")],
    },
    "user_orders": {
        "kind": "view",
        "args": [],
        # #11：tour_base 的全部欄位 ＋ order_item_id ＋ 付款狀態、數量、出發日期、小計、促銷小計
        "columns": [("使用者編號", "uuid"), ("order_item_id", "uuid")]
        + _TOUR_LIST_COLUMNS
        + [
            ("付款狀態", "smallint"),
            ("數量", "integer"),
            ("出發日期", "timestamp"),
            ("小計", "double precision"),
            ("促銷小計", "double precision"),
        ],
    },
    "user_order_item": {
        "kind": "view",
        "args": [],
        # #11 命名 A（全部英文）：order_item 的欄位 ＋ tour.*（tour_id 只出現一次）＋ #47 的 使用者編號
        "columns": [
            ("order_item_id", "uuid"),
            ("使用者編號", "uuid"),
            ("order_id", "uuid"),
            ("tour_id", "uuid"),
            ("payment_status", "smallint"),
            ("total_price", "double precision"),
            ("discount_price", "double precision"),
            ("quantity", "integer"),
            ("start_date", "timestamp"),
            ("end_date", "timestamp"),
            ("room_type", "varchar"),
            ("type", "varchar"),
            ("item", "varchar"),
            ("status", "smallint"),
            ("title", "varchar"),
            ("slogan", "varchar"),
            ("tour_start_date", "timestamp"),
            ("tour_end_date", "timestamp"),
            ("days", "integer"),
            ("price", "integer"),
            ("country", "varchar"),
            ("region", "varchar"),
            ("address", "text"),
            ("google_map_url", "varchar"),
            ("calendar_url", "varchar"),
            ("preference1", "smallint"),
            ("preference2", "smallint"),
            ("preference3", "smallint"),
            ("notice", "text"),
            ("description", "text"),
            ("cover_image", "text"),
        ]
        + [(f"img{i}{suffix}", typ) for i in range(1, 7) for suffix, typ in (("", "text"), ("_desc", "varchar"))]
        + [("created_at", "timestamptz"), ("updated_at", "timestamptz")],
    },
    "user_adminList": {
        "kind": "view",
        "args": [],
        # #11 A：user ＋ user_level（鏡射 user_level_point_coupon 去掉優惠卷）；不含 password 等（契約「契約要求」）
        "columns": [
            ("使用者編號", "uuid"),
            ("名稱", "varchar"),
            ("信箱", "varchar"),
            ("角色", "varchar"),
            ("個人照片 Url", "varchar"),
            ("個人偏好 1", "smallint"),
            ("個人偏好 2", "smallint"),
            ("個人偏好 3", "smallint"),
            ("旅遊等級", "varchar"),
            ("旅遊等級名稱", "varchar"),
            ("旅遊徽章 Url", "varchar"),
            ("使用者旅遊積分", "integer"),
        ],
    },
}
