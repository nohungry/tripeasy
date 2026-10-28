"""docs/db-contract.md 的 21 個 view／function 的機器可讀版。

key 是 CREATE 時的識別字（等於 pg_class.relname／pg_proc.proname，所以
restaurant_isClosed 的 key 是小寫的 restaurant_isclosed）。
型別用契約寫法；args 只比型別與順序，名稱僅供閱讀。
Task 4 放 A 組，Task 5、6 加入 B、C 組。
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
    ("異動通知內容", "text"),  # 旅遊標語、旅遊結束日期、旅遊天數、旅遊代表圖 Url、異動通知內容 為 #26 加入
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
}
