"""把團隊留下的 fakedata 轉成可重複執行的 Flyway seed。

來源：db/seed-build/tripeasy_fakedata.sql（2025-05，使用者提供；依序跑 V1 → V2 → 本檔沒有錯誤）
產出：db/seed/R__seed.sql（Flyway repeatable migration，只在本機與展示環境載入）
執行：uv run python db/seed-build/build_seed.py

每個轉換都 assert 次數：來源檔一旦跟預期不同，就停下來，而不是默默產生錯的 seed。
"""
import json
import re
import uuid
from datetime import date, timedelta
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "tripeasy_fakedata.sql"
EXTRA = HERE / "extra_seed.sql"
TARGET = HERE.parent / "seed" / "R__seed.sql"

DATA_MARKER = "/* ------------------ 產生假資料"
INSERT_COUNT = 24  # 來源檔的 INSERT 數；payment 沒有資料列，由 extra_seed.sql 補

# 主鍵一律由「表名 + 自然鍵」決定性地產生 v4 形狀的 id（seed_id）。
# 來源檔的手寫主鍵會在不同表重複使用同一個字面值，所以對照表依「欄位所屬的表」建立
SEED_ID_NAMESPACE = uuid.UUID("6f1c2b8e-0d4a-4c1e-9b7a-3e5f2a1d8c90")
GENERATED_ID = "uuid_generate_v4()"

# 優惠卷代碼要符合 discounts_Validatior.js 的 ^[A-Z0-9]{6}$（契約 §0.1 第 2 項）
COUPON_CODES = {
    "WELCOME100": "WEL100", "SUMMER50": "SUM050", "TRAVEL10P": "TRV010",
    "VIP300": "VIP300", "SPRING20": "SPR020",
}
TRV010_OLD_DESCRIPTION = "'旅遊商品 10% 折扣 (最高折抵 500 元)'"
TRV010_NEW_DESCRIPTION = "'旅遊商品折抵新台幣 10 元'"

# 每位使用者只留 1 個購物車（契約 §0.1 第 7 項）：有項目的、項目多的、total_price 大的
EXPECTED_KEPT_CARTS = {
    "83018530-f182-4734-afc2-cf4ecc96802d",  # alice
    "65d6a65f-bcd8-4970-bf47-e28ae67a1c11",  # bob
    "08b4e271-f584-4297-9441-a299afb81098",  # carol
}

# 契約 §0.1 第 9、10 項：這三張表的來源檔列整批丟掉，改由 extra_seed.sql 重建（P1b 計畫 2026-10-25 controller 裁決）
REBUILT_TABLES = {"orders": 5, "order_item": 10, "point_record": 2}
REBUILT_FINAL_COUNTS = {"orders": 20, "order_item": 20, "point_record": 18}  # 契約 §0.1 第 1 項
PAYMENT_HEADING = '---- 19. 付款紀錄資料 "payment"'

# 以下的舊 id 都是來源檔的手寫主鍵
ALICE, BOB, CAROL = "alice@example.com", "bob@example.com", "carol@example.com"
# 契約 §0.1 第 6 項：(行程 title) → 促銷期間（相對載入日的天數）。來源檔的兩筆促銷日期要改成期間內
SOURCE_PROMOS = {"北海道雪景 5 日深度遊": (-10, 20), "馬爾地夫蜜月天堂 6 日": (-5, 25)}
# 第 7 項：保留的 cart_item（來源檔 id）→ (start_date, end_date) 相對載入日的天數；end 為 None 表示不改
CART_ITEM_DATES = {
    "53f15e11-2350-4d9d-ade4-f4483af848da": (30, None),  # alice 大阪美食自由行，原本 end_date 是 NULL
    "c5cefe38-ff77-497c-b3fb-2831bbfb898c": (14, None),  # bob 高雄夜市美食攻略，原本 end_date 是 NULL
    "ecc926ca-d9f6-422f-8366-5d273236051b": (20, 21),    # carol 巴黎歷史建築巡禮
}
# 第 8 項：來源檔 7 筆收藏的 created_at（載入時間減幾天）
FAVORITE_DAYS_AGO = {
    (ALICE, "紐西蘭壯麗景觀自駕遊"): 10, (ALICE, "馬爾地夫蜜月天堂 6 日"): 7, (ALICE, "大阪美食自由行"): 3,
    (BOB, "北海道雪景 5 日深度遊"): 9, (BOB, "巴黎歷史建築巡禮"): 5,
    (CAROL, "馬爾地夫蜜月天堂 6 日"): 8, (CAROL, "曼谷設計旅店探索"): 4,
}
# 第 11 項：來源檔 2 則 web 評論的 created_at
WEB_REVIEW_DAYS_AGO = {ALICE: 5, BOB: 4}
# 第 9 項最後一段：user_coupon（來源檔 id）→ extra_seed.sql 的訂單佔位 id（訂單 #2、#6、#4）
USER_COUPON_ORDERS = {
    "6f610e1c-51cf-4709-b8e2-5b8b96751100": "extra-order-02",  # bob TRV010
    "870df12e-1ec6-49da-8f91-3ffefb4ca8b0": "extra-order-06",  # bob VIP300
    "4b202c03-9bde-4c8c-9c03-f23aac550c03": "extra-order-04",  # alice VIP300
}

# 明文 Tripeasy123（寫在 .env.example 的註解）。bcrypt cost 10，跟 backend 註冊時相同
SEED_PASSWORD_HASH = "$2b$10$9Bd0v0X7eLfhzEL5BC8pROe7OWUfOq4rFDMi.8K/Gg7prMuyn8OKi"
FAKE_HASHES = (
    "$2b$10$abcd1234abcd1234abcd12",
    "$2b$10$efgh5678efgh5678efgh56",
    "$2b$10$ijkl9012ijkl9012ijkl90",
)

# fakedata 的資料大約建立在 2025-05-20。所有日期平移成「以今天為基準」，
# 讓行程、優惠券在 seed 載入的那一天都還在未來
DATE_ANCHOR = "2025-05-20"
DATE_LITERAL = re.compile(r"'(\d{4}-\d{2}-\d{2}(?: \d{2}:\d{2}:\d{2})?)'")
DATE_COUNT = 75  # 來源檔 53 個，扣掉被移除的購物車項目 8 個、重建的 order_item 18 個，加上 extra_seed.sql 的 48 個

IMAGE_BASE = "http://localhost:3000/uploads/seed"
IMAGE_URL = re.compile(r"'https://example\.com/(images|avatar|badges|feature|hidden)/[^']*'")
IMAGE_FILE = {"images": "tour", "feature": "feature", "hidden": "hidden", "badges": "badge", "avatar": "avatar"}
IMAGE_COUNT = 241  # 來源檔 103 個，加上 extra_seed.sql 的 138 個

HEADER = """\
-- 本檔由 db/seed-build/build_seed.py 產生，請勿手動修改；要改請改腳本後重新產生。
-- 來源：db/seed-build/tripeasy_fakedata.sql、db/seed-build/extra_seed.sql
-- 只在本機與展示環境載入（compose 的 Flyway -locations 加上 db/seed），正式環境不載入。
-- 每個 INSERT 都是 ON CONFLICT DO NOTHING：重跑時既有的資料不會被更新。
-- 改了既有資料列的內容，要 docker compose down -v 重建 DB 才看得到。
-- 主鍵由自然鍵決定；改了主鍵或自然鍵，保留舊 volume 重跑會讓資料重複，要 docker compose down -v。
-- 日期以 seed 載入那天為基準（CURRENT_DATE 在載入時計算一次）；volume 保留太久，行程和優惠券會漸漸過期，要 down -v 重建。

"""


def drop_delete_block(text: str) -> str:
    _, marker, data = text.partition(DATA_MARKER)
    assert marker, "找不到「產生假資料」區段"
    return marker + data


@dataclass
class Insert:
    table: str  # 來源檔的原樣寫法，例如 '"user"'、'cart_item'
    columns: list[str]
    rows: list[list[str]]  # 每個值是原樣的 SQL 字面值或運算式
    heading: str = ""  # 來源檔 INSERT 前面的區段標題註解（---- N. ...）


INSERT_HEAD = re.compile(r'INSERT\s+INTO\s+("[^"]+"|\w+)\s*\(', re.I)
HEADING = re.compile(r"^-{4,5} .*$", re.M)


def _skip_ws_comments(sql: str, i: int) -> int:
    while i < len(sql):
        if sql[i].isspace():
            i += 1
        elif sql.startswith("--", i):
            while i < len(sql) and sql[i] != "\n":
                i += 1
        else:
            break
    return i


def _read_group(sql: str, i: int) -> tuple[list[str], int]:
    """sql[i] 是 '('：讀到對應的 ')'，回傳頂層以逗號分隔的各段（已 strip）與 ')' 之後的位置。"""
    assert sql[i] == "("
    i += 1
    depth, in_quote = 0, False
    parts, buf = [], []
    while i < len(sql):
        c = sql[i]
        if in_quote:
            buf.append(c)
            if c == "'":
                if sql.startswith("''", i):
                    buf.append("'")
                    i += 1
                else:
                    in_quote = False
        elif c == "'":
            in_quote = True
            buf.append(c)
        elif sql.startswith("--", i):
            while i < len(sql) and sql[i] != "\n":
                i += 1
            continue
        elif c == "(":
            depth += 1
            buf.append(c)
        elif c == ")":
            if depth == 0:
                parts.append("".join(buf).strip())
                return parts, i + 1
            depth -= 1
            buf.append(c)
        elif c == "," and depth == 0:
            parts.append("".join(buf).strip())
            buf = []
        else:
            buf.append(c)
        i += 1
    raise AssertionError("括號沒有成對")


def parse_inserts(sql: str) -> list[Insert]:
    inserts, pos = [], 0
    while (m := INSERT_HEAD.search(sql, pos)):
        headings = HEADING.findall(sql[pos:m.start()])
        columns, i = _read_group(sql, m.end() - 1)
        i = _skip_ws_comments(sql, i)
        assert sql[i:i + 6].upper() == "VALUES", f"{m.group(1)} 後面不是 VALUES"
        i = _skip_ws_comments(sql, i + 6)
        rows = []
        while True:
            row, i = _read_group(sql, i)
            assert len(row) == len(columns), f"{m.group(1)}：{len(row)} 個值，{len(columns)} 個欄位"
            rows.append(row)
            i = _skip_ws_comments(sql, i)
            if sql[i] == ",":
                i = _skip_ws_comments(sql, i + 1)
            else:
                assert sql[i] == ";", f"{m.group(1)}：預期 , 或 ;"
                i += 1
                break
        inserts.append(Insert(m.group(1), columns, rows, headings[-1] if headings else ""))
        pos = i
    return inserts


def emit(inserts: list[Insert]) -> str:
    blocks = []
    for ins in inserts:
        lines = [ins.heading] if ins.heading else []
        lines.append(f"INSERT INTO {ins.table} ({', '.join(ins.columns)}) VALUES")
        lines.append(",\n".join(f"({', '.join(row)})" for row in ins.rows))
        lines.append("ON CONFLICT DO NOTHING;")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks) + "\n"


def seed_id(table: str, key: str) -> str:
    """uuid5(namespace, 'table:key') 的位元組，版本位設成 4、variant 設成 10xx（v4 專用驗證器才收）。"""
    b = bytearray(uuid.uuid5(SEED_ID_NAMESPACE, f"{table}:{key}").bytes)
    b[6] = (b[6] & 0x0F) | 0x40
    b[8] = (b[8] & 0x3F) | 0x80
    return str(uuid.UUID(bytes=bytes(b)))


def bare(table: str) -> str:
    return table.strip('"')


def unquote(literal: str) -> str:
    """'it''s' -> it's；NULL -> 空字串。"""
    if literal == "NULL":
        return ""
    assert literal.startswith("'") and literal.endswith("'"), literal
    return literal[1:-1].replace("''", "'")


def quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


# 表 → 主鍵欄位（取自 V1）。外鍵欄位的名稱跟被參照的主鍵欄位相同
PK_COLUMN = {
    "user": "user_id", "socialLogin": "login_id", "user_level": "level_id",
    "coupon": "coupon_id", "tour": "tour_id", "tour_detail": "tour_detail_id",
    "restaurant": "restaurant_id", "restaurant_business": "restaurant_business_id",
    "restaurant_menu": "restaurant_menu_id", "hotel": "hotel_id",
    "hotel_room": "hotel_room_id", "notification": "notification_id",
    "country": "country_id", "region": "region_id", "cart": "cart_id",
    "cart_item": "cart_item_id", "orders": "order_id", "order_item": "order_item_id",
    "payment": "payment_id", "review": "review_id", "hidden_play": "hidden_play_id",
    "auto_setting": "auto_setting_id", "favorite": "favorite_id",
    "point_record": "point_id", "user_coupon": "user_coupon_id",
}
PK_OWNER = {col: table for table, col in PK_COLUMN.items()}
assert len(PK_OWNER) == len(PK_COLUMN)

# 表 → 從一列取出自然鍵。row 是 {欄位: 去引號的值}，另外附上 user_email / tour_title / country_name，
# 以及（有 order_id 的表）order_email / order_title：該訂單的使用者 email 與行程 title
# 沒列在這裡的表，主鍵是手寫字面值，就用舊主鍵當 key
# 形狀見契約 §0.1：orders / order_item / favorite / payment 是 {email}:{title}，point_record 再加 :{type}，
# notification 是 {title}:{type}
NATURAL_KEY: dict[str, Callable[[dict], str]] = {
    "user": lambda r: r["email"],
    "coupon": lambda r: r["code"],
    "tour": lambda r: r["title"],
    "country": lambda r: r["name"],
    "region": lambda r: f"{r['country_name']}/{r['name']}",
    # 以下的來源檔主鍵是 uuid_generate_v4()：取最小的唯一欄位組合
    # web 評論沒有行程：同一位使用者可以有好幾則，所以再加內文
    "review": lambda r: f"{r['user_email']}:{r['tour_title']}:{r['type']}" + (f":{r['content']}" if not r["tour_title"] else ""),
    "hidden_play": lambda r: f"{r['user_email']}:{r['tour_title']}",
    "favorite": lambda r: f"{r['user_email']}:{r['tour_title']}",
    "notification": lambda r: f"{r['tour_title']}:{r['type']}",
    # 訂單沒有行程欄位：一張訂單只有 1 個項目，行程取自它的 order_item（remap_ids 會附上 order_title）
    "orders": lambda r: f"{r['user_email']}:{r['order_title']}",
    "order_item": lambda r: f"{r['order_email']}:{r['order_title']}",
    "payment": lambda r: f"{r['order_email']}:{r['order_title']}",
    "point_record": lambda r: f"{r['order_email']}:{r['order_title']}:{r['type']}",
}
# 自然鍵會用到別張表的自然鍵（名稱、email、訂單的 email 與 title）：被用到的表要先處理
NATURAL_NEEDS = {
    "region": ("country",), "review": ("user", "tour"), "hidden_play": ("user", "tour"),
    "favorite": ("user", "tour"), "notification": ("tour",), "orders": ("user", "tour"),
    "order_item": ("orders",), "payment": ("orders",), "point_record": ("orders",),
}
NATURAL_FIRST = ("user", "tour", "country", "orders")
# 其餘的表依檔案順序處理；order_item / payment / point_record 要排在 orders 之後（上面已先處理 orders）


def remap_ids(inserts: list[Insert]) -> list[Insert]:
    by_table = {bare(ins.table): ins for ins in inserts}
    assert len(by_table) == len(inserts), "同一張表出現兩個 INSERT"
    old_to_new: dict[str, dict[str, str]] = defaultdict(dict)
    new_ids: dict[str, list[str]] = {}  # 表 → 每列的新主鍵（依列順序）
    natural: dict[str, dict[str, str]] = defaultdict(dict)  # 表 → {舊主鍵: 自然欄位值}，給外鍵查詢用
    order_info: dict[str, tuple[str, str]] = {}  # 舊 order_id → (使用者 email, 行程 title)
    order_tour: dict[str, str] = {}  # 舊 order_id → 舊 tour_id（取自 order_item）
    if "order_item" in by_table:
        item = by_table["order_item"]
        oi, ti = item.columns.index("order_id"), item.columns.index("tour_id")
        for row in item.rows:
            assert unquote(row[oi]) not in order_tour, f"訂單 {row[oi]} 有多個項目：自然鍵 {{email}}:{{title}} 不成立"
            order_tour[unquote(row[oi])] = unquote(row[ti])

    def row_dict(ins: Insert, row: list[str]) -> dict:
        r = {c: unquote(v) if v.startswith("'") or v == "NULL" else v for c, v in zip(ins.columns, row)}
        table = bare(ins.table)
        if "user_id" in r and table != "user":
            assert r["user_id"] in natural["user"], f"{table}.user_id = {r['user_id']} 在 user 找不到"
            r["user_email"] = natural["user"][r["user_id"]]
        if "tour_id" in r and table != "tour":
            assert r["tour_id"] == "" or r["tour_id"] in natural["tour"], \
                f"{table}.tour_id = {r['tour_id']} 在 tour 找不到"
            r["tour_title"] = natural["tour"].get(r["tour_id"], "")
        if "country_id" in r and table != "country":
            assert r["country_id"] in natural["country"], f"{table}.country_id = {r['country_id']} 在 country 找不到"
            r["country_name"] = natural["country"][r["country_id"]]
        if table == "orders":
            old_tour = order_tour.get(r["order_id"])
            assert old_tour in natural["tour"], f"訂單 {r['order_id']} 沒有項目，或項目的行程 {old_tour} 在 tour 找不到"
            r["order_title"] = natural["tour"][old_tour]
        elif r.get("order_id"):
            assert r["order_id"] in order_info, f"{table}.order_id = {r['order_id']} 在 orders 找不到"
            r["order_email"], r["order_title"] = order_info[r["order_id"]]
        return r

    order = list(NATURAL_FIRST) + [t for t in by_table if t not in NATURAL_FIRST]
    done: set[str] = set()
    for table in order:
        if table not in by_table:
            continue
        assert all(n in done or n not in by_table for n in NATURAL_NEEDS.get(table, ())), \
            f"{table} 的自然鍵要先有 {NATURAL_NEEDS[table]}：調整 NATURAL_FIRST"
        done.add(table)
        ins, pk = by_table[table], PK_COLUMN[table]
        pk_idx = ins.columns.index(pk)
        keys, ids = [], []
        for row in ins.rows:
            old = row[pk_idx]
            if table in NATURAL_KEY:
                key = NATURAL_KEY[table](row_dict(ins, row))
            else:
                assert old != GENERATED_ID, f"{table}：主鍵是 {GENERATED_ID}，要在 NATURAL_KEY 補自然鍵"
                key = unquote(old)
            keys.append(key)
            ids.append(seed_id(table, key))
        assert len(set(keys)) == len(keys), f"{table} 的自然鍵有重複"
        new_ids[table] = ids
        for row, new in zip(ins.rows, ids):
            old = row[pk_idx]
            if old != GENERATED_ID:
                assert unquote(old) not in old_to_new[table], f"{table} 的舊主鍵 {old} 重複"
                old_to_new[table][unquote(old)] = new
        if table == "orders":
            for row, key in zip(ins.rows, keys):
                email, title = key.split(":", 1)
                order_info[unquote(row[pk_idx])] = (email, title)
        natural_col = {"user": "email", "tour": "title", "country": "name"}.get(table)
        if natural_col:
            nc = ins.columns.index(natural_col)
            for row in ins.rows:
                natural[table][unquote(row[pk_idx])] = unquote(row[nc])

    out = []
    for ins in inserts:
        table = bare(ins.table)
        rows = []
        for n, row in enumerate(ins.rows):
            row = list(row)
            for j, col in enumerate(ins.columns):
                owner = PK_OWNER.get(col)
                if owner is None:
                    continue
                if col == PK_COLUMN[table]:
                    row[j] = quote(new_ids[table][n])
                elif row[j] != "NULL":
                    old = unquote(row[j])
                    assert old in old_to_new[owner], f"{table}.{col} = {old} 在 {owner} 找不到"
                    row[j] = quote(old_to_new[owner][old])
            rows.append(row)
        out.append(Insert(ins.table, ins.columns, rows, ins.heading))
    return out


def _col(ins: Insert, name: str) -> int:
    return ins.columns.index(name)


def rewrite_coupons(by_table: dict[str, Insert]) -> None:
    ins = by_table["coupon"]
    code, desc = _col(ins, "code"), _col(ins, "description")
    for row in ins.rows:
        old = unquote(row[code])
        assert old in COUPON_CODES, f"未預期的優惠卷代碼 {old}"
        row[code] = quote(COUPON_CODES[old])
        if old == "TRAVEL10P":
            assert row[desc] == TRV010_OLD_DESCRIPTION, row[desc]
            row[desc] = TRV010_NEW_DESCRIPTION
    assert len(ins.rows) == len(COUPON_CODES)


def keep_one_cart_per_user(by_table: dict[str, Insert]) -> None:
    cart, item = by_table["cart"], by_table["cart_item"]
    cid, uid, total = _col(cart, "cart_id"), _col(cart, "user_id"), _col(cart, "total_price")
    item_cart = _col(item, "cart_id")
    counts = defaultdict(int)
    for row in item.rows:
        counts[unquote(row[item_cart])] += 1
    best: dict[str, list[str]] = {}
    for row in cart.rows:
        rank = (counts[unquote(row[cid])], float(row[total]))
        user = unquote(row[uid])
        if user not in best or rank > (counts[unquote(best[user][cid])], float(best[user][total])):
            best[user] = row
    kept = {unquote(r[cid]) for r in best.values()}
    assert kept == EXPECTED_KEPT_CARTS, f"保留的購物車 {sorted(kept)}，跟契約不同"
    cart.rows = [r for r in cart.rows if unquote(r[cid]) in kept]
    item.rows = [r for r in item.rows if unquote(r[item_cart]) in kept]
    assert (len(cart.rows), len(item.rows)) == (3, 6), (len(cart.rows), len(item.rows))


def merge_duplicate_auto_settings(by_table: dict[str, Insert]) -> None:
    """同一 user_id 多列時併成一列（P5 R1、F10）：每個欄位取 updated_at 較新那列的值；
    updated_at 相同、或有一邊不是可比較的字面值（例如 CURRENT_TIMESTAMP）時，取 auto_setting_id 較小那列。"""
    ins = by_table["auto_setting"]
    idx, uid, upd = _col(ins, "auto_setting_id"), _col(ins, "user_id"), _col(ins, "updated_at")
    groups: dict[str, list[list[str]]] = {}
    for row in ins.rows:
        groups.setdefault(unquote(row[uid]), []).append(row)

    def pick(rows: list[list[str]]) -> list[str]:
        def newer_key(row):  # 較新者排前面：不可比較的字面值視為同一時間
            return row[upd] if row[upd].startswith("'") else ""
        stamps = {newer_key(r) for r in rows}
        pool = rows
        if len(stamps) > 1 and "" not in stamps:
            latest = max(stamps)
            pool = [r for r in rows if newer_key(r) == latest]
        return min(pool, key=lambda r: unquote(r[idx]))

    merged = []
    for rows in groups.values():
        merged.append(list(pick(rows)) if len(rows) > 1 else rows[0])
    ins.rows = merged
    users = [unquote(r[uid]) for r in ins.rows]
    assert len(users) == len(set(users)), "auto_setting 合併後仍有同一 user_id 多列"


def fix_roles(by_table: dict[str, Insert]) -> None:
    # 程式用 authRole('User') / authRole('admin')，fakedata 寫的是 'user'。只改 user 表的 role 欄
    ins = by_table["user"]
    role, n = _col(ins, "role"), 0
    for row in ins.rows:
        if row[role] == "'user'":
            row[role] = "'User'"
            n += 1
    assert n == 2, f"角色 'user' 有 {n} 個，預期 2"


def anchor_date(days: int, end_of_day: bool = False) -> str:
    """相對載入日的天數 → 以 DATE_ANCHOR 為基準的日期字面值，之後由 shift_dates 平移。"""
    day = date.fromisoformat(DATE_ANCHOR) + timedelta(days=days)
    return quote(f"{day} 23:59:59" if end_of_day else f"{day} 00:00:00")


def anchor_day(days: int) -> str:
    return quote(str(date.fromisoformat(DATE_ANCHOR) + timedelta(days=days)))


def _old_names(by_table: dict[str, Insert]) -> tuple[dict[str, str], dict[str, str]]:
    """來源檔的舊 id → email / title，給逐列改寫用（改寫在 remap_ids 之前）。"""
    user, tour = by_table["user"], by_table["tour"]
    emails = {unquote(r[_col(user, "user_id")]): unquote(r[_col(user, "email")]) for r in user.rows}
    titles = {unquote(r[_col(tour, "tour_id")]): unquote(r[_col(tour, "title")]) for r in tour.rows}
    return emails, titles


def rewrite_promotions(by_table: dict[str, Insert]) -> None:
    """來源檔 2 筆促銷的日期改成載入日在期間內（契約 §0.1 第 6 項）。"""
    ins = by_table["notification"]
    _, titles = _old_names(by_table)
    tour, kind = _col(ins, "tour_id"), _col(ins, "type")
    start, end = _col(ins, "start_date"), _col(ins, "end_date")
    hits = 0
    for row in ins.rows:
        if unquote(row[kind]) != "促銷":
            continue
        title = titles.get(unquote(row[tour]))
        assert title in SOURCE_PROMOS, f"來源檔有預期之外的促銷：{title}"
        s_off, e_off = SOURCE_PROMOS[title]
        row[start], row[end] = anchor_date(s_off), anchor_date(e_off, True)
        hits += 1
    assert hits == len(SOURCE_PROMOS), f"促銷 {hits} 筆，預期 {len(SOURCE_PROMOS)}"


def rewrite_cart_item_dates(by_table: dict[str, Insert]) -> None:
    """保留的購物車項目：早於載入日的 start_date 移到未來（契約 §0.1 第 7 項）。"""
    ins = by_table["cart_item"]
    pk, start, end = _col(ins, "cart_item_id"), _col(ins, "start_date"), _col(ins, "end_date")
    hits = 0
    for row in ins.rows:
        target = CART_ITEM_DATES.get(unquote(row[pk]))
        if target is None:
            continue
        row[start] = anchor_day(target[0])
        if target[1] is not None:
            row[end] = anchor_day(target[1])
        else:
            assert row[end] == "NULL", row[end]
        hits += 1
    assert hits == len(CART_ITEM_DATES), f"cart_item {hits} 筆，預期 {len(CART_ITEM_DATES)}"


def _days_ago(days: int) -> str:
    return f"CURRENT_TIMESTAMP - INTERVAL '{days} days'"


def rewrite_favorite_times(by_table: dict[str, Insert]) -> None:
    """來源檔 7 筆收藏原本同一個 CURRENT_TIMESTAMP：改成各不相同的「載入時間減 N 天」（第 8 項）。"""
    ins = by_table["favorite"]
    emails, titles = _old_names(by_table)
    user, tour = _col(ins, "user_id"), _col(ins, "tour_id")
    created, updated = _col(ins, "created_at"), _col(ins, "updated_at")
    hits = 0
    for row in ins.rows:
        key = (emails.get(unquote(row[user])), titles.get(unquote(row[tour])))
        assert key in FAVORITE_DAYS_AGO, f"來源檔有預期之外的收藏：{key}"
        days = FAVORITE_DAYS_AGO[key]
        row[created] = row[updated] = _days_ago(days)
        hits += 1
    assert hits == len(FAVORITE_DAYS_AGO), f"favorite {hits} 筆，預期 {len(FAVORITE_DAYS_AGO)}"


def rewrite_web_review_times(by_table: dict[str, Insert]) -> None:
    """來源檔 2 則 web 評論的 created_at（第 11 項）；首頁以評論時間排序，所以 5 則要各不相同。"""
    ins = by_table["review"]
    emails, _ = _old_names(by_table)
    user, kind = _col(ins, "user_id"), _col(ins, "type")
    created, updated = _col(ins, "created_at"), _col(ins, "updated_at")
    hits = 0
    for row in ins.rows:
        if unquote(row[kind]) == "web":
            email = emails.get(unquote(row[user]))
            assert email in WEB_REVIEW_DAYS_AGO, f"來源檔有預期之外的 web 評論：{email}"
            row[created] = row[updated] = _days_ago(WEB_REVIEW_DAYS_AGO[email])
            hits += 1
    assert hits == len(WEB_REVIEW_DAYS_AGO), f"web 評論 {hits} 則，預期 {len(WEB_REVIEW_DAYS_AGO)}"


def rewrite_user_coupon_orders(by_table: dict[str, Insert]) -> None:
    """user_coupon 指向重建後的訂單（第 9 項最後一段）；carol 沒用過的那張維持 NULL。"""
    ins = by_table["user_coupon"]
    pk, order = _col(ins, "user_coupon_id"), _col(ins, "order_id")
    hits = 0
    for row in ins.rows:
        target = USER_COUPON_ORDERS.get(unquote(row[pk]))
        if target is None:
            assert row[order] == "NULL", row[order]
            continue
        row[order] = quote(target)
        hits += 1
    assert hits == len(USER_COUPON_ORDERS), f"user_coupon {hits} 筆，預期 {len(USER_COUPON_ORDERS)}"


def merge_extra(inserts: list[Insert], extra: list[Insert]) -> list[Insert]:
    """丟掉要重建的來源檔列，再把 extra_seed.sql 的列併到同名的表；來源檔沒有的表（payment）接在 order_item 後面。"""
    by_table = {bare(i.table): i for i in inserts}
    for table, expected in REBUILT_TABLES.items():
        n = len(by_table[table].rows)
        assert n == expected, f"{table} 來源檔 {n} 列，預期 {expected}"
        by_table[table].rows = []
    out = list(inserts)
    for ins in extra:
        table = bare(ins.table)
        if table in by_table:
            target = by_table[table]
            assert target.columns == ins.columns or table in REBUILT_TABLES, f"{table} 的欄位跟來源檔不同"
            target.columns = ins.columns
            target.rows += ins.rows
        else:
            assert table == "payment", f"extra_seed.sql 的 {table} 在來源檔沒有"
            ins.heading = PAYMENT_HEADING
            out.insert(out.index(by_table["order_item"]) + 1, ins)
    for table, expected in REBUILT_FINAL_COUNTS.items():
        n = len(by_table[table].rows)
        assert n == expected, f"{table} 重建後 {n} 列，預期 {expected}：檢查 extra_seed.sql"
    return out


def fill_payment_return_data(inserts: list[Insert]) -> None:
    """return_data 內含該訂單的 order_id（契約 §0.1 第 9 項），要等 id 換完才寫得出來。"""
    ins = next(i for i in inserts if bare(i.table) == "payment")
    order, method, data = _col(ins, "order_id"), _col(ins, "payment_method"), _col(ins, "return_data")
    for row in ins.rows:
        assert row[data] == "NULL", row[data]
        body = {"Status": "SUCCESS", "Result": {
            "MerchantOrderNo": unquote(row[order]), "PaymentType": unquote(row[method]), "Message": "付款成功",
        }}
        row[data] = quote(json.dumps(body, ensure_ascii=False, separators=(",", ":")))
    assert len(ins.rows) == 15, len(ins.rows)


def fix_password_hashes(text: str) -> str:
    for fake in FAKE_HASHES:
        assert text.count(f"'{fake}'") == 1, fake
        text = text.replace(f"'{fake}'", f"'{SEED_PASSWORD_HASH}'")
    return text


def shift_dates(text: str) -> str:
    text, n = DATE_LITERAL.subn(
        lambda m: f"(TIMESTAMP '{m.group(1)}' + (CURRENT_DATE - DATE '{DATE_ANCHOR}') * INTERVAL '1 day')",
        text,
    )
    assert n == DATE_COUNT, f"日期 {n} 個，預期 {DATE_COUNT}"
    return text


def use_local_images(text: str) -> str:
    text, n = IMAGE_URL.subn(lambda m: f"'{IMAGE_BASE}/{IMAGE_FILE[m.group(1)]}.svg'", text)
    assert n == IMAGE_COUNT, f"圖片網址 {n} 個，預期 {IMAGE_COUNT}"
    return text


def build(text: str, extra_text: str) -> str:
    text = text.replace("\r\n", "\n")
    text = drop_delete_block(text)
    inserts = parse_inserts(text)
    assert len(inserts) == INSERT_COUNT, f"INSERT 數量 {len(inserts)}，預期 {INSERT_COUNT}"
    by_table = {bare(i.table): i for i in inserts}
    # 對來源檔既有列的逐列改寫（用舊 id 找列，所以要在併入 extra_seed.sql 之前）
    rewrite_coupons(by_table)
    keep_one_cart_per_user(by_table)
    fix_roles(by_table)
    merge_duplicate_auto_settings(by_table)
    rewrite_promotions(by_table)
    rewrite_cart_item_dates(by_table)
    rewrite_favorite_times(by_table)
    rewrite_web_review_times(by_table)
    rewrite_user_coupon_orders(by_table)
    extra = parse_inserts(extra_text.replace("\r\n", "\n"))
    assert extra, "extra_seed.sql 沒有任何 INSERT"
    inserts = remap_ids(merge_extra(inserts, extra))
    fill_payment_return_data(inserts)
    text = emit(inserts)
    assert GENERATED_ID not in text, f"{GENERATED_ID} 沒有被換掉"
    text = fix_password_hashes(text)
    text = shift_dates(text)
    text = use_local_images(text)
    assert "${" not in text, "Flyway 會把 ${...} 當成 placeholder"
    return HEADER + text


if __name__ == "__main__":
    TARGET.write_text(
        build(SOURCE.read_text(encoding="utf-8"), EXTRA.read_text(encoding="utf-8")), encoding="utf-8"
    )
    print(f"wrote {TARGET.relative_to(HERE.parent.parent)}")
