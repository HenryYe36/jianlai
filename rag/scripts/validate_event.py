#!/usr/bin/env python3
"""校验 event_memory yaml (事件/地点级别的粗粒度记忆) 的格式与版权红线.

用法:
  python3 scripts/validate_event.py path/to/event.yaml [...]

字段:
  event           (str, 必填)        事件中文名
  event_id        (str, 必填)        英文/拼音 id
  type            (str, 可选)        event | place | arc
  chapters        (list[str], 必填)  章节范围, e.g. ["0001", "0085"]
  participants    (list[str], 必填)  参与人员
  cause           (str, 必填)        起因 (我们的话)
  process         (str, 必填)        经过 (我们的话)
  result          (str, 必填)        结果 (我们的话)
  roles           (dict, 必填)       每人 actions/stance/inner_thought
  related_events  (list[str], 可选)  其他相关 event_id
  fine_grain_hint (str, 可选)        装好原文后可调出的更细内容

版权红线:
  - 所有自由文本字段单条 ≤ 600 字 (避免变成情节复述)
  - 全文「」直引段总数 ≤ 50 处, 单条 ≤ 15 字
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("需要 pyyaml: pip install pyyaml")


REQUIRED_TOP = ["event", "event_id", "chapters", "participants",
                "cause", "process", "result", "roles"]
OPTIONAL_TOP = ["type", "related_events", "fine_grain_hint", "tags"]
ALL_TOP = set(REQUIRED_TOP) | set(OPTIONAL_TOP)

REQUIRED_ROLE = ["actions", "stance", "inner_thought"]
ALL_ROLE = set(REQUIRED_ROLE) | {"tags"}

MAX_TEXT_LEN = 600
MAX_QUOTE_LEN = 15
MAX_QUOTES_PER_FILE = 50

QUOTE_RE = re.compile(r"「([^」]*)」")


def collect_quotes(text: str) -> list[str]:
    return QUOTE_RE.findall(text or "")


def check_text(ctx: str, field: str, text: str) -> list[str]:
    errs: list[str] = []
    if text and len(text) > MAX_TEXT_LEN:
        errs.append(
            f"{ctx}.{field}: 长度 {len(text)} > {MAX_TEXT_LEN}; 避免变成情节复述"
        )
    return errs


def validate_file(path: Path) -> list[str]:
    errors: list[str] = []
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        return [f"yaml 解析失败: {e}"]

    if not isinstance(data, dict):
        return ["顶层必须是 dict"]

    for f in REQUIRED_TOP:
        if f not in data:
            errors.append(f"缺少必填字段 '{f}'")
    for f in data:
        if f not in ALL_TOP:
            errors.append(f"未知顶层字段 '{f}' (允许: {sorted(ALL_TOP)})")

    chapters = data.get("chapters")
    if isinstance(chapters, list):
        for c in chapters:
            if not (isinstance(c, str) and re.fullmatch(r"\d{4}", c)):
                errors.append(f"chapters: 项 {c!r} 必须是 4 位数字字符串")

    if "participants" in data and not isinstance(data["participants"], list):
        errors.append("participants 必须是 list")

    total_quotes = 0

    for f in ["cause", "process", "result", "fine_grain_hint"]:
        if f in data:
            errors += check_text("top", f, data[f] or "")
            total_quotes += len(collect_quotes(data[f] or ""))

    roles = data.get("roles", {})
    if not isinstance(roles, dict):
        errors.append("roles 必须是 dict")
    else:
        for name, info in roles.items():
            ctx = f"roles.{name}"
            if not isinstance(info, dict):
                errors.append(f"{ctx}: 必须是 dict")
                continue
            for f in REQUIRED_ROLE:
                if f not in info:
                    errors.append(f"{ctx}: 缺少必填字段 '{f}'")
            for f in info:
                if f not in ALL_ROLE:
                    errors.append(f"{ctx}: 未知字段 '{f}' (允许: {sorted(ALL_ROLE)})")
            for f in REQUIRED_ROLE:
                if f in info:
                    errors += check_text(ctx, f, info[f] or "")
                    total_quotes += len(collect_quotes(info[f] or ""))

    # 引号长度检查
    all_text = ""
    for v in data.values():
        if isinstance(v, str):
            all_text += "\n" + v
        elif isinstance(v, dict):
            for vv in v.values():
                if isinstance(vv, dict):
                    for vvv in vv.values():
                        if isinstance(vvv, str):
                            all_text += "\n" + vvv
    for q in QUOTE_RE.findall(all_text):
        if len(q) > MAX_QUOTE_LEN:
            errors.append(
                f"单条「」直引 {len(q)} 字 > {MAX_QUOTE_LEN}: 「{q}」"
            )

    if total_quotes > MAX_QUOTES_PER_FILE:
        errors.append(
            f"全文 「」直引 {total_quotes} 处 > {MAX_QUOTES_PER_FILE}"
        )

    return errors


def main() -> int:
    if len(sys.argv) < 2:
        sys.exit("usage: validate_event.py <file.yaml> [...]")
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
