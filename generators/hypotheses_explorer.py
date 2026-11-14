"""Render /campaign/hypotheses/ (the hypothesis explorer) from assets/data/*.json.

The explorer is a static list of all 179 hypotheses (works without JS) that
assets/js/pages/hypotheses.js enhances with filters, search, live counts and
hash state. It is rebuilt on every build, so it never goes stale.
"""
from collections import Counter, OrderedDict


def generate(ctx):
    C = ctx.components
    O = ctx.outcomes
    esc = C.esc
    H = ctx.load_json("hypotheses")
    RUNS = {r["run"]: r for r in ctx.load_json("runs")}
    CAMP = ctx.load_json("campaign")
    body, title, description = _page(C, O, esc, H, RUNS, CAMP)
    ctx.render_page("/campaign/hypotheses/", title, body, description=description,
                    section="hypotheses", layout="wide",
                    breadcrumb=[("Campaign", "/campaign/"), ("Hypotheses", None)],
                    source="generators/hypotheses_explorer.py")


def _page(C, O, esc, H, RUNS, CAMP):
    V = CAMP["verified"]
    KEYS = O.OUTCOME_KEYS
    EVAL = O.EVALUATED_KEYS

    # ---- consistency checks against the verified numbers (fail loudly) ----------
    cnt = Counter(h["outcome"] for h in H)
    assert len(H) == V["hypotheses_nominated"] == 179, len(H)
    assert sum(cnt[k] for k in EVAL) == V["hypotheses_evaluated"] == 136
    assert cnt["not_run"] == V["hypotheses_not_run"] == 43
    assert dict(cnt) == {k: v for k, v in CAMP["outcomes"].items() if v}, (cnt, CAMP["outcomes"])
    assert len({h["id"] for h in H}) == len(H)

    by_run = OrderedDict()
    for h in sorted(H, key=lambda h: h["run"]):   # stable: keeps hypothesis order within a run
        by_run.setdefault(h["run"], []).append(h)
    eval_runs = [r for r, hs in by_run.items() if any(h["outcome"] in EVAL for h in hs)]
    assert len(eval_runs) == V["completed_a_test"] == 27
    never = [r for r, hs in by_run.items() if all(h["outcome"] == "not_run" for h in hs)]
    never_h = sum(len(by_run[r]) for r in never)
    # README: "30 of them come from 6 planned runs that never completed a test, and 13 from runs that tested other hypotheses"
    assert (len(never), never_h, cnt["not_run"] - never_h) == (6, 30, 13), (len(never), never_h)
    assert len(by_run) == V["reached_planning"] == 33

    n_ns_nt = cnt["not_supported"] + cnt["not_testable"]          # 83 (README)
    n_upper = cnt["supported"] + cnt["partial"] + cnt["inconclusive"]  # 53 (README)
    assert (n_ns_nt, n_upper) == (83, 53)

    ORIGIN_SHORT = {"plan": "Pre-registered", "on_the_fly": "On the fly"}
    DISEASE_ORDER = ["PD", "AD", "CROSS"]

    # Fuller definitions, from HYPOTHESES.md "Outcome classes" table of the campaign release.
    DEFS = {
        "supported": "Tested. The pre-registered decision rule was met.",
        "partial": "Tested. Some components of the decision rule were met, but not all (for example, the direction was right but a replication arm failed).",
        "not_supported": "Tested. The decision rule was not met: a null result, a refutation or an opposite effect. Includes powered negatives.",
        "inconclusive": "Tested, but underpowered, ambiguous or confounded, so the data cannot settle it.",
        "not_testable": "Not tested, or tested only through a proxy, because a suitable dataset, modality, sample size or metadata was unavailable, access-restricted or unsuitable.",
        "not_run": "Not tested for a reason unrelated to data: the run halted before execution, a technical failure, a time or compute limit, or a follow-up that was proposed but never run. Excluded from evaluated totals.",
    }


    def dom_id(h):
        return "hx-" + h["run"] + "--" + h["hypothesis_id"]


    def fmt_kb(b):
        return f"{round(b / 1024):,} KB" if b < 1024 * 1024 else f"{b / 1024 / 1024:.1f} MB"


    def report_link(run, cls=""):
        rep = RUNS[run]["report"]
        if not rep:
            return '<span class="hx-noreport">No final report</span>'
        c = f' class="{cls}"' if cls else ""
        if rep["kind"] == "pdf":
            return (f'<a{c} href="{esc(rep["url"])}">Final report <span class="hx-filemeta">'
                    f'PDF, {fmt_kb(rep["bytes"])}</span></a>')
        return f'<a{c} href="{esc(rep["url"])}">Final report</a>'


    def item(h):
        hid = esc(h["hypothesis_id"])
        otf = ('<span class="tag hx-otf" title="Proposed on the fly during execution">on the fly</span>'
               if h["origin"] == "on_the_fly" else "")
        q = h["evidence_quote"]
        n = h["adjudication_note"]
        quote = (f'<blockquote class="hx-quote"><p>{esc(q)}</p></blockquote>' if q
                 else '<p class="muted">No verbatim quote was recorded for this verdict.</p>')
        note = f'<p>{esc(n)}</p>' if n else '<p class="muted">No adjudication note was recorded.</p>'
        rep = (f'<a href="{esc(h["report_url"])}">Final report{" (PDF)" if h["report_kind"] == "pdf" else ""}</a>'
               if h["report_url"] else '<span class="muted">No final report for this run</span>')
        return f"""<li class="hx-item" id="{esc(dom_id(h))}" data-id="{esc(h['id'])}" data-run="{esc(h['run'])}" data-disease="{esc(h['disease'])}" data-outcome="{esc(h['outcome'])}" data-origin="{esc(h['origin'])}">
    <div class="hx-item__id"><span class="hx-hid">{hid}</span>{otf}</div>
    <div class="hx-item__verdict">{C.outcome_badge(h['outcome'], short=True)}</div>
    <div class="hx-item__main">
    <p class="hx-item__text">{esc(h['hypothesis'])}</p>
    <details class="hx-more">
    <summary><span class="hx-more__label">Evidence and adjudication</span><span class="visually-hidden"> for {esc(h['run'])} {hid}</span></summary>
    <div class="hx-more__body">
    <div class="hx-more__grid">
    <div><h4 class="hx-more__h">Evidence quoted from the run</h4>{quote}</div>
    <div><h4 class="hx-more__h">Adjudication note</h4>{note}</div>
    </div>
    <p class="hx-more__links"><span>Verdict: <strong>{esc(h['verdict'])}</strong></span><span>Origin: {esc(O.ORIGIN_LABEL[h['origin']])}</span>{rep}<a href="/campaign/runs/{esc(h['run'])}/">Run page</a><a class="hx-permalink" href="#{esc(dom_id(h))}" data-h="{esc(h['id'])}">Link to this hypothesis</a></p>
    </div>
    </details>
    </div>
    </li>"""


    def group(run, hs):
        r = RUNS[run]
        c = Counter(h["outcome"] for h in hs)
        counts = {k: c.get(k, 0) for k in KEYS}
        ev = sum(counts[k] for k in EVAL)
        assert r["counts"] == counts, run  # runs.json and hypotheses.json agree
        meta = f'{len(hs)} hypotheses, {ev} evaluated' if ev else f'{len(hs)} hypotheses, none evaluated'
        never_note = ('<p class="hx-run__note">This run reached planning but never completed a test.</p>'
                      if run in never else "")
        bar = C.stacked_bar(counts, size="sm", label=f"Verdicts of {run}")
        items = "\n".join(item(h) for h in hs)
        return f"""<section class="hx-run" data-run="{esc(run)}" data-disease="{esc(r['disease'])}" aria-labelledby="hxr-{esc(run)}">
    <header class="hx-run__head">
    <h3 class="hx-run__title" id="hxr-{esc(run)}"><a href="/campaign/runs/{esc(run)}/">{esc(run)}</a></h3>
    <div class="hx-run__meta">{C.disease_tag(r['disease'])}<span class="hx-run__count" data-total="{len(hs)}">{meta}</span>{report_link(run)}</div>
    <div class="hx-run__bar">{bar}</div>
    {never_note}
    </header>
    <ol class="hx-list" role="list">
    {items}
    </ol>
    </section>"""


    def chip(group_name, value, label, count, swatch=""):
        return (f'<button type="button" class="chip" data-filter="{group_name}" data-value="{esc(value)}" aria-pressed="false">'
                f'{swatch}{esc(label)} <span class="chip__count">{count}</span></button>')


    all_counts = {k: cnt.get(k, 0) for k in KEYS}
    dcount = Counter(h["disease"] for h in H if h["outcome"] in EVAL)
    ocount = Counter(h["origin"] for h in H if h["outcome"] in EVAL)

    disease_chips = "".join(chip("disease", d, O.DISEASE_LABEL[d], dcount[d]) for d in DISEASE_ORDER)
    origin_chips = "".join(chip("origin", o, O.ORIGIN_LABEL[o], ocount[o]) for o in ("plan", "on_the_fly"))
    outcome_chips = "".join(chip("outcome", k, O.SHORT[k], all_counts[k] if k != "not_run" else all_counts[k],
                                 C.swatch(k)) for k in KEYS)

    opts = []
    for d in DISEASE_ORDER:
        rs = [r for r in by_run if RUNS[r]["disease"] == d]
        o = "".join(f'<option value="{esc(r)}">{esc(r)} ({len(by_run[r])})</option>' for r in rs)
        opts.append(f'<optgroup label="{esc(O.DISEASE_LABEL[d])} ({len(rs)} runs)">{o}</optgroup>')
    run_select = "".join(opts)

    defs = "".join(
        f'<div class="hx-def hx-def--{k}"><dt>{C.outcome_badge(k)}</dt><dd>{esc(DEFS[k])}</dd></div>'
        for k in KEYS)

    static_tally = "".join(
        f'<li class="hx-tally__item" data-key="{k}"><span class="swatch swatch--{k}" aria-hidden="true"></span>'
        f'<span class="hx-tally__label">{esc(O.SHORT[k])}</span>'
        f'<span class="hx-tally__n">{all_counts[k]}</span></li>' for k in KEYS)

    groups = "\n".join(group(r, hs) for r, hs in by_run.items())

    pct_sup = C.pct(cnt["supported"], 136)

    page = f"""<link rel="stylesheet" href="/assets/css/pages/hypotheses.css">
    <div class="container hx">

    <header class="page-head hx-head">
    <p class="kicker">Campaign data</p>
    <h1>Hypothesis explorer</h1>
    <p class="lede">The 33 runs that reached planning nominated {V['hypotheses_nominated']} hypotheses. {V['hypotheses_evaluated']} were evaluated against their pre-registered decision rules, and {cnt['supported']} of those ({pct_sup}) were supported. Every null, negative and untestable result is listed here with its evidence, so that nobody has to run the same analysis twice.</p>
    </header>

    <section class="hx-intro" aria-labelledby="hx-defs-h">
    <div class="hx-intro__head">
    <h2 id="hx-defs-h" class="hx-h2">What the verdicts mean</h2>
    <p class="muted small">Six verdicts, always shown in this order. The first five make up the {V['hypotheses_evaluated']} evaluated hypotheses. {n_ns_nt} of the {V['hypotheses_evaluated']} were not supported or not testable with the available data; even counting every partial and inconclusive verdict as support would give at most {n_upper} of {V['hypotheses_evaluated']}.</p>
    </div>
    <dl class="hx-defs">{defs}</dl>
    <aside class="callout callout--caution hx-caveat">
    <p class="callout__title">Who assigned these verdicts</p>
    <p>AI adjudication agents, not human experts. For each hypothesis an agent read the run's final outputs and applied the run's own pre-registered decision rule. It was deliberately conservative: where the data did not meet the rule, the verdict follows the data, even if the run's own label or its report claimed support, and proxy analyses do not count as tests. In about 15 cases the verdict is stricter than the run's own label; the adjudication note explains each one. Read the note before relying on any verdict.</p>
    </aside>
    </section>

    <section class="hx-explorer" aria-labelledby="hx-results-h">
    <h2 id="hx-results-h" class="visually-hidden">Explore the hypotheses</h2>

    <form class="filter-bar hx-filters" role="search" aria-label="Filter hypotheses" data-hx-form>
    <div class="filter-bar__row hx-filters__top">
    <label class="search hx-search"><span class="visually-hidden">Search hypotheses, evidence and notes</span>
    <svg class="icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><circle cx="11" cy="11" r="6.5"/><path d="M16 16l4.5 4.5"/></svg>
    <input class="input input--search" type="search" name="q" placeholder="Search text, evidence, notes or IDs" autocomplete="off" spellcheck="false" data-hx-q></label>
    <label class="hx-runsel"><span class="visually-hidden">Run</span>
    <select class="select" name="run" data-hx-run><option value="">All {len(by_run)} runs with hypotheses</option>{run_select}</select></label>
    </div>
    <fieldset class="filter-group hx-fg hx-fg--outcome"><legend>Verdict</legend>
    <div class="chips">{outcome_chips}</div>
    </fieldset>
    <fieldset class="filter-group hx-fg"><legend>Disease</legend>
    <div class="chips">{disease_chips}</div>
    </fieldset>
    <fieldset class="filter-group hx-fg"><legend>Origin</legend>
    <div class="chips">{origin_chips}</div>
    </fieldset>
    <div class="filter-bar__row hx-filters__bottom">
    <label class="hx-switch"><input type="checkbox" name="evaluated" checked data-hx-evaluated>
    <span>Evaluated only <span class="muted">(hide the {V['hypotheses_not_run']} hypotheses whose test never ran)</span></span></label>
    <button type="reset" class="button button--small button--ghost hx-reset" data-hx-reset>Reset filters</button>
    </div>
    </form>

    <div class="hx-summary" data-hx-summary>
    <div class="hx-summary__line">
    <p class="hx-summary__count" aria-live="polite" aria-atomic="true" data-hx-count><strong>{len(H)}</strong> hypotheses from <strong>{len(by_run)}</strong> runs</p>
    <p class="hx-summary__rate" data-hx-rate>{cnt['supported']} of {V['hypotheses_evaluated']} evaluated were supported ({pct_sup}).</p>
    </div>
    <div class="hx-summary__bar" data-hx-bar>{C.stacked_bar(all_counts, size="lg", show_values=True, label="All hypotheses")}</div>
    <ul class="hx-tally" data-hx-tally>{static_tally}</ul>
    </div>

    <div class="hx-empty" hidden data-hx-empty>
    <p><strong>No hypotheses match these filters.</strong></p>
    <p><button type="button" class="button button--small" data-hx-reset>Reset filters</button></p>
    </div>

    <div class="hx-results" data-hx-results>
    {groups}
    </div>
    </section>

    <section class="hx-downloads section--tight" aria-labelledby="hx-dl-h">
    <h2 id="hx-dl-h" class="hx-h2">Download the data</h2>
    <p class="muted small">Released under CC BY 4.0. The download is the sanitized copy shown on this site: internal source-file paths were dropped and run-internal file names in the text were replaced by neutral wording.</p>
    <ul class="hx-dl">
    <li class="hx-dl__js"><button type="button" class="button button--small" data-hx-csv="view">CSV of the current view</button></li>
    <li class="hx-dl__js"><button type="button" class="button button--small" data-hx-csv="all">CSV of all {len(H)} hypotheses</button></li>
    <li><a class="button button--small" href="/assets/data/hypotheses.json" download>JSON, all {len(H)} hypotheses</a></li>
    <li><a class="button button--small" href="/assets/data/runs.json" download>JSON, all {V['runs_launched']} runs</a></li>
    <li><a class="button button--small" href="/assets/data/hypotheses.csv" download>Sanitized hypotheses CSV</a></li>
    <li><a class="button button--small" href="/assets/data/runs.csv" download>Runs CSV</a></li>
    <li><a class="link-external" href="https://github.com/dummyindex/OmiCairn-neurodegeneration-campaign">Campaign data repository</a></li>
    </ul>
    </section>

    </div>
    <script src="/assets/data/hypotheses.js"></script>
    <script src="/assets/js/pages/hypotheses.js"></script>
    """

    title = "Hypothesis explorer"
    description = ("All 179 hypotheses of the OmiCairn neurodegeneration campaign with their adjudicated "
                   "verdicts, verbatim evidence and adjudication notes. 136 were evaluated; 15 were supported.")
    return page, title, description
