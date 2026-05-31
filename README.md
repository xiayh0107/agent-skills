# agent-skills

一套面向 AI Agent（Claude Code 等）的技能合集。每个技能是 `skills/` 下一个独立目录，包含 `SKILL.md`、可执行脚本与按需加载的参考文档。

[![skills.sh](https://skills.sh/b/xiayh0107/agent-skills)](https://skills.sh/xiayh0107/agent-skills)

## 技能列表

| 技能 | 说明 |
|---|---|
| [`pubmed-research`](skills/pubmed-research) | 端到端的 PubMed 检索与引用核验：构建高级检索式、通过 NCBI E-utilities 抓取文献、本地缓存摘要，并核验某条声明是否真的被对应 PMID 的摘要支持。 |

## 安装

通过 [skills.sh](https://www.skills.sh) 的 CLI 安装（无需克隆仓库）：

```bash
# 查看本仓库包含哪些技能
npx skills add xiayh0107/agent-skills --list

# 只安装某个技能（推荐）
npx skills add xiayh0107/agent-skills --skill pubmed-research

# 安装全部技能
npx skills add xiayh0107/agent-skills

# 全局安装（装到 ~/.claude/skills/，所有项目可用）
npx skills add xiayh0107/agent-skills --skill pubmed-research -g
```

安装位置：
- 项目级 → 当前项目的 `.claude/skills/`
- 全局（`-g`）→ `~/.claude/skills/`

## 目录结构

```
agent-skills/
└── skills/
    └── pubmed-research/
        ├── SKILL.md        # 技能入口：frontmatter（name/description）决定何时触发 + 操作说明
        ├── scripts/        # 真实可执行的工具脚本
        └── references/     # 按需加载的参考文档（渐进式披露）
```

## 首次配置说明

部分技能首次使用需要配置密钥（例如 `pubmed-research` 需要 NCBI API Key + 邮箱）。
具体步骤见各技能目录内 `SKILL.md` 的「Setup」章节。**密钥保存在本地
`~/.config/<skill>/.env`，不会、也不应被提交进本仓库。**
