# imagegen — GPT Image 位图生成 / 编辑技能

用 GPT Image API（默认 `gpt-image-2`）生成或编辑位图：照片、插画、游戏精灵、贴图、UI/产品样机、Banner、Logo 概念、信息图、透明抠图。命令行驱动，支持单张、批量、绿幕去背。

> 适用：「生成图片 / 画一张图 / 配图 / 改图 / P图 / 抠图 / 透明背景 / 产品图 / 封面图」。
> 不适用：架构图 / 流程图 / 时序图（交给绘图工具），编辑已有 SVG/矢量，或直接用 HTML/CSS/canvas 更合适的场景。

## 安装

```bash
# 推荐：用 skills.sh 全局安装到 ~/.claude/skills/
npx skills add xiayh0107/agent-skills --skill imagegen -g

# 或只装到当前项目的 .claude/skills/
npx skills add xiayh0107/agent-skills --skill imagegen
```

## 依赖

```bash
# Python 包：openai 必需；pillow 仅在抠图/缩放时需要
uv pip install openai pillow      # 或 pip install openai pillow
```

## 配置 key（一次）

```bash
cd ~/.claude/skills/imagegen
cp .env.example .env
# 编辑 .env，填入你自己的 OPENAI_API_KEY（如用第三方中转再填 OPENAI_BASE_URL）
```

key 的解析顺序：已 export 的环境变量 > 项目 `./.env` > `~/.claude/skills/imagegen/.env`。**填好真实 key 的 `.env` 不会、也不应被提交。**

## 冒烟测试

```bash
IMAGE_GEN="$HOME/.claude/skills/imagegen/scripts/image_gen.py"

# 不联网、不耗 key，只打印请求体，验证参数无误
python3 "$IMAGE_GEN" generate --prompt "a red apple on a wooden table" --dry-run

# 真出一张草稿图
python3 "$IMAGE_GEN" generate --prompt "a red apple on a wooden table" \
  --quality low --size 1024x1024 --out /tmp/imagegen-test.png
```

## 三个子命令

- `generate` — 从提示词生成新图
- `edit` — 编辑一张或多张已有图（`--image` 可重复，可选 `--mask`）
- `generate-batch` — 从 JSONL 并发跑多个不同提示词（需 `--out-dir`）

提示词结构建议：场景 → 主体 → 细节 → 约束。图内文字逐字加引号并要求「无多余字符」；改图时每轮都重复声明不变量（「只改 X，保持 Y 不变」）。草稿用 `--quality low`，终稿/密集文字用 `high`。

## 透明背景

`gpt-image-2` 不支持原生透明。默认走「绿幕 + 本地去键」：在纯 `#00ff00` 背景上生成，再用 `scripts/remove_chroma_key.py` 去背（头发/玻璃/烟雾等复杂主体才考虑降级到 `gpt-image-1.5 --background transparent`）。

## 目录结构

```
imagegen/
├── SKILL.md                    # Claude 读取的主说明（含 gpt-image-2 参数表）
├── .env.example                # key 模板（复制为 .env 使用）
├── references/
│   ├── prompting.md            # 提示词原则 / 用例分类 / prompt schema
│   ├── sample-prompts.md       # 按资产类型的可复制提示词配方
│   ├── cli.md                  # 完整 CLI 参数（mask / 缩放 / 批量 JSONL）
│   └── image-api.md            # API 参数参考
└── scripts/
    ├── image_gen.py            # generate / edit / generate-batch
    └── remove_chroma_key.py    # 绿幕去键 → 透明 PNG
```

## License

MIT
