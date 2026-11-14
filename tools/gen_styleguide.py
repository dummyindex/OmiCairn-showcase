#!/usr/bin/env python3
"""Write content/styleguide/index.html: every component, live, with its copy-paste HTML.

Each demo is defined once below; the snippet shown under it is the same HTML, escaped.
Re-run after changing components:  python3 tools/gen_styleguide.py
"""
from __future__ import annotations

import json
import sys
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import components as C  # noqa: E402
from outcomes import DEFINITION, EVALUATED_KEYS, LABEL, OUTCOME_KEYS, SHORT  # noqa: E402

runs = json.loads((ROOT / "assets/data/runs.json").read_text(encoding="utf-8"))
camp = json.loads((ROOT / "assets/data/campaign.json").read_text(encoding="utf-8"))
V = camp["verified"]
R = {r["run"]: r for r in runs}

sections: list[tuple[str, str, str, list]] = []  # (id, title, intro_html, [(label, demo_html, show_code)])


def sec(id_, title, intro, demos):
    sections.append((id_, title, intro, demos))


# --- Tokens -------------------------------------------------------------------
def swatch_card(var, name, note=""):
    return (f'<div class="sg-swatch"><div class="sg-swatch__chip" style="background:var({var})"></div>'
            f'<div class="sg-swatch__meta"><strong>{name}</strong><br><code>{var}</code>{("<br>" + note) if note else ""}</div></div>')


base_tokens = "".join(swatch_card(v, n) for v, n in [
    ("--bg", "Background"), ("--bg-elev", "Raised surface"), ("--bg-tint", "Tinted band"),
    ("--bg-sunken", "Sunken"), ("--ink", "Ink"), ("--ink-2", "Ink 2 (secondary)"),
    ("--ink-3", "Ink 3 (tertiary)"), ("--rule", "Rule"), ("--accent", "Accent"),
    ("--accent-soft", "Accent soft"), ("--caution", "Caution")])
outcome_tokens = "".join(
    (f'<div class="sg-swatch"><div class="sg-swatch__chip seg--{k}"></div><div class="sg-swatch__meta">'
     f'<strong>{escape(LABEL[k])}</strong><br><code>{k}</code><br><code>.seg--{k} · .badge--{k}</code></div></div>')
    for k in OUTCOME_KEYS)
sec("tokens", "Color tokens",
    "<p>All colors are CSS custom properties on <code>:root</code>, redefined for dark mode. Never hard-code a color in a page; "
    "use a token or an outcome class. The six outcome colors are semantic and colorblind-safe: teal shades for support, "
    "slate for not supported, amber for inconclusive, hatched grey for not testable, and a dashed outline for hypotheses whose run never executed.</p>",
    [("Base tokens", f'<div class="sg-swatches">{base_tokens}</div>', False),
     ("Outcome tokens", f'<div class="sg-swatches">{outcome_tokens}</div>', False)])

# --- Typography -----------------------------------------------------------------
sec("type", "Typography",
    "<p>System fonts only: a serif for page and section headings and big numbers, a sans for everything else. "
    "Prose is limited to a 72-character measure with <code>.prose</code>. Numbers use tabular figures.</p>",
    [("Headings and text", """<div class="sg-type">
<p class="kicker">Kicker label</p>
<h2 class="mt-0">Section heading (h2, serif)</h2>
<h3>Subsection heading (h3, sans)</h3>
<p class="lede">Lede paragraph: one or two plain sentences that say what the page shows.</p>
<p>Body text. Short sentences. Numbers come from the data files, for example <span class="num">2,766</span> audited sentences. Inline <code>code</code> and <a href="/campaign/">a link</a>.</p>
<p class="muted small">Muted small text for notes and provenance.</p>
</div>""", True)])

# --- Layout --------------------------------------------------------------------
sec("layout", "Layout",
    "<p>Pages are built from full-width <code>.section</code> bands containing a <code>.container</code> (max 1200px plus gutters). "
    "Use <code>.prose</code> for reading text, <code>.grid</code> (with <code>--2</code>, <code>--3</code>, <code>--4</code>) for card grids, "
    "<code>.split</code> for text-beside-figure, and <code>.stack</code> / <code>.cluster</code> for vertical and inline spacing. "
    "<code>.section--alt</code> gives a tinted band. A page title block is <code>&lt;header class=\"page-head\"&gt;</code>.</p>",
    [("Page skeleton", """<section class="section section--tight">
  <div class="container">
    <div class="section__head">
      <p class="kicker">Campaign</p>
      <h2>Section title</h2>
      <p class="lede">What this section shows.</p>
    </div>
    <div class="grid grid--3">
      <div class="card"><h3 class="card__title">Card</h3><p>Content.</p></div>
      <div class="card"><h3 class="card__title">Card</h3><p>Content.</p></div>
      <div class="card"><h3 class="card__title">Card</h3><p>Content.</p></div>
    </div>
  </div>
</section>""", True)])

# --- Badges --------------------------------------------------------------------
badges = "\n".join(C.outcome_badge(k) for k in OUTCOME_KEYS)
badges_short = "\n".join(C.outcome_badge(k, short=True, count=camp["outcomes"][k]) for k in OUTCOME_KEYS)
defs = "".join(f"<div><dt>{C.outcome_badge(k)}</dt><dd>{escape(DEFINITION[k])}</dd></div>" for k in OUTCOME_KEYS)
sec("badges", "Outcome badge",
    "<p>One badge per verdict. Keys: " + ", ".join(f"<code>{k}</code>" for k in OUTCOME_KEYS) +
    ". Python: <code>components.outcome_badge(key, short=False, count=None)</code>. JS: <code>OC.badge(key, {short, count})</code>.</p>",
    [("Full labels", f'<div class="cluster">{badges}</div>', True),
     ("Short labels with counts", f'<div class="cluster">{badges_short}</div>', True),
     ("Verdict definitions", f'<dl class="deflist">{defs}</dl>', True)])

# --- Legend ----------------------------------------------------------------------
sec("legend", "Legend and swatch",
    "<p>Every chart that uses outcome colors carries a legend. <code>components.legend(keys, counts)</code>; "
    "a single swatch is <code>&lt;span class=\"swatch swatch--KEY\"&gt;</code>.</p>",
    [("Legend with counts (evaluated outcomes)", C.legend(EVALUATED_KEYS, camp["outcomes"]), True)])

# --- Stat tiles ------------------------------------------------------------------
stats = "\n".join([
    C.stat(f'{V["hypotheses_evaluated"]}', "hypotheses evaluated", f'in {V["completed_a_test"]} runs, against pre-registered decision rules'),
    C.stat(f'{camp["outcomes"]["supported"]}', "supported", f'{C.pct(camp["outcomes"]["supported"], V["hypotheses_evaluated"])} of evaluated hypotheses', tone="supported"),
    C.stat(f'{camp["outcomes"]["not_supported"]}', "not supported", None, tone="not_supported"),
    C.stat(f'{camp["outcomes"]["not_testable"]}', "not testable for lack of data", None, tone="not_testable"),
])
sec("stats", "Stat tile",
    "<p><code>components.stat(value, label, note=None, tone=\"\")</code>. Tone is <code>accent</code> or an outcome key (adds a colored edge). "
    "Wrap tiles in <code>.stat-grid</code>. Every number must come from the data files or the verified list in <code>campaign.json</code>.</p>",
    [("Stat grid", f'<div class="stat-grid">{stats}</div>', True)])

# --- Funnel -----------------------------------------------------------------------
fun = C.funnel([
    ("Runs launched", V["runs_launched"], None),
    ("Genuine runs", V["genuine_runs"], f'{V["dry_run_or_superseded"]} were dry-run tests or superseded launches'),
    ("Executed analyses", V["executed_analyses"], None),
    ("Completed at least one test", V["completed_a_test"], None),
    ("Completed the pipeline", V["completed_pipeline"], "reached the multi-agent review stage"),
])
fun += (f'<div class="funnel-aside"><p class="funnel-aside__n num">{V["final_reports"]}</p>'
        f'<p class="funnel-aside__text"><strong>runs produced a final research report</strong>, including some '
        f'that stopped before review, so it is not a funnel step.</p></div>')
sec("funnel", "Funnel",
    "<p><code>components.funnel([(label, value, note), ...])</code>. Bar widths are relative to the first row. "
    "It is an ordered list, so screen readers read the stages in order with their numbers. Every row must be a subset of the row above; "
    "a count that is not (such as final reports) goes in a <code>.funnel-aside</code> next to it.</p>",
    [("Campaign funnel", fun, True)])

# --- Stacked bar ---------------------------------------------------------------------
ev = {k: camp["outcomes"][k] for k in EVALUATED_KEYS}
rows = []
for d, info in camp["by_disease"].items():
    rows.append(f'<div class="stackbar-row"><span class="stackbar-row__label">{escape(info["label"])}</span>'
                f'{C.stacked_bar(info["counts"], keys=EVALUATED_KEYS, label=info["label"])}'
                f'<span class="stackbar-row__total">{info["evaluated"]}</span></div>')
sec("stackbar", "Stacked bar",
    "<p><code>components.stacked_bar(counts, keys=None, size=\"\", label=None, show_values=False)</code>; JS <code>OC.stackedBar(counts, {keys, size, label, showValues})</code>. "
    "Sizes: <code>sm</code> (cards), default, <code>lg</code> (headline). The bar has <code>role=\"img\"</code> and an <code>aria-label</code> listing every count. "
    "Pass <code>keys=EVALUATED_KEYS</code> to show only the 136 evaluated hypotheses.</p>",
    [("Large, with values", C.stacked_bar(ev, keys=EVALUATED_KEYS, size="lg", show_values=True, label="Evaluated hypotheses") + C.legend(EVALUATED_KEYS, ev), True),
     ("Rows by disease (evaluated only)", "".join(rows), True),
     ("Default and small, all six outcomes", C.stacked_bar(camp["outcomes"], label="All nominated hypotheses") + '<div style="height:12px"></div>' + C.stacked_bar(camp["outcomes"], size="sm"), True)])

# --- SVG chart --------------------------------------------------------------------------
maxv = max(ev.values())
bars = []
for i, k in enumerate(EVALUATED_KEYS):
    y = 8 + i * 34
    w = 360 * ev[k] / maxv
    bars.append(f'<text class="chart-text" x="0" y="{y + 17}">{escape(SHORT[k])}</text>'
                f'<rect class="fill--{k}" x="120" y="{y + 4}" width="{w:.1f}" height="20" rx="3"/>'
                f'<text class="chart-text chart-text--strong" x="{126 + w:.1f}" y="{y + 19}">{ev[k]}</text>')
svg = (f'<figure class="figure mt-0"><svg width="520" height="178" viewBox="0 0 520 178" role="img" aria-labelledby="sg-chart-t">'
       f'<title id="sg-chart-t">Evaluated hypotheses by verdict: ' + "; ".join(f"{LABEL[k]} {ev[k]}" for k in EVALUATED_KEYS) +
       f'</title>{"".join(bars)}</svg><figcaption>Inline SVG chart using <code>.fill--KEY</code> classes; the hatch comes from the '
       f'page-wide <code>#oc-hatch</code> pattern in the layout. The <code>&lt;title&gt;</code> is the text equivalent.</figcaption></figure>')
sec("svg", "Inline SVG charts",
    "<p>Hand-built SVG uses <code>.fill--KEY</code> for outcome fills (<code>.fill--not_testable</code> uses the global hatch pattern), "
    "<code>.chart-text</code> / <code>.chart-text--strong</code> for labels and <code>.chart-rule</code> for gridlines. Give every chart "
    "<code>role=\"img\"</code> plus a <code>&lt;title&gt;</code>, or a table, as its text equivalent. Do not add <code>.figure img</code> padding to SVGs.</p>",
    [("Bar chart", svg, True)])

# --- Run card ---------------------------------------------------------------------------
cards = "\n".join(C.run_card(R[r]) for r in ["parkinson-cellchat-immune-axis-r3", "neurodeg-microglia-convergence-r1", "parkinson-lincs-reversal-r1"])
sec("run-card", "Run card",
    "<p><code>components.run_card(run)</code> takes one entry of <code>runs.json</code>. The thumbnail is the first page of the final report "
    "(or its first figure); runs without a report get a hatched placeholder. Put cards in <code>.grid.grid--3</code>.</p>",
    [("Run cards", f'<div class="grid grid--3">{cards}</div>', True)])

# --- Case card ------------------------------------------------------------------------------
case = """<div class="grid grid--3">
<a class="case-card" href="/cases/astrocytoma/">
  <div class="case-card__media"><img src="/assets/img/paper/fig7-case3-astrocytoma.webp" alt="" loading="lazy"></div>
  <div class="case-card__body">
    <p class="kicker">Case 3 · Astrocytoma</p>
    <h3 class="case-card__title">Expert feedback rounds raise concordance with a reference study</h3>
    <p class="case-card__text">Concordance with 17 reference findings rose from 6/17 to 7/17 to 9/17 over three rounds.</p>
    <p class="case-card__meta">Public CGGA subset (DataSet ID CCell_4083)</p>
  </div>
</a>
</div>"""
sec("case-card", "Case card",
    "<p>A whole-card link. The image is decorative (<code>alt=\"\"</code>) because the title carries the meaning.</p>",
    [("Case card", case, True)])

# --- Figure --------------------------------------------------------------------------------
fig = C.figure("/assets/img/paper/fig6-case2-ab.webp",
               "Panels A and B of Figure 6: the fuzzy and comprehensive prompt workflows side by side, and a table rating five fibrosis programs by conservation, spatial support, cell specificity, druggability and priority.",
               "<strong>Figure 6A–B.</strong> The same fibrosis question under a fuzzy and a comprehensive prompt.",
               note_html="Panel D of this figure is not reproduced because it contains a labelling error; its content is restated in the text.")
sec("figure", "Figure with caption",
    "<p><code>components.figure(src, alt, caption_html, credit=True, note_html=\"\")</code>. Every figure needs real alt text. "
    "Manuscript figures carry the credit line <em>Figure from the OmiCairn manuscript (in preparation).</em> "
    "Use <code>.figure__note</code> for corrections. Figures sit on a light card in both themes because their artwork is drawn on white.</p>",
    [("Figure", fig, True)])

# --- Callouts ---------------------------------------------------------------------------------
sec("callout", "Callout",
    "<p><code>components.callout(kind, title, body_html)</code> with <code>note</code> or <code>caution</code>. Use caution for "
    "limitations and corrections, note for definitions and context. Keep them short.</p>",
    [("Note", C.callout("note", "How verdicts were assigned", "<p>AI adjudication agents applied each run's own pre-registered decision rule to its latest outputs.</p>"), True),
     ("Caution", C.callout("caution", "Hypothesis-generating", "<p>Treatment combinations named here are hypotheses nominated for testing, not recommendations.</p>"), True)])

# --- Breadcrumb ---------------------------------------------------------------------
sec("chrome", "Breadcrumb",
    "<p>Rendered by the layout on every page; do not add it yourself. The breadcrumb comes from the "
    "<code>breadcrumb</code> front-matter key (or the <code>breadcrumb=</code> argument of <code>render_page</code>); "
    "Home is added automatically.</p>",
    [("Breadcrumb (layout)", """<nav class="breadcrumb" aria-label="Breadcrumb example"><ol><li><a href="/">Home</a></li><li><a href="/campaign/">Campaign</a></li><li><span aria-current="page">parkinson-gut-brain-axis-r4</span></li></ol></nav>""", True)])

# --- Filter bar ----------------------------------------------------------------------------------
chips = "".join(
    f'<button type="button" class="chip" aria-pressed="{"true" if k == "supported" else "false"}" data-value="{k}">'
    f'<span class="swatch swatch--{k}" aria-hidden="true"></span>{escape(SHORT[k])} <span class="chip__count">{camp["outcomes"][k]}</span></button>'
    for k in OUTCOME_KEYS)
filt = f"""<form class="filter-bar" role="search" aria-label="Filter hypotheses (example)" onsubmit="return false">
  <label class="search"><span class="visually-hidden">Search hypotheses</span>
    <svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="6.5"/><path d="M16 16l4.5 4.5"/></svg>
    <input class="input input--search" type="search" placeholder="Search hypotheses, genes, datasets">
  </label>
  <div class="filter-group"><label class="filter-group__label" for="sg-disease">Disease</label>
    <select class="select" id="sg-disease"><option>All diseases</option><option>Parkinson's disease</option><option>Alzheimer's disease</option><option>Cross-disease</option></select>
  </div>
  <fieldset class="filter-group"><legend>Outcome</legend><div class="chips">{chips}</div></fieldset>
  <p class="filter-bar__count" aria-live="polite"><strong>15</strong> of 179 hypotheses</p>
</form>"""
sec("filters", "Filter bar",
    "<p>A <code>form.filter-bar</code> with <code>role=\"search\"</code>. Toggle chips are <code>button.chip</code> with "
    "<code>aria-pressed</code> (set it from JS). Group chips in <code>fieldset.filter-group</code> with a <code>legend</code>. "
    "The result count is a live region. Keep filter state in the URL hash with <code>OC.hash</code>.</p>",
    [("Filter bar", filt, True)])

# --- Data table ------------------------------------------------------------------------------------
trs = []
for i, r in enumerate([R["parkinson-gut-brain-axis-r4"], R["parkinson-tcell-foothold-r3"], R["alzheimer-rorb-ec-vulnerability-r1"]]):
    c = r["counts"]
    trs.append(f"""<tr>
  <td><a href="{r['page']}" class="mono">{r['run']}</a></td><td>{r['disease']}</td>
  <td class="num">{r['evaluated']}</td><td class="num">{c['supported']}</td><td>{C.stacked_bar(c, size='sm', label=r['run'])}</td>
  <td><button type="button" class="row-toggle" data-oc-row-toggle aria-expanded="false" aria-controls="sg-row-{i}">Details</button></td>
</tr>
<tr class="row-detail" id="sg-row-{i}" hidden><td colspan="6">{escape((r['report'] or {}).get('main_conclusion', '')[:220])}…</td></tr>""")
table = f"""<div class="table-wrap" tabindex="0" role="region" aria-label="Example runs table">
<table class="data-table">
<caption>Three runs, with hypothesis outcomes. Expand a row for the report's main conclusion.</caption>
<thead><tr><th scope="col">Run</th><th scope="col">Disease</th><th scope="col" class="num">Evaluated</th><th scope="col" class="num">Supported</th><th scope="col">Outcomes</th><th scope="col"><span class="visually-hidden">Details</span></th></tr></thead>
<tbody>
{''.join(trs)}
</tbody>
</table>
</div>"""
sec("table", "Data table",
    "<p>Wrap tables in <code>.table-wrap</code> (horizontal scroll on small screens; give it <code>tabindex=\"0\"</code>, <code>role=\"region\"</code> and a label). "
    "Numeric cells get <code>.num</code>. <code>.data-table--compact</code> tightens padding. Expandable rows: a <code>button.row-toggle[data-oc-row-toggle]</code> "
    "with <code>aria-controls</code> pointing at a <code>tr.row-detail</code> that starts <code>hidden</code>; site.js does the rest.</p>",
    [("Table", table, True)])

# --- Disclosure / steps / deflist -------------------------------------------------------------------------
sec("disclosure", "Disclosure",
    "<p>Native <code>details.disclosure</code> for optional depth (evidence quotes, adjudication notes, methods).</p>",
    [("Disclosure", """<details class="disclosure">
  <summary>Adjudication note</summary>
  <div class="disclosure__body"><p>Why the verdict differs from the run's own label, and any alternative reading.</p></div>
</details>
<details class="disclosure">
  <summary>Evidence quote</summary>
  <div class="disclosure__body"><p>Verbatim excerpt from the run outputs.</p></div>
</details>""", True)])

sec("steps", "Steps",
    "<p>An ordered list for process strips such as the run-level phases.</p>",
    [("Steps", """<ol class="steps">
  <li><p class="steps__title">Pre-register</p><p>Hypotheses and decision rules are fixed before analysis.</p></li>
  <li><p class="steps__title">Execute</p><p>Code runs on public data; outputs are recorded.</p></li>
  <li><p class="steps__title">Cross-check</p><p>A deterministic check compares claims with results.</p></li>
  <li><p class="steps__title">Review</p><p>A claim-review agent and reviewer agents audit the report.</p></li>
</ol>""", True)])

sec("deflist", "Definition list",
    "<p><code>dl.deflist</code> with <code>div</code> rows for key–value facts (run metadata, dataset details).</p>",
    [("Definition list", """<dl class="deflist">
  <div><dt>Run</dt><dd class="mono">parkinson-gut-brain-axis-r4</dd></div>
  <div><dt>Disease</dt><dd>Parkinson's disease</dd></div>
  <div><dt>Final status</dt><dd>Halted</dd></div>
</dl>""", True)])

# --- Buttons & links -----------------------------------------------------------------------------
sec("buttons", "Buttons and links",
    "<p><code>.button</code>, <code>.button--primary</code>, <code>.button--ghost</code>, <code>.button--small</code>. "
    "<code>.link-arrow</code> for “read more” links; <code>.link-external</code> marks off-site links. Tags: <code>.tag</code>.</p>",
    [("Buttons", """<div class="cluster">
  <a class="button button--primary" href="/campaign/hypotheses/">Explore all 179 hypotheses</a>
  <a class="button" href="/assets/data/hypotheses.json" download>Download JSON</a>
  <button class="button button--ghost" type="button">Reset filters</button>
  <button class="button button--small" type="button">Small</button>
</div>""", True),
     ("Links and tags", """<p><a class="link-arrow" href="/campaign/">Campaign overview</a></p>
<p><a class="link-external" href="https://github.com/dummyindex/OmiCairn-neurodegeneration-campaign">Campaign data on GitHub</a></p>
<p class="cluster"><span class="tag">PD</span><span class="tag">AD</span><span class="tag">CROSS</span></p>""", True)])

# --- Citation ------------------------------------------------------------------------------------
sec("cite", "Citation block",
    "<p>A <code>pre</code> inside <code>.cite-block</code>, with a copy button using <code>data-oc-copy</code>.</p>",
    [("Citation", """<div class="cite-block">
<pre id="sg-cite"><code>@unpublished{omicairn2026,
  title  = {OmiCairn: an accountable self-learning platform for hypothesis-driven biomedical multi-omics analysis},
  author = {{The OmiCairn Authors}},
  year   = {2026},
  note   = {Manuscript in preparation}
}</code></pre>
<button class="button button--small" type="button" data-oc-copy="#sg-cite">Copy citation</button>
</div>""", True)])

# --- Assemble ------------------------------------------------------------------------------------
toc = "".join(f'<li><a href="#{i}">{escape(t)}</a></li>' for i, t, _, _ in sections)
parts = []
for id_, title, intro, demos in sections:
    d_html = []
    for label, demo, code in demos:
        snippet = (f'<details class="sg-code"><summary>HTML</summary><pre><code>{escape(demo.strip(), quote=True)}</code></pre></details>'
                   if code else "")
        d_html.append(f'<p class="kicker">{escape(label)}</p><div class="sg-demo">{demo}</div>{snippet}')
    parts.append(f'<section class="sg-section" id="{id_}" aria-labelledby="{id_}-h"><h2 id="{id_}-h" class="mt-0">{escape(title)}</h2>'
                 f'<div class="prose">{intro}</div>{"".join(d_html)}</section>')

page = f"""<!--
title: Style guide
description: Living style guide for the OmiCairn showcase: tokens, typography, layout and every component with copy-paste HTML.
section: styleguide
breadcrumb: Style guide
layout: wide
-->
<!-- Generated by tools/gen_styleguide.py. Edit that script, not this file. -->
<div class="container">
<header class="page-head">
<p class="kicker">Design system</p>
<h1>Style guide</h1>
<p class="lede">Every component of the showcase, live, with the exact HTML and class names. Generators should use the Python helpers in <code>tools/components.py</code>; client-side code uses <code>window.OC</code> from <code>site.js</code>. See <code>CONTRACT.md</code>.</p>
</header>
<div class="doc doc--toc doc--toc-wide">
<div>{"".join(parts)}</div>
<nav class="toc" aria-label="Style guide sections"><div class="toc__inner"><p class="toc__title">Components</p><ol>{toc}</ol></div></nav>
</div>
</div>
"""
out = ROOT / "content" / "styleguide" / "index.html"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(page, encoding="utf-8")
print(f"wrote {out.relative_to(ROOT)}")
