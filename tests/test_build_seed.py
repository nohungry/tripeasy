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


# ---- auto_setting 一人一列（P5 R1、F10） ----

def _auto_rows(text):
    [ins] = [i for i in build_seed.parse_inserts(text) if build_seed.bare(i.table) == "auto_setting"]
    return [dict(zip(ins.columns, (build_seed.unquote(v) for v in row))) for row in ins.rows]


def test_alice_auto_settings_merged():
    text = build_seed.build(
        build_seed.SOURCE.read_text(encoding="utf-8"), build_seed.EXTRA.read_text(encoding="utf-8")
    )
    rows = _auto_rows(text)
    users = [r["user_id"] for r in rows]
    assert len(users) == len(set(users))
    [alice] = [r for r in rows if r["auto_setting_id"] == "1111aaaa-2222-bbbb-3333-cccc4444dddd"]
    assert (alice["early_notify"], alice["flexible_notify"]) == ("0", "1")
    assert (alice["country"], alice["region"], alice["price"]) == ("Japan", "Tokyo", "1200.5")
    assert not [r for r in rows if r["auto_setting_id"] == "4444dddd-5555-eeee-6666-ffff7777aaaa"]


def _fake_auto(rows):
    cols = ["auto_setting_id", "user_id", "early_notify", "flexible_notify", "country", "region", "price", "created_at", "updated_at"]
    return {"auto_setting": build_seed.Insert("auto_setting", cols, rows)}


def _row(i, early, country, updated):
    return [f"'{i}'", "'u1'", early, "0", f"'{country}'", "'R'", "100", "CURRENT_TIMESTAMP", updated]


def test_merge_auto_settings_prefers_newer_updated_at():
    by = _fake_auto([_row("a", "0", "Old", "'2025-01-01 00:00:00'"), _row("b", "1", "New", "'2025-02-01 00:00:00'")])
    build_seed.merge_duplicate_auto_settings(by)
    [row] = by["auto_setting"].rows
    assert row[0] == "'b'" and row[2] == "1" and row[4] == "'New'"


def test_merge_auto_settings_tie_takes_smaller_id():
    by = _fake_auto([_row("b", "1", "Big", "CURRENT_TIMESTAMP"), _row("a", "0", "Small", "CURRENT_TIMESTAMP")])
    build_seed.merge_duplicate_auto_settings(by)
    [row] = by["auto_setting"].rows
    assert row[0] == "'a'" and row[2] == "0" and row[4] == "'Small'"
