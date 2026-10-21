"""把團隊留下的 fakedata 轉成可重複執行的 Flyway seed。

來源：db/seed-build/tripeasy_fakedata.sql（2025-05，使用者提供；依序跑 V1 → V2 → 本檔沒有錯誤）
產出：db/seed/R__seed.sql（Flyway repeatable migration，只在本機與展示環境載入）
執行：uv run python db/seed-build/build_seed.py

每個轉換都 assert 次數：來源檔一旦跟預期不同，就停下來，而不是默默產生錯的 seed。
"""
import re
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "tripeasy_fakedata.sql"
TARGET = HERE.parent / "seed" / "R__seed.sql"

DATA_MARKER = "/* ------------------ 產生假資料"
INSERT_COUNT = 24

# review / hidden_play / region / favorite 的主鍵用 uuid_generate_v4() 產生，
# 重跑時每次都是新的值，ON CONFLICT 撞不到 → 資料變兩倍。產生 seed 時換成固定的 uuid
GENERATED_ID = "uuid_generate_v4()"
GENERATED_ID_COUNT = 110
SEED_ID_NAMESPACE = uuid.UUID("6f1c2b8e-0d4a-4c1e-9b7a-3e5f2a1d8c90")

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
DATE_COUNT = 53

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
-- 日期以 seed 載入那天為基準（CURRENT_DATE 在載入時計算一次）；volume 保留太久，行程和優惠券會漸漸過期，要 down -v 重建。

"""


def drop_delete_block(text: str) -> str:
    _, marker, data = text.partition(DATA_MARKER)
    assert marker, "找不到「產生假資料」區段"
    return marker + data


def add_on_conflict(text: str) -> str:
    lines = text.split("\n")
    n = 0
    for i, line in enumerate(lines):
        if line.rstrip().endswith(";"):
            lines[i] = line.rstrip()[:-1] + "\nON CONFLICT DO NOTHING;"
            n += 1
    assert n == INSERT_COUNT, f"INSERT 數量 {n}，預期 {INSERT_COUNT}"
    return "\n".join(lines)


def fix_generated_ids(text: str) -> str:
    # 依出現順序給固定的 uuid5，來源檔不變，產生的 id 就不變
    parts = text.split(GENERATED_ID)
    n = len(parts) - 1
    assert n == GENERATED_ID_COUNT, f"{GENERATED_ID} 有 {n} 個，預期 {GENERATED_ID_COUNT}"
    out = [parts[0]]
    for i, part in enumerate(parts[1:]):
        out.append(f"'{uuid.uuid5(SEED_ID_NAMESPACE, f'seed-row-{i}')}'")
        out.append(part)
    return "".join(out)


def fix_roles(text: str) -> str:
    # 程式用 authRole('User') / authRole('admin')，fakedata 寫的是 'user'
    text, n = re.subn(r"^(\s*)'user',(\s*)$", r"\1'User',\2", text, flags=re.M)
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
    text = add_on_conflict(text)
    text = fix_generated_ids(text)
    text = fix_roles(text)
    text = fix_password_hashes(text)
    text = shift_dates(text)
    text = use_local_images(text)
    assert "${" not in text, "Flyway 會把 ${...} 當成 placeholder"
    return HEADER + text


if __name__ == "__main__":
    TARGET.write_text(build(SOURCE.read_text(encoding="utf-8")), encoding="utf-8")
    print(f"wrote {TARGET.relative_to(HERE.parent.parent)}")
