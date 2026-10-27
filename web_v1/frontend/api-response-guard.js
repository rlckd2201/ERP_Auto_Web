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
  function waitForSetupRetry(delay, signal) {
    return new Promise((resolve, reject) => {
      const abort = () => {
        clearTimeout(timer);
        reject(signal.reason || new DOMException("The operation was aborted", "AbortError"));
      };
      const timer = setTimeout(() => {
        signal?.removeEventListener("abort", abort);
        resolve();
      }, delay);
      if (signal?.aborted) abort();
      else signal?.addEventListener("abort", abort, { once: true });
    });
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
    const options = args[1] || {};
    const method = String(options.method || input?.method || "GET").toUpperCase();
    const signal = options.signal || input?.signal;
    const setupRead = method === "GET" && !options.body && !input?.body && url.origin === location.origin && /(?:^|\/)api\/setup\/status\/?$/.test(url.pathname);
    let response;
    for (let attempt = 0; ; attempt += 1) {
      response = await upstreamFetch(...args);
      if (!setupRead || ![502, 503, 504].includes(response.status) || attempt >= 2 || signal?.aborted) break;
      console.warn("Accounting setup query retry", response.status, attempt + 1, url.pathname);
      try { await response.body?.cancel(); } catch {}
      await waitForSetupRetry([350, 1000][attempt], signal);
    }
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
