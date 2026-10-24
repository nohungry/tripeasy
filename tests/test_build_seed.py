"""seed 產生腳本的單元測試：不需要 DB。"""
import re

from conftest import load_build_seed

build_seed = load_build_seed()
V4 = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")


def test_seed_id_is_deterministic_v4():
    a = build_seed.seed_id("tour", "北海道雪景 5 日深度遊")
    assert a == build_seed.seed_id("tour", "北海道雪景 5 日深度遊")
    assert V4.match(a)
    assert a != build_seed.seed_id("coupon", "北海道雪景 5 日深度遊")


def test_parse_inserts_round_trip():
    # 含 '' 跳脫、巢狀括號、VALUES 之間的 -- 註解
    sql = "INSERT INTO \"t\" (a, b) VALUES\n-- note\n('it''s', (1 + 2)),\n(NULL, now());"
    [ins] = build_seed.parse_inserts(sql)
    assert ins.table == '"t"' and ins.columns == ["a", "b"]
    assert ins.rows == [["'it''s'", "(1 + 2)"], ["NULL", "now()"]]


def test_remap_follows_column_owner():
    # 同一個字面值同時是 tour 和 coupon 的主鍵。表名用 parse_inserts 回傳的寫法（有雙引號或沒有）
    same = "'11111111-aaaa-bbbb-cccc-111111111111'"
    inserts = [
        build_seed.Insert('"coupon"', ["coupon_id", "code"], [[same, "'VIP300'"]]),
        build_seed.Insert('"tour"', ["tour_id", "title"], [[same, "'A'"]]),
        build_seed.Insert("cart_item", ["cart_item_id", "tour_id"], [["'x'", same]]),
    ]
    out = {i.table: i for i in build_seed.remap_ids(inserts)}
    assert out["cart_item"].rows[0][1] == f"'{build_seed.seed_id('tour', 'A')}'"
    assert out['"coupon"'].rows[0][0] == f"'{build_seed.seed_id('coupon', 'VIP300')}'"
