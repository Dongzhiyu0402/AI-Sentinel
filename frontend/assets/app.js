/* 页面编排：加载规则库信息、字数校验、提交检测、渲染报告、复制建议与错误恢复。
   业务与视图分别下沉到 api.js / ui.js / findings.js，本文件只做状态与事件绑定。 */
(function () {
  "use strict";

  var API = window.SentinelApi;
  var UI = window.SentinelUI;
  var Findings = window.SentinelFindings;

  var SAMPLE_TEXT = [
    "本店新品上市，全网最低价，国家级认证，100%有效。",
    "使用七天即可根治失眠，无副作用，药到病除。",
    "现在关注并转发朋友圈，集赞满30个，加微信领体验装。",
    "点击领取专属优惠，速看！",
    "",
    "（本文部分内容由AI整理）"
  ].join("\n");

  var el = {
    metaRow: document.getElementById("metaRow"),
    textarea: document.getElementById("textInput"),
    charNow: document.getElementById("charNow"),
    charCount: document.getElementById("charCount"),
    lengthWarn: document.getElementById("lengthWarn"),
    aiCheck: document.getElementById("aiCheck"),
    sampleBtn: document.getElementById("sampleBtn"),
    checkBtn: document.getElementById("checkBtn"),
    checkBtnLabel: document.getElementById("checkBtnLabel"),
    feedback: document.getElementById("feedback"),
    results: document.getElementById("results"),
    resultsTitle: document.getElementById("resultsTitle"),
    overview: document.getElementById("overview"),
    aiBlock: document.getElementById("aiBlock"),
    chips: document.getElementById("chips"),
    findingList: document.getElementById("findingList"),
    disclaimer: document.getElementById("disclaimer"),
    copyAllBtn: document.getElementById("copyAllBtn"),
    recheckBtn: document.getElementById("recheckBtn")
  };

  var state = {
    meta: null,
    findings: [],
    sourceText: "",
    filter: "all",
    busy: false,
    cooldownUntil: 0
  };

  function clearFeedback() {
    UI.clear(el.feedback);
  }

  function updateCount() {
    var length = el.textarea.value.length;
    el.charNow.textContent = String(length);
    var over = length > API.MAX_TEXT;
    el.charCount.classList.toggle("is-over", over);
    el.charCount.classList.toggle("is-near", !over && length > API.MAX_TEXT * 0.9);
    el.lengthWarn.hidden = !over;
    if (over) {
      el.lengthWarn.textContent = "文本超过 20000 字，请分段检测；不会自动截断，以免漏检。";
    }
    el.checkBtn.disabled = state.busy || over || Date.now() < state.cooldownUntil;
  }

  function setLoading(loading) {
    state.busy = loading;
    el.checkBtn.classList.toggle("is-loading", loading);
    el.checkBtn.setAttribute("aria-busy", loading ? "true" : "false");
    el.textarea.readOnly = loading;
    el.checkBtnLabel.textContent = loading
      ? "正在比对 " + (state.meta ? state.meta.total_rules : 0) + " 条规则"
      : "开始体检";
    updateCount();
  }

  function loadMeta() {
    API.fetchMeta()
      .then(function (meta) {
        state.meta = meta;
        UI.renderMeta(el.metaRow, meta);
      })
      .catch(function () {
        UI.renderMeta(el.metaRow, null);
      });
  }

  function renderFilters() {
    var counts = Findings.countByLevel(state.findings);
    if (counts.all === 0) {
      el.chips.hidden = true;
      UI.clear(el.chips);
      return;
    }
    el.chips.hidden = false;
    Findings.renderChips(el.chips, counts, state.filter);
    Array.prototype.forEach.call(el.chips.querySelectorAll(".chip"), function (chip) {
      chip.addEventListener("click", function () {
        state.filter = chip.dataset.level || "all";
        renderFilters();
        renderFindings();
      });
    });
  }

  function renderFindings() {
    var items = state.findings;
    if (state.filter !== "all") {
      items = items.filter(function (item) {
        return item.level === state.filter;
      });
    }
    Findings.renderList(el.findingList, items, {
      text: state.sourceText,
      totalRules: state.meta ? state.meta.total_rules : 0,
      filtered: state.filter !== "all",
      onShowRules: function () {
        el.metaRow.scrollIntoView({ behavior: "smooth", block: "center" });
      }
    });
  }

  function renderResult(data) {
    state.sourceText = el.textarea.value;
    state.findings = (data.findings || []).filter(function (item) {
      return item.rule_id !== "ai-label-missing";
    });
    state.filter = "all";

    var counts = Findings.countByLevel(state.findings);
    UI.renderOverview(
      el.overview,
      {
        high: counts.high,
        medium: counts.medium,
        low: counts.low,
        elapsed_ms: data.summary ? data.summary.elapsed_ms : 0
      },
      state.meta
    );
    UI.renderAiBlock(el.aiBlock, data.ai_label, handleCopy);
    renderFilters();
    renderFindings();
    el.disclaimer.textContent = data.disclaimer || "";
    el.results.hidden = false;
    el.resultsTitle.focus({ preventScroll: true });
    el.results.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function handleCopy(ruleId, text, button) {
    UI.copyText(text).then(function (ok) {
      if (!ok) return;
      var label = button.querySelector(".btn-label");
      var original = label ? label.textContent : "";
      if (label) label.textContent = "已复制";
      window.setTimeout(function () {
        if (label) label.textContent = original;
      }, 1600);
      if (ruleId) API.trackSuggestionCopied(ruleId);
    });
  }

  function startCooldown(seconds, sub) {
    var total = Math.max(1, Math.floor(seconds));
    state.cooldownUntil = Date.now() + total * 1000;
    updateCount();
    function render() {
      var left = Math.ceil((state.cooldownUntil - Date.now()) / 1000);
      if (left <= 0) {
        state.cooldownUntil = 0;
        updateCount();
        if (sub) sub.textContent = "";
        window.clearInterval(timer);
        return;
      }
      if (sub) sub.textContent = "本次检测额度已用完，约 " + Math.ceil(left / 60) + " 分钟后可再次检测。";
    }
    var timer = window.setInterval(render, 1000);
    render();
  }

  function handleError(error) {
    var code = error && error.code ? error.code : "unknown";
    API.trackError(code);
    clearFeedback();
    var result = UI.showError(el.feedback, {
      message: (error && error.message) || "检测失败，请稍后重试。",
      onRetry: runCheck
    });
    if (code === "http_429" && error.retryAfter) {
      startCooldown(error.retryAfter, result.sub);
    }
  }

  function runCheck() {
    var text = el.textarea.value;
    if (!text.trim()) {
      clearFeedback();
      UI.showGuide(el.feedback, "先粘贴一段文案，再开始体检。");
      el.textarea.focus();
      return;
    }
    if (text.length > API.MAX_TEXT) {
      updateCount();
      el.textarea.focus();
      return;
    }

    clearFeedback();
    setLoading(true);
    var status = UI.showStatus(el.feedback, "规则引擎比对中，通常不超过 2 秒");

    API.check(text, el.aiCheck.checked)
      .then(function (data) {
        status.node.remove();
        renderResult(data);
      })
      .catch(function (error) {
        status.node.remove();
        handleError(error);
      })
      .finally(function () {
        setLoading(false);
      });
  }

  el.textarea.addEventListener("input", function () {
    updateCount();
    if (!el.lengthWarn.hidden) return;
  });

  el.sampleBtn.addEventListener("click", function () {
    el.textarea.value = SAMPLE_TEXT;
    el.aiCheck.checked = true;
    updateCount();
    el.textarea.focus();
    clearFeedback();
  });

  el.checkBtn.addEventListener("click", runCheck);
  el.recheckBtn.addEventListener("click", runCheck);

  el.copyAllBtn.addEventListener("click", function () {
    var texts = state.findings
      .map(function (item) {
        return item.suggestion;
      })
      .filter(function (text) {
        return typeof text === "string" && text.length > 0;
      });
    if (texts.length === 0) return;
    UI.copyText(texts.join("\n\n")).then(function (ok) {
      var label = el.copyAllBtn.querySelector(".btn-label");
      if (!ok || !label) return;
      var original = label.textContent;
      label.textContent = "已复制";
      window.setTimeout(function () {
        label.textContent = original;
      }, 1600);
    });
  });

  el.findingList.addEventListener("click", function (event) {
    var button = event.target.closest(".btn-copy");
    if (!button) return;
    var card = button.closest(".finding");
    var suggestion = card ? card.querySelector(".suggestion-text") : null;
    if (!suggestion) return;
    handleCopy(button.dataset.ruleId, suggestion.textContent, button);
  });

  updateCount();
  loadMeta();
})();
