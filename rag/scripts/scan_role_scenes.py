#!/usr/bin/env python3
"""扫描指定角色在全书中的出场场景。

输入:
  - corpus/meta/chapters.jsonl
  - corpus/chapters/{NNNN}-*.txt
输出 (per role):
  - roles/{role}/scenes.jsonl       每条 = 一个场景片段
  - roles/{role}/chapter_index.jsonl  每章命中次数

策略:
  - 每个角色用其 needles 集合命中 (任一字串命中即视为该角色出场)
  - 同章内命中行间隔 <= WINDOW_LINES 视为同一场景
  - 场景前后扩展 PAD_LINES 行作为上下文
  - co_present: 在场景窗口里检测核心角色名是否出现 (用 aliases.is_present)
  - 单 pass 全章扫描: 每个章节文件只读一次, 同时为所有角色建索引
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

WINDOW_LINES = 6
PAD_LINES = 2
SNIPPET_CHARS = 220


def load_chapters() -> list[dict]:
    with META.open("r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def find_scenes_in_chapter(
    chap_lines: list[str],
    chap_meta: dict,
    needles: list[str],
    role: str,
) -> tuple[list[dict], dict | None]:
    """对一个章节扫一遍, 返回 (scenes, chapter_index_row)."""
    hit_offsets = [
        k for k, line in enumerate(chap_lines)
        if any(n in line for n in needles)
    ]
    if not hit_offsets:
        return [], None

    # 合并临近命中为场景
    groups: list[list[int]] = [[hit_offsets[0]]]
    for off in hit_offsets[1:]:
        if off - groups[-1][-1] <= WINDOW_LINES:
            groups[-1].append(off)
        else:
            groups.append([off])

    co_pool = [c for c in ALIASES.co_present_pool() if c != role]

    scenes: list[dict] = []
    for s_idx, group in enumerate(groups, start=1):
        start_off = max(0, group[0] - PAD_LINES)
        end_off = min(len(chap_lines) - 1, group[-1] + PAD_LINES)
        window_lines = chap_lines[start_off : end_off + 1]
        window_text = "\n".join(window_lines)

        co = sorted({c for c in co_pool if ALIASES.is_present(c, window_text)})

        snippet = window_text.replace("\n", " ")
        if len(snippet) > SNIPPET_CHARS:
            snippet = snippet[:SNIPPET_CHARS] + "…"

        scenes.append({
            "scene_id": f"{chap_meta['chapter_id']}-{s_idx:02d}",
            "chapter_id": chap_meta["chapter_id"],
            "chapter_title": chap_meta["title"],
            "line_start": chap_meta["line_start"] + start_off,
            "line_end": chap_meta["line_start"] + end_off,
            "hit_count": len(group),
            "co_present": co,
            "snippet": snippet,
        })

    chap_idx_row = {
        "chapter_id": chap_meta["chapter_id"],
        "chapter_title": chap_meta["title"],
        "line_start": chap_meta["line_start"],
        "hit_count": len(hit_offsets),
        "scene_count": len(groups),
    }
    return scenes, chap_idx_row


def scan_all(roles_to_scan: dict[str, list[str]]) -> dict[str, dict[str, int]]:
    """单 pass 扫描全部章节, 同时为所有指定角色建索引.

    roles_to_scan: {role_name: [needles]}
    返回: {role_name: {scenes: N, hits: N}}
    """
    chapters = load_chapters()
    stats = {role: {"scenes": 0, "hits": 0} for role in roles_to_scan}

    # 每个角色一个写句柄
    handles: dict[str, dict] = {}
    for role in roles_to_scan:
        out_dir = ROLES_DIR / role
        out_dir.mkdir(parents=True, exist_ok=True)
        handles[role] = {
            "scenes_f": (out_dir / "scenes.jsonl").open("w", encoding="utf-8"),
            "chap_f": (out_dir / "chapter_index.jsonl").open("w", encoding="utf-8"),
        }

    try:
        for chap in chapters:
            # 每章只读一次
            chap_lines = (ROOT / chap["file"]).read_text(encoding="utf-8").splitlines()

            for role, needles in roles_to_scan.items():
                scenes, chap_idx = find_scenes_in_chapter(chap_lines, chap, needles, role)
                if not scenes:
                    continue
                h = handles[role]
                for s in scenes:
                    h["scenes_f"].write(json.dumps(s, ensure_ascii=False) + "\n")
                    stats[role]["scenes"] += 1
                    stats[role]["hits"] += s["hit_count"]
                h["chap_f"].write(json.dumps(chap_idx, ensure_ascii=False) + "\n")
    finally:
        for h in handles.values():
            h["scenes_f"].close()
            h["chap_f"].close()

    return stats


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
        roles_to_scan = {args.role: [n.strip() for n in args.needles.split(",") if n.strip()]}
    elif args.role:
        roles_to_scan = {args.role: ALIASES.needles_for(args.role)}
    else:
        roles_to_scan = {role: ALIASES.needles_for(role) for role in ALIASES.ROLES}

    stats = scan_all(roles_to_scan)

    for role, s in stats.items():
        print(f"role={role} needles={roles_to_scan[role]}")
        print(f"  scenes: {s['scenes']}")
        print(f"  hits  : {s['hits']}")


if __name__ == "__main__":
    main()
