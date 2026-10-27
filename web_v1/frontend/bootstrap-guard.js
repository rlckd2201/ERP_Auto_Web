(function () {
  "use strict";
  let failed = false;
  function report(message, source, line) {
    if (failed || !document.querySelector("#loginSubmitButton")?.disabled) return;
    failed = true;
    console.error("Accounting bootstrap failed", String(message).slice(0, 180), String(source || "").split("?")[0], Number(line) || 0);
    const notice = document.createElement("section");
    notice.id = "accountingBootstrapError";
    notice.setAttribute("role", "alert");
    notice.style.cssText = "max-width:640px;margin:12vh auto;padding:24px;background:white;border:1px solid #d7e0e8;border-radius:12px;color:#17334d;font:16px sans-serif";
    const title = document.createElement("h2");
    title.textContent = "회계 화면을 시작하지 못했습니다.";
    const text = document.createElement("p");
    text.textContent = "화면을 새로고침해 주세요. 같은 문제가 계속되면 담당자에게 알려 주세요.";
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = "새로고침";
    button.addEventListener("click", () => location.reload());
    notice.append(title, text, button);
    document.body.appendChild(notice);
  }
  window.addEventListener("error", event => {
    if (String(event.filename || "").includes("/assets/app.js")) report(event.message, event.filename, event.lineno);
    else if (event.target?.tagName === "SCRIPT" && String(event.target.src || "").includes("/assets/app.js")) {
      report("Application script could not be loaded", event.target.src, 0);

    }
  }, true);
})();
