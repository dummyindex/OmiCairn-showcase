/* Campaign overview: filter and sort the statically rendered run cards.
 * Without JS every card is visible in the default order and the filter bar is hidden.
 * Hash state (shareable): #disease=PD,AD&stage=pipeline&report=1&q=text&sort=supported
 * Plain anchors (#runs, #funnel) are left alone. */
(function () {
  "use strict";
  var OC = window.OC;
  OC.ready(function () {
    var form = OC.qs("[data-cmp-filter]");
    var grid = OC.qs("[data-cmp-grid]");
    if (!form || !grid) return;
    var cards = OC.qsa(".cmp-card", grid);
    var defaultOrder = cards.slice();
    var chips = OC.qsa("button.chip[data-filter]", form);
    var q = OC.qs("[data-cmp-q]", form);
    var sort = OC.qs("[data-cmp-sort]", form);
    var count = OC.qs("[data-cmp-count]", form);
    var empty = OC.qs("[data-cmp-empty]");
    var SORTS = ["report", "depth", "supported", "evaluated", "run"];

    function num(el, k) { return Number(el.getAttribute("data-" + k)) || 0; }
    function byRun(a, b) { var x = a.getAttribute("data-run"), y = b.getAttribute("data-run"); return x < y ? -1 : x > y ? 1 : 0; }
    var comparators = {
      report: null,
      depth: function (a, b) { return num(b, "depth") - num(a, "depth") || num(b, "report") - num(a, "report") || byRun(a, b); },
      supported: function (a, b) { return num(b, "supported") - num(a, "supported") || num(b, "evaluated") - num(a, "evaluated") || byRun(a, b); },
      evaluated: function (a, b) { return num(b, "evaluated") - num(a, "evaluated") || num(b, "supported") - num(a, "supported") || byRun(a, b); },
      run: byRun
    };

    function pressed(filter) {
      return chips.filter(function (c) { return c.getAttribute("data-filter") === filter && c.getAttribute("aria-pressed") === "true"; })
        .map(function (c) { return c.getAttribute("data-value"); });
    }

    function apply(writeHash) {
      var dis = pressed("disease"), st = pressed("stage"), rep = pressed("report").length > 0;
      var text = (q.value || "").trim().toLowerCase();
      var terms = text ? text.split(/\s+/) : [];
      var shown = 0;
      var order = comparators[sort.value] ? defaultOrder.slice().sort(comparators[sort.value]) : defaultOrder;
      order.forEach(function (c) { grid.appendChild(c); });
      cards.forEach(function (c) {
        var hay = c.getAttribute("data-text") || "";
        var ok = (!dis.length || dis.indexOf(c.getAttribute("data-disease")) >= 0) &&
          (!st.length || st.indexOf(c.getAttribute("data-stage")) >= 0) &&
          (!rep || c.getAttribute("data-report") === "1") &&
          terms.every(function (t) { return hay.indexOf(t) >= 0; });
        c.hidden = !ok;
        if (ok) shown++;
      });
      count.innerHTML = "Showing <strong>" + shown + "</strong> of " + cards.length + " runs";
      if (empty) empty.hidden = shown > 0;
      if (writeHash) {
        var active = dis.length || st.length || rep || text || sort.value !== "report";
        if (active) {
          OC.hash.set({ disease: dis, stage: st, report: rep ? "1" : null, q: text || null,
                        sort: sort.value !== "report" ? sort.value : null });
        } else if (location.hash.indexOf("=") >= 0) {
          OC.hash.set({});
        }
      }
    }

    function readHash() {
      if (location.hash.indexOf("=") < 0) return;
      var h = OC.hash.get();
      var sets = {
        disease: (h.get("disease") || "").split(",").filter(Boolean),
        stage: (h.get("stage") || "").split(",").filter(Boolean),
        report: h.get("report") === "1" ? ["1"] : []
      };
      chips.forEach(function (c) {
        var on = (sets[c.getAttribute("data-filter")] || []).indexOf(c.getAttribute("data-value")) >= 0;
        c.setAttribute("aria-pressed", on ? "true" : "false");
      });
      q.value = h.get("q") || "";
      var s = h.get("sort");
      sort.value = SORTS.indexOf(s) >= 0 ? s : "report";
    }

    function reset() {
      chips.forEach(function (c) { c.setAttribute("aria-pressed", "false"); });
      q.value = "";
      sort.value = "report";
      apply(true);
    }

    chips.forEach(function (c) {
      c.addEventListener("click", function () {
        c.setAttribute("aria-pressed", c.getAttribute("aria-pressed") === "true" ? "false" : "true");
        apply(true);
      });
    });
    var t;
    q.addEventListener("input", function () { clearTimeout(t); t = setTimeout(function () { apply(true); }, 120); });
    sort.addEventListener("change", function () { apply(true); });
    form.addEventListener("submit", function (ev) { ev.preventDefault(); apply(true); });
    OC.qsa("[data-cmp-reset]").forEach(function (b) { b.addEventListener("click", reset); });
    window.addEventListener("hashchange", function () { readHash(); apply(false); });

    readHash();
    apply(false);
  });
})();
