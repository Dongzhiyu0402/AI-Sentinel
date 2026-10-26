/* 报告条目层渲染：命中原文切片高亮（textContent + <mark>，禁用 innerHTML）、
   建议块、依据条文、空命中态与分级筛选。 */
(function (global) {
  "use strict";

  var UI = global.SentinelUI;
  var CONTEXT = 12;
  var LEVEL_TEXT = { high: "高风险", medium: "中风险", low: "提示" };
  var LEVEL_ICON = { high: "octagon-alert", medium: "triangle-alert", low: "info" };
  var COLLAPSE_LIMIT = 10;

  function levelBadge(level) {
    var badge = UI.el("span", "level-badge level-" + level);
    badge.appendChild(UI.icon(LEVEL_ICON[level] || "info", 16));
    badge.appendChild(UI.el("span", "", LEVEL_TEXT[level] || "提示"));
    return badge;
  }

  function sliceValid(finding, source) {
    var matched = finding.matched;
    if (typeof matched !== "string" || matched.length === 0) return false;
    if (typeof source !== "string" || source.length === 0) return false;
    if (!Number.isInteger(finding.start) || !Number.isInteger(finding.end)) return false;
    if (finding.start < 0 || finding.end <= finding.start) return false;
    if (finding.end - finding.start !== matched.length) return false;
    return source.slice(finding.start, finding.end) === matched;
  }

  /* 校验失败时降级为纯文本命中词，绝不渲染半截上下文或错位高亮 */
  function appendExcerpt(target, finding, source) {
    if (!sliceValid(finding, source)) {
      if (typeof finding.matched === "string" && finding.matched.length > 0) {
        target.appendChild(UI.el("span", "matched-fallback", finding.matched));
      }
      return;
    }
    var start = finding.start;
    var end = finding.end;
    var from = Math.max(0, start - CONTEXT);
    var to = Math.min(source.length, end + CONTEXT);

    if (from > 0) target.appendChild(document.createTextNode("…"));
    target.appendChild(document.createTextNode(source.slice(from, start)));
    var mark = document.createElement("mark");
    mark.textContent = source.slice(start, end);
    target.appendChild(mark);
    target.appendChild(document.createTextNode(source.slice(end, to)));
    if (to < source.length) target.appendChild(document.createTextNode("…"));
  }

  function buildCard(finding, ctx) {
    var card = UI.el("article", "finding level-" + (finding.level || "low"));

    var head = UI.el("div", "finding-head");
    head.appendChild(levelBadge(finding.level || "low"));
    if (finding.category) head.appendChild(UI.el("span", "finding-category", finding.category));
    card.appendChild(head);

    var excerpt = UI.el("p", "finding-excerpt");
    appendExcerpt(excerpt, finding, ctx.text);
    card.appendChild(excerpt);

    var block = UI.el("div", "finding-suggestion");
    var title = UI.el("p", "suggestion-title");
    title.appendChild(UI.icon("pen-line", 16));
    title.appendChild(UI.el("span", "", "建议这样改"));
    block.appendChild(title);
    block.appendChild(
      UI.el("p", "suggestion-text", finding.suggestion || "该条命中暂无模板建议，请按依据条文人工修改。")
    );
    if (finding.suggestion_source === "llm") {
      block.appendChild(UI.el("p", "suggestion-source", "模型改写"));
    }

    var actions = UI.el("div", "suggestion-actions");
    var copy = UI.el("button", "btn btn-ghost btn-copy");
    copy.type = "button";
    if (finding.rule_id) copy.dataset.ruleId = finding.rule_id;
    copy.appendChild(UI.icon("copy", 16));
    copy.appendChild(UI.el("span", "btn-label", "复制这条建议"));
    actions.appendChild(copy);
    block.appendChild(actions);
    card.appendChild(block);

    var basis = UI.el("p", "finding-basis");
    basis.appendChild(UI.icon("book-open", 16));
    var basisText = UI.el("span", "");
    basisText.appendChild(UI.el("span", "basis-label", "依据 · "));
    basisText.appendChild(document.createTextNode(finding.basis || "规则库内置判定依据"));
    basis.appendChild(basisText);
    card.appendChild(basis);

    if (finding.note) card.appendChild(UI.el("p", "finding-note", finding.note));
    return card;
  }

  /* 空命中：不复用风险卡（避免徽章 + 色条的自我矛盾语义） */
  function buildEmpty(ctx) {
    var card = UI.el("div", "finding is-empty");
    var title = UI.el("p", "empty-title");
    title.appendChild(UI.icon("shield-check", 20));
    title.appendChild(UI.el("span", "", "未发现明显违规表述"));
    card.appendChild(title);

    var text = "建议发布前再用平台官方预检复核一遍 —— 合规风险还会来自平台未公开的审核细则、行业资质与上下文语境。";
    if (ctx.totalRules) text = "已比对 " + ctx.totalRules + " 条规则。" + text;
    card.appendChild(UI.el("p", "empty-text", text));

    var actions = UI.el("div", "empty-actions");
    var button = UI.el("button", "btn btn-ghost");
    button.type = "button";
    button.appendChild(UI.el("span", "btn-label", "查看规则库覆盖范围"));
    if (typeof ctx.onShowRules === "function") button.addEventListener("click", ctx.onShowRules);
    actions.appendChild(button);
    card.appendChild(actions);
    return card;
  }

  function renderList(root, items, ctx) {
    UI.clear(root);
    if (items.length === 0) {
      if (ctx.filtered) {
        root.appendChild(UI.el("p", "empty-text", "当前筛选下没有条目，切换上方筛选可查看其他命中。"));
      } else {
        root.appendChild(buildEmpty(ctx));
      }
      return;
    }
    var fragment = document.createDocumentFragment();
    items.forEach(function (finding) {
      fragment.appendChild(buildCard(finding, ctx));
    });
    root.appendChild(fragment);
  }

  function renderChips(root, counts, active) {
    UI.clear(root);
    var options = [
      { key: "all", label: "全部", count: counts.all },
      { key: "high", label: "高风险", count: counts.high },
      { key: "medium", label: "中风险", count: counts.medium },
      { key: "low", label: "低风险", count: counts.low }
    ];
    var fragment = document.createDocumentFragment();
    options.forEach(function (option) {
      var chip = UI.el("button", "chip");
      chip.type = "button";
      chip.dataset.level = option.key;
      chip.setAttribute("aria-pressed", option.key === active ? "true" : "false");
      chip.appendChild(document.createTextNode(option.label));
      chip.appendChild(UI.el("span", "chip-count", String(option.count)));
      fragment.appendChild(chip);
    });
    root.appendChild(fragment);
  }

  function countByLevel(items) {
    return items.reduce(
      function (acc, item) {
        if (item.level === "high") acc.high += 1;
        else if (item.level === "medium") acc.medium += 1;
        else acc.low += 1;
        return acc;
      },
      { all: items.length, high: 0, medium: 0, low: 0 }
    );
  }

  global.SentinelFindings = {
    COLLAPSE_LIMIT: COLLAPSE_LIMIT,
    renderList: renderList,
    renderChips: renderChips,
    countByLevel: countByLevel,
    sliceValid: sliceValid
  };
})(window);
