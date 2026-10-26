/* 接口层：请求封装、错误映射（英文技术信息一律转中文可行动提示）与埋点旁路。
   埋点只上报两个白名单事件：suggestion_copied / error_occurred（check_submitted 由服务端记录）。 */
(function (global) {
  "use strict";

  var API_BASE = "/api/v1";
  var CHECK_TIMEOUT_MS = 12000;
  var META_TIMEOUT_MS = 5000;
  var MAX_TEXT = 20000;

  var TEXT = {
    network: "网络连接失败，文本仍保留在输入框中，请检查网络后重试。",
    timeout: "检测超过 12 秒仍未返回，文本仍保留在输入框中，可稍后重试或先按平台官方预检自查。",
    server: "检测服务暂时不可用，请稍后再试，或先按平台官方预检自查。",
    client: "提交内容不符合要求，请检查文本后重试。",
    busy: "本次检测额度已用完，请稍后再试。"
  };

  // 422 的 detail[0].msg 是英文校验串，只做语义映射，绝不把数组或 JSON 渲染到页面
  var VALIDATION_RULES = [
    { pattern: /at least 1 char|too_short|min_length/i, text: "文本不能为空，请先粘贴需要体检的文案。" },
    { pattern: /20000|too_long|max_length/i, text: "文本超过 20000 字上限，请删减后重试；不会替你截断，避免漏检。" },
    { pattern: /bool/i, text: "「文中包含 AI 生成内容」选项提交异常，请刷新页面后重试。" },
    { pattern: /json|decode|parse/i, text: "提交内容格式异常，请刷新页面后重试。" }
  ];

  function device() {
    var width = window.innerWidth || document.documentElement.clientWidth || 0;
    if (width < 640) return "mobile";
    if (width < 1024) return "tablet";
    return "desktop";
  }

  function makeError(code, message, retryAfter) {
    var error = new Error(message);
    error.code = code;
    error.message = message;
    error.retryAfter = typeof retryAfter === "number" && retryAfter > 0 ? retryAfter : null;
    return error;
  }

  function mapValidationMessage(msg) {
    var raw = typeof msg === "string" ? msg : "";
    for (var i = 0; i < VALIDATION_RULES.length; i += 1) {
      if (VALIDATION_RULES[i].pattern.test(raw)) return VALIDATION_RULES[i].text;
    }
    return TEXT.client;
  }

  function userMessage(payload) {
    if (!payload || typeof payload !== "object") return "";
    var detail = payload.detail;
    if (typeof detail === "string") return detail.trim();
    if (Array.isArray(detail) && detail.length > 0) {
      var first = detail[0];
      return mapValidationMessage(first && typeof first.msg === "string" ? first.msg : "");
    }
    return "";
  }

  function readJson(response) {
    return response.json().catch(function () {
      return null;
    });
  }

  function withTimeout(ms) {
    var controller = new AbortController();
    var timer = setTimeout(function () {
      controller.abort();
    }, ms);
    return {
      signal: controller.signal,
      clear: function () {
        clearTimeout(timer);
      }
    };
  }

  function parseRetryAfter(response, detailText) {
    var header = response.headers.get("Retry-After");
    var fromHeader = header === null ? NaN : Number.parseInt(header, 10);
    if (Number.isFinite(fromHeader) && fromHeader > 0) return fromHeader;
    var minutes = /约\s*(\d+)\s*分钟/.exec(detailText || "");
    if (minutes) return Number.parseInt(minutes[1], 10) * 60;
    return null;
  }

  function fetchMeta() {
    var guard = withTimeout(META_TIMEOUT_MS);
    return fetch(API_BASE + "/meta", { signal: guard.signal })
      .then(function (response) {
        if (!response.ok) throw makeError("meta_" + response.status, TEXT.server);
        return readJson(response);
      })
      .then(function (data) {
        if (!data || typeof data.total_rules !== "number") throw makeError("meta_bad_payload", TEXT.server);
        return data;
      })
      .finally(guard.clear);
  }

  function check(text, hasAiContent) {
    var guard = withTimeout(CHECK_TIMEOUT_MS);
    return fetch(API_BASE + "/check", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: text, has_ai_content: Boolean(hasAiContent) }),
      signal: guard.signal
    })
      .catch(function (error) {
        if (error && error.name === "AbortError") throw makeError("timeout", TEXT.timeout);
        throw makeError("network_error", TEXT.network);
      })
      .then(function (response) {
        if (response.ok) return readJson(response);
        return readJson(response).then(function (payload) {
          var detailText = userMessage(payload);
          if (response.status === 429) {
            throw makeError("http_429", detailText || TEXT.busy, parseRetryAfter(response, detailText));
          }
          if (response.status === 422) throw makeError("http_422", detailText || TEXT.client);
          if (response.status >= 500) throw makeError("http_" + response.status, TEXT.server);
          throw makeError("http_" + response.status, detailText || TEXT.client);
        });
      })
      .then(function (data) {
        if (!data || !data.summary || !Array.isArray(data.findings)) throw makeError("bad_payload", TEXT.server);
        return data;
      })
      .finally(guard.clear);
  }

  // 埋点：单批一条，静默失败、不重试、不阻塞任何可见状态
  function postEvents(items) {
    try {
      fetch(API_BASE + "/events", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ events: items.slice(0, 20) }),
        keepalive: true
      }).catch(function () {});
    } catch (error) {
      /* 埋点不得影响主流程 */
    }
  }

  function trackSuggestionCopied(ruleId) {
    if (!ruleId) return;
    postEvents([
      {
        event: "suggestion_copied",
        rule_id: ruleId,
        timestamp: new Date().toISOString(),
        device: device()
      }
    ]);
  }

  function trackError(errorCode) {
    if (!errorCode) return;
    postEvents([
      {
        event: "error_occurred",
        error_code: String(errorCode),
        timestamp: new Date().toISOString(),
        device: device()
      }
    ]);
  }

  global.SentinelApi = {
    MAX_TEXT: MAX_TEXT,
    TEXT: TEXT,
    device: device,
    check: check,
    fetchMeta: fetchMeta,
    trackSuggestionCopied: trackSuggestionCopied,
    trackError: trackError
  };
})(window);
