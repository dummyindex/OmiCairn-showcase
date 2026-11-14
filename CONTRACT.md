# Contributor contract

Everything a page author or generator author needs. The live reference for the
markup is the style guide page (`content/styleguide/index.html`, built at
`/styleguide/`). Read `BRIEF` rules first: no company info, no run timestamps,
no internal paths, "report" not "paper", "reviewer agents" not "peer review".

## 1. Test-build

```bash
P=python3   # any Python 3.10+ with `markdown`
$P tools/build.py --out /tmp/<your-label>/site      # private out dir; never commit site/
$P tools/build.py --out /tmp/<your-label>/site --strict   # also fail on stub pages
```

The build exits non-zero on any problem and prints one `build: ERROR:` line per
problem. A clean build ends with `build: ok: N pages, M files`. Pages promised by
the IA but not yet written are rendered as stubs with a WARNING (an error with
`--strict`).

Screenshots: `"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new --hide-scrollbars --window-size=1440,2200 --screenshot=out.png "file://<out>/campaign/index.html?theme=light"`.
Add `?theme=dark|light` explicitly: headless Chrome follows the OS theme. Headless
Chrome cannot go below a 500px viewport; to test 390px, load the page in a 390px
iframe from a scratch harness page.

## 2. Pages from `content/`

One file per page. `content/campaign/index.html` becomes `/campaign/`
(`site/campaign/index.html`). Only directory pages (`.../index.html`) are expected.

Each file starts with a front-matter HTML comment, `key: value` per line:

```html
<!--
title: Hypothesis explorer
description: All 179 hypotheses of the campaign with verdicts, evidence and adjudication notes.
section: hypotheses
breadcrumb: Campaign=/campaign/ > Hypotheses
layout: wide
-->
<div class="container"> ... page body ... </div>
```

| key | required | meaning |
|---|---|---|
| `title` | yes | `<title>` becomes "title · OmiCairn"; also og:title |
| `description` | yes | meta description and og:description (one or two sentences) |
| `section` | no | highlights the nav item: `home`, `campaign`, `hypotheses`, `cases`, `how-it-works`, `about`, `styleguide`, `none` (default) |
| `breadcrumb` | no | `Label=/path/ > Label=/path/ > Current` (Home is prepended; last item is the current page) |
| `layout` | no | `default`, `wide`, `prose`, `bare` (adds `layout-<x>` on `<body>`; the body markup decides widths) |
| `og_image` | no | root-relative image path (default `/assets/img/og-default.png`) |
| `body_class` | no | extra classes on `<body>` |
| `page_title` | no | full `<title>` override |
| `stylesheet` | no | comma-separated page stylesheets under `/assets/css/`, linked in `<head>` (preferred over a `<link>` in the fragment) |

Build-time includes: a fragment may contain `<!--oc:include NAME key=value-->`, replaced by
`components.INCLUDES[NAME]`: `case-cards h=2|3 [cls=x]` (the three case cards, one data list in
`components.CASES`) and `case-nav current=<slug>` (previous / all / next at the end of a case page).

HTML comments are stripped from every built page (outside `<script>`, `<style>`, `<pre>`), so source
notes in `content/` stay for maintainers and are not published. The build also writes `/404.html`.

The fragment is the content of `<main>`. The layout supplies `<head>`, header and
nav, the breadcrumb, and the footer. **Each page must have
exactly one `<h1>`.** Page-specific scripts go at the end of the fragment:

```html
<script src="/assets/data/hypotheses.js"></script>
<script src="/assets/js/hypotheses.js"></script>
```

`site.js` is loaded (not deferred) in `<head>`, so `window.OC` exists before any page
script runs. Wrap DOM start-up code in `OC.ready(fn)` or put scripts at the end of the fragment.

## 3. Links

Write every internal link **root-relative**: `href="/campaign/"`,
`src="/assets/img/paper/fig1-overview.webp"`, `href="/campaign/runs/<run>/#h-H1"`.
The build rewrites `href`, `src`, `srcset`, `poster`, `action`, `data-src` and
`data-href` attributes to relative paths and adds `index.html` to directory
links, so the site works from `file://` and any S3 prefix. Do not write relative
links by hand, and never write `href="campaign/"` (directory links without
`index.html` are build errors).

- Links inside JavaScript strings are NOT rewritten: use `OC.url("/campaign/runs/x/")`.
- Root-relative URLs inside data files (`report.url`, `page`, `thumb`) need `OC.url()` too.
- External links are allowed only as `<a href="https://...">`. Any external `src`,
  stylesheet, script, iframe or `fetch` is a build error. No `mailto:`.
- Anchors (`#id`) to other pages are checked. Hash-state fragments containing `=`
  are not.
- To skip the checker for one element (rare), add `data-linkcheck="skip"`.

## 4. Generators (`generators/*.py`)

Every module with a `generate(ctx)` function is run after `content/` pages, in
file-name order. Files starting with `_` are ignored. Name yours after your area,
e.g. `generators/run_pages.py`.

```python
def generate(ctx):
    runs = ctx.load_json("runs")                 # assets/data/runs.json
    c = ctx.components                           # tools/components.py
    for r in runs:
        body = f'<div class="container"><header class="page-head"><h1>{ctx.esc(r["run"])}</h1></header>...</div>'
        ctx.render_page(r["page"], r["run"], body,
                        description=f"Run {r['run']} of the OmiCairn campaign.",
                        section="campaign", layout="wide",
                        breadcrumb=[("Campaign", "/campaign/"), (r["run"], None)],
                        source="generators/run_pages.py")
```

`ctx` API:

| member | |
|---|---|
| `ctx.render_page(path, title, body_html, *, description, section="none", breadcrumb=None, layout="default", og_image=None, body_class="", page_title=None, source="generator")` | wrap and write a page. `path` like `/campaign/runs/x/`. Rendering the same path twice is an error. |
| `ctx.load_json(name)` | `hypotheses`, `runs` or `campaign` from `assets/data/` |
| `ctx.components` | helper module (section 6) |
| `ctx.outcomes` | `tools/outcomes.py` (keys, labels, definitions, disease labels) |
| `ctx.esc(s)` | HTML-escape |
| `ctx.markdown(text)` | Markdown to HTML (tables, fenced code, heading ids) |
| `ctx.rel(from_path, to_path)` | relative URL between two site paths (rarely needed) |
| `ctx.out_path(path)` | output file for a site path |
| `ctx.copy_file(src, "/site/path.ext")` / `ctx.write_text("/site/path.ext", text)` | extra output files |
| `ctx.data_dir`, `ctx.assets_dir`, `ctx.out_dir`, `ctx.root` | paths |
| `ctx.warn(msg)` | non-fatal warning |

Raise an exception for anything missing; the build must fail loudly. Keep output
deterministic (sort everything; no dates).

Existing generators: `campaign.py` (overview slots and the 57 run pages), `hypotheses_explorer.py`
(`/campaign/hypotheses/`, rebuilt from the data on every build) and `run_reports.py` (the 5 markdown
reports at `/campaign/runs/<run>/report/`; heading ids prefixed `r-`).

Planned pages (stubbed until someone renders them): `/`, `/campaign/`,
`/campaign/hypotheses/`, `/cases/`, `/cases/ccrcc/`, `/cases/fibrosis/`,
`/cases/astrocytoma/`, `/how-it-works/`, `/platform/`, `/about/`, and `/campaign/runs/<run>/`
for all 57 runs. `content/index.html` is a placeholder for the home-page author to
replace; `content/cases/index.html` is a simple cases overview that the cases
author may rewrite. `/about/` must contain an element with `id="disclaimer"` (it
disclaimer strip links to `/about/#disclaimer`).

## 5. Data files

Generated by a local data-preparation step (not included) and committed. Each JSON has a `.js` twin that
sets `window.OC_DATA[name]`; use the `.js` file in pages, because browsers block
`fetch()` of local JSON under `file://`. Read it with `OC.data("hypotheses")`.
Link the `.json` for downloads.

### `assets/data/hypotheses.json` — array of 179

```json
{
 "id": "alzheimer-apoe4-microglia-ldam-r1/H1",
 "run": "alzheimer-apoe4-microglia-ldam-r1",
 "disease": "AD",                      // PD | AD | CROSS
 "hypothesis_id": "H1",                // H1, H1a, ... or OTF1 ... (on the fly)
 "origin": "plan",                     // plan | on_the_fly
 "hypothesis": "APOE4/4 vs APOE3/3 microglial pseudobulk: ...",
 "verdict": "Not supported",           // label as in the campaign CSV
 "outcome": "not_supported",           // normalized key, see section 7
 "outcome_class": "negative",          // positive | positive (partial) | negative | inconclusive | not tested
 "evidence_quote": "The H1 decision rule required ...",
 "adjudication_note": "0/7 markers FDR<0.05; ...",
 "report_url": "/assets/reports/alzheimer-apoe4-microglia-ldam-r1.pdf",   // or /campaign/runs/<run>/report/ or null
 "report_kind": "pdf"                  // pdf | html | null
}
```

`evidence_source` is intentionally absent. Text fields were scrubbed of
run-internal file names and stage directories ("EXECUTE stage 9", "results
record", "report" instead of "paper"); see the data-preparation step, not included in this repository.

### `assets/data/runs.json` — array of 57

```json
{
 "run": "parkinson-gut-brain-axis-r4",
 "topic": "parkinson-gut-brain-axis",
 "attempt": 4,
 "disease": "PD",
 "census_class": "SUCCESS",            // SUCCESS | PARTIAL | EARLY (process census; not the funnel)
 "final_status": "halted",             // done | halted | in_progress (= stopped without final status)
 "n_hypotheses": 5,                    // null if the run never reached planning
 "counts": {"supported": 1, "partial": 0, "not_supported": 4, "inconclusive": 0, "not_testable": 0, "not_run": 0},
 "evaluated": 5,                       // sum of the first five counts
 "stop_reason": null,                  // null | INFRASTRUCTURE | IDEATE_ONLY (runs that never planned)
 "question": "Wallen, Z.D., ... (multi-paragraph plain text, paragraphs separated by \n\n)",  // null for 3 topics
 "report": {                           // null for the 34 runs without a final report
  "kind": "pdf",                       // pdf -> url is the PDF; html -> url is /campaign/runs/<run>/report/
  "url": "/assets/reports/parkinson-gut-brain-axis-r4.pdf",
  "bytes": 373174,                     // pdf only
  "title": "Gut microbiome and DMNX transcriptomics share 10 of 131 KEGG modules ...",
  "main_conclusion": "Pre-registered null: 10 of 131 KEGG modules ...",
  "thumb": "/assets/img/thumbs/parkinson-gut-brain-axis-r4.webp"   // 600 px wide
 },
 "page": "/campaign/runs/parkinson-gut-brain-axis-r4/"
}
```

`question` comes from the topic's current `RESEARCH.md` (shared by all attempts of a
topic; earlier attempts may have used an earlier wording). Report titles are the
system's own and can overstate; show `main_conclusion` and the verdicts next to them.

### `assets/data/campaign.json`

- `verified`: the verified headline numbers (`runs_launched` 57,
  `dry_run_or_superseded` 16, `genuine_runs` 41, `ideation_only_runs` 4,
  `stopped_at_scoping` 4, `reached_planning` 33, `executed_analyses` 32,
  `completed_a_test` 27, `completed_pipeline` 17, `final_reports` 23,
  `hypotheses_nominated` 179, `hypotheses_preregistered` 160,
  `hypotheses_on_the_fly` 19, `hypotheses_evaluated` 136, `hypotheses_not_run` 43,
  `claim_review_sentences_audited` 2766, `claim_integrity_issues` 240,
  `runs_reexecuted_after_checks` 19, `benchmark_tasks_completed` 36,
  `benchmark_tasks_total` 40). Use these; do not retype numbers.
- `outcomes`: counts per outcome key over all 179.
- `by_disease.{PD,AD,CROSS}`: `{label, runs, runs_with_tests, counts, evaluated}`.
- `by_origin.{plan,on_the_fly}`: `{label, counts}`.
- `runs_with_supported`: 11.
- `labels`: display labels for outcome, disease, origin, stop_reason, census_class, final_status.
- `how_computed`: one sentence per derived number.

Other files: `assets/reports/<run>.pdf` (18 PDFs), `assets/img/thumbs/<run>.webp`
(23), `assets/img/reports/<run>/*.webp` (markdown-report figures),
`data/campaign/*` (sanitized CSV copies, `report_index.json`,
`research_questions.json`).

### Manuscript figures (`assets/img/paper/`)

| file | content |
|---|---|
| `fig1-overview.webp` | Figure 1, system overview |
| `fig5-case1-ccrcc.webp` | Figure 5, Case 1 |
| `fig6-case2-ab.webp` | Figure 6 panels A–B (prompts schematic, program table) |
| `fig6-case2-c.webp` | Figure 6 panel C (Venn: 9 / 8 / 15) |
| `fig7-case3-astrocytoma.webp` | Figure 7, Case 3 |

Figure 6 panel D is deliberately not provided (labelling error); restate it in HTML.
Caption every manuscript figure with the credit line (the `figure()` helper adds it).

## 6. Components and classes

Python helpers in `tools/components.py` (available as `ctx.components`):
`esc`, `pct(n, total, digits=0)`, `outcome_badge(key, short=False, count=None)`,
`swatch(key)`, `legend(keys=None, counts=None, short=False)`,
`stacked_bar(counts, keys=None, size="", label=None, show_values=False)`,
`funnel([(label, value, note), ...])`, `stat(value, label, note=None, tone="")`,
`callout("note"|"caution", title, body_html)`,
`figure(src, alt, caption_html="", credit=True, note_html="", wide=False, width=None, height=None)`,
`disease_tag(code)`, `run_card(run)`.

| component | classes |
|---|---|
| layout | `.grid--cases` (fixed 3 columns), `.jump` (on-this-page pills), `.scroll-x` + `.scroll-hint` (sideways scroller with edge shadows), `.funnel-aside` (count next to a funnel that is not a step), `.container`, `.container--narrow`, `.prose` (72ch), `.section`, `.section--tight`, `.section--alt`, `.section__head`, `.page-head`, `.grid` + `.grid--2/3/4`, `.split` (+`--even`), `.stack`, `.stack--lg`, `.cluster`, `.doc` + `.doc--toc` / `.doc--toc-wide` with `nav.toc > .toc__inner` |
| type | `.kicker`, `.lede`, `.muted`, `.small`, `.mono`, `.num` (tabular), `.serif`, `.hero`, `.hero__title`, `.hero__lede`, `.hero__actions` |
| outcome badge | `.badge.badge--<key>`, `.badge__count` |
| swatch / fills | `.swatch.swatch--<key>`, `.seg--<key>` (HTML bars), `.fill--<key>` (SVG; `fill--not_testable` uses the layout's `#oc-hatch` pattern), `.fill--accent`, `.fill--muted`, `.chart-text`, `.chart-text--strong`, `.chart-rule` |
| legend | `ul.legend > li.legend__item` (+ `.legend__count`) |
| stat tile | `.stat-grid > .stat` (+ `.stat--accent` / `.stat--<key>`), `.stat__value`, `.stat__label`, `.stat__note` |
| funnel | `ol.funnel > li.funnel__row[style="--w:NN%"]` with `.funnel__label`, `.funnel__note`, `.funnel__track > .funnel__bar`, `.funnel__value` |
| stacked bar | `.stackbar` (+ `--sm`, `--lg`, `--empty`) `> .stackbar__seg.seg--<key>[style="--w:NN%"]` (+ `.stackbar__val`); rows: `.stackbar-row` with `__label`, `__total` |
| run card | `article.run-card > a.run-card__link > (img.run-card__thumb | .run-card__thumb--none) + .run-card__body (.run-card__id, h3.run-card__title)`, then `.run-card__foot` |
| case card | `a.case-card > .case-card__media img + .case-card__body (.kicker, .case-card__title, .case-card__text, .case-card__meta)` |
| figure | `figure.figure` (+`--wide`) `> img + figcaption (.figure__note, .figure__credit)` |
| callout | `aside.callout.callout--note|--caution > .callout__title + p` |
| disclosure | `details.disclosure > summary + .disclosure__body` |
| steps | `ol.steps > li > p.steps__title + p` |
| definition list | `dl.deflist > div > dt + dd` |
| filter bar | `form.filter-bar[role=search]`, `.filter-bar__row`, `fieldset.filter-group > legend` (or `.filter-group__label`), `.chips > button.chip[aria-pressed]` (+ `.chip__count`), `label.search > svg.icon + input.input.input--search`, `select.select`, `.label`, `.filter-bar__count[aria-live=polite]` |
| data table | `.table-wrap[tabindex=0][role=region][aria-label] > table.data-table` (+ `--compact`), `td.num`, `tr.row-detail[hidden]`, `button.row-toggle[data-oc-row-toggle][aria-controls][aria-expanded]` |
| buttons/links | `.button`, `.button--primary`, `.button--ghost`, `.button--small`, `.link-arrow`, `.link-external`, `.tag` |
| misc | `.card`, `.card__title`, `.cite-block`, `.visually-hidden`, `.report-body`, `.report-meta` |
| layout chrome (do not add) | `.site-header`, `.site-nav`, `.breadcrumb`, `.site-footer` |

Never hard-code colors; use the tokens (`--bg`, `--bg-elev`, `--bg-tint`,
`--bg-sunken`, `--ink`, `--ink-2`, `--ink-3`, `--rule`, `--rule-strong`,
`--accent`, `--accent-ink`, `--accent-soft`, `--caution`, `--caution-soft`,
`--oc-<key-with-dashes>`, `--oc-<key>-bg`, `--oc-<key>-ink`). Page-specific CSS
goes in its own file under `assets/css/` (linked from the page fragment) or a
`<style>` block; do not edit `site.css` without coordinating.

## 7. Outcome keys

| key | label (CSV verdict) | short | color |
|---|---|---|---|
| `supported` | Supported | Supported | teal `--oc-supported` |
| `partial` | Partially supported | Partial | light teal `--oc-partial` |
| `not_supported` | Not supported | Not supported | slate `--oc-not-supported` |
| `inconclusive` | Inconclusive | Inconclusive | amber `--oc-inconclusive` |
| `not_testable` | Not testable (data) | Not testable | hatched grey |
| `not_run` | Not tested (run did not execute) | Not run | pale grey dashed outline |

The first five are the 136 **evaluated** hypotheses (`EVALUATED_KEYS`); `not_run`
(43) are excluded from evaluated totals. Always show them in this order. Definitions:
`tools/outcomes.py` (`DEFINITION`) and `OC.OUTCOMES`.

## 8. JavaScript (`assets/js/site.js`, global `OC`)

`OC.root`, `OC.url(rootRelative)`, `OC.data(name)`, `OC.OUTCOMES`,
`OC.EVALUATED_KEYS`, `OC.outcome(key)`, `OC.badge(key, {short, count})`,
`OC.stackedBar(counts, {keys, size, label, showValues})`, `OC.esc`, `OC.fmt`,
`OC.qs`, `OC.qsa`, `OC.ready(fn)`, `OC.hash.get()` (URLSearchParams of the hash),
`OC.hash.set({key: value | [values] | null})` (replaceState, no scroll),
`OC.setTheme("dark"|"light")`.

Declarative hooks: `[data-oc-theme-toggle]`, `[data-oc-nav-toggle]`,
`[data-oc-row-toggle]` (+`aria-controls`), `[data-oc-copy="#selector"]`.
`<html>` gets class `js` before paint; theme is `data-theme="dark|light"` on
`<html>` (absent = follow the OS). `?theme=dark|light` forces a theme without
saving it (for QA).

**Hypothesis explorer hash state** (shared format so other pages can deep-link):
`/campaign/hypotheses/#run=<run>&disease=PD&outcome=supported,partial&origin=plan&q=text&h=<run>/<H1>`.
All keys optional; multi-values are comma-separated; `h` expands/scrolls to one
hypothesis.

## 9. Writing rules (short form of the brief)

Report, never paper/manuscript, for a run's output. Reviewer agents / claim-review
agent, never peer review, for the system's own review. "136 hypotheses evaluated",
never "tested". No benchmark scores. No dates or times of runs. No company names,
emails or hosted-case links. Case 2: the prompts disagreed on the macrophage program
and the three-cell niche; never "converged on" or "preserved" it. Case 3 data: the
publicly available CGGA subset (DataSet ID CCell_4083), never "in-house". Case 1
combinations are hypotheses nominated for testing. The build's policy check
(`tools/policy.py: POLICY_PATTERNS`) catches some of this, not all of it.
