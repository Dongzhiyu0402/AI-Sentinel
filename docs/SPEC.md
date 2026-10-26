# SPEC - 合规哨兵 v0.9（三文档对齐版）

> 日期：2026-10-26
> 依据：PRD v0.3 + ARCHITECTURE.md + DESIGN.md + CONVENTIONS.md
> 状态：待队长确认三文档后冻结

## 1. 产品定义

- 一句话：合规哨兵是发布前内容合规体检工具，回答"哪句话有问题、依据哪一条、换成什么"。
- 定位：**官方预检之前的自查**，不替代平台审核，不构成法律意见。
- 用户：一人公司主理人、接商单的兼职创作者。

## 2. MVP 范围（P0）

| # | 功能 | 验收要点 |
|---|---|---|
| 1 | 粘贴检测（≤20000 字） | 规则链路 2000 字 p95 ≤100ms；默认模式（未配置 LLM）下 /check 全链路 ≤2s；前端不得设置 maxlength 静默截断，超长由服务端 422 返回并提示"请分段检测" |
| 2 | 规则库 100 条 | 广告法 38 / 医疗健康 22 / 平台规则 16 / 金融理财 10 / 教育培训 8 / 通用表达 6；每条含 basis 与 suggestion；双人复核；Top 30 高频规则的建议必须是可直接粘贴的完整改写句 |
| 3 | 风险清单 | 返回 matched / start / end / basis / suggestion；按 high → medium → low 排序，同级按 start 升序，同一位置按 rule_id 升序 |
| 4 | AI 标识检查 | 独立区块；勾选含 AI 内容且无显式声明 → high 级 ai-label-missing + 可粘贴话术；**不计入 categories** |
| 5 | LLM 降级 | 未配置或超时仍返回规则结果，建议降级为模板，页面不报错 |
| 6 | 埋点 | POST /api/v1/events，白名单 2 事件（suggestion_copied / error_occurred）；`check_submitted` 仅服务端产生，前端上报被忽略；只写日志，不接收自由文本；不落原文、不落 IP |
| 7 | 公网部署 | PC 与手机可访问；/api/v1/health 通过；首页 3 秒内展示规则统计 |
| 8 | 限流 | 同 IP 60 次/小时；429 返回 `Retry-After` 秒数，文案"本次检测额度已用完，约 N 分钟后可再次检测" |
| 9 | 空态 / 错误态 | 未输入给引导；服务不可用给"稍后再试 + 人工复核建议"，不显示技术堆栈 |

## 3. 明确不做

视频/音频检测、涉政涉黄词库、小程序/App、用户系统与支付、历史记录与批量检测、模型训练、开放 API、自动发布、报告分享页（11 月）。

## 4. 技术栈（锁定）

FastAPI + 纯 Python Aho-Corasick + YAML 规则库 + 原生 HTML/CSS/JS 单页 + 阿里云轻量 + Nginx；图标 Lucide（ISC，1.75 描边）；无构建链路。

## 5. API 契约

| Method | Path | 说明 |
|---|---|---|
| GET | /api/v1/health | `{"status":"ok","version":"0.3.0"}` |
| GET | /api/v1/meta | `total_rules`、`categories`（六类，不含 AI 标识）、`version`、`updated_at` |
| POST | /api/v1/check | 请求 `{text, has_ai_content}`；响应 `summary / findings / ai_label / disclaimer`；`Finding` 含 `suggestion_source`（rule / llm） |
| POST | /api/v1/events | 前端埋点，白名单 2 事件：suggestion_copied / error_occurred；其余事件忽略；只写日志，不接收自由文本 |

错误体：保持 FastAPI 默认 `{"detail": ...}`（422/429/500）；前端统一映射中文，不展示技术堆栈。429 额外返回 `Retry-After` 响应头（秒），文案含"约 N 分钟后可再次检测"，与响应头同源计算。契约以 `docs/openapi.yaml` 为准，字段名不在前端二次改名。

## 6. 页面（单页三视图）

- `/`：Landing（首屏）→ 工具页（#tool）→ 报告页（#results），同一页；P0 不拆 `/report/:id`（11 月）。
- 报告区渲染规则：
  1. `rule_id = ai-label-missing` **不进 findings 列表**，只在 AI 标识区块展示；
  2. 列表为空时写"未发现明显违规表述"，并附"建议发布前再用平台官方预检复核一遍"，同时显示 `/meta` 返回的 `total_rules`；
  3. 所有"规则库 N 条"文案必须来自 `/meta` 的 `total_rules`，禁止硬编码；分类条数来自 `categories`，展示顺序按条数降序、同数按分类名排序。
  4. 总览行显示耗时（如"0.32 秒"），数值来自 `summary.elapsed_ms`；
- 组件：按钮 loading 用 `.is-loading` 类切换内部两个 `<span>`，禁止用 `textContent` 覆盖（会吞掉 SVG）。

## 7. 设计 Token（锁定，来源 docs/design-tokens.json）

| 类别 | 值 |
|---|---|
| 主色 | `#16324F`（hover `#203F63`，active `#0E2338`） |
| 背景 / 表面 | `#F4F6F9` / `#FFFFFF` |
| 文字 | 主 `#17202E`，次 `#3D4A5E`，弱 `#5C6A80` |
| 边框 | 装饰 `#DFE5EE`，交互 `#7E8CA1` |
| 风险 | 高 `#A32B32`，中 `#8A5D0E`，低 `#4B5B70`（各配 soft 背景） |
| 字号 | 12 / 13 / 14 / 16 / 18 / 22 / 28 / 36；正文 16px（Phase 3 从 15 调整） |
| 圆角 | 6 / 8 / 12 / 9999 |
| 布局 | 容器 1080px；断点 640 / 768 / 1024；点击目标 ≥44px |
| 图标 | Lucide（ISC），描边 1.75，尺寸 16/20/24，SVG sprite + `<use>`（详见 §7.2），不引 CDN |

纪律：组件内不硬编码色值；主色只有一支；`#A8731B` 仅作品牌标记（面积 ≤1%），不承担任何风险语义；中风险固定 `#8A5D0E`；风险三级色相梯度冻结，不得改动；不使用紫粉渐变。

### 7.1 字体（冻结）

- `--font-display` / `--font-body`：`"Public Sans", "HarmonyOS Sans SC", "Source Han Sans SC", "PingFang SC", "Microsoft YaHei", sans-serif`
- `--font-mono`：`"JetBrains Mono", "Sarasa Mono SC", ui-monospace, Consolas, monospace`
- 不加载 Google Fonts CDN：国内链路不稳定，直接拖累 AC-06 的 3 秒首屏，MVP 走系统回退链
- 后续若自托管中文字族：子集 ≤180KB，且只允许一个中文字族

### 7.2 图标（冻结）

| 项 | 冻结值 |
|---|---|
| 库 | Lucide（lucide.dev），ISC 许可，可商用、可内联拷贝；全项目唯一图标来源 |
| 实施 | SVG sprite（`frontend/assets/icons.svg`，`<symbol>` 自带 viewBox 24 / fill none / stroke currentColor / 1.75）：页面侧只写 width/height + aria-hidden + focusable=false |
| 描边与着色 | `stroke-width` 统一 1.75，颜色 `currentColor` 跟随 Token |
| 尺寸 | 仅 16 / 20 / 24px 三档 |
| 禁止 | 混用 Heroicons / Feather / 手绘形状替代图标；emoji 作功能图标（团队级 P0，出现即退回） |

Token 落地：`docs/design-tokens.json`（机器可读）、`frontend/assets/design-tokens.css`（须在 `styles.css` 之后引入，内含 Legacy Alias 覆盖 `styles.css` 既有 20 个变量，`styles.css` 不改动）。

## 8. 验收标准（EARS）

| 编号 | 标准 |
|---|---|
| AC-01 | When 提交 2000 字文本，规则链路稳态 p95 必须 ≤100ms、含冷启动首请求 ≤200ms；默认模式（首交不配 LLM）下 /check 全链路必须 ≤2s；演示模式启用 LLM 时规则结果先返回，LLM 2 秒超时即降级为模板，降级不计为失败、单独记降级率 |
| AC-02 | When 命中规则，必须返回 matched / start / end / basis / suggestion / suggestion_source |
| AC-03 | If 勾选含 AI 内容且无显式标识，必须返回 high 级 `ai-label-missing` 与可粘贴话术 |
| AC-04 | If LLM 未配置或超时，必须仍返回规则结果，建议降级为模板 |
| AC-05 | While 同一 IP 超过 60 次/小时，必须返回 429，携带 `Retry-After`（秒）与中文文案"本次检测额度已用完，约 N 分钟后可再次检测"（两者同源计算）；前端按 Retry-After 禁用提交并显示倒计时 |
| AC-06 | When 打开首页，必须在 3 秒内展示 `total_rules` / `categories` / `version` / `updated_at` |
| AC-07 | If 接口返回 422/500，页面必须显示中文可行动提示，不显示英文技术信息 |
| AC-08 | When `ai-label-missing` 存在，报告列表不得重复渲染该条 |
| AC-09 | 前端不得出现 emoji 功能图标与硬编码色值（`:root` 除外） |
| AC-10 | 10 篇公开处罚案例召回 ≥7/10；误报率抽 50 条、双人判定，目标 ≤20% |
| AC-11 | When 前端提交埋点事件，系统必须只接受 2 个白名单事件名（suggestion_copied / error_occurred），拒绝自由文本，日志不含原文与 IP |

## 9. 隐私与安全

- 不落库原文、不落 IP：日志只存哈希、耗时、命中计数与分类分布。
- `/check` 日志增加 `rule_hits` 字段：本次命中的规则 id 与条数（仅 id 与计数，不含原文片段），供规则运营复盘。
- 埋点只收事件名与计数，不接受自由文本；事件日志保留 30 天，不含 IP。
- LLM 只发送 `rule_id / category / matched`（最多 8 条），不发送全文与用户身份。
- 生产环境关闭 `/docs` 与 `/openapi.json`；CORS 白名单；Nginx 加安全头；页面无内联脚本/样式。
- 单 worker（内存限流）；反代启用 `--proxy-headers` 与 `X-Forwarded-For`，并限制限流桶上限。

## 10. 验证

按 `docs/validation/README.md` 执行：误报 50 条抽检（豁免降级项单列、不计入误报率）、召回 10 案例、有效试用 ≥10 人（24h 内 ≥2 次检测且 ≥1 次复制/采纳）。AI 标识变体 ≥12 条（含空格、全角写法），匹配前做全角→半角（NFKC）与去空格归一化；规则去重做 pattern + suggestion 两两比对，同 pattern 不同 suggestion 判为冲突并修正。

演示验收：对 finding 截图做 20px 高斯模糊后，第一眼仍应看到"建议"而不是风险徽章——这条写进演示脚本。

## 11. 变更记录

| 日期 | 变更 | 原因 |
|---|---|---|
| 2026-10-26 | v0.2 初版 | 评审修订后冻结范围 |
| 2026-10-26 | v0.3 | 三文档对齐：六类分类口径、/meta 增加 updated_at、单页三视图、Token 冻结、错误映射与渲染规则 |
| 2026-10-26 | v0.4 | 契约收口：新增 /events 与 suggestion_source、429 携带 Retry-After、LLM 2 秒超时口径、AI 标识变体与去重规则、性能口径统一（稳态 ≤100ms / 冷启动 ≤200ms / 全链路 ≤2s） |
| 2026-10-26 | v0.5 | 分类定稿（40/12/6/10/25/7）、事件白名单收敛为 2 个、Top 30 建议句质量标准、AI 标识归一化（NFKC + 去空格） |
| 2026-10-26 | v0.6 | 定版：分类按 38/22/16/10/8/6（40/12/6/10/25/7 作废）；排序改为风险等级优先；新增 rule_hits 日志；零命中文案统一为"当前没有需要处理的风险" |
| 2026-10-26 | v0.7 | 零命中文案回退为"未发现明显违规表述"（与免责声明一致）；amber 仅作品牌标记、中风险固定 #8A5D0E；图标实施统一为 sprite；429 文案定稿；补充演示截图验收 |
| 2026-10-26 | v0.8 | 图标最终定为内联 SVG（sprite 作废）；排序补"同级按 start、同位置按 rule_id"；耗时验收移入报告区；事件白名单定稿 2 项、白名单外忽略 |
| 2026-10-26 | v0.9 | 图标实施最终冻结为 SVG sprite（内联作废，附 16 图标 id 与三条静默失败模式）；§7 表格与 §7.2 统一，此后不再变更 |
