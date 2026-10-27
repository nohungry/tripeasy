"""seed 產生腳本的單元測試：不需要 DB。"""
import re

import pytest

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


def test_emit_round_trip():
    sql = (
        '---- 1. t\nINSERT INTO "t" (a, b) VALUES\n'
        "('it''s', (1 + 2)),\n(NULL, now());\n"
    )
    [ins] = build_seed.parse_inserts(sql)
    assert ins.heading == "---- 1. t"
    out = build_seed.emit([ins])
    assert out.startswith("---- 1. t\n") and out.rstrip().endswith("ON CONFLICT DO NOTHING;")
    # emit 加了 ON CONFLICT；parse_inserts 讀的是來源檔寫法，所以還原成 ; 再讀
    [again] = build_seed.parse_inserts(out.replace("\nON CONFLICT DO NOTHING;", ";"))
    assert (again.table, again.columns, again.rows, again.heading) == (
        ins.table, ins.columns, ins.rows, ins.heading,
    )


def test_remap_asserts_when_foreign_key_has_no_mapping():
    inserts = [
        build_seed.Insert('"tour"', ["tour_id", "title"], [["'t1'", "'A'"]]),
        build_seed.Insert("cart_item", ["cart_item_id", "tour_id"], [["'x'", "'no-such-tour'"]]),
    ]
    with pytest.raises(AssertionError, match="no-such-tour"):
        build_seed.remap_ids(inserts)


def test_remap_keeps_null_foreign_keys():
    inserts = [
        build_seed.Insert('"tour"', ["tour_id", "title"], [["'t1'", "'A'"]]),
        build_seed.Insert("cart_item", ["cart_item_id", "tour_id"], [["'x'", "NULL"]]),
    ]
    out = {i.table: i for i in build_seed.remap_ids(inserts)}
    assert out["cart_item"].rows[0][1] == "NULL"


def test_remap_asserts_on_unknown_user_with_message():
    # review 的自然鍵要用 user 的 email；user_id 不存在時要有可讀的訊息，不是裸 KeyError
    inserts = [
        build_seed.Insert('"user"', ["user_id", "email"], [["'u1'", "'a@x'"]]),
        build_seed.Insert(
            '"review"', ["review_id", "user_id", "tour_id", "type"],
            [["uuid_generate_v4()", "'ghost'", "NULL", "'web'"]],
        ),
    ]
    with pytest.raises(AssertionError, match="ghost"):
        build_seed.remap_ids(inserts)
