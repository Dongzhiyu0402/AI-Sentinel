# 合规哨兵 Compliance Sentinel · DESIGN.md

> 生成日期：2026-10-26 | 设计师：颜好看 | 基于：SPEC v0.2（D0 骨架）+ ADR-001
> 三轴刻度：**Variance = 3 / Motion = 3 / Density = 6**
> 寄存器：**Product Register**（设计服务产品，不是营销页。标杆是"赢得熟悉感"，不是"独特新奇"）
> 平台轴：**web**（响应式，移动端必须可用，评委可能用手机打开）

---

## 1. Visual Theme & Atmosphere

**品牌声音三词**：`文书式` · `克制` · `可追责`（documented / restrained / accountable）

**物理参照物**：检验科化验单 + 法条单行本。不是"AI 产品"，是"可被引用、可被复核、写错了要担责的东西"。

**氛围**：白纸、深墨、一支深蓝钢笔。信息密度偏高（Density 6，报告需要密），但没有一处装饰是多余的。全站只有一支强调色，出现次数少到你会注意它。

**对标品牌**：
| 品牌 | 借鉴什么 | 不借鉴什么 |
|---|---|---|
| **Grammarly**（主对标） | 「文本 ↔ 建议」双向定位的双栏检查模型；逐条建议可采纳/忽略；分级下划线；结果不阻塞原文 | 紫色品牌色、彩色下划线、emoji 语气、消费化插画 |
| **Stripe Docs** | 文书式排版（长文行宽、依据条文引用块）、克制的单一强调色 | 深色大 Hero、渐变 |
| **Cloudflare Dashboard** | 仪表式数据卡的紧凑表达；风险分级的语义色纪律 | 深色主题（本项目用浅色） |

**为什么选 Grammarly 做对标**：合规体检在用户心理上等同于"检查我的文本并逐条告诉我怎么改"——这正是 Grammarly 用十年建立的心智模型。评委打开页面 3 秒内必须知道"左边是我的文本，右边是我的问题"，这个结构不需要学习。而国产违禁词工具（句易网、零克查词、k3达人社）的界面是"左右两个文本框 + 一片染色"，只标错不给出处、不给改法、广告与登录引导挤占注意力——这是我们要在视觉上明确拉开差距的地方，因此**不作为对标，只作为反面样本**。

> 竞品调研结论（2026-10-26，web 检索）：
> - **句易网 ju1.cn**：广告法词库最权威，但界面被用户评价为"像上个世纪的产物，全是文字"，右栏纯染色结果，广告位多。→ 反面样本。
> - **零克查词**：垂直小红书词库精准、界面清新，但会员/「零蛋」积分体系在首屏占用显著篇幅，右栏结果是"标红 + 词性解释"，无改法。→ 反面样本（信息架构可取：左侧输入、右侧结果）。
> - **千墨查词**：极简、打开即巨大文本框、无广告，编辑体验最好。→ 借鉴其"零摩擦输入"。
> - **Grammarly 2025**：块状文档 + 常驻 AI 侧栏 + 每类建议独立 agent + AI 检测。→ **主对标**。

---

## 2. Color Palette & Roles

### 主色只有一支（不是三支）
规则是"主色 ≤3 个"，我们只用 **1 支品牌色 + 3 支风险语义色**。关键决断：

> **深藏青 `--accent` 同时承担「主按钮」与「唯一强调色」。**
> 这样强调色天然被约束在每屏 ≤2 处，不存在"品牌色太亮到处刷"的问题。
> 风险三色属于**语义色（0-5% 面积）**，不参与品牌识别，不用于 CTA。

| Token | 值 | 角色 | 对比度 |
|---|---|---|---|
| `--bg` | `#F4F6F9` | 页面底色（冷调纸灰，**刻意不用奶油/米色**） | — |
| `--surface` | `#FFFFFF` | 卡片/容器 | — |
| `--fg` | `#17202E` | 主文本 | **15.1:1** on bg |
| `--fg-2` | `#3D4A5E` | 长段落 | 9.4:1 |
| `--muted` | `#5C6A80` | 次级文本 | **4.72:1** on bg / 5.11:1 on surface |
| `--meta` | `#8794A8` | 元数据 | 3.07:1 → **仅 ≥24px 或图标，禁止正文** |
| `--border` | `#DFE5EE` | 装饰性 1px 分隔 | 非交互边界，豁免 3:1 |
| `--border-strong` | `#7E8CA1` | 输入框/可交互边界 | **3.41:1**（满足 WCAG 1.4.11） |
| `--accent` | `#16324F` | 品牌色 + 可交互强调色 | **13.1:1**（白字） |
| `--accent-warm` | `#A8731B` | amber 品牌暖色点，**面积 ≤1%，仅品牌标记位** | 4.09:1 → **不可做正文/徽章** |
| `--risk-high` | `#A32B32` | 高风险 | **7.13:1** |
| `--risk-med` | `#8A5D0E` | 中风险 | **5.77:1** |
| `--risk-low` | `#4B5B70` | 提示级/无命中 | **6.93:1** |
| `--success` | `#1D6B47` | AI 标识检查通过 | **6.47:1**（仅状态色） |

**配色来源**：`references/design-systems/color-palettes.md` 中「金融/合规 · 稳重权威」色相族（navy 主色 + 暖赭警示 + 砖红风险），非默认 Indigo `#6366F1`。

### 强调色纪律（navy + amber 都在，但分工定死）

| 色 | Token | 允许出现的位置 | 面积 | 绝对禁止 |
|---|---|---|---|---|
| navy `#16324F` | `--accent` | 主 CTA、当前选中项、焦点环 | 每屏 ≤2 处 | 标题染色、全站图标染色 |
| amber `#A8731B` | `--accent-warm` | **仅**品牌标记位（logo 细节、页脚标识） | ≤1% 面积 | 徽章、数值、按钮、图标、图表、任何"数据" |

> **为什么 amber 不做主按钮（这条要写进评审记录）**：
> amber 原值 `#A8731B` 对白底实测 **4.09:1**，未达 AA 正文 4.5:1。它一旦承担主 CTA 就必须上面积，而「中风险」占着同一暖色族——两块暖色同屏，用户分不清哪个是品牌、哪个是警报。
> 所以：**amber 交给风险语义**（`--risk-med #8A5D0E`，5.77:1 达标），**navy 承担可交互强调**。两色都存在、都可见，只是不再互相抢角色。品牌暖色的情绪由「砖红风险色 + 暖灰过渡」承接，不靠一支按钮色。
> 若评审坚持 amber 做主 CTA，唯一解法是把中风险换成非暖色（如深蓝灰），但这会让三级风险的扫描速度变慢——不建议。

- 每屏 `--accent` 可见使用 **≤2 处**：① 主 CTA（开始体检）；② 当前选中项/焦点环。
- × 不允许：标题用强调色、图标全站铺强调色、链接全用强调色。
- × 禁止 Indigo→Pink / 紫→粉任意渐变。全站 **零渐变**（唯一例外：无）。
- × 不允许多强调色堆叠：`--accent` 与 `--accent-warm` 不得在同一区块内同时出现。

### 风险分级色彩规则（报告页核心）
- 颜色**永远不单独承载语义**，必须与文字标签同时出现（`高风险` / `中风险` / `提示`）。
- 徽章 = 软底色 + 深色文字（如 `--risk-high-soft` 底 / `--risk-high` 字，6.2:1）。
- 分级色**只出现在左色条与徽章**，不染整张卡片的底色——避免"整页红"的焦虑感。

---

## 3. Typography

**字体栈**（明确锁定，不是"系统字体直出"）：

```css
--font-display: "Public Sans", "HarmonyOS Sans SC", "Source Han Sans SC",
                "PingFang SC", "Microsoft YaHei", sans-serif;
--font-body:    同上;
--font-mono:    "JetBrains Mono", "Sarasa Mono SC", ui-monospace, Consolas, monospace;
```

**为什么是 Public Sans + HarmonyOS Sans SC**：
- `Public Sans` 源自美国联邦政府 USWDS 设计系统（SIL OFL），字面方、字重扎实、无品牌腔调——正好是"准官方文书"的气质，且不是 Inter / DM Sans / Outfit 这类被用滥的默认值。
- 中文用 `HarmonyOS Sans SC`（开源可商用）承重，回退 `Source Han Sans SC` → `PingFang SC`。中文不做"换字体制造差异"，差异靠字重与字距。
- `JetBrains Mono` 只用于「命中词」与「条文编号」，让"机器查到的东西"和"人写的话"在视觉上可区分。

> **部署约束**：首屏 3 秒内要出规则库统计（AC-06），因此 **不依赖 Google Fonts CDN**（国内访问不稳定，且会阻塞渲染）。MVP 阶段走系统已有字体回退链；如后续自托管，放 `/assets/fonts/` + `font-display: swap`，中文子集 ≤180KB，不引入第二个中文字族。

### 8 级字号 + 1 个 Hero 扩展

| Token | px | 用途 | 行高 | 字距 | 字重 |
|---|---|---|---|---|---|
| `--text-xs` | 12 | 徽章、角标、字数计数 | 1.5 | `0.01em` | 500 |
| `--text-sm` | 13 | 辅助说明、字段提示、免责 | 1.7 | `0.01em` | 400 |
| `--text-base` | 14 | 卡片正文、按钮、表单 | 1.7 | `0` | 400 / 按钮 500 |
| `--text-md` | 16 | 主要阅读正文（报告长文） | 1.7 | `0` | 400 |
| `--text-lg` | 18 | 区块标题 | 1.5 | `-0.005em` | 600 |
| `--text-xl` | 22 | 页面级小节标题 | 1.35 | `-0.005em` | 600 |
| `--text-2xl` | 28 | 结果关键数值（风险条数） | 1.25 | `-0.015em` | 600 |
| `--text-3xl` | 36 | 报告主标题 | 1.25 | `-0.015em` | 600 |
| `--text-display` | clamp(30→44) | 仅 landing 第一屏 | 1.22 | `-0.015em` | 600 |

**字重三级**：400 Read（正文）/ 500 Emphasize（按钮、小标题、徽章）/ 600 Announce（页面主标题、关键数值）。
**禁止**：正文 12px 以下、`font-weight: 700+` 堆砌、全大写无字距（`.caps` 类必须带 `0.08em`）。

---

## 4. Components

### 图标系统（P0 红线：无 emoji）
**锁定一套：Lucide**（`https://lucide.dev`，**ISC License**，24×24 网格，描边风格）。
- 描边统一 `stroke-width: 1.75`，`currentColor`，`stroke-linecap: round`
- 尺寸只有三档：`16px`（徽章/正文内）/ `20px`（按钮内）/ `24px`（导航与区块强调）
- 实施方式：**内联 SVG 字符串**（SPEC §7.2 定稿；无构建、无 CDN、无 icon font、无额外请求、无 404 风险；离线或内网演示不会丢图标）
  ```html
  <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor"
       stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"
       aria-hidden="true" focusable="false">
    <path d="…"/>   <!-- 直接从 Lucide 拷 path，删掉原文件的 width/height/class -->
  </svg>
  ```
- 每个图标自带 `viewBox="0 0 24 24"`、`fill="none"`、`stroke="currentColor"`、`stroke-width="1.75"`、`stroke-linecap="round"`、`stroke-linejoin="round"`、`aria-hidden="true"`、`focusable="false"`；颜色由 Token 经 `currentColor` 传递，**不在 SVG 内写任何色值**
- **禁止**在 `<svg>` 上写内联 `style`（CSP `style-src 'self'`）；尺寸只用 `width`/`height` 属性或 CSS 类。内联 `<svg>` **元素**本身不受 CSP 限制（CSP 管的是内联 `style` 属性和 `<style>` 块），所以内联方案与 CSP 并不冲突
- 「无构建」的代价接受：同一图标会在不同位置重复若干份 path，页面图标总量 ≤20，体积可忽略；换来零额外请求与零 404 风险
- 全项目只用这一套，**不得混入 Heroicons / Feather / 手绘示意图形**

本项目所需图标清单（全部取自 Lucide，命名即 Lucide 图标名）：

| 位置 | Lucide 名 | 尺寸 |
|---|---|---|
| 品牌标记 | `shield-check` | 24 |
| 开始体检（主按钮） | `scan-text` | 20 |
| 载入示例（次按钮） | `clipboard-paste` | 20 |
| 复制 / 一键复制 | `copy` | 16 |
| 高风险 | `octagon-alert` | 16 |
| 中风险 | `triangle-alert` | 16 |
| 提示级 | `info` | 16 |
| 依据条文 | `book-open` | 16 |
| 修改建议 | `pen-line` | 16 |
| AI 标识通过 | `badge-check` | 20 |
| AI 标识缺失 | `badge-alert` | 20 |
| 加载中 | `loader-circle`（`animation: spin 900ms linear infinite` —— **唯一允许超过 240ms 的动效**，因为它是持续循环而非一次性过渡；`prefers-reduced-motion` 下改为静态图标 + 文案） | 20 |
| 重试 | `refresh-cw` | 20 |
| 错误 | `circle-alert` | 20 |
| 展开/折叠 | `chevron-down` | 16 |
| 移动端导航 | `menu` / `x` | 24 |

### 按钮

| 变体 | 背景 | 文字 | 边框 | 用途 |
|---|---|---|---|---|
| Primary | `--accent` | `--accent-on` | 无 | 每屏唯一主操作（开始体检） |
| Secondary | 透明 | `--accent-line` | `1px --border-strong` | 载入示例 |
| Ghost | 透明 | `--muted` | 无 | 报告内次要动作（复制、折叠） |

- 尺寸：`padding: 10px 16px`，`border-radius: --radius-sm`，`font-size: --text-base`，`font-weight: 500`
- 最小点击区 **44×44px**（移动端 padding 提到 `12px 18px`）
- 状态：default / hover（`--accent-hover`）/ active（`--accent-active`，`translateY(1px)` 90ms）/ focus-visible（`--focus-ring`）/ **disabled**（`opacity: .5` + `cursor: not-allowed`，不用灰色替换颜色）/ **loading**（图标换 `loader-circle` 旋转 + 文案「正在比对 N 条规则」，`aria-busy="true"`，**保留原宽度不抖动**）

### 输入框（textarea）
- 边框 `1px --border-strong`（3.41:1，不是浅灰）
- focus：`border-color: --accent-line` + `box-shadow: --focus-ring`
- error：`border-color: --risk-high` + 下方 `--risk-high` 文案（`aria-describedby` 关联）
- 右下角实时字数 `当前/20000`，`--text-xs` `--meta`；超 90% 转 `--risk-med`，超限转 `--risk-high`
- 占位符是**说明性示例**（"粘贴需要体检的文案，例如：本店新品全网最低价，国家级认证……"），不是占位空话

### 卡片
- `--surface` 底 + `1px --border` 边 + `--radius-lg`(12px) + **无阴影**（`--elev-flat`）
- hover：`border-color: --border-strong`（**不做位移、不做放大**）
- 全站禁止：`border-left: 3px solid 强调色`（AI 味）、边框 + 模糊阴影叠加（幽灵卡片）、圆角 ≥16px

### 风险条目（Finding）—— 本项目最核心的组件

**PRD 硬口径**：每条必须三件套齐全 —— ① 命中原句（带上下文，不是孤立词）② 依据（条文名/规则名）③ **可直接替换的写法**。
**视觉层级反过来**：让「建议」比「标红」更显眼。所以红色只出现在 3px 色条 + 小徽章 + 一行软底 `<mark>`，**「建议」用最大字号、最深前景、占最大面积**。

```
┌───────────────────────────────────────────────────┐
│▎ 高风险 · 广告法/绝对化用语                          │  ← 3px 色条 + 徽章 + 分类（--text-sm --muted）
│                                                     │
│  命中原文                                            │  ← --text-sm --muted，1 行上下文，命中词 <mark>
│  …本店新品为全网最低价，国家级认证，欢迎选购…            │
│                                                     │
│  ┌ 建议这样改 ──────────────────────────────────┐   │  ← 本卡最高权重：--text-md --fg 400 lh1.7
│  │ 把「全网最低价」换成可验证的具体表述：              │   │     软底 --surface-2 + 左内边距 14px
│  │ 「同规格商品中价格较低，近 30 天成交价 89 元起」      │   │     标题用 12px 500 --fg（唯一比正文小的字）
│  │                          [复制这条建议]        │   │
│  └───────────────────────────────────────────────┘   │
│                                                     │
│  依据 · 《广告法》第九条第（三）项                      │  ← 最小权重：--text-sm --muted lh1.85
│  不得使用"国家级""最高级""最佳"等用语                   │
└───────────────────────────────────────────────────┘
```

**层级纪律（这是"别人只标红，我们帮改好"的唯一视觉证据）**：
| 元素 | 字号 | 色 | 面积 | 权重 |
|---|---|---|---|---|
| 建议改法 | `--text-md`(16) | `--fg`(15.1:1) | 最大（独立软底块） | **1** |
| 命中原文 + `<mark>` | `--text-sm`(13) | `--fg-2` / mark 8.67:1 | 中 | 2 |
| 分级徽章 + 分类 | `--text-xs`(12) | 语义色 | 小 | 3 |
| 依据条文 | `--text-sm`(13) | `--muted`(4.72:1) | 小 | 4 |

- 左色条仅 3px；色条 + 徽章文字 = 分级的**唯一**载体，不染底、不染整卡（避免"整页红"的焦虑）
- 命中词用 `<mark>` + `--mark-bg`/`--mark-fg`（软底不盖满整行），**不用等宽字体做命中标记**——等宽留给「条文编号」与「耗时」，避免两处都用等宽导致区分失效
- 命中原文必须含上下文（前后各 ~12 字），由 `start/end`（左闭右开，`end-start == matched.length`）切片还原
- 建议块内「复制这条建议」为 Ghost 按钮，16px 图标，点击后原地变「已复制」160ms 后复原，不弹 Toast
- 依据条文块：`--surface-2` 底 + `1px --border-soft` + 左内边距 12px，行高 1.85（密集阅读）
- **AI 标识条目例外**：`ai-label-missing` 的 `matched` 为空、`start=end=0`，**不得拿去切片**，渲染为独立的「AI 标识」块（放在总览行与 findings 列表之间）。**且只渲染一次（SPEC AC-08）——findings 列表必须过滤掉它，重复渲染算缺陷**。AI 标识区块只读 `ai_label` 字段，**不从 `categories` 里取**（"AI 标识"不是规则分类）。
- **建议来源 `suggestion_source`（`rule` | `llm`）**：`rule` 时**不加任何标注**（首交全量是 rule，降级即常态，标注"规则生成"只会让用户以为功能不全）；`llm` 时在建议块末尾加一行 12px `--meta` 小字「模型改写」。
  **该字段只用于界面，不进埋点 payload**——`/events` 契约已冻结，事件只带 `rule_id`，不加 `suggestion_source`；按来源拆分采纳率放 11 月。字段仍须原样取到、不得丢弃（否则 `llm` 分支永远不触发）。

### 徽章 / Toast / 空状态
- 徽章：`--radius-pill`，`padding: 2px 10px`，`--text-xs` 500，`letter-spacing: 0.04em`
- Toast：底部居中，`--elev-raised`，`--radius-md`，160ms 淡入，2.4s 自动消失，`role="status"`
- 空状态：图标 24px `--meta` + 一句**具体引导**（不是"暂无数据"）+ 一个动作

---

## 5. Layout & Spacing

- 间距基准 **4px 网格**，只允许 `4 / 8 / 12 / 16 / 20 / 24 / 32 / 40 / 48 / 64`（禁止 5/7/13/15/22/30）
- 容器 `--container-max: 1080px`，移动端 gutter 16px
- 报告长文列 `--container-narrow: 720px`（中文 25-37 字/行）
- 节区节奏：桌面 64px / 平板 48px / 手机 32px
- 栅格：桌面 12 列 gap 24 / 平板 8 列 gap 16 / 手机 4 列 gap 12
- 断点：**640 / 768 / 1024**（mobile-first 写，向上叠加）

### 页面结构（三视图 = 一条旅程）

> MVP 为单页应用（SPEC §6），因此「工具页 / 报告页 / landing」定义为**同一路由下的三个视图**，不做三个独立 HTML，避免路由与构建成本。P1 再拆 `/report/:id` 分享页。

#### 视图 A · Landing（`/` 首屏，滚动前）
| 区块 | 组件 | 信息层级 |
|---|---|---|
| 1 | 顶栏：`shield-check` + 品牌名 + 3 个锚点导航（开始体检 / 工作方式 / 合规声明） | 三级 |
| 2 | Hero：`eyebrow`（**改为小号 `--meta` 全大写带 0.08em 字距，不再用暖色**）→ H1「别人只标红，我们帮改好。」→ 一句 `lede`（说清"依据条文 + 修改建议 + AI 标识检查"） | **一级** |
| 3 | **规则库统计行（AC-06，3 秒内必须可见，绝不折叠、不进折叠区）**：`{total_rules} 条规则` · `广告法 {n} / 医疗健康 {n} / 平台规则 {n} / 金融理财 {n} / 教育培训 {n} / 通用表达 {n}` · `最近更新 {updated_at}` · `{version}`。<br>**四项全来自 `/api/v1/meta`**（`total_rules` / `categories` / `updated_at` / `version`），字段名按契约不变；分类**当前固定六类**、合计等于 `total_rules`；**展示顺序在前端做**：按条数降序、同数按分类名排序（不依赖对象键顺序）。<br>**容错（比白名单更重要）**：`categories` 的 key 已是中文可直接展示，无需映射表；但遇到**不认识的 key 必须原样展示该 key**，不得因不在六类白名单里就丢弃或显示空白——丢项会让合计与 `total_rules` 对不上，一眼就被看出问题。<br>`version` 当作**原样字符串**展示（当前值 `2026.10`，可加 `v` 前缀），**不做数字解析、不拼接任何后缀**（出现 demo/骨架/草稿等阶段词属纪律违规）。以**文本行**呈现，不做 6 张 KPI 卡 | 四级 |
| 4 | **工具卡（首屏可见，不折叠）** ← 核心，不做"点击展开" | 一级 |
| 5 | 工作方式：3 栏（规则引擎 → AI 补改法 → 标识检查），编号用 `--meta` 数字不用彩色 | 三级 |
| 6 | 页脚：定位说明 + 免责（不构成法律意见） | 五级 |

> **反 AI 模板约束**：Hero 不做"居中 CTA + 抽象 3D 图形 + 三个图标卡片"；本页 Hero 左对齐、无插画、下方直接是**可用的输入框**——产品本身就是首屏视觉。

#### 视图 B · 工具页（输入态，`#tool` 锚点 / 滚动后聚焦）
组件清单：`textarea`（min-height 190px，桌面 / 160px 移动）/ AI 内容勾选框 / 字数计数 / 载入示例 / 开始体检 / 隐私与限流说明。
- 勾选框：`16px`，`accent-color: --accent`，label 与框垂直居中，**label 可点击区域覆盖整行 ≥44px**
- 说明文案（固定）："文本仅用于本次检测，默认不落库；同一 IP 每小时最多 60 次。本工具提供自查参考，不构成法律意见。"

#### 视图 C · 报告页（结果态，`#results`）
```
① 总览行   ─ 一行式（采纳 PM 口径，不做 4 张同尺寸卡）：
             高风险 2 · 中风险 3 · 低风险 4        比对 {total_rules} 条 · 耗时 18 毫秒
             ├ 数字 --text-2xl 600；标签 --text-sm --muted，单位跟在数字后
             ├ 分隔用 1px 竖线 --border，不用卡片包裹
             └ 耗时取 summary.elapsed_ms（整数毫秒），**按量级切换单位**：
               <1000 → `{n} 毫秒`（实测常见 10-40，直接显示 `18 毫秒`）
               >=1000 → `{(n/1000).toFixed(2)} 秒`（如 `1.24 秒`）
               禁止无条件 /1000：18ms 会变成 `0.02 秒`，看起来像出错
               缺失则不渲染耗时区，绝不编造
               仅「高风险 > 0」时该数字用 --risk-high，其余保持 --fg
② AI 标识块 ─ 通过（--success-soft）或 缺失（--risk-med-soft）+ 可复制标识话术
③ 分级筛选  ─ 全部 / 高风险 / 中风险 / 低风险（chips，选中态 --accent-tint + --accent 文字）
④ 条目列表  ─ Finding 组件 × N，按 高 → 中 → 低 排序
⑤ 免责声明 ─ API 返回的 disclaimer **原样完整展示，不截断、不改写、不折叠**
⑥ 操作区   ─ [复制全部建议] [重新体检]   ← 移动端吸底
```
> 少用一张"4 个相同卡片"的网格，同时满足两条纪律：① PM 要的一行式总览；② 本项目反模式清单里「同尺寸卡片网格无限重复」。手机端总览行允许折为两行（风险计数一行、耗时另起），仍不改成卡片。
- **无命中时的表述（信任关键，SPEC v0.7 定稿口径）**：
  > 标题：`未发现明显违规表述`
  > 正文：`本次已比对 {total_rules} 条规则。建议发布前再用平台官方预检复核一遍 —— 合规风险还会来自平台未公开的审核细则、行业资质与上下文语境。`
  > 动作：`查看规则库覆盖范围`（Ghost）
  > 并保留「已比对 {total_rules} 条规则」作为可信度锚点 —— **绝不使用"暂无数据 / 100% 安全 / 完全合规 / 通过审核"**。
- 免责声明有两个位置、不重复：① 页脚固定合规声明（永远在）；② 报告底部渲染 API `disclaimer` 原文（可能更详细）。两者都不可折叠。

---

## 6. Depth & Elevation

| 层级 | 值 | 用在哪 |
|---|---|---|
| flat | `none` | 默认。卡片靠 1px 边框分层 |
| ring | `0 0 0 1px --border` | 需要边框但不受 layout 影响时 |
| raised | `0 1px 2px rgba(16,36,56,.05), 0 4px 8px rgba(16,36,56,.05)` | 仅移动端吸底栏、Toast |

- 阴影模糊 **≤8px**。禁止"1px 边框 + ≥16px 模糊"同时出现在同一元素（幽灵卡片）。
- 禁止装饰性毛玻璃 / 背景模糊（现有 `header` 的 `backdrop-filter: blur(8px)` 仅因吸顶需要，保留但降为 `blur(6px)` 并确保 `background` 不透明度 ≥95%）。
- z-index：base 0 / sticky 100 / 吸底栏 200 / overlay 300 / toast 400。

---

## 7. Do's & Don'ts

### √ 应该做
1. 每屏只用一次强调色做主动作，其余全部用 `--accent-line` / `--muted`。
2. 风险分级**永远配文字标签**（高风险/中风险/提示），不靠颜色单独表意。
3. 命中词用等宽字体，与用户原文形成视觉区分。
4. 报告里每条都给出「依据 + 改法」，缺一不可。
5. 无命中时说明**规则库比对了几条、边界在哪**，把不确定性讲清楚。
6. 移动端主动作吸底，单手可触达。
7. 所有数字（比对条数、字数、耗时）真实来自 API，不编造。
8. 动效只用于"状态发生了什么"（160ms 淡入、spinner 旋转），不做入场编排。

### × 不应该做
1. × 用表情符号充当功能图标（放大镜、对勾、警告三角等一律换成 Lucide SVG）。
2. × 紫色→粉色渐变、发光边框、装饰性毛玻璃"三位一体"。
3. × 卡片左侧 3px 以上彩色强调边（除 Finding 的 3px 分级色条这个**语义**用法）。
4. × 圆角 ≥16px 的"过度圆滑"卡片。
5. × 文案空洞化：`Welcome to` / `开始你的合规之旅` / `一站式解决方案` / `赋能` / `无限可能`。
6. × 虚构指标：`10,000+ 用户信赖` / `99.9% 准确率`（无来源）。规则条数必须来自 `/api/v1/meta`。
7. × 弹跳缓动 `cubic-bezier(0.68,-0.55,0.265,1.55)`；任何 >240ms 的动画。
8. × 组件内硬编码色值（唯一例外 `#fff`/`#000`）。
9. × `outline: none` 而不提供 `--focus-ring` 替代。
10. × 用"完全合规 / 100% 安全 / 保证通过"这类承诺性表述。

---

## 8. Responsive & Accessibility

### 响应式（mobile-first）
| 断点 | 行为 |
|---|---|
| `<640px` | 单列；顶栏导航收为 `menu` 图标 + 抽屉；概览卡 **2×2**；Finding 左色条改**顶部 2px 横条**；主按钮**全宽**；底部出现**吸底操作栏**（开始体检 / 复制全部，`env(safe-area-inset-bottom)` 兜底）；textarea 160px；节区间距 32px |
| `640–768px` | 单列加宽；概览卡 2×2；吸底栏保留 |
| `768–1024px` | 概览卡 4 列；Finding 恢复左色条；顶栏导航展开 3 项 |
| `>1024px` | 满布局，容器 1080px，节区 64px |

- `viewport` 已含 `width=device-width, initial-scale=1.0`，**不得加 `user-scalable=no`**
- 任何断点下 **无横向滚动**（`overflow-x: hidden` 不是解法，是要修布局）
- 触摸目标 ≥44×44px，相邻按钮间距 ≥8px

### 无障碍（WCAG 2.1 AA 基线）
| 项 | 要求 |
|---|---|
| 文本对比度 | 正文 ≥4.5:1（已实测，见 §2 表）；大字 ≥3:1 |
| UI 边界 | 输入框边框 3.41:1（WCAG 1.4.11） |
| 焦点 | 全站 `:focus-visible` 用 `--focus-ring`（2px 白 + 4px 半透明深蓝），**不允许移除** |
| 键盘 | Tab 顺序 = 视觉顺序：导航 → 输入框 → 勾选框 → 载入示例 → 开始体检 → 结果筛选 → 条目动作；结果区出现后焦点移到结果标题（`tabindex="-1"`），不劫持 |
| 屏幕阅读器 | 结果区 `aria-live="polite"`；`aria-busy="true"` 表示加载；错误 `role="alert"`；字数计数 `aria-live="off"` 避免刷屏；图标 `aria-hidden="true"` + 按钮 `aria-label` |
| 表单 | label 显式可见（不用 placeholder 顶替）；说明用 `aria-describedby` |
| 动效 | `prefers-reduced-motion: reduce` 下关闭位移与淡入（已在 design-tokens.css 兜底） |
| 缩放 | 200% 文字放大不横向滚动、不裁切；正文基准 16px，辅助不低于 12px |
| 标题层级 | 全页唯一 `<h1>`；报告标题用 `<h2>`，条目用 `<h3>`，不跳级 |
| 语言 | `<html lang="zh-CN">`（已具备） |

### 四态设计（每个有状态组件都要覆盖）

| 状态 | 触发 | 视觉 | 文案（写死，不允许"加载中..."） | 实现约束 |
|---|---|---|---|---|
| **① 空态 Empty** | 首次进入，未输入 | 工具卡可见，结果区**不渲染**（不显示空骨架，避免"页面没东西"的错觉）；textarea 聚焦态给出示例 | 占位符：`粘贴需要体检的文案，例如：本店新品全网最低价，国家级认证……`；字数 `0/20000` | **按钮保持可点，不 disabled**（PM 口径：未输入点检测要"引导粘贴，不报错"）。点击空提交 → 焦点移到 textarea + 显示 `.hint-guide`：「先把要体检的文案粘贴到上面，再点开始体检」——用中性引导样式（`--muted` + `info` 图标），**不用红色错误条、不出 `role="alert"`、不调接口** |
| **② 加载态 Loading** | 点击开始体检 | 按钮内图标换 `loader-circle` 旋转，按钮 `aria-busy="true"`、宽度锁定不抖；textarea `readonly`；结果区插入 **骨架屏**（总览行占位 + 2 条 Finding 灰块，1200ms 微光扫过，`prefers-reduced-motion` 下静态） | 按钮：`正在比对 {total_rules} 条规则`；结果区顶部 `role="status"`：`规则引擎比对中，通常不超过 2 秒` | **禁止**用 `textContent` 覆盖按钮内容（会吞掉内联 SVG 图标）——改用 `.is-loading` 类切换内部两个 svg 与 `<span class="btn-label">`；2 秒未返回则追加"仍在比对，长文可能需要更久" |
| **③ 错误态 Error** | 网络失败 / 429 / 422 / 503 | 工具卡下方插入 `--risk-high-soft` 底 + `--risk-high` 边的内联错误条（**不是顶部 toast**），带 `circle-alert` 16px + 重试按钮。5xx/网络类错误若响应含降级结果，仍展示规则结果并加一条 `--risk-med-soft` 提示条 | 说"发生了什么 + 怎么办"，不出现堆栈；<br>**429：直接展示响应 `detail` 原文**（例：`本次检测额度已用完，约 31 分钟后可再次检测`），**不自己编"系统繁忙"**；同时按 `Retry-After` 头显示倒计时并禁用提交<br>**422（超长）：取 `detail[0].msg`** 转成中文提示；**绝对不在前端自动截断后送检**（截断会漏报）<br>网络：`网络连接失败，文本仍保留在输入框中，请检查网络后重试。`<br>503：`检测服务暂时不可用，请稍后再试，或先按平台官方预检自查。` | **绝不清空用户输入**；错误条 `role="alert"`；重试按钮 44px；429 期间按钮 `disabled` 且倒计时每秒刷新（`--text-sm`，不闪动）；**不把 `detail` 数组/JSON 直接渲染** |
| **④ 结果态 Populated** | 检测成功 | 总览行（一行式 + 耗时）→ AI 标识块 → 分级 chips → Finding 列表 → API disclaimer → 操作区；240ms 淡入（仅 opacity + 4px 上移） | 有命中：`高风险 2 · 中风险 3 · 低风险 4` + 右侧 `比对 {total_rules} 条 · 耗时 18 毫秒`（`elapsed_ms` 按量级切换：<1000 用毫秒、>=1000 用两位小数秒）；无命中：`未发现明显违规表述` / `建议发布前再用平台官方预检复核一遍`（见 §5 视图 C，禁用"暂无数据 / 完全合规"） | 结果区 `aria-live="polite"`；`scrollIntoView({ block: 'start' })` 并聚焦结果标题；`disclaimer` 必须原样完整渲染 |
| **⑤ 边界态 Edge**（附加） | 超长文本 / 零结果 / 极多命中 | 文本超 20000 字：字数计数转 `--risk-high`，输入框下给一条 `--risk-high` 提示，**提交按钮置灰但不截断任何字符**；命中 >20 条：列表折叠为「显示全部 {n} 条」，前 10 条常显（`<details>` 保键盘可达）；命中词超 24 字符：`<mark>` 内 `overflow-wrap: anywhere` 不撑破卡片 | `已超出 20000 字上限 {n} 字，请删减后重试`（若走服务端 422，则展示 `detail[0].msg`） | 注意！**必须移除 textarea 的 `maxlength="20000"`**：浏览器会在粘贴时静默截断，用户以为全文已检、实际漏报，这正是产品明确不接受的行为。改为字数计数 + 禁用提交 + 服务端 422 兜底；长文本不截断用户内容 |

---

## 9. Agent Implementation Guide

### 引入顺序（前端唯一需要动的两行）
```html
<link rel="stylesheet" href="/assets/styles.css">
<link rel="stylesheet" href="/assets/design-tokens.css">   <!-- 必须在其后 -->
```
`design-tokens.css` 末尾的 **Legacy Alias** 会把现有 `--color-ink / --color-navy / --radius-s / --shadow-soft / --font-sans` 全部指向新 Token，因此 **styles.css 不需要改一个字符**即可吃到新色值与收紧后的阴影。

### 已知实现坑（前端务必处理）
1. **`app.js:65` 用 `elements.checkBtn.textContent = "体检中..."` 会抹掉按钮内的图标**，且按钮宽度会跳动。改为切换 `.is-loading` 类，内部结构：
   ```html
   <button class="btn btn-primary" id="checkBtn">
     <svg class="icon-scan" viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.75" aria-hidden="true" focusable="false"><path d="…"/></svg>
     <svg class="icon-spin" viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.75" aria-hidden="true" focusable="false"><path d="…"/></svg>
     <span class="btn-label">开始体检</span>
   </button>
   ```
   CSS：`.btn.is-loading .icon-scan{display:none} .btn.is-loading .icon-spin{display:inline-block;animation:spin 900ms linear infinite}`，`.btn-label` 文案由 JS 改。
2. **`app.js:153` 无命中时复用 `.finding.level-low` 卡片**——层级上正确，但需要换成专用 `.finding.is-empty`，避免出现"空的风险条目"这种自我矛盾的语义（会拿到徽章 + 左色条的奇怪组合）。文案采用 §5 视图 C 的 PM 定稿口径。
3. 现有 `.panel` 同时有 `1px border` + `blur 30px` 阴影 = 幽灵卡片，Token 已把 `--shadow-soft` 收窄到 8px；建议前端直接把 `.panel` 改为 `box-shadow: var(--elev-flat)`。
4. `header` 的 `backdrop-filter: blur(8px)` 配 92% 背景会让正文透出来干扰阅读，改为 96% 不透明度 + `blur(6px)`。
5. `meta-item` 用 `--radius: 999px` 的 pill 是对的，但 `font-size: 12.5px` 属非标值 → 统一 `--text-sm`(13px)。
6. 全站 `font-size: 15px` 的 body 基准改为 `--text-md`(16px)，15px 会让 200% 缩放下的行宽计算失准。
7. **原文高亮必须防 XSS**：只允许 `textContent` 分段 + `document.createElement('mark')` 拼接（按 `start/end` 左闭右开切片），**禁止把用户文本拼进 `innerHTML`**。切片前先校验 `end > start && (end - start) === matched.length`，不满足则跳过该条高亮但仍渲染该条 Finding。
8. **`ai-label-missing` 不可切片**：`matched` 为空、`start = end = 0`，必须单独渲染为「AI 标识」块（见 §4），塞进 findings 列表会得到一条高亮空字符串的怪条目。
9. **CSP `style-src 'self'`**：不允许任何 `style="..."` 内联样式，也不允许 `onclick=` / `oninput=` 内联事件。所有状态（`.is-loading` / `.is-error` / `.is-empty` / `.is-collapsed`）走 CSS 类 + `addEventListener`。高亮色也不得写内联，用 `--mark-bg` / `--mark-fg` 类。
10. **免责声明**：`disclaimer` 字段原样完整渲染，**不截断、不换行折叠、不二次改写**；与页脚固定合规声明分开，不要合并成一句。
11. **`summary.elapsed_ms`**：整数毫秒（`type: integer`，实测常见 10-40）。**按量级切换单位**：`<1000` 显示 `{n} 毫秒`，`>=1000` 显示 `{(n/1000).toFixed(2)} 秒`。**禁止无条件 `/1000`** —— 18ms 会显示成 `0.02 秒`，用户会以为出错。缺失则不渲染耗时区，不编造；前端不做耗时打点（服务端已实测）。
12. **移除 textarea 的 `maxlength="20000"`**：浏览器会在粘贴超长文本时静默截断 → 用户以为全文已检、实际漏报，产品明确不接受。改为「字数计数 + 超限置灰提交 + 服务端 422 兜底」，**任何情况下不自动截断用户输入**。
13. **`ai-label-missing` 全页只渲染一次**（SPEC AC-08）：findings 列表必须 `filter(f => f.rule_id !== 'ai-label-missing')`，AI 标识区块只读 `ai_label` 字段，不从 `categories` 取。

### 埋点（POST /api/v1/events）—— 纯旁路，零 UI
**设计原则：埋点不存在于用户的视觉世界。** 不显示 loading、不显示成功、不显示失败、不重试、不影响检测流程时序。
| 时机 | event | 必带字段 | UI 关联 |
|---|---|---|---|
| 结果区渲染完成并可见后 | `check_result_viewed` | `elapsed_ms`、`finding_count`、`by_level{high,medium,low}` | 无 |
| 点击「复制这条建议」 | `suggestion_copied` | `rule_id`（复制的是哪条） | 按钮原地变「已复制」160ms 后复原 |
| AI 标识块命中/提示时 | `ai_label_flagged` | 不带 `rule_id` | 无 |
| 出现 429/网络错误等 | `error_occurred` | `error_code`（如 `http_429` / `network_error`） | 已有错误条，埋点不额外提示 |

- `check_submitted` **由服务端记，前端绝不上报**（否则双计）。
- `timestamp` 用 `new Date().toISOString()`；`device` 取 `desktop/mobile/tablet/unknown`（按视口宽度判断，与断点 640/768 对齐）。
- 单批 ≤20 条；`fetch` + `.catch(() => {})` 静默丢弃；**不得 `await` 在渲染路径上**，也不得因埋点失败阻塞或延迟任何可见状态。
- 埋点失败**不重试**：重试会在弱网下堆请求，且评测环境无价值。
- 文案层面：**任何埋点相关的可见文字都不允许出现**（不要写"正在保存记录"这类假进度）。

### CSS 变量定义
完整定义见 `frontend/assets/design-tokens.css`（A1 / A2 / B-slot / C-ext 四层分区 + Legacy Alias）。
机器可读版见 `docs/design-tokens.json`，前端可直接 `import tokens from './design-tokens.json'` 生成主题。

### 技术栈提示
- 栈锁定为原生 HTML/CSS/JS、无构建（ADR-001）→ **不引入 Tailwind 编译链**；如需工具类，手写 12 个原子类即可。
- 图标走**内联 SVG 字符串**（Lucide 拷贝，SPEC §7.2 定稿），**不引 CDN、不用 icon font、不做 sprite/`<use>`**。内联 `<svg>` 元素不违反 CSP，但不得带内联 `style` 属性。
- 中文字体不加载 web font，靠系统回退链；若后续自托管，只加一个中文字族，子集 ≤180KB。

### 变更记录
| 日期 | 变更 | 原因 |
|---|---|---|
| 2026-10-26 | 初版 v1.0；强调色由 amber 收敛为单一 navy，amber 降级为中风险语义色 | amber 同时被用作品牌强调与中风险，语义打架；合规工具需要冷色权威感 |
| 2026-10-26 | 圆角上限 16→12px，`--shadow-soft` 模糊 30→8px | 消除幽灵卡片与过度圆滑的 AI 观感 |
| 2026-10-26 | `--color-ink-3` 映射由 `#7b849e` 改为 `--muted #5C6A80` | 原值对比度 3.9:1，未达正文 4.5:1 |
| 2026-10-26 | 对齐 PM 口径：总览由 4 卡改为**一行式 + 耗时**；无命中改用定稿文案「未发现明显违规表述」；空提交改为**引导不报错**；错误态按 429/422/503 分支；免责声明原样不折叠 | PM 反馈 PRD 硬口径，避免返工 |
| 2026-10-26 | 图标落地方式由「内联 SVG 拷贝」改为单文件 sprite `icons.svg` + `<use>` | 初判 CSP 需外链资源 |
| 2026-10-26 | 补 `--accent-warm`（amber 品牌点，面积 ≤1%）、`--mark-bg/fg` 高亮 Token | 保留 PRD 的 navy+amber 双色，但用面积规则隔离品牌色与风险语义 |
| 2026-10-26 **v1.1** | 图标回退为内联 SVG 字符串（当时依据架构师 SPEC §7.2 消息）；新增 `suggestion_source` 渲染规则、`/api/v1/events` 旁路埋点设计、429 Retry-After 处理、422 超长禁用自动截断；耗时改按 `0.32 秒` 两位小数展示；`categories` 六类与排序规则写入统计行 | 架构师 SPEC §7.2 与 openapi.yaml 最终版 |
| 2026-10-26 **v1.2** | 图标一度改为 **SVG sprite `icons.svg` + `<use>`** | 当时 team-lead 称「统一 sprite，SPEC 已改」，但随后 SPEC §7.2 与架构文档均确认回到内联 |
| 2026-10-26 **v1.3（当前）** | 图标**最终定稿内联 SVG 字符串**（覆盖 v1.2）；耗时改为**按量级切换单位**（<1000 → 毫秒，>=1000 → 两位小数秒）；`suggestion_source` 明确**不进埋点 payload**，只作用于界面；`categories` 增加「不认识的 key 原样展示」容错；`version` 定为原样字符串不解析 | 与 SPEC v0.7 §7.2、openapi.yaml、ARCHITECTURE 1.1 三处对齐。**图标以本版为准：内联，不是 sprite** |

---

## 附录 A · 视觉验收清单（QA / 总监门禁逐条打勾，12 项）

| # | 检查项 | 判定方法 | 通过标准 |
|---|---|---|---|
| 1 | **零 emoji 图标** | 对 `frontend/**` 跑 emoji 正则扫描（见 P0 检测式） | 命中数 0；所有图标为**内联** Lucide SVG（ISC），`viewBox="0 0 24 24"`、`stroke-width` 1.75、尺寸仅 16/20/24、带 `aria-hidden` + `focusable="false"`、无内联 `style` |
| 2 | **无紫粉渐变** | 搜 `gradient` 与 `#7C3AED / #A855F7 / #9333EA / #EC4899` | 命中数 0；全站零渐变 |
| 3 | **色值 Token 化 + 无内联样式** | 搜 CSS 裸 `#` 十六进制（排除 `design-tokens.css` 定义处与 `#fff/#000`）；搜 HTML/JS 里的 `style="` 与 `onclick=` | 组件层裸色值 0；内联样式 0 处（CSP `style-src 'self'`） |
| 4 | **强调色克制** | 单屏截图点数 `--accent` 可见元素；查 `--accent-warm` 是否越界 | `--accent` ≤2 处且为 CTA；`--accent-warm` 面积 ≤1% 且不在徽章/数值/按钮上 |
| 5 | **对比度** | 抽查正文、辅助文本、输入框边框、徽章、`<mark>` 文字 | 正文 ≥4.5:1；UI 边界 ≥3:1；实测值符合 §2 表 |
| 6 | **焦点可见** | 纯键盘 Tab 走完全流程 | 每一步都有清晰焦点环；无 `outline:none` 裸奔 |
| 7 | **移动端 375px** | DevTools 375×667 | 无横向滚动；主按钮可单手触达（吸底或首屏）；触摸目标 ≥44px |
| 8 | **四态齐备 + 文案对齐 PRD** | 空/加载/错误/结果 + 无命中；空提交、429、422 超长各打一次 | 空提交是**引导不是报错**；错误不清空输入；429 用 `detail` 原文 + `Retry-After` 倒计时并禁用提交；422 超长展示 `detail[0].msg` 且**未发生任何自动截断**；无命中=「未发现明显违规表述」且不含"暂无数据/完全合规" |
| 9 | **文案真实 + 三件套齐全** | 通读全部可见文案；逐条看 finding | 无 `Lorem ipsum` / `Welcome to` / `一站式` / `赋能`；数字全部来自 API（禁出现"128"这类无依据数字）；每条 finding 都有「命中原文 + 依据 + 可替换写法」；`suggestion_source=rule` 时不出现"规则生成"字样 |
| 10 | **无 AI 模板味** | 看首屏 3 秒 | 不是"大标题+副标题+居中 CTA+抽象图形"；首屏直接可用；总览不是 4 张同尺寸卡；卡片无左侧强调色边框、圆角 ≤12px、无边框+大模糊叠加 |
| 11 | **免责声明完整** | 对比 API `disclaimer` 与页面渲染 | 原样完整、不截断、不折叠、不改写；页脚固定声明独立存在 |
| 12 | **建议比标红更显眼** | 对一张 finding 截屏做高斯模糊 / 眯眼看 | 第一眼看到的是「建议这样改」块，不是红色徽章 |

## 附录 B · 交付物清单

| 文件 | 说明 |
|---|---|
| `docs/design-tokens.json` | 机器可读 Token（color / font / space / radius / shadow / motion / layout / icon / zIndex） |
| `frontend/assets/design-tokens.css` | 四层 CSS 变量 + Legacy Alias + a11y 基元（focus-visible / reduced-motion / selection） |
| `docs/DESIGN.md` | 本文件：9 节标准 + 页面结构 + 四态 + 移动端 + 无障碍 + 10 条验收清单 |
