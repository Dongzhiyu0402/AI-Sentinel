# 合规哨兵 架构设计（v0.3）

- 版本锚定：Python 3.11+ / FastAPI 0.110+ / Pydantic 2.6+ / PyYAML 6.0+ / uvicorn 0.29+（以 `backend/requirements.txt` 为准）
- 契约：`docs/openapi.yaml` 为前后端唯一接口依据；本文档说明"为什么这样分层、边界在哪、失效时怎么退"
- 关联：`docs/SPEC.md`（范围与验收）、`docs/decisions/ADR-001-tech-stack.md`（选型结论）、`docs/CONVENTIONS.md`（交付纪律）
- 本次交付不含：视频/音频检测、小程序、用户系统、模型训练、涉政涉黄词库。范围以 SPEC 第 3 节为准，本文不放宽

---

## 1. 分层架构

```
                       ┌──────────────────────────────────────────┐
   浏览器（PC/移动）    │ 表现层  frontend/index.html + app.js     │
                       │ 无构建步骤；JSON 契约来自 openapi.yaml    │
                       └───────────────┬──────────────────────────┘
                                       │ HTTPS /api/v1/*
                       ┌───────────────▼──────────────────────────┐
                       │ Nginx：TLS 终止、静态资源、限流兜底、      │
                       │ 安全响应头、client_max_body_size、访问日志 │
                       └───────────────┬──────────────────────────┘
                                       │ 127.0.0.1:8000（仅本地回环）
   ┌───────────────────────────────────▼──────────────────────────────┐
   │ 应用层  FastAPI（uvicorn，单 worker + 多线程）                     │
   │ ┌──────────────────────────────────────────────────────────────┐ │
   │ │ api/routes.py    HTTP 入口：参数校验、限流、响应装配（无算法）  │ │
   │ ├──────────────────────────────────────────────────────────────┤ │
   │ │ services/rule_engine.py  规则匹配与降级编排（纯函数、无 IO）    │ │
   │ │ services/llm_service.py  可选增强层，异常一律降级              │ │
   │ ├──────────────────────────────────────────────────────────────┤ │
   │ │ schemas/models.py  Pydantic 契约模型（= openapi.yaml 的映射）  │ │
   │ │ core/config.py     环境变量集中读取，业务代码不读 os.environ    │ │
   │ └──────────────────────────────────────────────────────────────┘ │
   └──────────┬───────────────────────────────────────┬───────────────┘
              │ 只读加载（进程启动一次）               │ 出网（可选，超时 2s）
   ┌──────────▼──────────┐                 ┌──────────▼───────────────┐
   │ app/data/rules.yaml │                 │ DeepSeek / 兼容接口       │
   │ Git 版本管理，无 DB │                 │ 失败即回退模板建议         │
   └─────────────────────┘                 └──────────────────────────┘
```

依赖方向单向：`api → services → schemas/core`。反向依赖（services 引 routes）视为门禁不通过。不落数据库、不落原文：MVP 阶段没有需要事务一致性的状态，引入 PostgreSQL 只会增加运维面与泄露面。

### 1.1 目录与文件组织硬约束

| 约束 | 具体要求 | 当前状态 |
|---|---|---|
| 单文件 ≤300 行 | 代码文件（.py/.js/.css）超过 300 行必须拆分 | rule_engine.py 214 行、routes.py 74 行，合规 |
| 入口只装配 | `main.py` 只做实例化、中间件、路由、静态资源，零业务逻辑 | 35 行，合规 |
| 路由不写算法 | 匹配、降级、分级全在 services；routes 只做限流与装配 | 合规 |
| 规则与代码解耦 | 规则只能改 `data/rules.yaml`，不允许在代码里硬编码词条 | 合规 |
| 规则文件增长 | 100 条规则约 700 行 YAML，属数据文件不受 300 行限制；单文件上限 1200 行，超限按 `rules/ad.yaml`、`rules/platform.yaml` 拆目录并同步 `_load`（`Path.rglob("*.yaml")`） | 现 30 条，D5 前需评估 |
| 图标库锁定 | **Lucide（ISC 许可）**，实施方式为**单文件 SVG sprite**：`frontend/assets/icons.svg` 内每个 `<symbol id>` 自带 `viewBox="0 0 24 24"`、`fill="none"`、`stroke="currentColor"`、`stroke-width="1.75"`；页面用 `<svg width height aria-hidden="true" focusable="false"><use href="/assets/icons.svg#id"/></svg>` 引用。sprite 内不写任何色值，颜色由 `currentColor` 从 Token 继承 | 图标口径以 SPEC v0.9 为准，已冻结。全项目禁止 emoji 图标，禁止混用第二套图标库或手绘形状替代 |
| 设计 Token 落地 | `frontend/assets/design-tokens.css` 必须在 `styles.css` **之后**引入（内含 Legacy Alias 覆盖 styles.css 既有变量）；不引 Google Fonts CDN，走系统回退链；组件内不硬编码色值 | 已由设计侧产出，接入顺序按此约束 |

---

## 2. 检测链路数据流

```
POST /api/v1/check
  │
  ├─(1) Pydantic 校验：text 1..20000 字符，has_ai_content 布尔
  │     失败 → 422（FastAPI 默认错误体）
  ├─(2) 限流：按客户端 IP 的 1 小时滑动窗口，上限 60 次
  │     超限 → 429，不进入匹配
  ├─(3) rule_engine.check()
  │     ├ Aho-Corasick 单次扫描 字面规则 → (rule_id, start, end)
  │     ├ re.finditer 顺序跑 正则规则（is_regex: true）
  │     ├ 去重键 (rule_id, start, end)：同一条规则对同一区间只出一条
  │     ├ 豁免降级：命中窗口 ±40 字内含 exempt 关键词（《广告法》/转述/不得使用）
  │     │   → level 降为 low，note 写明"疑似豁免场景，建议人工复核"
  │     └ AI 标识检查：has_ai_content=true 且标识用语均未命中（保守判定，见下）
  │         → 追加 ai-label-missing（high，matched 为空，start=end=0）
  ├─(4) llm_service.enhance()：仅对 level=high 且 matched 非空 的前 8 条
  │     未配密钥 / 超时 / 非 200 / JSON 解析失败 / 空结果 → 返回原 findings
  │     每条建议标记来源 suggestion_source = rule | llm
  ├─(5) 装配 summary（high/medium/low/total/elapsed_ms）+ disclaimer
  └─(6) 埋点日志一行（结构化，无原文、无明文 IP）
```

**关键不变量**（改动代码前必须保持）：

1. `findings` 覆盖 `[start, end)` 区间且可在 `text` 上直接切片还原，前端据此做高亮。
2. 返回的 `findings` 与 `summary` 计数必须自洽：`total == high + medium + low`。
3. 规则结果永远可用：LLM 链路的任何异常都不得让 `/check` 返回 5xx，也不得删减 `findings` 条目（只允许替换 `suggestion` 文本并置 `suggestion_source=llm`）。
4. `elapsed_ms` 用 `time.perf_counter()` 差值取整，覆盖规则匹配与 LLM 全链路。
5. **去重与合并策略**：同一 `(start, end)` 上不同 `rule_id` 的命中一律保留——它们对应不同法律依据，合并会丢掉可解释性；"同一位置出现两条一模一样的建议"由规则库治理消除，不靠运行时合并：入库校验禁止两条规则出现"相同 pattern 且相同 suggestion"，该约束落成测试用例（对 `rules.yaml` 全量两两比对）。同一位置多条命中时，`findings` 先按 `level`（high→medium→low）、再按 `start`、最后按 `rule_id` 升序排列，前端按顺序渲染即可，最严重的排在最前。排序键与 `rule_engine._finding_sort_key` 一致，改排序必须同时改 SPEC 与本条。
6. **AI 标识保守判定**：只要 `has_ai_content=true`，除已命中标识用语外，一律追加高风险项（宁可提示也不漏，对应《人工智能生成合成内容标识办法》第十条）。标识用语清单必须覆盖常见真实写法，当前 7 条偏窄，需补入"由AI生成""内容由AI辅助""AI创作""本文含AI生成"等变体（含全角/半角与中英文混排差异），补齐后由测试固定用例。

---

## 3. 限流失效点与修正（上线前必须完成）

现实现 `_hits: dict[str, deque[float]]` 是进程内内存桶，在"阿里云轻量 + Nginx 反代"下存在硬伤：

| 风险 | 后果 | 修正 |
|---|---|---|
| `request.client.host` 在反代后恒为 `127.0.0.1` | 全站用户共用 60 次/小时配额，第 61 个请求起全员 429，演示当场失败 | uvicorn 启动加 `--proxy-headers --forwarded-allow-ips=127.0.0.1`，并在 Nginx 侧写 `proxy_set_header X-Forwarded-For $remote_addr;`（不用 `$proxy_add_x_forwarded_for`，避免客户端伪造前缀） |
| 字典按 IP 无界增长 | 被扫描器刷 IP 时内存持续上涨 | 单桶保留，另加全局上限（如 5000 个 IP）：超过时先剔除窗口已空的桶，再剔除最久未访问的桶 |
| 进程重启即清零 | 可被"重启即重置"绕过，MVP 可接受 | 记录为已知限制，不引入 Redis（多一个故障点与运维成本）。触发条件：日活破千或出现真实滥用 |
| 必须单 worker | 多 worker 各自计数，实际配额 = 60 × worker 数 | `uvicorn --workers 1 --threads 4`（2 核 2G 足够支撑演示与种子用户）；如需横向扩容，先补 Redis 限流再改 workers |

Nginx 侧再加一层兜底：`limit_req_zone $binary_remote_addr zone=check:10m rate=1r/s;`，仅对 `/api/v1/check` 生效，`limit_req_status 429`。两层限流目的不同：应用层控"每小时配额"，Nginx 层控"瞬时并发"。

429 响应必须同时给出"何时能再试"：`Retry-After: <秒>`（按窗口内最早一条请求的时间差计算，向上取整到分钟展示）+ `detail` 文案"本次检测额度已用完，约 N 分钟后可再次检测"。只写"请求过于频繁"不满足产品要求，也不写"系统繁忙"这类无信息量的话。

---

## 4. LLM 降级树

降级是产品承诺（SPEC AC-04），不是兜底代码，必须逐层可判定：

```
LLM_API_KEY 为空 ────────────────────────→ 模板建议（默认态，零成本）
  ↓ 有密钥
targets（high 且 matched 非空）为空 ──────→ 模板建议（无需外发）
  ↓ 有目标
取前 8 条，构造 JSON 请求（temperature 0.2）
  ├ 连接/读写超时 2s（与性能承诺一致）→ 记 warning，模板建议
  ├ 非 2xx / 网络异常 ────────────────────→ 记 warning，模板建议
  ├ 响应体非 JSON / 缺 choices ───────────→ 记 warning，模板建议
  ├ 返回 rule_id 与请求不匹配 ────────────→ 忽略该条，保留模板建议
  └ 全部命中 ─────────────────────────────→ 替换 suggestion 文本并置 suggestion_source=llm
```

延迟承诺的边界（口径与 SPEC §2、AC-01 一致）：规则链路稳态 p95 ≤100ms、含冷启动首请求 ≤200ms（实测 10–30ms，20000 字亦在同量级）；首交不配 LLM 时 `/check` 全链路 ≤2s，实测在 50ms 以内。开启 LLM 后，单次请求耗时应由模型响应决定，与上述数字不可同时保证——因此**首交版本不配置 `LLM_API_KEY`**，页面展示的"改稿建议"全部来自规则模板（`suggestion_source=rule`）；需要演示模型改写能力时临时配置密钥，`LLM_TIMEOUT_SECONDS` 固定 2s（代码里的旧默认值 12 必须改为 2，否则演示会击穿全链路口径），该场景下 `elapsed_ms` 单独统计，不与性能承诺混算。若 11 月要把 LLM 变成常规能力，改造方向是"规则先返回、建议后补"的两次响应，不在本次范围。

外发内容边界：只发 `rule_id / category / matched`（命中片段，非全文），最多 8 条。**不外发**：原文上下文、`has_ai_content`、IP、时间戳。这条边界写进代码注释与隐私声明，任何扩展都要先过评审。

---

## 5. 隐私与数据留存

产品承诺"粘贴的内容不留存"，架构上逐条对应：

| 数据 | 是否落盘 | 是否外发 | 说明 |
|---|---|---|---|
| 用户原文 | 否 | 否（仅命中片段最多 8 条发往 LLM，且仅当配置了密钥） | 不建数据库、不写文件 |
| 命中片段 | 否 | 可选（见上） | 仅在内存中随请求生命周期存在 |
| 访问日志 | 是 | 否 | Nginx access log 只记 method/path/status/耗时/UA，不记 body；保留 7 天轮转 |
| 埋点日志 | 是 | 否 | 字段固定，见 §5.1；不含任何原文，`ip_hash` 为 IP 的 SHA-256 前 12 位 |
| 错误日志 | 是 | 否 | 不得打印 `payload.text`；异常信息里出现原文视为缺陷 |

对外声明（前端页脚 + `disclaimer` 字段）：文本仅在内存中检测，不保存、不用于训练；涉及具体法律问题请咨询专业律师。

### 5.1 埋点字段（稳定契约，字段名不得随手改）

服务端事件（`/check` 成功时输出一行 JSON）：

| 字段 | 类型 | 说明 |
|---|---|---|
| `event` | string | 固定 `check_submitted` |
| `ts` | string | ISO 8601 UTC 时间戳 |
| `device` | string | `desktop` / `mobile` / `tablet` / `unknown`，按 UA 粗分 |
| `text_len` | int | 字符数，不含内容 |
| `elapsed_ms` | int | 服务端处理耗时 |
| `finding_count` | int | 命中总数 |
| `by_level` | object | `{"high":n,"medium":n,"low":n}` |
| `rule_hits` | object | `{rule_id: 命中次数}`，同规则同请求多次命中合并计数；键上限 100（等值规则库规模），无原文 |
| `llm` | string | `on` / `off`，表示本次是否走模型增强 |
| `ip_hash` | string | 12 位哈希，用于去重与滥用排查，不可逆推 IP |

`rule_hits` 是误报率抽样的数据源：按 `rule_id` 聚合即可得到每条规则的真实命中频次，长尾规则（次数 1–3 次）由此可枚举，抽样不必依赖人工记忆。取数方式为 `journalctl -u compliance-sentinel \| grep check_submitted` 后按 JSON 解析，不需要数据库。

前端上报只走两个事件：`suggestion_copied`（带 `rule_id`）与 `error_occurred`（带 `error_code`），通过 `POST /api/v1/events` 批量提交（契约见 `openapi.yaml`）。该端点属 P0：不接受它，建议采纳率就无法统计。落地要求：白名单 2 项、白名单外事件忽略并返回 202（不计入 `accepted`，不返回 422）、单批 ≤20 条、只写日志不落库、日志保留 30 天（journald 配置保留期与轮转，不用 logrotate 手写规则），日志内不含原文与明文 IP。

`check_submitted` 与 `ai_label_flagged` 不占前端白名单，因为两者都能从服务端拿到的数据推导：`check_submitted` 由 `/check` 成功时记录；`ai_label_flagged` 等价于该次请求的 `rule_hits` 中含 `ai-label-missing`，聚合 `rule_hits` 即可得到检出次数，不需要前端再报一遍（重复上报还会与 `check_submitted` 的口径打架）。`check_result_viewed` 不作为验收指标：它只能证明页面渲染完成，不能证明用户采纳，采纳率用 `suggestion_copied / check_submitted` 计算更可信。


---

## 6. 安全设计

上线前必须补齐（当前缺失，属"缺失系统上下文"失效）：

| 项 | 现状 | 要求 |
|---|---|---|
| CORS | `allow_origins=["*"]` | 收敛为 `["https://<正式域名>"]` + 本地调试用 `http://127.0.0.1:8000`；方法限定 GET/POST |
| 安全响应头 | 无 | Nginx 加：`X-Content-Type-Options: nosniff`、`X-Frame-Options: SAMEORIGIN`、`Referrer-Policy: strict-origin-when-cross-origin`、`Permissions-Policy: geolocation=(), microphone=(), camera=()`、HSTS（TLS 就绪后） |
| CSP | 无 | `default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'self'`。前端因此不得使用内联 `<script>`/`onclick=`/`style=`，事件全部 `addEventListener` 绑定 |
| 请求体上限 | 仅 Pydantic 字符数校验（读完 body 才校验） | Nginx `client_max_body_size 256k;`，在入口挡住超大体 |
| 接口文档暴露 | FastAPI 默认开 `/docs`、`/openapi.json` | 生产 `docs_url=None, redoc_url=None, openapi_url=None`；对外契约以 `docs/openapi.yaml` 为准 |
| 密钥管理 | 环境变量 | systemd `EnvironmentFile=/etc/compliance-sentinel/env`，文件权限 600，不写进仓库；`.env.example` 只留键名 |
| 错误泄露 | 500 会带堆栈 | 加全局异常处理，对外统一 `{"detail": "服务暂时不可用，请稍后重试"}`，堆栈只进日志 |

---

## 7. 可观测性

- 健康检查：`GET /api/v1/health` 返回 `{status, version}`，Nginx/巡检每 60s 探测；返回体含 `version` 便于确认发布的代码版本。
- 埋点：每个 `/check` 请求一行 JSON 到 `journald`（`logger.info`），字段固定，便于 `grep` 统计"今日检测次数 / 高中低分布 / 平均耗时 / LLM 命中率"——这正是参赛材料要的验证数据。
- 规则版本：`/meta` 返回 `version`（取自 YAML 的 `version` 字段，目标值形如 `2026.10`），用于确认线上规则是哪个版本。首页会展示该值，因此它必须是对外可读的版本号，不能带阶段后缀。
- 耗时告警：演示前以 2000 字中文实测 ≤2s（SPEC AC-01）；超过则先关 LLM（`LLM_API_KEY` 置空）再查规则量。
- 不做：APM、Prometheus、分布式追踪。单机单服务，投入产出不成立。

---

## 8. 部署拓扑

```
用户 ──HTTPS 443──→ 阿里云轻量 2C2G（Ubuntu 22.04）
                     ├ nginx：TLS(Let's Encrypt)、静态 frontend/、反代 /api/ → 127.0.0.1:8000
                     │         安全头、client_max_body_size 256k、limit_req 兜底
                     └ systemd: compliance-sentinel
                          ExecStart=/opt/sentinel/venv/bin/uvicorn app.main:app \
                             --host 127.0.0.1 --port 8000 --workers 1 --threads 4 \
                             --proxy-headers --forwarded-allow-ips=127.0.0.1
```

- 只监听回环，公网只开 443（22 限源 IP）。8000 不对公网暴露。
- 发布流程：`git pull` → `pip install -r requirements.txt` → `pytest tests -q` → `systemctl restart` → `curl /api/v1/health` 核对 version → 浏览器走一遍检测。回滚：`git reset --hard <上一个 tag>` + 重启，30 秒内完成。
- 静态资源版本：`index.html` 引用改为 `/assets/app.js?v=<APP_VERSION>`，避免更新后浏览器用旧 JS。
- 成本（含域名与 LLM，1 个月内）：轻量 ¥60–100/月（年付更低）＋域名 ¥30–60/年＋SSL 免费＋DeepSeek 按量约 ¥3–10/月（仅高风险片段，日检 100 次量级）→ **合计 < ¥200/月，符合 <500 元预算**。
- 备份：规则 YAML 与文档在 Git；服务器无业务数据，无需备份。这是"不落库"设计换来的运维简化。

---

## 9. 技术选型矩阵

评分口径 1–5，权重按 MVP 阶段：可维护性 0.35 / 交付速度 0.25 / 环境风险 0.20 / 性能 0.10 / 生态 0.10。

### 9.1 前端

| 方案 | 可维护 | 速度 | 环境风险 | 性能 | 生态 | 加权 | 结论 |
|---|---|---|---|---|---|---|---|
| 原生 HTML/CSS/JS | 3 | 5 | 5 | 5 | 3 | **4.05** | **采用**。单页 + 一个第三方库都没有，Nginx 直接托管，改文案不用发版构建；团队已跑通 |
| Vue 3（CDN，无构建） | 4 | 4 | 4 | 4 | 4 | 3.90 | 备选。若 11 月要做分享页/历史记录多状态，首个候选 |
| React + Vite | 4 | 2 | 2 | 4 | 5 | 3.00 | 不采用。构建链路、node_modules、CI 都是 5 天内不值的风险 |

DOM 渲染约束：结果区一次性 `replaceChildren`，不引虚拟 DOM；高亮用 `textContent` 分段 + `<mark>` 拼接，**禁止把用户文本拼进 `innerHTML`**（XSS 面，用户文本完全可控）。

### 9.2 后端

| 方案 | 可维护 | 速度 | 环境风险 | 性能 | 生态 | 加权 | 结论 |
|---|---|---|---|---|---|---|---|
| FastAPI | 5 | 5 | 5 | 4 | 5 | **4.90** | **采用**。Pydantic 模型即校验即文档，与 `openapi.yaml` 一一对应，避免"文档与实现各写一套" |
| Flask | 4 | 4 | 5 | 4 | 4 | 4.15 | 备选。要自己补校验与 OpenAPI，等于把 FastAPI 白送的能力重写一遍 |
| Django | 2 | 2 | 3 | 3 | 5 | 2.35 | 不采用。ORM/Admin/迁移全是不需要的重量，且团队无 Django 经验 |

### 9.3 规则引擎

| 方案 | 可维护 | 速度 | 环境风险 | 性能 | 生态 | 加权 | 结论 |
|---|---|---|---|---|---|---|---|
| 纯正则逐条 `re.search` | 4 | 4 | 5 | 2 | 5 | 4.10 | 不采用为主方案。100 条规则 × 20000 字 = 200 万次比较，单请求已接近 1s，加规则即线性劣化 |
| pyahocorasick（C 扩展） | 3 | 5 | 2 | 5 | 4 | 3.75 | 不采用。Windows 上 `pip install` 需编译工具链，环境风险不可控；与"零编译依赖"决策冲突 |
| **自实现纯 Python Aho-Corasick + 少量正则** | 4 | 4 | 5 | 4 | 4 | **4.30** | **采用**。214 行、7 项测试覆盖、一次扫描 O(n)、无编译依赖；字面词走 AC、模式类走正则，职责清晰 |

性能口径：AC 预处理 O(Σpattern)，单次扫描 O(len(text) + 命中数)。20000 字中文实测量级 10–30ms，LLM 2s 超时是唯一的长尾，已隔离在降级树内。规则从 30 → 100 条对扫描时间影响可忽略（只增预处理），风险不在性能而在规则准确性。

### 9.4 部署

| 方案 | 可维护 | 速度 | 环境风险 | 性能 | 生态 | 加权 | 结论 |
|---|---|---|---|---|---|---|---|
| **阿里云轻量 + Nginx + systemd** | 4 | 4 | 4 | 4 | 4 | **4.00** | **采用**。团队已有机器与权限，SSL 与反代都是成熟路径，出问题能登机排查 |
| 云托管（函数计算/SAAS 平台） | 3 | 3 | 3 | 3 | 3 | 3.00 | 不采用。冷启动会击穿 2s 验收；规则 100 条每次冷启重载，且日志与排查链路陌生 |
| Docker + 编排 | 3 | 2 | 3 | 4 | 4 | 3.10 | 不采用。镜像构建与镜像内规则更新都要额外设计，当前无多环境需求 |

---

## 10. 风险清单（未来 5 天）

| # | 风险 | 触发信号 | 处置 | 责任 |
|---|---|---|---|---|
| R1 | 反代后限流取不到真实 IP，全员 429 | 上线后第 61 个请求起连续 429 | 按 §3 加 `--proxy-headers` 与 XFF 头；上线后立刻用两台设备各打 3 次验证计数独立 | 后端 |
| R2 | 规则从 30 条扩到 100 条，出现"该报不报/误报" | 抽样 20 篇真实文案，命中与人工判断不符 | 双人复核每条 `pattern/basis/level/exempt`；条号不确定只写规则名；每条至少 1 个正例 + 1 个豁免例进 `tests/` | 规则 |
| R3 | LLM 未配或超时导致演示卡顿 | `/check` 耗时 >3s 或页面长转 | 演示环境不配 `LLM_API_KEY`（走模板建议，全程 <1s）；需要展示 LLM 时限定 8 条 + 2s 超时 | 后端 |
| R4 | 前端把用户文本拼进 `innerHTML`，构成 XSS | 输入 `<img onerror=...>` 触发执行 | 高亮函数只产出文本节点 + `<mark>`；发布前用该 payload 手测一次 | 前端 |
| R5 | 交付纪律残留（图标用 emoji、文案有空话、调试语句）导致门禁退回 | `CONVENTIONS.md` 第 4 节扫描有输出 | 每次交付前跑 4 条扫描命令，命中即改；文档与界面只写具体结论 | 全体 |
| R7 | `/meta` 把规则库版本号直接展示给用户，若版本串带阶段后缀则违反"用户可见处不写阶段词" | 首页出现带后缀的版本号 | `rules.yaml` 的 `version` 与 `note` 在发布前按对外口径改写；前端展示时只渲染版本号本身 | 规则 + 前端 |
| R6 | 契约漂移：前端按 `openapi.yaml` 写、后端改了字段 | 页面字段取值为 `undefined` | 后端改 `schemas/models.py` 必须先改 `openapi.yaml` 并经总监同步前端；`/docs` 关掉后 openapi.yaml 是唯一真相 | 架构 |

---

## 11. 明确不做（out of scope）

数据库与 ORM、缓存中间件、消息队列、用户体系与鉴权、多租户、规则热更新与灰度、指标监控平台、容器化、视频/音频检测、涉政涉黄词库、API 开放平台。以上每一项都要先改 SPEC 再动代码。

规则热更新（当前需重启生效）暂不做：重启 5 秒内完成、单 worker 无状态竞争，收益低于引入文件监听 + 并发重建的复杂度。触发条件：一天内需改规则 ≥3 次，或规则由非技术同学自行维护。

---

## 12. 端到端验证

```bash
cd backend
python -m pytest tests -q                       # 期望：全部通过
uvicorn app.main:app --port 8000 --proxy-headers --forwarded-allow-ips=127.0.0.1

# 1) 健康检查
curl -s http://127.0.0.1:8000/api/v1/health
# 2) 规则统计：total_rules 与 rules.yaml 条数一致，version 与 YAML 一致
curl -s http://127.0.0.1:8000/api/v1/meta
# 3) 命中（期望 ad-001 国家级 / ad-008 全网最低，level=high，位置可切片还原）
curl -s -X POST http://127.0.0.1:8000/api/v1/check -H "Content-Type: application/json" \
  -d '{"text":"本店产品为全网最低价，国家级认证。","has_ai_content":false}'
# 4) 豁免降级（期望该条 level=low 且 note 非空）
curl -s -X POST http://127.0.0.1:8000/api/v1/check -H "Content-Type: application/json" \
  -d '{"text":"《广告法》规定，不得使用“国家级”这类表述。","has_ai_content":false}'
# 5) AI 标识缺失（期望出现 ai-label-missing，level=high）
curl -s -X POST http://127.0.0.1:8000/api/v1/check -H "Content-Type: application/json" \
  -d '{"text":"这是一段普通文案。","has_ai_content":true}'
# 6) 边界：空文本 422、超 20000 字 422、第 61 次 429
```

第 6 项为必测错误流：`text: ""` 返回 422，`text` 长度 20001 返回 422，循环 61 次后返回 429 且响应为 `{"detail": "..."}`（与 `openapi.yaml` 的 `ErrorDetail` 一致）。

---

## 13. 契约缺口登记

| 项 | 现状 | 决定 | 理由 |
|---|---|---|---|
| 错误响应体 | `{"detail": "..."}`（`HTTPException` 默认），前端 `app.js` 已按 `detail.detail` 取值 | **保持现状，写入契约** | 改成 `{code, data, message}` 统一信封需要同时改后端异常处理与前端取值，5 天内属纯风险无收益；统一信封列入 v2（届时加 `/api/v2` 前缀并行） |
| 422 响应体 | FastAPI 默认 `{"detail": [{loc, msg, type}]}` | 保持，写入契约 | 前端只需展示 `detail` 为字符串的场景；422 仅在程序调用出错时出现 |
| 埋点格式 | 仅 `logging` 一行 JSON | 保持，按 §5.1 补字段 | 赛事只需检测次数、命中分布与按规则聚合的命中次数，日志聚合足够，不引入存储 |
| `Finding.suggestion_source` | 模型里还没有该字段 | **契约已定（`rule` / `llm`），须后端补 2 处改动**：`schemas/models.py` 加字段（默认 `rule`），`llm_service.enhance()` 替换建议时置 `llm` | 产品需要区分建议来源以统计采纳率；不加字段就只能靠"文本像不像模型写的"猜，不可靠 |
| 429 响应头 `Retry-After` | 只有 `detail` 文案 | **契约已定，须后端补 1 处**：超限时返回 `Retry-After`（秒，按窗口最早一条的时间差计算），`detail` 写明"本次额度已用完，约 N 分钟后可再次检测" | 产品要求提示"大致何时可再试"；不写"系统繁忙"。注意两者要同源计算，避免文案与秒数不一致 |
| `POST /api/v1/events` | 不存在 | **契约已定（白名单 2 项：`suggestion_copied` / `error_occurred`；白名单外忽略并 202）**，端点实现由后端在 Phase 3 落（批 ≤20 条、不收自由文本、不落库只落日志） | 采纳率统计必须有前端事件；先把字段与状态码钉死，避免前端写完再改 |
| `RuleMeta.updated_at` | `rules.yaml` 已有 `updated_at` 字段，但引擎未读取、模型未暴露 | **契约已定，须后端补 2 处**：`rule_engine._load()` 读取 `data.get("updated_at")` 存为 `self.updated_at`；`RuleMeta` 加 `updated_at: str`，`/meta` 回填 | 首屏"最近更新"必须来自接口（AC-06），硬编码即虚构指标 |
| `categories` 口径 | 现有实现按已加载规则实时统计，键取决于 YAML 里的 category 值 | **保持实时统计，字段名不改**；口径锁定为六类：广告法 / 医疗健康 / 平台规则 / 金融理财 / 教育培训 / 通用表达，合计等于 `total_rules`；"AI标识"不作为一个分类出现 | 改字段名（`rule_count` / `categories[]`）会同时改动已跑通的后端模型、前端渲染与全部测试，收益只是命名偏好，5 天内属纯风险。展示顺序在前端按条数降序、同数按名称排序 |
| `LLM_TIMEOUT_SECONDS` 默认值 | `core/config.py` 仍是 `"12"` | **须后端补 1 处**：默认值改为 `"2"`，`.env.example` 同步 | SPEC 已把超时口径定为 2 秒；默认值不改，演示时一旦忘记设置环境变量就击穿全链路口径 |

---

## 变更记录

| 日期 | 变更 | 原因 |
|---|---|---|
| 2026-10-26 | 初版：分层、数据流、限流修正、降级树、隐私、安全、部署、选型矩阵、风险清单 | 配合 SPEC v0.3 与 openapi.yaml 形成可执行契约 |
| 2026-10-26 | 按 PRD 口径补充：去重与合并策略、AI 标识保守判定、建议来源字段、429 的 Retry-After、埋点字段表与 `rule_hits` 聚合、p95 承诺边界 | 产品需要稳定字段名与可抽样的误报数据，先把契约钉死 |
| 2026-10-26 | 与设计侧冻结项对齐：字体回退链与禁 CDN、Token 文件引入顺序；`/meta` 增加 `updated_at`，分类口径锁定六类；性能口径统一为稳态 ≤100ms / 冷启动 ≤200ms / 全链路 ≤2s | 三文档（PRD / SPEC / DESIGN）口径必须一致，否则前端按 A 写、后端按 B 实现 |
| 2026-10-26 | 图标实施冻结为 SVG sprite（`icons.svg` + `<use>`），以 SPEC v0.9 为准；埋点白名单收敛为 2 项、白名单外忽略并 202；说明 `ai_label_flagged` 由 `rule_hits` 推导、`check_result_viewed` 不作验收指标 | team-lead 定稿；避免三文档各说一套 |
