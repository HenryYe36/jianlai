# 取证版：让人物 Skill 记住书中细节

## 这是什么

原版人物 Skill 的强项在思维框架、表达 DNA、人物画像；弱项在涉及书中具体情节的问题上容易空泛、记不清细节。

这个目录提供一套可复现的工具链，把原文切章建索引，让 Skill 在回答事件类问题时**先去原文里取证、再以人物口吻作答**。

## 双模式架构（重要）

为了开源后**别人不必重训也能直接用**，Skill 设计成双模式：

| 模式 | 触发 | 能答粗粒度 | 能答细粒度 | 用户成本 |
|---|---|---|---|---|
| **轻量记忆模式** | 默认（无原文） | ✓ 用 `character_memory.yaml` | ✗ 引导用户 setup | 0 |
| **全量取证模式** | 跑过 `setup.sh` | ✓ | ✓ grep 原文 + 引证 | 5 分钟 |

每个角色 skill 包里都带一份 `character_memory.yaml`——**不是原文片段、是人物事件指针 + 用我们自己的话写的动机摘要**（合理使用范畴）。即装即用，能回答粗粒度问题。

需要细粒度（具体原话、章节内细节）的用户，跑一次根目录的 `setup.sh /path/to/novel.txt`，5 分钟内全切片完成 → Skill 自动切到全量取证模式。

## 工作原理

```text
用户问"你为什么放过顾璨"
    │
    ▼
SKILL.md 启动检测
    │
    ├─ 看到 corpus/chapters/ 有内容? ─→ 全量取证模式
    │       │
    │       ├─ grep roles/陈平安/scenes.jsonl  关键词组合
    │       ├─ Read corpus/chapters/0XXX-XX.txt 原文
    │       ├─ 留档版到 roles/陈平安/qa_log/   (带 [章XXXX] 引证)
    │       └─ 屏幕台前版                       (自然口吻、无引证)
    │
    └─ 没有?                          ─→ 轻量记忆模式
            │
            ├─ 加载 character_memory.yaml
            ├─ events 列表里找最相关 1-3 条
            └─ 用 motive_in_my_words + chapter_title 拼答
                 (超出 memory 范围 → 引导用户 setup)
```

## 一键 Setup（推荐）

```bash
# 在仓库根:
./setup.sh /path/to/novel.txt
# 5 分钟内: 自动探测编码 → 切章 → 扫描所有角色 → 全量模式就绪
```

如果自动编码探测出错（剑来.txt 是 UTF-16LE）：

```bash
./setup.sh /path/to/novel.txt UTF-16LE
```

## 手动复现（剑来项目）

如果不想用 setup.sh，分步运行：

### 0. 准备原文

```bash
# 仓库不附带原文（版权原因）
mkdir -p corpus/raw
file /your/path/to/剑来.txt   # 检查编码
iconv -f UTF-16LE -t UTF-8 /your/path/to/剑来.txt > corpus/raw/novel.utf8.txt
```

### 1. 切章节

```bash
python3 rag/scripts/split_chapters.py
# 产出: corpus/chapters/{0001..1210}-*.txt
#      corpus/meta/chapters.jsonl
```

### 2. 扫描角色场景（单 pass 全角色，约 1 秒）

```bash
# 默认按 rag/scripts/aliases.py 的 ROLES 表批量扫描全部角色
python3 rag/scripts/scan_role_scenes.py

# 单个角色:
python3 rag/scripts/scan_role_scenes.py --role 陈平安
python3 rag/scripts/scan_role_scenes.py --role 崔瀺  # 自动用 [崔瀺,崔诚,绣虎,大骊国师]

# 产出: roles/{角色}/scenes.jsonl, chapter_index.jsonl
```

## 移植到其他小说

按下面顺序改 4 处：

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

**踩坑警告**：**只能加跟角色独占的别名**。跟常见词同形的不能加（剑来项目踩过的坑：`不要钱` 既是裴钱原想用的名字、也是常见成语"免费"，加进别名表后假阳性满天飞）。

### 3. character_memory.yaml（每角色一份）

每个角色 skill 目录下放一份 `character_memory.yaml`，作为轻量模式下的事件指针。

格式参考 `剑来人物/陈平安/chen-pingan-perspective/character_memory.yaml`：

```yaml
character: 角色名
events:
  - id: take_baoping_to_school
    name_zh: 收下小宝瓶
    chapter: "0084"
    chapter_title: 我有一剑
    when_short: 学塾马先生死后
    co_present: [李宝瓶, 阮邛]
    motive_in_my_words: |
      她说「一个人就有点怕」. 这话她敢说, 我就不能装没听见.
      ……（用我们自己的话写的动机解读）
    related_models: [模型2 答应了就负责到底]
    fine_grain_hint: 装好原文后可调出更细的内容
```

**版权红线**：

- ❌ 不放 `scenes.jsonl` 里 200 字 snippet（那是原文派生品）
- ❌ 不复述情节（"X 做了 A，然后 Y 做了 B"）
- ✓ 章节号、章节标题、人物名（事实，不受版权保护）
- ✓ 动机解读、思维框架对应（我们的话，二次创作）
- ⚠️ 短引「」≤15 字、整文件 ≤30 处（fair use 边界内）

写完用 validator 校验：

```bash
python3 rag/scripts/validate_memory.py 路径/character_memory.yaml
# pip install pyyaml 一次
```

### 4. SKILL.md 模板

复制 `rag/SKILL_template_Step0.md` 的"启动检测 + Step 0"块到你每个角色的 SKILL.md，把 `{角色}` 改对应名字。如果你的角色有专属术语别名（如剑来里"功德林=被罚反省地"），在补救策略里加一条 hint。

## 已知局限（Phase 2 才能解）

Phase 1 用 grep + Read 走通"具体事件 + 独占名词"类问题，约 85-90% 的题能 PASS+PARTIAL。下面几类仍受限：

- **抽象情感聚合**：如"X 对 Y 的真感情"，召回 200+ 候选大半是叙事性提及，需要 cross-encoder 重排区分"在场流露"vs"被人提到"
- **多义指代消歧**：如"先生"在不同章节指不同人
- **事件命名时差**：事件被事后命名（"甲子之约"），原文当下用别的词
- **同义/反义改写**：靠 SKILL.md 让模型多 grep 几次能补救一部分

升级到 Phase 2 的方案：本地 ONNX embedding（`bge-m3` 适合中文）+ ChromaDB + cross-encoder 重排。参考 [lyonzin/knowledge-rag](https://github.com/lyonzin/knowledge-rag) 的 MCP server 形态。

## 文件清单

入仓的（合规、可分发）：

```text
setup.sh                              一键 setup 入口
rag/
├── README.md                         本文件
├── SKILL_template_Step0.md           启动检测 + Step 0 + 双轨输出补丁模板
└── scripts/
    ├── split_chapters.py             章节切分
    ├── scan_role_scenes.py           角色场景扫描（单 pass 多角色）
    ├── aliases.py                    角色别名单一事实源
    └── validate_memory.py            character_memory.yaml 校验器
剑来人物/{角色}/{role}-perspective/
├── SKILL.md                          已植入双模式启动检测 + Step 0 取证铁律
└── character_memory.yaml             轻量模式记忆库（仅陈平安已完成，其他角色 TBD）
```

运行后会在仓库根产生（**不入版本控制**，因涉及原文版权）：

```text
corpus/
├── raw/novel.utf8.txt                你的原文（UTF-8）
├── chapters/{NNNN}-{title}.txt       一章一个文件
└── meta/chapters.jsonl               章节元数据

roles/{角色}/
├── scenes.jsonl                      场景索引（每行一个场景）
├── chapter_index.jsonl               每章命中次数
└── qa_log/                           Skill 自动留档（每次问答一份）
```

## 版权声明

本仓库**不附带、不分发**任何原文。请通过正规渠道（实体书 / 起点中文网订阅 / 其他授权电子书平台）获取《剑来》原文，再用 setup.sh 接入本地工具链。这套工具是阅读辅助工具，不是替代品——遇到精彩段落，请去看原书。
