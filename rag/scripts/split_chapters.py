#!/usr/bin/env python3
"""按章节切分《剑来》全文。

输入: corpus/raw/剑来.utf8.txt (UTF-8)
输出:
  - corpus/chapters/{NNNN}-{title}.txt   每章原文 (UTF-8)
  - corpus/meta/chapters.jsonl           每章元数据 {chapter_id, title, raw_title, line_start, line_end, char_count}

章节标记: 行首允许任意空白 + 第X章 + 空白 + 标题
            X 可为中文数字或阿拉伯数字。
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "corpus" / "raw" / "剑来.utf8.txt"
CHAPTERS_DIR = ROOT / "corpus" / "chapters"
META_DIR = ROOT / "corpus" / "meta"

CHAPTER_RE = re.compile(
    r"^[\s　]*第[一二三四五六七八九十百千零〇0-9]+章[\s　]+(?P<title>.+?)[\s　]*$"
)

INVALID_FS_CHARS = re.compile(r'[\\/:*?"<>|\s]+')


def safe_filename(s: str, maxlen: int = 30) -> str:
    cleaned = INVALID_FS_CHARS.sub("_", s).strip("_")
    return cleaned[:maxlen] or "untitled"


def main() -> None:
    if not RAW.exists():
        raise SystemExit(f"missing input: {RAW}")
    CHAPTERS_DIR.mkdir(parents=True, exist_ok=True)
    META_DIR.mkdir(parents=True, exist_ok=True)

    lines = RAW.read_text(encoding="utf-8").splitlines(keepends=True)
    print(f"loaded {len(lines)} lines")

    headers: list[tuple[int, str, str]] = []  # (line_idx_1based, raw_title_line, parsed_title)
    for i, line in enumerate(lines, start=1):
        m = CHAPTER_RE.match(line)
        if m:
            headers.append((i, line.rstrip("\n"), m.group("title").strip()))

    print(f"found {len(headers)} chapter headers")
    if not headers:
        raise SystemExit("no chapters detected")

    chapters_meta: list[dict] = []
    for idx, (line_no, raw_title, title) in enumerate(headers):
        chapter_id = f"{idx + 1:04d}"
        next_line_no = headers[idx + 1][0] if idx + 1 < len(headers) else len(lines) + 1
        body_lines = lines[line_no - 1 : next_line_no - 1]
        body_text = "".join(body_lines)
        char_count = sum(len(l.rstrip("\n")) for l in body_lines)

        fname = f"{chapter_id}-{safe_filename(title)}.txt"
        (CHAPTERS_DIR / fname).write_text(body_text, encoding="utf-8")

        chapters_meta.append(
            {
                "chapter_id": chapter_id,
                "title": title,
                "raw_title": raw_title.strip(),
                "line_start": line_no,
                "line_end": next_line_no - 1,
                "char_count": char_count,
                "file": f"corpus/chapters/{fname}",
            }
        )

    meta_path = META_DIR / "chapters.jsonl"
    with meta_path.open("w", encoding="utf-8") as f:
        for row in chapters_meta:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"wrote {len(chapters_meta)} chapter files to {CHAPTERS_DIR}")
    print(f"wrote metadata to {meta_path}")


if __name__ == "__main__":
    main()
