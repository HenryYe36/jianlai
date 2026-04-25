# 取证版：让人物 Skill 记住书中细节

## 这是什么

原版人物 Skill 的强项在思维框架、表达 DNA、人物画像；弱项在涉及书中具体情节的问题上容易空泛、记不清细节。

这个目录提供一套可复现的工具链，把原文切章建索引，让 Skill 在回答事件类问题时**先去原文里取证、再以人物口吻作答**。

## 工作原理

```
用户问"你为什么放过顾璨"
    │
    ▼
SKILL.md Step 0 取证铁律
    │
    ├─ grep roles/陈平安/scenes.jsonl  关键词组合 (顾璨 + 不杀/饶)
    │      ↓
    ├─ Read corpus/chapters/0XXX-XX.txt  原文章节
    │      ↓
    ├─ 写留档版到 roles/陈平安/qa_log/   (带 [章XXXX] 引证)
    │      ↓
    └─ 屏幕输出台前版                     (自然口吻、无引证)
```

两层关键设计：

- **场景索引**：`roles/{角色}/scenes.jsonl` 每行一个场景，带绝对行号、同场角色、片段摘要，可直接 grep
- **双轨输出**：留档版带引证留盘可审计；屏幕输出像正常对话，不暴露取证流程

## 快速复现（剑来项目）

### 0. 准备原文

```bash
# 仓库不附带原文（版权原因）
mkdir -p corpus/raw
cp /your/path/to/剑来.txt corpus/raw/

# 如果原文是 UTF-16，先转码（剑来.txt 就是这样）
file corpus/raw/剑来.txt
iconv -f UTF-16LE -t UTF-8 corpus/raw/剑来.txt > corpus/raw/剑来.utf8.txt
```

### 1. 切章节

```bash
python3 rag/scripts/split_chapters.py
# 产出: corpus/chapters/{0001..1210}-*.txt
#      corpus/meta/chapters.jsonl
```

### 2. 扫描角色场景

```bash
# 默认按 rag/scripts/aliases.py 的 ROLES 表批量扫描全部角色
python3 rag/scripts/scan_role_scenes.py

# 单个角色:
python3 rag/scripts/scan_role_scenes.py --role 陈平安
python3 rag/scripts/scan_role_scenes.py --role 崔瀺  # 自动用 [崔瀺,崔诚,绣虎,大骊国师]

# 自定义 needles:
python3 rag/scripts/scan_role_scenes.py --role 自定义 --needles "甲,乙,丙"
# 产出: roles/{角色}/scenes.jsonl, chapter_index.jsonl
```

### 3. 给每个角色 SKILL.md 打补丁

把 `rag/SKILL_template_Step0.md` 里的 Step 0 块插入到 `.claude/skills/{role}-perspective/SKILL.md` 的 `## 回答工作流` 标题之下，把 `{角色}` 替换成你这个角色的目录名。

### 4. 给角色建 qa_log 目录

```bash
mkdir -p roles/{陈平安,齐静春,崔瀺,...}/qa_log
```

## 移植到其他小说

按下面顺序改 3 处：

### 1. 章节切分正则

`rag/scripts/split_chapters.py` 默认匹配 `第X章 标题` 格式：

```python
CHAPTER_RE = re.compile(
    r"^[\s　]*第[一二三四五六七八九十百千零〇0-9]+章[\s　]+(?P<title>.+?)[\s　]*$"
)
```

如果你的小说用 `Chapter X` 或 `第X回` 等格式，改这个正则。

### 2. 角色别名表

`rag/scripts/aliases.py` 的两张表：

- `ROLES`：每个主要角色 → 索引 needles。同一灵魂的分身/化名都列进来（如崔瀺=崔诚=绣虎=大骊国师）。
- `CO_PRESENT`：所有可能在场的角色 → 别名列表。检测共现时任一别名命中算到场。

**重要**：**只能加跟角色独占的别名**。跟常见词同形的不能加（剑来项目踩过的坑：`不要钱` 既是裴钱原想用的名字、也是常见成语"免费"，加进别名表后假阳性满天飞）。

### 3. SKILL.md 模板

复制 `rag/SKILL_template_Step0.md` 的 Step 0 块到你每个角色的 SKILL.md，把 `{角色}` 改对应名字。如果你的角色有专属术语别名（如剑来里"功德林=被罚反省地"），在补救策略 #2 里加一条 hint。

## 已知局限（Phase 2 才能解）

Phase 1 用 grep + Read 走通"具体事件 + 独占名词"类问题，约 85-90% 的题能 PASS+PARTIAL。下面几类仍受限：

- **抽象情感聚合**：如"X 对 Y 的真感情"，召回 200+ 候选大半是叙事性提及，需要 cross-encoder 重排区分"在场流露"vs"被人提到"
- **多义指代消歧**：如"先生"在不同章节指不同人
- **事件命名时差**：事件被事后命名（"甲子之约"），原文当下用别的词
- **同义/反义改写**：靠 SKILL.md 让模型多 grep 几次能补救一部分

升级到 Phase 2 的方案：本地 ONNX embedding（`bge-m3` 适合中文）+ ChromaDB + cross-encoder 重排。参考 [lyonzin/knowledge-rag](https://github.com/lyonzin/knowledge-rag) 的 MCP server 形态。

## 文件清单

```
rag/
├── README.md                         (本文件)
├── SKILL_template_Step0.md           取证 + 双轨输出补丁模板
└── scripts/
    ├── split_chapters.py             章节切分
    ├── scan_role_scenes.py           角色场景扫描
    └── aliases.py                    角色别名单一事实源
```

运行后会在仓库根产生（这些不入版本控制，因涉及原文版权）：

```
corpus/
├── raw/{你的小说}.utf8.txt
├── chapters/{NNNN}-{title}.txt       一章一个文件
└── meta/chapters.jsonl               章节元数据

roles/{角色}/
├── scenes.jsonl                      场景索引（每行一个场景）
├── chapter_index.jsonl               每章命中次数
└── qa_log/                           Skill 自动留档
```
