/* 视图层基元：图标、反馈条、规则库统计行、总览行、AI 标识块、剪贴板。
   所有文本节点一律走 textContent，杜绝 innerHTML 拼接用户原文。 */
(function (global) {
  "use strict";

  var SVG_NS = "http://www.w3.org/2000/svg";
  var SPRITE = "/assets/icons.svg#i-";

  function icon(name, size, extraClass) {
    var svg = document.createElementNS(SVG_NS, "svg");
    svg.setAttribute("class", "icon icon-" + size + (extraClass ? " " + extraClass : ""));
    svg.setAttribute("aria-hidden", "true");
    svg.setAttribute("focusable", "false");
    var use = document.createElementNS(SVG_NS, "use");
    use.setAttribute("href", SPRITE + name);
    svg.appendChild(use);
    return svg;
  }

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (typeof text === "string" && text.length > 0) node.textContent = text;
    return node;
  }

  function clear(node) {
    node.replaceChildren();
    return node;
  }

  function formatSeconds(ms) {
    return (ms / 1000).toFixed(2) + " 秒";
  }

  function sortedCategories(categories) {
    if (!categories || typeof categories !== "object") return [];
    return Object.keys(categories)
      .map(function (name) {
        return { name: name, count: Number(categories[name]) || 0 };
      })
      .sort(function (a, b) {
        if (b.count !== a.count) return b.count - a.count;
        return a.name.localeCompare(b.name, "zh-Hans-CN");
      });
  }

  /* ── 规则库统计行：四项全部来自 /api/v1/meta ─────────────────────────── */
  function renderMeta(row, meta) {
    clear(row);
    if (!meta) {
      row.appendChild(el("span", "meta-item", "规则库信息读取失败，请刷新页面重试"));
      return;
    }
    row.appendChild(el("span", "meta-item", "规则库 " + meta.total_rules + " 条"));

    var parts = sortedCategories(meta.categories).map(function (item) {
      return item.name + " " + item.count;
    });
    if (parts.length > 0) row.appendChild(el("span", "meta-item", parts.join(" / ")));
    if (meta.updated_at) row.appendChild(el("span", "meta-item", "最近更新 " + meta.updated_at));
    if (meta.version) row.appendChild(el("span", "meta-item", "版本 " + meta.version));
  }

  /* ── 总览行：一行式，耗时只来自 summary.elapsed_ms ───────────────────── */
  function overviewItem(label, value, tone) {
    var wrap = el("span", "ov-item");
    var num = el("span", "ov-num" + (tone ? " " + tone : ""), String(value));
    wrap.appendChild(num);
    wrap.appendChild(document.createTextNode(label));
    return wrap;
  }

  function renderOverview(root, summary, meta) {
    clear(root);
    var counts = el("div", "overview-counts");
    var high = Number(summary.high) || 0;
    counts.appendChild(overviewItem("高风险", high, high > 0 ? "is-high" : ""));
    counts.appendChild(el("span", "ov-sep"));
    counts.appendChild(overviewItem("中风险", Number(summary.medium) || 0, ""));
    counts.appendChild(el("span", "ov-sep"));
    counts.appendChild(overviewItem("低风险", Number(summary.low) || 0, ""));
    root.appendChild(counts);

    var metaLine = el("p", "overview-meta");
    if (meta && typeof meta.total_rules === "number") {
      metaLine.appendChild(el("span", "mono", "比对 " + meta.total_rules + " 条规则"));
    }
    if (typeof summary.elapsed_ms === "number" && isFinite(summary.elapsed_ms)) {
      metaLine.appendChild(el("span", "mono", "耗时 " + formatSeconds(summary.elapsed_ms)));
    }
    if (metaLine.childNodes.length > 0) root.appendChild(metaLine);
  }

  /* ── AI 标识块：只读 ai_label，且全页只渲染一次 ───────────────────────── */
  function renderAiBlock(root, aiLabel, onCopy) {
    clear(root);
    if (!aiLabel || typeof aiLabel !== "object") return;

    var missing = aiLabel.required === true && aiLabel.detected !== true;
    var panel = el("div", "ai-panel" + (missing ? " is-missing" : aiLabel.detected ? " is-ok" : ""));
    var iconName = missing ? "badge-alert" : aiLabel.detected ? "badge-check" : "info";
    panel.appendChild(icon(iconName, 20, "ai-icon"));

    var body = el("div", "ai-body");
    body.appendChild(el("p", "ai-title", "AI 标识检查"));
    body.appendChild(el("p", "ai-text", typeof aiLabel.message === "string" ? aiLabel.message : ""));

    var suggestion = typeof aiLabel.suggestion === "string" ? aiLabel.suggestion.trim() : "";
    if (missing && suggestion) {
      body.appendChild(el("div", "ai-suggestion", suggestion));
      var actions = el("div", "suggestion-actions");
      var button = el("button", "btn btn-ghost btn-copy");
      button.type = "button";
      button.dataset.ruleId = "ai-label-missing";
      button.appendChild(icon("copy", 16));
      button.appendChild(el("span", "btn-label", "复制标识话术"));
      if (typeof onCopy === "function") {
        button.addEventListener("click", function () {
          onCopy("ai-label-missing", suggestion, button);
        });
      }
      actions.appendChild(button);
      body.appendChild(actions);
    }
    panel.appendChild(body);
    root.appendChild(panel);
  }

  /* ── 反馈区：错误条 / 中性引导 / 加载播报 ─────────────────────────────── */
  function showError(root, options) {
    var alert = el("div", "alert " + (options.tone === "warn" ? "is-warn" : "is-error"));
    alert.setAttribute("role", "alert");
    alert.appendChild(icon("circle-alert", 20, "alert-icon"));

    var body = el("div", "alert-body");
    body.appendChild(el("p", "alert-text", options.message));
    var sub = el("p", "alert-sub");
    body.appendChild(sub);
    alert.appendChild(body);

    if (typeof options.onRetry === "function") {
      var button = el("button", "btn btn-ghost");
      button.type = "button";
      button.appendChild(icon("refresh-cw", 20));
      button.appendChild(el("span", "btn-label", "重试"));
      button.addEventListener("click", options.onRetry);
      alert.appendChild(button);
    }

    root.appendChild(alert);
    return { node: alert, sub: sub };
  }

  function showGuide(root, message) {
    var box = el("div", "hint-guide");
    box.appendChild(icon("info", 16));
    box.appendChild(el("span", "", message));
    root.appendChild(box);
  }

  function showStatus(root, message) {
    var box = el("div", "load-status");
    box.setAttribute("role", "status");
    box.appendChild(icon("loader-circle", 16, "is-spinning"));
    box.appendChild(el("span", "", message));
    root.appendChild(box);
    return box;
  }

  /* ── 剪贴板：优先 Clipboard API，非安全上下文降级为 execCommand ────────── */
  function legacyCopy(text) {
    var shim = el("textarea", "copy-shim");
    shim.value = text;
    shim.setAttribute("readonly", "");
    document.body.appendChild(shim);
    var ok = false;
    try {
      shim.select();
      ok = document.execCommand("copy");
    } catch (error) {
      ok = false;
    }
    document.body.removeChild(shim);
    return ok;
  }

  function copyText(text) {
    if (!text) return Promise.resolve(false);
    if (navigator.clipboard && typeof navigator.clipboard.writeText === "function") {
      return navigator.clipboard.writeText(text).then(
        function () {
          return true;
        },
        function () {
          return legacyCopy(text);
        }
      );
    }
    return Promise.resolve(legacyCopy(text));
  }

  global.SentinelUI = {
    icon: icon,
    el: el,
    clear: clear,
    formatSeconds: formatSeconds,
    renderMeta: renderMeta,
    renderOverview: renderOverview,
    renderAiBlock: renderAiBlock,
    showError: showError,
    showGuide: showGuide,
    showStatus: showStatus,
    copyText: copyText
  };
})(window);
