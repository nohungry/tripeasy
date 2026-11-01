"""契約 §0、§1–§3：每個物件的識別字、欄位（view）與簽章（function）都要和 docs/db-contract.md 一致。"""
import re

import pytest

from conftest import ROOT
from db_contract import OBJECTS

VIEWS_FUNCTIONS_SQL = ROOT / "backend" / "migrations" / "R__views_functions.sql"

VIEWS = sorted(n for n, o in OBJECTS.items() if o["kind"] == "view")
FUNCTIONS = sorted(n for n, o in OBJECTS.items() if o["kind"] == "function")

_TYPE_ALIASES = {
    "character varying": "varchar",
    "timestamp without time zone": "timestamp",
    "timestamp with time zone": "timestamptz",
    "time without time zone": "time",
}


def normalize_type(s: str) -> str:
    """把 PostgreSQL 的型別名稱換成契約的寫法：去掉 (…) 長度，並套用別名。"""
    base = re.sub(r"\s+", " ", re.sub(r"\([^)]*\)", "", s)).strip()
    return _TYPE_ALIASES.get(base, base)


def test_normalize_type():
    assert normalize_type("character varying(255)") == "varchar"
    assert normalize_type("timestamp without time zone") == "timestamp"
    assert normalize_type("timestamp with time zone") == "timestamptz"
    assert normalize_type("time without time zone") == "time"
    assert normalize_type("numeric(10,2)") == "numeric"
    assert normalize_type("timestamp(3) with time zone") == "timestamptz"
    assert normalize_type("time(0) without time zone") == "time"
    assert normalize_type("double precision") == "double precision"


@pytest.mark.parametrize("name", sorted(OBJECTS))
def test_object_exists_with_exact_identifier(db, name):
    if OBJECTS[name]["kind"] == "view":
        row = db.execute(
            "SELECT relkind FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
            "WHERE n.nspname = 'public' AND c.relname = %s",
            (name,),
        ).fetchone()
        assert row == ("v",), f"public.{name} 不是 view 或不存在"
    else:
        (count,) = db.execute(
            "SELECT count(*) FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace "
            "WHERE n.nspname = 'public' AND p.proname = %s",
            (name,),
        ).fetchone()
        assert count == 1, f"public.{name} 應恰有 1 個 function，實際 {count}"


@pytest.mark.parametrize("name", VIEWS)
def test_view_columns_match_contract(db, name):
    rows = db.execute(
        "SELECT a.attname, format_type(a.atttypid, a.atttypmod) "
        "FROM pg_attribute a JOIN pg_class c ON c.oid = a.attrelid "
        "JOIN pg_namespace n ON n.oid = c.relnamespace "
        "WHERE n.nspname = 'public' AND c.relname = %s AND a.attnum > 0 AND NOT a.attisdropped",
        (name,),
    ).fetchall()
    actual = [(col, normalize_type(typ)) for col, typ in rows]
    expected = OBJECTS[name]["columns"]
    assert len(actual) == len(expected), f"欄位數 {len(actual)} ≠ 契約 {len(expected)}"
    assert set(actual) == set(expected)


@pytest.mark.parametrize("name", FUNCTIONS)
def test_function_signature_matches_contract(db, name):
    def params(mode_sql):
        return db.execute(
            "SELECT p.parameter_name, p.data_type FROM information_schema.parameters p "
            "JOIN information_schema.routines r ON r.specific_name = p.specific_name "
            "AND r.specific_schema = p.specific_schema "
            f"WHERE r.routine_schema = 'public' AND r.routine_name = %s AND {mode_sql} "
            "ORDER BY p.ordinal_position",
            (name,),
        ).fetchall()

    in_types = [normalize_type(t) for _, t in params("p.parameter_mode = 'IN'")]
    assert in_types == [t for _, t in OBJECTS[name]["args"]]

    out = [(n, normalize_type(t)) for n, t in params("p.parameter_mode = 'OUT'")]
    expected = OBJECTS[name]["columns"]
    assert len(out) == len(expected), f"輸出欄位數 {len(out)} ≠ 契約 {len(expected)}"
    assert set(out) == set(expected)


def test_views_functions_file_is_rerunnable(tx):
    """repeatable migration 套用兩次都不能出錯（先 DROP … CASCADE 再 CREATE）。"""
    script = VIEWS_FUNCTIONS_SQL.read_text(encoding="utf-8")
    tx.execute(script)
    tx.execute(script)


def test_contract_lists_all_21_objects():
    kinds = [o["kind"] for o in OBJECTS.values()]
    assert (len(OBJECTS), kinds.count("view"), kinds.count("function")) == (21, 12, 9)
