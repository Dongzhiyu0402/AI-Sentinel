"""AI 标识检查测试：NFKC 全角转半角、去空白、零宽字符、位置无关与保守判定。"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.services.rule_engine import RuleEngine  # noqa: E402

RULES_PATH = BACKEND_DIR / "app" / "data" / "rules.yaml"

# 12 种以上真实写法的变体，覆盖空格、全角、大小写、零宽与位置差异
LABELED_VARIANTS = [
    "本文含 AI 生成内容，已由作者核校。",
    "本文包含ＡＩ生成内容。",
    "本内容由 AI 生成，仅供参考。",
    "本内容含ＡＩ生成。",
    "本文由AI生成。",
    "以下内容由 AI 生成。",
    "AI 辅助生成，已人工改写。",
    "A I 辅助创作，供参考。",
    "AI生成内容声明：本段由模型产出并核校。",
    "#AI生成 今日菜谱合集",
    "含 AI 生成内容，请读者知悉。",
    "配图使用AI生成。",
    "本段为ai生成，已校对。",
    "本稿AI参与创作。",
    "本文含\u200bAI生成内容。",
    "开头是正常表述。中间才是本文含AI生成内容。后面还有正文。",
]


@pytest.fixture(scope="module")
def engine() -> RuleEngine:
    return RuleEngine(RULES_PATH)


@pytest.mark.parametrize("text", LABELED_VARIANTS)
def test_explicit_labels_are_detected(engine: RuleEngine, text: str) -> None:
    findings, ai_label = engine.check(text, has_ai_content=True)
    assert ai_label.required is True
    assert ai_label.detected is True
    assert "ai-label-missing" not in {item.rule_id for item in findings}


def test_missing_label_is_flagged(engine: RuleEngine) -> None:
    findings, ai_label = engine.check("本文由AI整理，介绍我们的产品。", has_ai_content=True)
    assert ai_label.detected is False
    assert ai_label.suggestion
    missing = [item for item in findings if item.rule_id == "ai-label-missing"]
    assert len(missing) == 1
    assert missing[0].level == "high"
    assert missing[0].matched == ""
    assert (missing[0].start, missing[0].end) == (0, 0)


def test_label_not_required_without_declaration(engine: RuleEngine) -> None:
    findings, ai_label = engine.check("本文含AI生成内容。", has_ai_content=False)
    assert ai_label.required is False
    assert ai_label.detected is True
    assert "ai-label-missing" not in {item.rule_id for item in findings}


def test_marker_count_covers_variants() -> None:
    from app.services.rule_engine import AI_LABEL_MARKERS

    assert len(AI_LABEL_MARKERS) >= 12
    assert len(set(AI_LABEL_MARKERS)) == len(AI_LABEL_MARKERS)
