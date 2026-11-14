/* /platform/ page: screenshot lightbox and in-view autoplay for clips.
 * Without JS, every screenshot links to its full-size file and clips have plain controls.
 * Lightbox: Esc closes, Left/Right arrows navigate, Tab is trapped inside, focus returns
 * to the thumbnail that opened it. Clips autoplay (muted) only while visible and only if
 * the user has not asked for reduced motion. */
(function () {
  "use strict";
  var doc = document;

  function ready(fn) {
    if (doc.readyState !== "loading") fn(); else doc.addEventListener("DOMContentLoaded", fn);
  }

  function captionFor(link) {
    var fig = link.closest("figure");
    var title = link.getAttribute("data-pf-title") || "";
    var text = "";
    if (fig) {
      var t = fig.querySelector(".shot__title");
      var x = fig.querySelector(".shot__text");
      if (t && !title) title = t.childNodes[0] ? t.childNodes[0].textContent : t.textContent;
      if (x) text = x.textContent;
    }
    if (link.hasAttribute("data-pf-caption")) text = link.getAttribute("data-pf-caption");
    var img = link.querySelector("img");
    return { title: (title || "").trim(), text: (text || "").trim(), alt: img ? img.getAttribute("alt") || "" : "" };
  }

  function el(tag, cls, attrs) {
    var e = doc.createElement(tag);
    if (cls) e.className = cls;
    if (attrs) Object.keys(attrs).forEach(function (k) { e.setAttribute(k, attrs[k]); });
    return e;
  }

  function setupLightbox() {
    var links = Array.prototype.slice.call(doc.querySelectorAll("a[data-pf-lightbox]"));
    if (!links.length) return;

    var box = el("div", "pf-lb", { role: "dialog", "aria-modal": "true", "aria-labelledby": "pf-lb-title", hidden: "" });
    var top = el("div", "pf-lb__top");
    var label = el("span", "pf-lb__label");
    // The visible label lives in the page HTML (data-pf-lightbox-label on the first link's
    // gallery), so shared assets do not carry product names.
    var holder = doc.querySelector("[data-pf-lightbox-label]");
    label.textContent = holder ? holder.getAttribute("data-pf-lightbox-label") : "First version of OmiCairn";
    var count = el("span", "pf-lb__count", { "aria-live": "polite" });
    var close = el("button", "pf-lb__btn pf-lb__close", { type: "button", "aria-label": "Close (Esc)" });
    close.innerHTML = "&times;";
    top.appendChild(label); top.appendChild(count); top.appendChild(close);

    var stage = el("div", "pf-lb__stage");
    var img = el("img", "pf-lb__img", { alt: "" });
    var prev = el("button", "pf-lb__btn pf-lb__nav pf-lb__nav--prev", { type: "button", "aria-label": "Previous screenshot" });
    prev.innerHTML = "&#8249;";
    var next = el("button", "pf-lb__btn pf-lb__nav pf-lb__nav--next", { type: "button", "aria-label": "Next screenshot" });
    next.innerHTML = "&#8250;";
    stage.appendChild(img); stage.appendChild(prev); stage.appendChild(next);

    var cap = el("div", "pf-lb__cap");
    var capTitle = el("strong", "", { id: "pf-lb-title" });
    var capText = el("span", "");
    cap.appendChild(capTitle); cap.appendChild(capText);

    box.appendChild(top); box.appendChild(stage); box.appendChild(cap);
    doc.body.appendChild(box);

    var index = 0, opener = null, touchX = null;

    function show(i) {
      index = (i + links.length) % links.length;
      var link = links[index];
      var c = captionFor(link);
      img.src = link.href;
      img.alt = c.alt;
      capTitle.textContent = c.title;
      capText.textContent = c.text;
      count.textContent = (index + 1) + " / " + links.length;
      // Preload neighbours for snappy navigation.
      [index - 1, index + 1].forEach(function (j) {
        var l = links[(j + links.length) % links.length];
        var p = new Image(); p.src = l.href;
      });
    }

    function open(i, from) {
      opener = from || doc.activeElement;
      show(i);
      box.hidden = false;
      doc.documentElement.classList.add("pf-lb-open");
      close.focus();
    }

    function shut() {
      box.hidden = true;
      doc.documentElement.classList.remove("pf-lb-open");
      img.removeAttribute("src");
      if (opener && opener.focus) opener.focus();
    }

    links.forEach(function (link, i) {
      link.addEventListener("click", function (ev) {
        if (ev.metaKey || ev.ctrlKey || ev.shiftKey || ev.altKey || ev.button !== 0) return;
        ev.preventDefault();
        open(i, link);
      });
    });

    close.addEventListener("click", shut);
    prev.addEventListener("click", function () { show(index - 1); });
    next.addEventListener("click", function () { show(index + 1); });
    stage.addEventListener("click", function (ev) { if (ev.target === stage) shut(); });

    box.addEventListener("keydown", function (ev) {
      if (ev.key === "Escape") { ev.preventDefault(); shut(); }
      else if (ev.key === "ArrowLeft") { ev.preventDefault(); show(index - 1); }
      else if (ev.key === "ArrowRight") { ev.preventDefault(); show(index + 1); }
      else if (ev.key === "Tab") {
        var f = [close, prev, next];
        var k = f.indexOf(doc.activeElement);
        ev.preventDefault();
        var n = ev.shiftKey ? (k <= 0 ? f.length - 1 : k - 1) : (k === -1 || k === f.length - 1 ? 0 : k + 1);
        f[n].focus();
      }
    });

    stage.addEventListener("touchstart", function (ev) { touchX = ev.touches[0].clientX; }, { passive: true });
    stage.addEventListener("touchend", function (ev) {
      if (touchX === null) return;
      var dx = ev.changedTouches[0].clientX - touchX;
      touchX = null;
      if (Math.abs(dx) > 50) show(index + (dx < 0 ? 1 : -1));
    });
  }

  function setupClips() {
    var vids = Array.prototype.slice.call(doc.querySelectorAll("video[data-pf-autoplay]"));
    if (!vids.length || !("IntersectionObserver" in window)) return;
    var mq = window.matchMedia ? window.matchMedia("(prefers-reduced-motion: reduce)") : { matches: false };
    var visible = new Map();

    function sync(v) {
      if (mq.matches || !visible.get(v)) {
        if (!v.paused && v.dataset.pfAuto === "1") { v.pause(); }
        return;
      }
      if (v.paused && v.dataset.pfUserPaused !== "1") {
        v.muted = true;
        v.dataset.pfAuto = "1";
        var p = v.play();
        if (p && p.catch) p.catch(function () {});
      }
    }

    vids.forEach(function (v) {
      v.addEventListener("pause", function () {
        // A pause while visible and not caused by us means the user wants it stopped.
        if (visible.get(v) && !mq.matches && !v.ended && v.dataset.pfAuto !== "pausing") v.dataset.pfUserPaused = "1";
      });
      v.addEventListener("play", function () { v.dataset.pfUserPaused = "0"; });
    });

    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        visible.set(e.target, e.isIntersecting && e.intersectionRatio >= 0.5);
        if (!visible.get(e.target) && !e.target.paused) {
          e.target.dataset.pfAuto = "pausing";
          e.target.pause();
          e.target.dataset.pfAuto = "1";
        } else {
          sync(e.target);
        }
      });
    }, { threshold: [0, 0.5] });
    vids.forEach(function (v) { io.observe(v); });

    var onChange = function () { vids.forEach(function (v) { if (mq.matches && !v.paused) v.pause(); else sync(v); }); };
    if (mq.addEventListener) mq.addEventListener("change", onChange); else if (mq.addListener) mq.addListener(onChange);
  }

  ready(function () {
    setupLightbox();
    setupClips();
  });
})();
