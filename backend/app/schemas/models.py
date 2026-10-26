"""API 请求与响应模型（与 docs/openapi.yaml 的 components.schemas 一一对应）。"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Level = Literal["high", "medium", "low"]
SuggestionSource = Literal["rule", "llm"]


class CheckRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=20000, description="待检测文本")
    has_ai_content: bool = Field(
        default=False,
        description="作者自述：文中是否包含 AI 生成内容（用于标识合规检查）",
    )


class Finding(BaseModel):
    rule_id: str
    category: str
    level: Level
    matched: str
    start: int
    end: int
    basis: str
    suggestion: str
    suggestion_source: SuggestionSource = Field(
        default="rule",
        description="建议来源：rule 为规则库模板，llm 为模型改写；降级时一律为 rule",
    )
    note: str | None = None


class CheckSummary(BaseModel):
    high: int
    medium: int
    low: int
    total: int
    elapsed_ms: int


class AiLabelCheck(BaseModel):
    required: bool
    detected: bool
    message: str
    suggestion: str | None = None


class CheckResponse(BaseModel):
    summary: CheckSummary
    findings: list[Finding]
    ai_label: AiLabelCheck
    disclaimer: str


class RuleMeta(BaseModel):
    total_rules: int
    categories: dict[str, int]
    version: str
    updated_at: str
