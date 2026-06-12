# agent-skills

一套面向 AI Agent（Claude Code 等）的技能合集。每个技能是 `skills/` 下一个独立目录，包含 `SKILL.md`、可执行脚本与按需加载的参考文档。

[![skills.sh](https://skills.sh/b/xiayh0107/agent-skills)](https://skills.sh/xiayh0107/agent-skills)

## 技能列表

| 技能 | 说明 |
|---|---|
| [`pubmed-research`](skills/pubmed-research) | 端到端的 PubMed 检索与引用核验：构建高级检索式、通过 NCBI E-utilities 抓取文献、本地缓存摘要，并核验某条声明是否真的被对应 PMID 的摘要支持。 |
| [`imagegen`](skills/imagegen) | 用 GPT Image API（`gpt-image-2`）生成或编辑位图：照片、插画、产品样机、封面、信息图、透明抠图。命令行驱动，支持批量与绿幕去背。 |
| [`layered-infographic`](skills/layered-infographic) | 把可编辑矢量文字与 `gpt-image-2` 栅格美术合成为分层信息图/海报，产出分层 SVG + 真·多图层 PSD；文字与美术各自可改、可重生。依赖 `imagegen`。 |

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

部分技能首次使用需要配置密钥：

- `pubmed-research` 需要 NCBI API Key + 邮箱（保存在 `~/.config/pubmed-research/.env`）
- `imagegen` 需要 `OPENAI_API_KEY`（复制其目录内 `.env.example` 为 `.env` 后填入）
- `layered-infographic` 依赖 `imagegen`，并需要 `rsvg-convert` 与 node（导出 PSD 用 `npm install` 重建依赖）

具体步骤见各技能目录内的 `README.md` 与 `SKILL.md`。**任何填好真实密钥的 `.env`
都不会、也不应被提交进本仓库（根 `.gitignore` 已默认忽略）。**
