#!/usr/bin/env bash
# 一键 setup: 让人物 Skill 切到全量取证模式.
# 用法:
#   ./setup.sh /path/to/novel.txt           # 自动探测编码
#   ./setup.sh /path/to/novel.txt UTF-16LE  # 显式指定编码
set -euo pipefail

src="${1:?usage: setup.sh <novel.txt> [encoding]}"
enc="${2:-auto}"

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

if [ ! -f "$src" ]; then
  echo "✗ 找不到原文: $src" >&2
  exit 1
fi

# 校验依赖
if ! python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)' 2>/dev/null; then
  echo "✗ 需要 Python 3.8+" >&2
  exit 1
fi

mkdir -p corpus/raw

echo "[1/3] 转码 → UTF-8…"
out="corpus/raw/novel.utf8.txt"
if [ "$enc" = "auto" ]; then
  detected=$(file -b --mime-encoding "$src")
  echo "  检测到编码: $detected"
  case "$detected" in
    utf-8|us-ascii) cp "$src" "$out" ;;
    *)              iconv -f "$detected" -t UTF-8 "$src" > "$out" ;;
  esac
else
  iconv -f "$enc" -t UTF-8 "$src" > "$out"
fi
echo "  -> $out ($(wc -l < "$out") 行)"

echo "[2/3] 切章…"
python3 rag/scripts/split_chapters.py

echo "[3/3] 扫描所有角色场景…"
python3 rag/scripts/scan_role_scenes.py

echo
echo "✓ Setup 完成. Skill 已可切到全量取证模式 (corpus/chapters/ 已生成)."
echo "  接下来对任一人物 skill 提问书中具体情节, Skill 会:"
echo "    1. grep roles/<角色>/scenes.jsonl 找候选场景"
echo "    2. Read corpus/chapters/<章号>.txt 读原文"
echo "    3. 写留档版到 roles/<角色>/qa_log/, 屏幕显示台前对话版"
