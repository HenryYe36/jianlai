#!/usr/bin/env python3
"""校验 character_memory yaml 的格式与版权红线。

用法:
  python3 scripts/validate_memory.py path/to/character_memory.yaml [...]

校验项:
  1. 顶层结构: character (str), events (list)
  2. 每个 event 的必填字段: id, chapter, chapter_title, motive_in_my_words
  3. 每个 event 的字段类型与最大长度
  4. **版权红线**:
     - motive_in_my_words 单条 ≤ 280 字 (避免变成情节复述)
     - 整个 yaml 中所有引号「」直引段加起来 ≤ 30 处
     - 单条「」直引 ≤ 15 字
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("需要 pyyaml: pip install pyyaml")


REQUIRED_EVENT_FIELDS = ["id", "chapter", "chapter_title", "motive_in_my_words"]
OPTIONAL_EVENT_FIELDS = [
    "name_zh", "when_short", "co_present", "related_models",
    "fine_grain_hint", "tags",
]
ALL_FIELDS = set(REQUIRED_EVENT_FIELDS) | set(OPTIONAL_EVENT_FIELDS)

MAX_MOTIVE_LEN = 280
MAX_QUOTE_LEN = 15
MAX_QUOTES_PER_FILE = 30

QUOTE_RE = re.compile(r"「([^」]*)」")


def validate_file(path: Path) -> list[str]:
    errors: list[str] = []
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        return [f"yaml 解析失败: {e}"]

    if not isinstance(data, dict):
        return ["顶层必须是 dict"]
    if "character" not in data or not isinstance(data["character"], str):
        errors.append("缺少 character (str) 字段")
    if "events" not in data or not isinstance(data["events"], list):
        return errors + ["缺少 events (list) 字段"]

    seen_ids: set[str] = set()
    total_quotes = 0

    for i, ev in enumerate(data["events"]):
        ctx = f"events[{i}]"
        if not isinstance(ev, dict):
            errors.append(f"{ctx}: 必须是 dict")
            continue

        for f in REQUIRED_EVENT_FIELDS:
            if f not in ev:
                errors.append(f"{ctx}: 缺少必填字段 '{f}'")

        for f in ev:
            if f not in ALL_FIELDS:
                errors.append(f"{ctx}: 未知字段 '{f}' (允许: {sorted(ALL_FIELDS)})")

        eid = ev.get("id")
        if eid in seen_ids:
            errors.append(f"{ctx}: 重复的 id '{eid}'")
        if eid:
            seen_ids.add(eid)

        chap = ev.get("chapter")
        if chap and not (isinstance(chap, str) and re.fullmatch(r"\d{4}", chap)):
            errors.append(f"{ctx}: chapter 必须是 4 位数字字符串 (得到 {chap!r})")

        co = ev.get("co_present", [])
        if co and not isinstance(co, list):
            errors.append(f"{ctx}: co_present 必须是 list")

        rm = ev.get("related_models", [])
        if rm and not isinstance(rm, list):
            errors.append(f"{ctx}: related_models 必须是 list")

        # 版权红线
        motive = ev.get("motive_in_my_words", "")
        if motive and len(motive) > MAX_MOTIVE_LEN:
            errors.append(
                f"{ctx}: motive_in_my_words 长度 {len(motive)} > {MAX_MOTIVE_LEN}; "
                f"避免变成情节复述, 写动机/解读"
            )

        # 全文 「」 引号检查
        for field_name in ["motive_in_my_words", "fine_grain_hint", "when_short"]:
            text = ev.get(field_name, "") or ""
            for q in QUOTE_RE.findall(text):
                total_quotes += 1
                if len(q) > MAX_QUOTE_LEN:
                    errors.append(
                        f"{ctx}.{field_name}: 单条「」直引 {len(q)} 字 > {MAX_QUOTE_LEN}; "
                        f"原文短引须控制在 {MAX_QUOTE_LEN} 字以内: 「{q}」"
                    )

    if total_quotes > MAX_QUOTES_PER_FILE:
        errors.append(
            f"全文 「」直引 {total_quotes} 处 > {MAX_QUOTES_PER_FILE}; "
            f"原文短引数量须控制在合理使用范围内"
        )

    return errors


def main() -> int:
    if len(sys.argv) < 2:
        sys.exit("usage: validate_memory.py <file.yaml> [<file.yaml> ...]")

    overall_ok = True
    for arg in sys.argv[1:]:
        path = Path(arg)
        print(f"--- {path} ---")
        errs = validate_file(path)
        if not errs:
            print("  ✓ ok")
        else:
            overall_ok = False
            for e in errs:
                print(f"  ✗ {e}")

    return 0 if overall_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
