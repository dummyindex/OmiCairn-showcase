/* OmiCairn showcase — shared behaviour. Vanilla JS, no network requests.
 *
 * Public API (window.OC), documented in CONTRACT.md:
 *   OC.root                 relative prefix to the site root ("" or "../../")
 *   OC.url("/campaign/")    root-relative -> relative URL (adds index.html to directories)
 *   OC.data(name)           window.OC_DATA[name] (load /assets/data/<name>.js first)
 *   OC.OUTCOMES             [{key, label, short, definition}] in display order
 *   OC.outcome(key)         one of the above
 *   OC.badge(key, {short, count})        outcome badge HTML
 *   OC.stackedBar(counts, {keys, size, label, showValues})  stacked bar HTML
 *   OC.esc(str)             HTML-escape
 *   OC.fmt(n)               thousands separator
 *   OC.hash.get()           URLSearchParams of location.hash
 *   OC.hash.set(obj)        replace hash state ({key: value|[values]|null}) without scrolling
 *   OC.qs / OC.qsa          querySelector helpers
 *   OC.ready(fn)            run after DOMContentLoaded
 * Declarative hooks: [data-oc-theme-toggle], [data-oc-nav-toggle], [data-oc-copy="#id"],
 *   [data-oc-row-toggle] (button with aria-controls of a row/element to show/hide).
 */
(function () {
  "use strict";
  var doc = document.documentElement;
  var OC = window.OC = window.OC || {};

  OC.root = doc.getAttribute("data-root") || "";

  OC.url = function (p) {
    if (!p || p.charAt(0) !== "/" || p.charAt(1) === "/") return p;
    var suffix = "", i = p.search(/[?#]/);
    if (i >= 0) { suffix = p.slice(i); p = p.slice(0, i); }
    p = p.slice(1);
    if (p === "" || p.charAt(p.length - 1) === "/") p += "index.html";
    return OC.root + p + suffix;
  };

  OC.esc = function (s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  };
  OC.fmt = function (n) { return Number(n).toLocaleString("en-US"); };
  OC.qs = function (sel, el) { return (el || document).querySelector(sel); };
  OC.qsa = function (sel, el) { return Array.prototype.slice.call((el || document).querySelectorAll(sel)); };
  OC.ready = function (fn) {
    if (document.readyState !== "loading") fn(); else document.addEventListener("DOMContentLoaded", fn);
  };

  OC.data = function (name) {
    var d = window.OC_DATA && window.OC_DATA[name];
    if (!d) throw new Error("OC.data: '" + name + "' not loaded; add <script src=\"/assets/data/" + name + ".js\"></script>");
    return d;
  };

  OC.OUTCOMES = [
    { key: "supported", label: "Supported", short: "Supported", definition: "The pre-registered decision rule was met." },
    { key: "partial", label: "Partially supported", short: "Partial", definition: "Some parts of the decision rule were met, but not all." },
    { key: "not_supported", label: "Not supported", short: "Not supported", definition: "The test ran and the decision rule was not met." },
    { key: "inconclusive", label: "Inconclusive", short: "Inconclusive", definition: "The test ran but was underpowered, ambiguous or confounded, so the data cannot settle it." },
    { key: "not_testable", label: "Not testable (data)", short: "Not testable", definition: "Not tested, or tested only through a proxy, because suitable data were unavailable or unsuitable." },
    { key: "not_run", label: "Not tested (run did not execute)", short: "Not run", definition: "Never tested: the run halted, failed technically or ran out of time or compute, or the hypothesis was proposed but never run." }
  ];
  OC.EVALUATED_KEYS = ["supported", "partial", "not_supported", "inconclusive", "not_testable"];
  var byKey = {};
  OC.OUTCOMES.forEach(function (o) { byKey[o.key] = o; });
  OC.outcome = function (key) { return byKey[key]; };

  OC.badge = function (key, opt) {
    opt = opt || {};
    var o = byKey[key];
    if (!o) throw new Error("unknown outcome " + key);
    var count = opt.count != null ? ' <span class="badge__count">' + OC.esc(opt.count) + "</span>" : "";
    var title = opt.short ? ' title="' + OC.esc(o.label) + '"' : "";
    return '<span class="badge badge--' + key + '"' + title + ">" + OC.esc(opt.short ? o.short : o.label) + count + "</span>";
  };

  OC.stackedBar = function (counts, opt) {
    opt = opt || {};
    var keys = opt.keys || OC.OUTCOMES.map(function (o) { return o.key; });
    var total = 0, desc = [], segs = "";
    keys.forEach(function (k) { total += counts[k] || 0; });
    keys.forEach(function (k) {
      var n = counts[k] || 0;
      desc.push(byKey[k].label + " " + n);
      if (!n) return;
      var w = 100 * n / total;
      var val = opt.showValues && w >= 4 ? '<span class="stackbar__val">' + n + "</span>" : "";
      segs += '<span class="stackbar__seg seg--' + k + '" style="--w:' + w.toFixed(3) + '%" title="' +
        OC.esc(byKey[k].label) + ": " + n + '">' + val + "</span>";
    });
    var aria = (opt.label ? opt.label + ": " : "") + desc.join("; ") + " (total " + total + ")";
    var cls = "stackbar" + (opt.size ? " stackbar--" + opt.size : "") + (total ? "" : " stackbar--empty");
    return '<div class="' + cls + '" role="img" aria-label="' + OC.esc(aria) + '">' + segs + "</div>";
  };

  OC.hash = {
    get: function () { return new URLSearchParams(location.hash.replace(/^#/, "")); },
    set: function (obj) {
      var p = new URLSearchParams();
      Object.keys(obj).forEach(function (k) {
        var v = obj[k];
        if (v == null || v === "" || (Array.isArray(v) && !v.length)) return;
        p.set(k, Array.isArray(v) ? v.join(",") : v);
      });
      var s = p.toString();
      var url = location.pathname + location.search + (s ? "#" + s : "");
      try { history.replaceState(null, "", url); } catch (e) { location.hash = s; }
    }
  };

  /* Theme toggle ---------------------------------------------------------- */
  function currentTheme() {
    var t = doc.getAttribute("data-theme");
    if (t === "dark" || t === "light") return t;
    return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }
  function labelToggles() {
    var next = currentTheme() === "dark" ? "light" : "dark";
    OC.qsa("[data-oc-theme-toggle]").forEach(function (b) {
      b.setAttribute("aria-label", "Switch to " + next + " theme");
      b.setAttribute("title", "Switch to " + next + " theme");
    });
  }
  OC.setTheme = function (t, persist) {
    doc.setAttribute("data-theme", t);
    if (persist !== false) { try { localStorage.setItem("oc-theme", t); } catch (e) { /* storage blocked */ } }
    labelToggles();
  };

  OC.ready(function () {
    labelToggles();
    OC.qsa("[data-oc-theme-toggle]").forEach(function (b) {
      b.addEventListener("click", function () { OC.setTheme(currentTheme() === "dark" ? "light" : "dark"); });
    });
    if (window.matchMedia) {
      var mq = window.matchMedia("(prefers-color-scheme: dark)");
      if (mq.addEventListener) mq.addEventListener("change", labelToggles);
    }

    /* Mobile nav ---------------------------------------------------------- */
    OC.qsa("[data-oc-nav-toggle]").forEach(function (btn) {
      var nav = document.getElementById(btn.getAttribute("aria-controls"));
      if (!nav) return;
      function close() { nav.classList.remove("is-open"); btn.setAttribute("aria-expanded", "false"); }
      btn.addEventListener("click", function () {
        var open = !nav.classList.contains("is-open");
        nav.classList.toggle("is-open", open);
        btn.setAttribute("aria-expanded", open ? "true" : "false");
        if (open) { var a = nav.querySelector("a"); if (a) a.focus(); }
      });
      document.addEventListener("keydown", function (e) {
        if (e.key === "Escape" && nav.classList.contains("is-open")) { close(); btn.focus(); }
      });
      document.addEventListener("click", function (e) {
        if (nav.classList.contains("is-open") && !nav.contains(e.target) && !btn.contains(e.target)) close();
      });
    });

    /* Row / panel toggles ------------------------------------------------- */
    document.addEventListener("click", function (e) {
      var b = e.target.closest && e.target.closest("[data-oc-row-toggle]");
      if (!b) return;
      var el = document.getElementById(b.getAttribute("aria-controls"));
      if (!el) return;
      var open = b.getAttribute("aria-expanded") !== "true";
      b.setAttribute("aria-expanded", open ? "true" : "false");
      el.hidden = !open;
    });

    /* Copy buttons -------------------------------------------------------- */
    OC.qsa("[data-oc-copy]").forEach(function (b) {
      b.addEventListener("click", function () {
        var src = OC.qs(b.getAttribute("data-oc-copy"));
        if (!src) return;
        var text = src.innerText;
        var done = function () { var t = b.textContent; b.textContent = "Copied"; setTimeout(function () { b.textContent = t; }, 1500); };
        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(text).then(done, function () {});
        } else {
          var r = document.createRange(); r.selectNodeContents(src);
          var s = window.getSelection(); s.removeAllRanges(); s.addRange(r);
          try { document.execCommand("copy"); done(); } catch (err) { /* ignore */ }
        }
      });
    });
  });
})();
