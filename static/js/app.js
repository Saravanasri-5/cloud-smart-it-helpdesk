(function () {
  "use strict";
  var MAX_SIZE = 10 * 1024 * 1024;
  var ALLOWED = ["png", "jpg", "jpeg", "pdf"];
  var $ = function (sel, root) { return (root || document).querySelector(sel); };
  var $$ = function (sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); };

  /* ---------- Toasts ---------- */
  function toast(message, category) {
    var box = $("#toast-container");
    if (!box) { return; }
    var el = document.createElement("div");
    el.className = "toast toast-" + (category || "info");
    var text = document.createElement("span");
    text.textContent = message;
    var close = document.createElement("button");
    close.type = "button";
    close.setAttribute("aria-label", "Dismiss");
    close.textContent = "\u00d7";
    close.addEventListener("click", function () { el.remove(); });
    el.appendChild(text);
    el.appendChild(close);
    box.appendChild(el);
    setTimeout(function () { el.remove(); }, 6000);
  }
  window.showToast = toast;

  function showFlashes() {
    var holder = $("#flash-data");
    if (!holder) { return; }
    try {
      JSON.parse(holder.getAttribute("data-messages") || "[]").forEach(function (m) { toast(m[1], m[0]); });
    } catch (e) { /* ignore malformed data */ }
  }

  /* ---------- Loader ---------- */
  var loader = $("#loader");
  function showLoader() { if (loader) { loader.classList.remove("hidden"); } }
  window.addEventListener("pageshow", function () { if (loader) { loader.classList.add("hidden"); } });

  /* ---------- Confirmation dialog ---------- */
  var modal = $("#confirm-modal");
  var pendingForm = null;
  function askConfirm(form, message) {
    pendingForm = form;
    $("#confirm-text").textContent = message;
    modal.classList.remove("hidden");
    $("#confirm-cancel").focus();
  }
  function closeConfirm() { modal.classList.add("hidden"); pendingForm = null; }
  if (modal) {
    $("#confirm-cancel").addEventListener("click", closeConfirm);
    $("#confirm-ok").addEventListener("click", function () {
      var form = pendingForm;
      closeConfirm();
      if (form) { form.removeAttribute("data-confirm"); showLoader(); form.submit(); }
    });
    document.addEventListener("keydown", function (e) { if (e.key === "Escape") { closeConfirm(); } });
  }

  /* ---------- Form validation ---------- */
  function setError(input, message) {
    clearError(input);
    input.classList.add("invalid");
    var small = document.createElement("small");
    small.className = "error-text js-error";
    small.textContent = message;
    input.parentNode.appendChild(small);
  }
  function clearError(input) {
    input.classList.remove("invalid");
    $$(".js-error", input.parentNode).forEach(function (n) { n.remove(); });
  }

  function validateForm(form) {
    var ok = true;
    $$("input, select, textarea", form).forEach(clearError);
    $$("input, select, textarea", form).forEach(function (input) {
      if (input.type === "hidden" || input.disabled) { return; }
      if (input.type === "file") {
        var file = input.files && input.files[0];
        if (!file) { if (input.required) { setError(input, "Please choose a file."); ok = false; } return; }
        var ext = file.name.split(".").pop().toLowerCase();
        if (ALLOWED.indexOf(ext) === -1) { setError(input, "Only PNG, JPG, JPEG or PDF files are allowed."); ok = false; }
        else if (file.size > MAX_SIZE) { setError(input, "File must be 10 MB or smaller."); ok = false; }
        return;
      }
      if (!input.checkValidity()) { setError(input, input.validationMessage); ok = false; }
      else if (input.required && input.type !== "checkbox" && !input.value.trim()) { setError(input, "This field is required."); ok = false; }
    });
    var pw = form.querySelector("[name='password'], [name='new_password']");
    var cf = form.querySelector("[name='confirm']");
    if (pw && cf && pw.value !== cf.value) { setError(cf, "Passwords must match."); ok = false; }
    if (pw && pw.value && !pw.hasAttribute("data-skip-strength") && form.querySelector("[name='confirm']") &&
        !(/[A-Za-z]/.test(pw.value) && /\d/.test(pw.value) && pw.value.length >= 8)) {
      setError(pw, "Use at least 8 characters including letters and numbers."); ok = false;
    }
    return ok;
  }

  $$("form[data-validate]").forEach(function (form) {
    form.addEventListener("submit", function (e) {
      if (!validateForm(form)) {
        e.preventDefault();
        e.stopImmediatePropagation();
        var bad = $(".invalid", form);
        if (bad) { bad.focus(); }
        toast("Please correct the highlighted fields.", "danger");
      }
    });
  });

  /* ---------- Generic submit handling (confirm + loader) ---------- */
  document.addEventListener("submit", function (e) {
    var form = e.target;
    if (e.defaultPrevented) { return; }
    var message = form.getAttribute("data-confirm");
    if (message) { e.preventDefault(); askConfirm(form, message); return; }
    showLoader();
  });

  $$("select[data-autosubmit]").forEach(function (select) {
    select.addEventListener("change", function () {
      if (select.form.requestSubmit) { select.form.requestSubmit(); } else { select.form.submit(); }
    });
  });

  /* ---------- Mobile sidebar ---------- */
  var sidebar = $("#sidebar"), backdrop = $("#sidebar-backdrop"), toggle = $("#menu-toggle");
  function setSidebar(open) {
    if (!sidebar) { return; }
    sidebar.classList.toggle("open", open);
    backdrop.classList.toggle("show", open);
  }
  if (toggle) { toggle.addEventListener("click", function () { setSidebar(!sidebar.classList.contains("open")); }); }
  if (backdrop) { backdrop.addEventListener("click", function () { setSidebar(false); }); }

  /* ---------- CSRF-aware fetch helper for the JSON API ---------- */
  window.apiFetch = function (url, options) {
    options = options || {};
    var meta = $("meta[name='csrf-token']");
    options.headers = Object.assign({ "Content-Type": "application/json", "X-CSRFToken": meta ? meta.content : "" }, options.headers || {});
    options.credentials = "same-origin";
    return fetch(url, options).then(function (r) { return r.json().then(function (body) { return { ok: r.ok, status: r.status, body: body }; }); });
  };

  showFlashes(); // script is deferred, so the DOM is already parsed
})();
