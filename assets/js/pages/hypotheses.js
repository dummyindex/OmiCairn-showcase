/* Hypothesis explorer (/campaign/hypotheses/).
 *
 * Progressive enhancement: the page ships a static list of all 179 hypotheses
 * grouped by run. This script adds filters, free-text search, faceted counts,
 * a live outcome summary, CSV export and shareable hash state:
 *   #run=<run>&disease=PD,AD&outcome=supported,partial&origin=plan&q=text&all=1&h=<run>/<H1>
 * `all=1` includes the hypotheses whose test never ran (outcome not_run);
 * it is implied when the hash names a run, a hypothesis (h) or outcome=not_run.
 */
(function () {
  "use strict";
  var OC = window.OC;
  if (!OC) return;

  OC.ready(function () {
    var form = OC.qs("[data-hx-form]");
    if (!form) return;
    var root = OC.qs(".hx");
    root.classList.add("hx--js");

    var KEYS = OC.OUTCOMES.map(function (o) { return o.key; });
    var EVAL = OC.EVALUATED_KEYS;
    var FACETS = ["disease", "outcome", "origin"];

    /* Index the static rows ------------------------------------------------ */
    var items = OC.qsa(".hx-item").map(function (el) {
      return {
        el: el,
        id: el.getAttribute("data-id"),
        run: el.getAttribute("data-run"),
        disease: el.getAttribute("data-disease"),
        outcome: el.getAttribute("data-outcome"),
        origin: el.getAttribute("data-origin"),
        text: norm(el.getAttribute("data-run") + " " + el.textContent),
        details: el.querySelector("details")
      };
    });
    var byId = {};
    items.forEach(function (it) { byId[it.id] = it; });
    var groups = OC.qsa(".hx-run").map(function (el) {
      return { el: el, run: el.getAttribute("data-run"), count: el.querySelector(".hx-run__count"),
               items: items.filter(function (it) { return it.run === el.getAttribute("data-run"); }) };
    });

    // Sanity check against the data file (the list is generated from it at build time).
    var DATA = null;
    try { DATA = OC.data("hypotheses"); } catch (e) { /* CSV export falls back to the DOM */ }
    if (DATA && DATA.length !== items.length && window.console) {
      console.warn("hypothesis explorer: page lists " + items.length + " rows, data file has " + DATA.length);
    }

    var qInput = OC.qs("[data-hx-q]", form);
    var runSel = OC.qs("[data-hx-run]", form);
    var evalBox = OC.qs("[data-hx-evaluated]", form);
    var chips = OC.qsa(".chip[data-filter]", form);
    var countEl = OC.qs("[data-hx-count]");
    var rateEl = OC.qs("[data-hx-rate]");
    var barEl = OC.qs("[data-hx-bar]");
    var tallyEl = OC.qs("[data-hx-tally]");
    var emptyEl = OC.qs("[data-hx-empty]");

    var state = defaults();

    function defaults() { return { q: "", run: "", disease: [], outcome: [], origin: [], all: false, h: "" }; }
    function norm(s) { return String(s || "").toLowerCase().replace(/\s+/g, " "); }
    function list(v) { return v ? v.split(",").filter(Boolean) : []; }
    function impliedAll(s) { return !!(s.run || s.h || s.outcome.indexOf("not_run") >= 0); }

    /* Hash <-> state ------------------------------------------------------- */
    function readHash() {
      var p = OC.hash.get(), s = defaults();
      s.q = p.get("q") || "";
      s.run = p.get("run") || "";
      s.disease = list(p.get("disease"));
      s.outcome = list(p.get("outcome")).filter(function (k) { return KEYS.indexOf(k) >= 0; });
      s.origin = list(p.get("origin"));
      s.h = p.get("h") || "";
      // Drop an unknown run or hypothesis (stale link) BEFORE deciding whether not-run rows are
      // implied, so a bad link falls back to the default 136-row view.
      s.missing = "";
      if (s.run && !groups.some(function (g) { return g.run === s.run; })) { s.missing = "run " + s.run; s.run = ""; }
      if (s.h && !byId[s.h]) { s.missing = s.missing || "hypothesis " + s.h; s.h = ""; }
      var a = p.get("all");
      s.all = a === "1" ? true : a === "0" ? false : impliedAll(s);
      return s;
    }
    function writeHash() {
      var all = state.all === impliedAll(state) ? null : (state.all ? "1" : "0");
      OC.hash.set({ run: state.run || null, disease: state.disease, outcome: state.outcome,
                    origin: state.origin, q: state.q.trim() || null, all: all, h: state.h || null });
    }

    /* Filtering ------------------------------------------------------------ */
    function tokens() { return norm(state.q).trim().split(" ").filter(Boolean); }
    function matches(it, skip, toks) {
      if (!state.all && it.outcome === "not_run" && skip !== "outcome") return false;
      if (state.run && it.run !== state.run) return false;
      for (var i = 0; i < FACETS.length; i++) {
        var f = FACETS[i];
        if (f !== skip && state[f].length && state[f].indexOf(it[f]) < 0) return false;
      }
      for (var j = 0; j < toks.length; j++) if (it.text.indexOf(toks[j]) < 0) return false;
      return true;
    }

    function render() {
      var toks = tokens();
      var shown = 0, runsShown = 0, counts = {};
      KEYS.forEach(function (k) { counts[k] = 0; });

      items.forEach(function (it) {
        var ok = matches(it, null, toks);
        it.el.hidden = !ok;
        if (ok) { shown++; counts[it.outcome]++; }
      });
      groups.forEach(function (g) {
        var n = 0;
        g.items.forEach(function (it) { if (!it.el.hidden) n++; });
        g.el.hidden = n === 0;
        if (n) runsShown++;
        var total = g.items.length;
        g.count.textContent = n === total ? g.count.getAttribute("data-base") : n + " of " + total + " hypotheses shown";
      });

      // Facet counts: each chip shows how many rows it would give with the other filters as they are.
      chips.forEach(function (c) {
        var f = c.getAttribute("data-filter"), v = c.getAttribute("data-value"), n = 0;
        items.forEach(function (it) {
          if (it[f] !== v) return;
          if (matches(it, f, toks)) n++;
        });
        c.querySelector(".chip__count").textContent = n;
        var on = state[f].indexOf(v) >= 0;
        c.setAttribute("aria-pressed", on ? "true" : "false");
        c.classList.toggle("is-empty", n === 0 && !on);
        c.classList.toggle("is-excluded", f === "outcome" && v === "not_run" && !state.all);
      });
      runSel.value = state.run;
      evalBox.checked = !state.all;
      if (qInput.value !== state.q && document.activeElement !== qInput) qInput.value = state.q;

      // Summary
      var ev = 0;
      EVAL.forEach(function (k) { ev += counts[k]; });
      countEl.innerHTML = "<strong>" + OC.fmt(shown) + "</strong> " + (shown === 1 ? "hypothesis" : "hypotheses") +
        " from <strong>" + runsShown + "</strong> " + (runsShown === 1 ? "run" : "runs") +
        (isDefault() ? "" : ' <span class="muted">(filtered)</span>');
      if (ev && state.outcome.length) {
        rateEl.textContent = "Verdict filter: " + KEYS.filter(function (k) { return state.outcome.indexOf(k) >= 0; })
          .map(function (k) { return OC.outcome(k).short; }).join(", ") + ".";
      } else if (ev) {
        rateEl.textContent = counts.supported + " of " + ev + " evaluated " + (ev === 1 ? "was" : "were") +
          " supported (" + Math.round(100 * counts.supported / ev) + "%)" +
          (counts.not_run ? "; " + counts.not_run + " never ran." : ".");
      } else {
        rateEl.textContent = shown ? "None of these hypotheses was evaluated; their tests never ran." : "";
      }
      barEl.innerHTML = shown ? OC.stackedBar(counts, { size: "lg", showValues: true, label: "Hypotheses in this view" }) : "";
      OC.qsa(".hx-tally__item", tallyEl).forEach(function (li) {
        var k = li.getAttribute("data-key"), n = counts[k];
        var pct = k !== "not_run" && ev ? Math.round(100 * n / ev) + "%" : "";
        li.querySelector(".hx-tally__n").innerHTML = n + (pct ? '<span class="hx-tally__pct">' + pct + "</span>" : "");
        li.classList.toggle("is-zero", n === 0);
      });
      emptyEl.hidden = shown !== 0;
    }

    function isDefault() {
      return !state.q.trim() && !state.run && !state.disease.length && !state.outcome.length &&
        !state.origin.length && !state.all;
    }

    function update(opts) {
      render();
      if (!opts || opts.hash !== false) writeHash();
    }

    function focusHypothesis(scroll) {
      OC.qsa(".hx-item.is-target").forEach(function (el) { el.classList.remove("is-target"); });
      var it = byId[state.h];
      if (!it) return;
      if (it.el.hidden) { // make sure a deep-linked hypothesis is visible
        state.q = ""; state.disease = []; state.origin = []; state.outcome = [];
        if (state.run && state.run !== it.run) state.run = "";
        if (it.outcome === "not_run") state.all = true;
        render();
        writeHash();
      }
      it.details.open = true;
      it.el.classList.add("is-target");
      if (scroll) {
        var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
        it.el.scrollIntoView({ block: "start", behavior: reduce ? "auto" : "smooth" });
        var s = it.details.querySelector("summary");
        if (s) s.focus({ preventScroll: true });
      }
    }

    /* Events --------------------------------------------------------------- */
    groups.forEach(function (g) { g.count.setAttribute("data-base", g.count.textContent); });

    chips.forEach(function (c) {
      c.addEventListener("click", function () {
        var f = c.getAttribute("data-filter"), v = c.getAttribute("data-value");
        var arr = state[f], i = arr.indexOf(v);
        if (i >= 0) arr.splice(i, 1); else arr.push(v);
        if (f === "outcome" && v === "not_run" && i < 0) state.all = true;
        update();
      });
    });
    var t = null;
    qInput.addEventListener("input", function () {
      clearTimeout(t);
      t = setTimeout(function () { state.q = qInput.value; update(); }, 120);
    });
    qInput.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && qInput.value) { qInput.value = ""; state.q = ""; update(); }
    });
    runSel.addEventListener("change", function () {
      var had = !!state.run;
      state.run = runSel.value;
      if (state.run && !had) state.all = true;  // a run's full list, including tests that never ran
      update();
    });
    evalBox.addEventListener("change", function () {
      state.all = !evalBox.checked;
      if (!state.all) state.outcome = state.outcome.filter(function (k) { return k !== "not_run"; });
      update();
    });
    form.addEventListener("submit", function (e) { e.preventDefault(); });
    form.addEventListener("reset", function (e) { e.preventDefault(); resetAll(); });
    OC.qsa("[data-hx-reset]").forEach(function (b) {
      if (b.type !== "reset") b.addEventListener("click", resetAll);
    });
    function resetAll() {
      state = defaults();
      qInput.value = "";
      update();
      qInput.focus();
    }

    // Permalinks: keep the current filters, add h=, copy the full URL.
    root.addEventListener("click", function (e) {
      var a = e.target.closest && e.target.closest(".hx-permalink");
      if (!a) return;
      e.preventDefault();
      state.h = a.getAttribute("data-h");
      writeHash();
      focusHypothesis(false);
      var url = location.href;
      var done = function () {
        var old = a.textContent;
        a.textContent = "Link copied";
        setTimeout(function () { a.textContent = old; }, 1600);
      };
      if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(url).then(done, function () {});
    });

    window.addEventListener("hashchange", function () {
      state = readHash();
      qInput.value = state.q;
      render();
      if (state.h) focusHypothesis(true);
    });

    /* CSV export ----------------------------------------------------------- */
    var COLS = ["id", "run", "disease", "hypothesis_id", "origin", "hypothesis", "verdict", "outcome",
                "outcome_class", "evidence_quote", "adjudication_note", "report_url"];
    function csvCell(v) {
      v = v == null ? "" : String(v);
      return /[",\n\r]/.test(v) ? '"' + v.replace(/"/g, '""') + '"' : v;
    }
    OC.qsa("[data-hx-csv]").forEach(function (b) {
      b.addEventListener("click", function () {
        var view = b.getAttribute("data-hx-csv") === "view";
        var keep = {};
        items.forEach(function (it) { if (!view || !it.el.hidden) keep[it.id] = true; });
        var rows = (DATA || []).filter(function (r) { return keep[r.id]; });
        var lines = [COLS.join(",")].concat(rows.map(function (r) {
          return COLS.map(function (c) { return csvCell(r[c]); }).join(",");
        }));
        var blob = new Blob(["﻿" + lines.join("\r\n") + "\r\n"], { type: "text/csv;charset=utf-8" });
        var a = document.createElement("a");
        a.href = URL.createObjectURL(blob);
        a.download = view ? "omicairn-hypotheses-view.csv" : "omicairn-hypotheses.csv";
        document.body.appendChild(a);
        a.click();
        setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 0);
      });
      if (!DATA) b.disabled = true;
    });

    /* Start ---------------------------------------------------------------- */
    state = readHash();
    qInput.value = state.q;
    render();
    if (state.h) focusHypothesis(true);
  });
})();
