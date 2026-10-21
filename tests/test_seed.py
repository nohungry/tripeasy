"""spec 3.2：fakedata 改寫成 Flyway repeatable migration，可以重複執行。"""
from conftest import ROOT

SEED = ROOT / "db" / "seed" / "R__seed.sql"

# fakedata（2025-05）每張表的筆數。測試可能另外新增資料，所以檢查「至少」
SEED_COUNTS = {
    "user": 3, "socialLogin": 3, "user_level": 3, "coupon": 5,
    "tour": 10, "tour_detail": 6, "restaurant": 2, "restaurant_business": 14,
    "restaurant_menu": 6, "hotel": 2, "hotel_room": 4, "notification": 4,
    "country": 37, "region": 87, "cart": 6, "cart_item": 10,
    "orders": 5, "order_item": 10, "review": 10, "hidden_play": 6,
    "auto_setting": 4, "favorite": 7, "point_record": 2, "user_coupon": 4,
}


def _counts(conn) -> dict:
    return {
        t: conn.execute(f'SELECT count(*) FROM "{t}"').fetchone()[0] for t in SEED_COUNTS
    }


def test_flyway_applied_seed(db):
    row = db.execute(
        "SELECT success FROM flyway_schema_history "
        "WHERE script = 'R__seed.sql' ORDER BY installed_rank DESC LIMIT 1"
    ).fetchone()
    assert row == (True,)


def test_seed_loaded_every_table(db):
    counts = _counts(db)
    short = {t: (counts[t], n) for t, n in SEED_COUNTS.items() if counts[t] < n}
    assert not short, f"（實際, 預期至少）：{short}"


def test_seed_is_rerunnable(tx):
    # 模擬「volume 還在、seed 內容改過」：Flyway 會把整份 seed 再跑一次
    before = _counts(tx)
    tx.execute(SEED.read_text(encoding="utf-8"))
    assert _counts(tx) == before
