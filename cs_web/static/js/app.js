/* CS Controle 360º — shared UI helpers
 *
 * Handles:
 *  - Sidebar toggle on small viewports.
 *  - Confirm dialogs for delete-style forms (`data-confirm="..."`).
 *  - Toast notifications triggered by query-string flash messages
 *    (`?flash=success&msg=...`) and a global `window.toast(...)` helper.
 */
(function () {
  "use strict";

  // ---------------------------------------------------------------------------
  // Sidebar toggle
  // ---------------------------------------------------------------------------
  document.addEventListener("click", function (event) {
    var sidebar = document.getElementById("app-sidebar");
    if (!sidebar) return;
    if (event.target.closest("[data-toggle-sidebar]")) {
      sidebar.classList.toggle("is-open");
      event.preventDefault();
    } else if (event.target.closest("[data-close-sidebar]")) {
      sidebar.classList.remove("is-open");
    } else if (
      sidebar.classList.contains("is-open") &&
      !event.target.closest(".sidebar") &&
      !event.target.closest("[data-toggle-sidebar]")
    ) {
      sidebar.classList.remove("is-open");
    }
  });

  // ---------------------------------------------------------------------------
  // Confirm dialogs
  // ---------------------------------------------------------------------------
  document.addEventListener(
    "submit",
    function (event) {
      var form = event.target;
      if (!(form instanceof HTMLFormElement)) return;
      var msg = form.getAttribute("data-confirm");
      if (!msg) return;
      if (!window.confirm(msg)) {
        event.preventDefault();
      }
    },
    true
  );

  document.addEventListener(
    "click",
    function (event) {
      var link = event.target.closest("a[data-confirm]");
      if (!link) return;
      if (!window.confirm(link.getAttribute("data-confirm"))) {
        event.preventDefault();
      }
    },
    true
  );

  // ---------------------------------------------------------------------------
  // Toasts
  // ---------------------------------------------------------------------------
  function ensureContainer() {
    var el = document.getElementById("toast-container");
    if (el) return el;
    el = document.createElement("div");
    el.id = "toast-container";
    document.body.appendChild(el);
    return el;
  }

  function toast(opts) {
    var container = ensureContainer();
    var level = opts.level || "info";
    var node = document.createElement("div");
    node.className = "toast " + level;

    var icon = document.createElement("span");
    icon.className = "toast__icon";
    icon.textContent =
      level === "success" ? "✓" : level === "error" ? "!" : "i";
    node.appendChild(icon);

    var body = document.createElement("div");
    body.className = "toast__body";
    if (opts.title) {
      var title = document.createElement("div");
      title.className = "toast__title";
      title.textContent = opts.title;
      body.appendChild(title);
    }
    if (opts.message) {
      var msg = document.createElement("div");
      msg.className = "toast__message";
      msg.textContent = opts.message;
      body.appendChild(msg);
    }
    node.appendChild(body);

    var close = document.createElement("button");
    close.type = "button";
    close.className = "toast__close";
    close.setAttribute("aria-label", "Fechar");
    close.textContent = "×";
    close.addEventListener("click", function () {
      node.remove();
    });
    node.appendChild(close);

    container.appendChild(node);

    var timeout = opts.timeout || 4500;
    if (timeout > 0) {
      setTimeout(function () {
        if (node.parentNode) node.remove();
      }, timeout);
    }
    return node;
  }

  window.toast = toast;

  // Flash messages via query string (?flash=success&msg=...)
  function consumeFlashFromUrl() {
    if (!window.URLSearchParams) return;
    var params = new URLSearchParams(window.location.search);
    var level = params.get("flash");
    var message = params.get("msg");
    if (!level) return;
    toast({
      level: level,
      title:
        level === "success"
          ? "Sucesso"
          : level === "error"
          ? "Erro"
          : "Aviso",
      message: message || undefined,
    });
    params.delete("flash");
    params.delete("msg");
    var query = params.toString();
    var url =
      window.location.pathname + (query ? "?" + query : "") + window.location.hash;
    window.history.replaceState({}, "", url);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", consumeFlashFromUrl);
  } else {
    consumeFlashFromUrl();
  }
})();
