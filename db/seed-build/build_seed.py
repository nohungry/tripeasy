"""把團隊留下的 fakedata 轉成可重複執行的 Flyway seed。

來源：db/seed-build/tripeasy_fakedata.sql（2025-05，使用者提供；依序跑 V1 → V2 → 本檔沒有錯誤）
產出：db/seed/R__seed.sql（Flyway repeatable migration，只在本機與展示環境載入）
執行：uv run python db/seed-build/build_seed.py

每個轉換都 assert 次數：來源檔一旦跟預期不同，就停下來，而不是默默產生錯的 seed。
"""
import re
import uuid
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "tripeasy_fakedata.sql"
TARGET = HERE.parent / "seed" / "R__seed.sql"

DATA_MARKER = "/* ------------------ 產生假資料"
INSERT_COUNT = 24

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
DATE_COUNT = 45  # 來源檔 53 個，扣掉被移除的 4 個購物車項目的 8 個

IMAGE_BASE = "http://localhost:3000/uploads/seed"
IMAGE_URL = re.compile(r"'https://example\.com/(images|avatar|badges|feature|hidden)/[^']*'")
IMAGE_FILE = {"images": "tour", "feature": "feature", "hidden": "hidden", "badges": "badge", "avatar": "avatar"}
IMAGE_COUNT = 103

HEADER = """\
-- 本檔由 db/seed-build/build_seed.py 產生，請勿手動修改；要改請改腳本後重新產生。
-- 來源：db/seed-build/tripeasy_fakedata.sql
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

# 表 → 從一列取出自然鍵。row 是 {欄位: 去引號的值}，另外附上 user_email / tour_title / country_name
# 沒列在這裡的表，主鍵是手寫字面值，就用舊主鍵當 key
NATURAL_KEY: dict[str, Callable[[dict], str]] = {
    "user": lambda r: r["email"],
    "coupon": lambda r: r["code"],
    "tour": lambda r: r["title"],
    "country": lambda r: r["name"],
    "region": lambda r: f"{r['country_name']}/{r['name']}",
    # 以下的來源檔主鍵是 uuid_generate_v4()：取最小的唯一欄位組合
    "review": lambda r: f"{r['user_email']}:{r['tour_title']}:{r['type']}",
    "hidden_play": lambda r: f"{r['user_email']}:{r['tour_title']}",
    "favorite": lambda r: f"{r['user_email']}:{r['tour_title']}",
}
# 先處理這幾張：其他表的自然鍵會用到它們的值
NATURAL_FIRST = ("user", "tour", "country")


def remap_ids(inserts: list[Insert]) -> list[Insert]:
    by_table = {bare(ins.table): ins for ins in inserts}
    assert len(by_table) == len(inserts), "同一張表出現兩個 INSERT"
    old_to_new: dict[str, dict[str, str]] = defaultdict(dict)
    new_ids: dict[str, list[str]] = {}  # 表 → 每列的新主鍵（依列順序）
    natural: dict[str, dict[str, str]] = defaultdict(dict)  # 表 → {舊主鍵: 自然欄位值}，給外鍵查詢用

    def row_dict(ins: Insert, row: list[str]) -> dict:
        r = {c: unquote(v) if v.startswith("'") or v == "NULL" else v for c, v in zip(ins.columns, row)}
        if "user_id" in r and bare(ins.table) != "user":
            r["user_email"] = natural["user"][r["user_id"]]
        if "tour_id" in r and bare(ins.table) != "tour":
            r["tour_title"] = natural["tour"].get(r["tour_id"], "")
        if "country_id" in r and bare(ins.table) != "country":
            r["country_name"] = natural["country"][r["country_id"]]
        return r

    order = list(NATURAL_FIRST) + [t for t in by_table if t not in NATURAL_FIRST]
    for table in order:
        if table not in by_table:
            continue
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


def fix_roles(text: str) -> str:
    # 程式用 authRole('User') / authRole('admin')，fakedata 寫的是 'user'
    text, n = re.subn(r"(?<=, )'user'(?=, )", "'User'", text)
    assert n == 2, f"角色 'user' 有 {n} 個，預期 2"
    return text


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


def build(text: str) -> str:
    text = text.replace("\r\n", "\n")
    text = drop_delete_block(text)
    inserts = parse_inserts(text)
    assert len(inserts) == INSERT_COUNT, f"INSERT 數量 {len(inserts)}，預期 {INSERT_COUNT}"
    by_table = {bare(i.table): i for i in inserts}
    rewrite_coupons(by_table)
    keep_one_cart_per_user(by_table)
    text = emit(remap_ids(inserts))
    assert GENERATED_ID not in text, f"{GENERATED_ID} 沒有被換掉"
    text = fix_roles(text)
    text = fix_password_hashes(text)
    text = shift_dates(text)
    text = use_local_images(text)
    assert "${" not in text, "Flyway 會把 ${...} 當成 placeholder"
    return HEADER + text


if __name__ == "__main__":
    TARGET.write_text(build(SOURCE.read_text(encoding="utf-8")), encoding="utf-8")
    print(f"wrote {TARGET.relative_to(HERE.parent.parent)}")
