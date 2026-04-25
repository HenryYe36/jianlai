#!/usr/bin/env python3
"""扫描指定角色在全书中的出场场景。

输入:
  - corpus/meta/chapters.jsonl
  - corpus/chapters/{NNNN}-*.txt
输出:
  - roles/{role}/scenes.jsonl       每条 = 一个场景片段
                                     {scene_id, chapter_id, chapter_title,
                                      line_start, line_end,         # 全文绝对行号
                                      hit_count, co_present, snippet}
  - roles/{role}/chapter_index.jsonl  每章命中次数
                                     {chapter_id, chapter_title, line_start,
                                      hit_count, scene_count}

策略:
  - 角色用 NEEDLE 单串匹配 (陈平安 是足够独占的全名, 别名容易污染)
  - 同章内, 命中行间隔 <= WINDOW_LINES 视为同一场景
  - 场景前后各扩展 PAD_LINES 行作为上下文
  - co_present: 在场景窗口里检测核心角色名是否出现
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import aliases as ALIASES

ROOT = Path(__file__).resolve().parent.parent
META = ROOT / "corpus" / "meta" / "chapters.jsonl"
CHAPTERS_DIR = ROOT / "corpus" / "chapters"
ROLES_DIR = ROOT / "roles"

WINDOW_LINES = 6   # 命中之间间隔 <= 此值则合并到同一场景
PAD_LINES = 2      # 场景前后各扩展行数
SNIPPET_CHARS = 220


def load_chapters() -> list[dict]:
    with META.open("r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def scan(role: str, needles: list[str]) -> None:
    out_dir = ROLES_DIR / role
    out_dir.mkdir(parents=True, exist_ok=True)

    chapters = load_chapters()
    scenes_path = out_dir / "scenes.jsonl"
    chap_idx_path = out_dir / "chapter_index.jsonl"

    # 配角池排除主角自己 (按规范名), 检测时用别名表
    co_pool = [c for c in ALIASES.co_present_pool() if c != role]

    total_scenes = 0
    total_hits = 0

    def line_hits(line: str) -> bool:
        return any(n in line for n in needles)

    with scenes_path.open("w", encoding="utf-8") as scenes_f, \
         chap_idx_path.open("w", encoding="utf-8") as chap_f:
        for chap in chapters:
            chap_path = ROOT / chap["file"]
            chap_lines = chap_path.read_text(encoding="utf-8").splitlines()

            hit_offsets = [k for k, line in enumerate(chap_lines) if line_hits(line)]
            if not hit_offsets:
                continue

            # 合并临近命中为场景
            scene_groups: list[list[int]] = []
            cur: list[int] = [hit_offsets[0]]
            for off in hit_offsets[1:]:
                if off - cur[-1] <= WINDOW_LINES:
                    cur.append(off)
                else:
                    scene_groups.append(cur)
                    cur = [off]
            scene_groups.append(cur)

            for s_idx, group in enumerate(scene_groups, start=1):
                start_off = max(0, group[0] - PAD_LINES)
                end_off = min(len(chap_lines) - 1, group[-1] + PAD_LINES)
                window_lines = chap_lines[start_off : end_off + 1]
                window_text = "\n".join(window_lines)

                co = sorted({c for c in co_pool if ALIASES.is_present(c, window_text)})

                snippet = window_text.replace("\n", " ")
                if len(snippet) > SNIPPET_CHARS:
                    snippet = snippet[:SNIPPET_CHARS] + "…"

                row = {
                    "scene_id": f"{chap['chapter_id']}-{s_idx:02d}",
                    "chapter_id": chap["chapter_id"],
                    "chapter_title": chap["title"],
                    "line_start": chap["line_start"] + start_off,
                    "line_end": chap["line_start"] + end_off,
                    "hit_count": len(group),
                    "co_present": co,
                    "snippet": snippet,
                }
                scenes_f.write(json.dumps(row, ensure_ascii=False) + "\n")
                total_scenes += 1
                total_hits += len(group)

            chap_f.write(
                json.dumps(
                    {
                        "chapter_id": chap["chapter_id"],
                        "chapter_title": chap["title"],
                        "line_start": chap["line_start"],
                        "hit_count": len(hit_offsets),
                        "scene_count": len(scene_groups),
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )

    print(f"role={role} needles={needles}")
    print(f"  scenes: {total_scenes}")
    print(f"  hits  : {total_hits}")
    print(f"  out   : {scenes_path}")
    print(f"          {chap_idx_path}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--role",
        default=None,
        help="角色规范名. 不传则扫描 aliases.ROLES 里的所有角色",
    )
    ap.add_argument(
        "--needles",
        default=None,
        help="逗号分隔的检索字符串. 默认从 aliases.ROLES 读取",
    )
    args = ap.parse_args()

    if args.role and args.needles:
        needles = [n.strip() for n in args.needles.split(",") if n.strip()]
        scan(args.role, needles)
        return

    if args.role:
        scan(args.role, ALIASES.needles_for(args.role))
        return

    for role in ALIASES.ROLES:
        scan(role, ALIASES.needles_for(role))


if __name__ == "__main__":
    main()
