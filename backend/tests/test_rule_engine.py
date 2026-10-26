"""规则引擎单元测试：覆盖命中、定位、豁免降级、AI 标识检查与正则规则。"""
from __future__ import annotations

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.services.rule_engine import RuleEngine  # noqa: E402

RULES_PATH = BACKEND_DIR / "app" / "data" / "rules.yaml"


def make_engine() -> RuleEngine:
    return RuleEngine(RULES_PATH)


def rule_ids(findings) -> set[str]:
    return {item.rule_id for item in findings}


def test_rule_library_metadata() -> None:
    engine = make_engine()
    assert engine.version == "2026.10"
    assert engine.updated_at == "2026-10-26"


def test_detects_ad_law_absolute_term() -> None:
    findings, _ = make_engine().check("本产品为国家级认证产品。", has_ai_content=False)
    assert "ad-001" in rule_ids(findings)


def test_positions_are_correct() -> None:
    text = "全国第一品牌"
    findings, _ = make_engine().check(text, has_ai_content=False)
    hit = next(item for item in findings if item.rule_id == "ad-005")
    assert text[hit.start:hit.end] == "第一品牌"


def test_exempt_downgrades_to_low() -> None:
    text = "《广告法》规定，不得使用“国家级”这类表述。"
    findings, _ = make_engine().check(text, has_ai_content=False)
    hit = next(item for item in findings if item.rule_id == "ad-001")
    assert hit.level == "low"
    assert hit.note is not None


def test_ai_label_missing() -> None:
    findings, ai_label = make_engine().check("本文由AI整理，介绍我们的产品。", has_ai_content=True)
    assert ai_label.required is True
    assert ai_label.detected is False
    assert "ai-label-missing" in rule_ids(findings)


def test_ai_label_present() -> None:
    text = "本文含AI生成内容，已由作者人工核校。"
    findings, ai_label = make_engine().check(text, has_ai_content=True)
    assert ai_label.detected is True
    assert "ai-label-missing" not in rule_ids(findings)


def test_ai_label_not_required_without_declaration() -> None:
    _, ai_label = make_engine().check("普通的一段产品介绍。", has_ai_content=False)
    assert ai_label.required is False


def test_regex_rule_hits_percentage() -> None:
    findings, _ = make_engine().check("通过率 100%，值得信赖。", has_ai_content=False)
    hit = next(item for item in findings if item.rule_id == "ad-030")
    assert hit.matched.replace(" ", "") == "100%"
