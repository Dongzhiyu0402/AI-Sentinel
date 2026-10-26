"""LLM 增强层：为高风险命中生成更贴合的改稿建议。

- 未配置 LLM_API_KEY 时自动降级为规则模板建议，不影响主流程；
- 调用失败/超时静默降级，保证“规则结果永远可用”；
- 只处理高风险且可定位的命中，控制成本与延迟。
"""
from __future__ import annotations

import json
import logging
import urllib.request

from app.core import config as cfg
from app.schemas.models import Finding

logger = logging.getLogger(__name__)

PROMPT_TEMPLATE = (
    "你是中文内容合规编辑。请为下面每个风险片段给出 1 条改写建议。"
    "要求：保留原意，删除或替换违规表述，不超过 40 字，只输出 JSON 数组，不要解释。"
    "输入：{items}\n"
    '输出格式：[{{"rule_id": "...", "suggestion": "..."}}]'
)


def enhance(findings: list[Finding]) -> list[Finding]:
    targets = [item for item in findings if item.level == "high" and item.matched]
    if not cfg.LLM_ENABLED or not targets:
        return findings

    try:
        suggestions = _request_suggestions(targets)
    except Exception as exc:  # noqa: BLE001 - 降级优先，任何异常都不能阻断主流程
        logger.warning("LLM 增强失败，降级为模板建议：%s", exc)
        return findings

    if not suggestions:
        return findings

    updated: list[Finding] = []
    for finding in findings:
        replacement = suggestions.get(finding.rule_id)
        if replacement and finding.level == "high":
            updated.append(
                finding.model_copy(update={"suggestion": replacement, "suggestion_source": "llm"})
            )
        else:
            updated.append(finding)
    return updated


def _request_suggestions(targets: list[Finding]) -> dict[str, str]:
    items = [
        {"rule_id": item.rule_id, "category": item.category, "text": item.matched}
        for item in targets[:8]
    ]
    payload = {
        "model": cfg.LLM_MODEL,
        "messages": [
            {
                "role": "user",
                "content": PROMPT_TEMPLATE.format(items=json.dumps(items, ensure_ascii=False)),
            }
        ],
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }
    request = urllib.request.Request(
        f"{cfg.LLM_BASE_URL.rstrip('/')}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {cfg.LLM_API_KEY}",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=cfg.LLM_TIMEOUT_SECONDS) as response:
        body = json.loads(response.read().decode("utf-8"))

    content = body["choices"][0]["message"]["content"]
    parsed = json.loads(content)
    if isinstance(parsed, dict):
        parsed = parsed.get("items", [])
    return {
        str(item["rule_id"]): str(item["suggestion"])
        for item in parsed
        if isinstance(item, dict) and item.get("rule_id")
    }
