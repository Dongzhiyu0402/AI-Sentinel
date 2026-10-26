# 合规哨兵（Compliance Sentinel）

> 发布前内容合规体检工具：粘贴文案，30 秒内得到风险清单——每条命中附依据条文、修改建议与 AI 生成内容标识检查。
>
> 一句话：**别人只标红，我们帮改好。**

## 版本状态

- 版本：v0.3.0（公测）
- 核心能力：规则引擎（纯 Python Aho-Corasick）、检测 API、单页工具、规则库（30 条）、57 项自动化测试
- 下一步：规则库扩充至 100 条、LLM 改稿增强（未配置密钥时自动降级）、生产环境部署
- 应用场景：自媒体与一人公司的发布前内容合规自查

## 快速开始（Windows PowerShell）

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

浏览器打开 <http://127.0.0.1:8000> 即可使用；API 文档在 <http://127.0.0.1:8000/docs>。

运行测试：

```powershell
cd backend
python -m pytest tests -q
```

## 目录结构

```
compliance-sentinel/
├─ backend/
│  ├─ app/
│  │  ├─ main.py              # 装配：FastAPI 实例、静态资源、路由挂载（零业务）
│  │  ├─ api/routes.py        # 路由层：/health /meta /check + 限流
│  │  ├─ services/
│  │  │  ├─ rule_engine.py    # 规则引擎：AC 自动机 + 规则加载 + 豁免/降级
│  │  │  └─ llm_service.py    # LLM 改稿增强（可降级为模板建议）
│  │  ├─ schemas/models.py    # Pydantic 请求/响应模型
│  │  ├─ core/config.py       # 配置与环境变量
│  │  └─ data/rules.yaml      # 规则库（版本化，运营可独立维护）
│  └─ tests/test_rule_engine.py
├─ frontend/
│  ├─ index.html
│  └─ assets/{styles.css,app.js}
├─ docs/
│  ├─ SPEC.md                 # 规格契约（范围/API/页面/验收）
│  └─ decisions/              # ADR 与未决事项
└─ scripts/sample_article.txt # 样例文本（含典型风险点）
```

## 规则库格式（YAML）

```yaml
version: "2026.10"
rules:
  - id: ad-001
    category: 广告法
    level: high          # high / medium / low
    pattern: 国家级
    basis: 《广告法》第九条第（三）项
    suggestion: 删除"国家级"，改为可验证的具体资质或事实描述
    exempt: 《广告法》/转述   # 命中窗口内出现这些词时降级，需人工复核
    is_regex: false
```

规则与代码解耦：运营同学只需要改 `rules.yaml` 并重启服务，不需要改 Python 代码。
**注意**：规则条文号需规则组逐条核对后上线；`basis` 不确定时只写规则名称、不写具体条号。

## API

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/v1/health` | 健康检查 |
| GET | `/api/v1/meta` | 规则总数、分类统计、规则库版本 |
| POST | `/api/v1/check` | 文本检测，返回风险清单与 AI 标识检查结果 |

请求示例：

```json
{ "text": "本店产品为全网最低价，国家级认证。", "has_ai_content": false }
```

## 设计约束

- 图标全部为内联 SVG，不使用表情符号作为功能图标
- 颜色通过 CSS 变量统一管理，组件内不硬编码色值
- 主视觉不使用紫粉渐变；动效使用 ease-out，不使用弹跳缓动
- 文案只写真实能力，不承诺"检测 AI 生成"，不做"保证通过审核"类表述

## 路线图

- D1-D5（10.27-10.31）：规则库扩到 100 条、报告页完善、部署上线、参赛材料提交
- 11 月：规则库扩充至 300 条、报告分享、误报反馈、对照测试扩至 50 篇

## 免责声明

本工具仅提供内容风险自查参考，不构成法律意见，不替代平台审核，不保证发布结果。涉及具体法律问题请咨询专业律师。

## 开源协议

MIT License，详见 [LICENSE](LICENSE)。
