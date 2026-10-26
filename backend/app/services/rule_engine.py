"""规则引擎：纯 Python Aho-Corasick 多模式匹配 + 规则加载 + 检测编排。

设计要点：
1. 规则与代码解耦：规则存放在 data/rules.yaml，运营可独立维护；
2. 不依赖 C 扩展：自带 Aho-Corasick 实现，Windows 环境零编译依赖；
3. 可解释优先：每条命中都携带依据条文与修改建议；
4. 豁免降级：命中窗口内出现引用/转述等信号时降级为 low，交由人工复核。
"""
from __future__ import annotations

import re
import unicodedata
from collections import deque
from dataclasses import dataclass
from pathlib import Path

import yaml

from app.schemas.models import AiLabelCheck, Finding

# 风险等级排序权重：先 high，再 medium，最后 low
_LEVEL_ORDER = {"high": 0, "medium": 1, "low": 2}

# AI 标识用语清单：覆盖真实写法（含"由AI生成""AI辅助创作"等变体）。
# 匹配前先做 NFKC 归一化 + 去空白 + 去零宽字符 + 大小写折叠，所以这里只写规范形态；
# 末尾的裸"ai生成"用于兜住未枚举的复合写法（例如"AI 生成图片"），避免漏判。
AI_LABEL_MARKERS = (
    "本文含ai生成内容",
    "本文包含ai生成内容",
    "本文由ai生成",
    "本内容由ai生成",
    "本内容含ai生成",
    "含ai生成内容",
    "由ai生成",
    "使用ai生成",
    "ai生成",
    "ai生成内容声明",
    "ai辅助生成",
    "ai辅助创作",
    "ai参与创作",
    "ai合成内容",
    "#ai生成",
)

_ZERO_WIDTH_PATTERN = re.compile(r"[\u200b-\u200f\u2060\ufeff]")
_WHITESPACE_PATTERN = re.compile(r"\s+")


def normalize_label_text(text: str) -> str:
    """把文本归一化到可比较形态：全角转半角、去空白、去零宽、大小写折叠。

    标识允许出现在文中任意位置，归一化只影响比较，不改动原文与命中位置。
    """
    normalized = unicodedata.normalize("NFKC", text)
    normalized = _ZERO_WIDTH_PATTERN.sub("", normalized)
    normalized = _WHITESPACE_PATTERN.sub("", normalized)
    return normalized.casefold()


_NORMALIZED_MARKERS = tuple(normalize_label_text(marker) for marker in AI_LABEL_MARKERS)


def _finding_sort_key(item: Finding) -> tuple[int, int, str]:
    return (_LEVEL_ORDER.get(item.level, len(_LEVEL_ORDER)), item.start, item.rule_id)


@dataclass(frozen=True)
class Rule:
    id: str
    category: str
    level: str
    pattern: str
    basis: str
    suggestion: str
    exempt: str = ""
    is_regex: bool = False


class _Node:
    __slots__ = ("children", "fail", "outputs")

    def __init__(self) -> None:
        self.children: dict[str, _Node] = {}
        self.fail: _Node | None = None
        self.outputs: list[int] = []


class AhoCorasick:
    """一次扫描找出全部模式串，返回 (模式下标, 起点, 终点)。"""

    def __init__(self, patterns: list[str]) -> None:
        self._patterns = patterns
        self._root = _Node()
        for idx, pattern in enumerate(patterns):
            node = self._root
            for char in pattern:
                node = node.children.setdefault(char, _Node())
            node.outputs.append(idx)

        queue: deque[_Node] = deque()
        for child in self._root.children.values():
            child.fail = self._root
            queue.append(child)

        while queue:
            node = queue.popleft()
            for char, child in node.children.items():
                fallback = node.fail
                while fallback is not None and char not in fallback.children:
                    fallback = fallback.fail
                child.fail = fallback.children[char] if fallback else self._root
                if child.fail is child:
                    child.fail = self._root
                child.outputs.extend(child.fail.outputs)
                queue.append(child)

    def search(self, text: str) -> list[tuple[int, int, int]]:
        results: list[tuple[int, int, int]] = []
        node = self._root
        for index, char in enumerate(text):
            while node is not None and char not in node.children:
                node = node.fail
            if node is None:
                node = self._root
                continue
            node = node.children[char]
            for pattern_index in node.outputs:
                start = index - len(self._patterns[pattern_index]) + 1
                results.append((pattern_index, start, index + 1))
        return results


class RuleEngine:
    def __init__(self, rules_path: str | Path) -> None:
        self.rules_path = Path(rules_path)
        self.version = "unknown"
        self.updated_at = ""
        self.rules: list[Rule] = []
        self._load()

    def _load(self) -> None:
        data = yaml.safe_load(self.rules_path.read_text(encoding="utf-8")) or {}
        self.version = str(data.get("version", "unknown"))
        self.updated_at = str(data.get("updated_at", ""))
        rules: list[Rule] = []
        for item in data.get("rules", []):
            rules.append(
                Rule(
                    id=str(item["id"]),
                    category=str(item["category"]),
                    level=str(item["level"]),
                    pattern=str(item["pattern"]),
                    basis=str(item["basis"]),
                    suggestion=str(item["suggestion"]),
                    exempt=str(item.get("exempt", "")),
                    is_regex=bool(item.get("is_regex", False)),
                )
            )
        self.rules = rules
        literals = [rule for rule in rules if not rule.is_regex]
        self._literal_map = {index: rule for index, rule in enumerate(literals)}
        self._automaton = AhoCorasick([rule.pattern for rule in literals])
        self._regex_rules = [rule for rule in rules if rule.is_regex]

    def check(self, text: str, has_ai_content: bool) -> tuple[list[Finding], AiLabelCheck]:
        findings: list[Finding] = []
        seen: set[tuple[str, int, int]] = set()

        for pattern_index, start, end in self._automaton.search(text):
            rule = self._literal_map[pattern_index]
            key = (rule.id, start, end)
            if key in seen:
                continue
            seen.add(key)
            findings.append(self._build_finding(rule, text, start, end))

        for rule in self._regex_rules:
            for match in re.finditer(rule.pattern, text):
                key = (rule.id, match.start(), match.end())
                if key in seen:
                    continue
                seen.add(key)
                findings.append(self._build_finding(rule, text, match.start(), match.end()))

        ai_label = self._check_ai_label(text, has_ai_content)

        if ai_label.required and not ai_label.detected:
            findings.append(
                Finding(
                    rule_id="ai-label-missing",
                    category="AI标识",
                    level="high",
                    matched="",
                    start=0,
                    end=0,
                    basis="《人工智能生成合成内容标识办法》（2025-09-01 施行）",
                    suggestion=ai_label.suggestion or "",
                    note="作者自述含 AI 生成内容，但未检出显式标识",
                )
            )

        # 契约排序：等级 high → medium → low，同级按 start 升序，同一位置按 rule_id 升序
        findings.sort(key=_finding_sort_key)
        return findings, ai_label

    @staticmethod
    def _context(text: str, start: int, end: int, radius: int = 40) -> str:
        return text[max(0, start - radius): min(len(text), end + radius)]

    def _build_finding(self, rule: Rule, text: str, start: int, end: int) -> Finding:
        level = rule.level
        note: str | None = None
        if rule.exempt:
            window = self._context(text, start, end)
            keywords = [keyword for keyword in rule.exempt.split("/") if keyword]
            if any(keyword in window for keyword in keywords):
                level = "low"
                note = "疑似豁免场景（引用/转述等），建议人工复核"
        return Finding(
            rule_id=rule.id,
            category=rule.category,
            level=level,
            matched=text[start:end],
            start=start,
            end=end,
            basis=rule.basis,
            suggestion=rule.suggestion,
            note=note,
        )

    @staticmethod
    def _check_ai_label(text: str, has_ai_content: bool) -> AiLabelCheck:
        normalized = normalize_label_text(text)
        detected = any(marker in normalized for marker in _NORMALIZED_MARKERS)
        if not has_ai_content:
            return AiLabelCheck(
                required=False,
                detected=detected,
                message="未声明含 AI 生成内容，跳过标识检查",
            )
        if detected:
            return AiLabelCheck(
                required=True,
                detected=True,
                message="已检出 AI 生成内容标识",
            )
        return AiLabelCheck(
            required=True,
            detected=False,
            message="你声明文中含 AI 生成内容，但未检出显式标识",
            suggestion=(
                "在文首或相应段落添加显式标识，例如："
                "“本文含AI生成内容，已由作者人工核校。”并按平台要求调整措辞。"
            ),
        )
