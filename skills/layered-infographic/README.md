# layered-infographic — 分层信息图 / 海报（SVG + PSD）

把**精确可编辑的矢量文字**和 **gpt-image-2 栅格美术**合成为分层成品：一个「活」的分层 SVG（文字随时改、美术可替换）+ 一个真正的多图层 PSD（交给 Photoshop / 设计师，每层独立可编辑）。

适合科研信息图、教学图、封面图、期刊风海报——任何「文字必须精确、美术希望好看且可重生」的图。单张独立图请直接用 [`imagegen`](../imagegen)；纯框线流程图请用绘图工具。

核心规则一句话：**只把必须精确的东西做成矢量（文字 / 公式 / 数据标签 / 数据图表），其余装饰全部交给 gpt-image-2 出栅格。** 手画装饰矢量只会更丑、还把布局焊死。

## 安装

```bash
# 它依赖 imagegen，两个一起装最省事
npx skills add xiayh0107/agent-skills --skill imagegen -g
npx skills add xiayh0107/agent-skills --skill layered-infographic -g
```

## 依赖（每会话检查一次）

```bash
# 1) imagegen 技能 —— 生成美术层、去键（见上）
# 2) rsvg-convert —— SVG → PNG（图层拆分 + 预览）
which rsvg-convert || brew install librsvg     # macOS

# 3) node + PSD 依赖 —— 仅导出 PSD 时需要，装一次
npm --prefix ~/.claude/skills/layered-infographic/scripts install
```

## 工作流

1. **规划图层**：`layer-bg`（卡片/背景）· `layer-art`（gpt-image-2 美术）· `layer-text`（标题/标签/公式）· 可选 `layer-annotations`（箭头/图表/节点）。
2. **写 SVG 骨架**：每个可视元素放进顶层 `<g id="layer-...">`；调色板/字号集中在 `<style>` 的 CSS token；美术槽位写 `xlink:href="asset://assets/<name>.png"`。
3. **生成美术**到 `assets/`（用 imagegen；透明主体走绿幕去键）。
4. **填充槽位**（把资产 base64 内嵌，文件自包含）：
   ```bash
   python ~/.claude/skills/layered-infographic/scripts/embed_assets.py \
     skeleton.svg --out final.svg --base . --max-width 1400
   ```
5. **渲染合成图**校验：
   ```bash
   rsvg-convert -w 2240 final.svg -o final.png
   ```
6. **导出分层交付物**（SVG + 每层 PNG + 真 PSD）：
   ```bash
   python ~/.claude/skills/layered-infographic/scripts/split_svg_layers.py \
     final.svg --out-dir build --width 1120 --psd-name myfig.psd
   node ~/.claude/skills/layered-infographic/scripts/build_psd.mjs build/psd_manifest.json .
   ```

产物：`final.svg`（文字可改 + 美术可替换）、`final.png`（发布）、`myfig.psd`（Photoshop，命名图层独立可编辑）。

## 脚本依赖的约定

- 顶层分组 `<g id="layer-NAME">` → PSD 图层 "NAME"，按文档顺序。
- 槽位 `xlink:href="asset://<relative-path>"` → 被 `embed_assets.py` 替换为内嵌资产。
- 整幅背景 `<rect>` 最好包进 `layer-bg`。

## 已知坑

- gpt-image-2 无原生透明、无 PSD 输出——这两样由本工作流产出，不是模型本身。
- 小而密的文字交给矢量层；gpt-image-2 擅长短标签和图像。
- PSD 必须带一张顶层合成图，否则部分查看器显示纯黑（脚本已处理）。
- 图层名用 ASCII，避免老旧查看器把非 ASCII 名乱码。
- imagegen 中转偶发 429——重试失败任务或降低并发。

## 目录结构

```
layered-infographic/
├── SKILL.md                    # Claude 读取的主说明 + 工作流
├── references/
│   ├── strategy.md             # 逐层路由 + 「只矢量化文字」规则
│   └── palettes.md             # 科研配色系统（Nature / Science / Cell / 医学 …）
└── scripts/
    ├── embed_assets.py         # 把 asset:// 槽位内嵌为 base64
    ├── split_svg_layers.py     # 拆成对齐的每层 PNG + PSD manifest
    ├── build_psd.mjs           # 组装多图层 PSD（ag-psd）
    └── package.json            # node 依赖（PSD 导出，npm install 重建）
```

## License

MIT
