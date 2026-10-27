/* Keep app.js request helpers unchanged: the portal adapts their source. */
(function () {
  "use strict";
  const upstreamFetch = window.fetch.bind(window);
  const htmlDocument = /<!doctype\s+html|<html\b|<head\b|<body\b/i;
  function message(status) {
    return [502, 503, 504].includes(status)
      ? `서버 연결이 일시적으로 원활하지 않습니다. 잠시 후 다시 시도해 주세요. (HTTP ${status})`
      : `서버에서 올바른 응답을 받지 못했습니다. 잠시 후 다시 시도해 주세요. (HTTP ${status})`;
  }
  async function safeText(response) {
    const text = await response.text();
    if (!text) return text;
    let data;
    let invalid = false;
    try { data = JSON.parse(text); } catch { invalid = true; }
    const detail = data && typeof data === "object" ? data.detail || data.message : "";
    const unsafeDetail = typeof detail === "string" && (htmlDocument.test(detail) || detail.length > 600);
    if (invalid || unsafeDetail) {
      if (!response.ok) return JSON.stringify({ detail: message(response.status) });
      const error = new Error(message(response.status));
      error.status = response.status;
      error.transient = [502, 503, 504].includes(response.status);
      throw error;
    }
    return text;
  }
  window.fetch = async function (...args) {
    const input = args[0];
    const url = new URL(typeof input === "string" ? input : input.url || String(input), location.href);
    const response = await upstreamFetch(...args);
    if (url.origin !== location.origin || !/(?:^|\/)api\//.test(url.pathname)) return response;
    return new Proxy(response, {
      get(target, key) {
        if (key === "text") return () => safeText(target);
        const value = Reflect.get(target, key, target);
        return typeof value === "function" ? value.bind(target) : value;
      },
    });
  };
})();
