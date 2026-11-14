"""Campaign overview data blocks and the 57 run pages.

1. /campaign/runs/<run>/ for every run in assets/data/runs.json (rendered here).
2. /campaign/ is written by content/campaign/index.html (prose and structure). This
   generator then fills that page's slots, after the content pass and before the
   build's checks:
     <!--oc-slot:NAME-->                  replaced by a generated block (SLOTS below)
     <span data-oc-n="verified.KEY">N</span>   inner text replaced by campaign.json
   so every number on the overview comes from the data files, not from retyped text.

Sources (all in the repo):
  assets/data/runs.json, hypotheses.json, campaign.json   (tools/prepare_data.py)
  _REVIEW_RUNS below: the "Runs that reached review" subset listed in HYPOTHESES.md of
  the OmiCairn-neurodegeneration-campaign release; checked against campaign.json and
  the subset totals published there (17 runs, 87 hypotheses evaluated, 9 supported).

Per-run "stage" is derived (not a column in the release): see stage_of().
"""
from __future__ import annotations

import re
from collections import Counter, defaultdict

PAGE = "/campaign/"
EXPLORER = "/campaign/hypotheses/"

# HYPOTHESES.md, "Summary" section, subset "Runs that reached review" (17 runs).
_REVIEW_RUNS = (
    "alzheimer-apoe4-microglia-ldam-r1", "alzheimer-ligrec-braak-breakdown-r1",
    "alzheimer-rorb-ec-vulnerability-r1", "ideate-parkinson-mechanism-r2",
    "neurodeg-microglia-convergence-r1", "parkinson-asyn-propagation-r2",
    "parkinson-cellchat-immune-axis-r3", "parkinson-celloracle-ko-r1",
    "parkinson-foundation-embedding-r4", "parkinson-lamda-multiregion-r3",
    "parkinson-lincs-reversal-r4", "parkinson-metabolic-flux-sn-r1",
    "parkinson-multimodal-ppmi-trajectory-r1", "parkinson-multimodal-spatial-proteomics-r3",
    "parkinson-prs-portability-r3", "parkinson-scenic-regulons-r1",
    "pd-vatpase-lysosomal-compensation-r1",
)
# Published subset totals for the runs above (HYPOTHESES.md summary table).
_REVIEW_SUBSET = {"hypotheses": 87, "supported": 9}


# --------------------------------------------------------------------------
# Stages: how far each run got. Derived per run from runs.json + _REVIEW_RUNS.
# key, short label, definition (plain language), depth (for sorting, deepest first)
# --------------------------------------------------------------------------
STAGES = [
    ("pipeline", "Completed the pipeline",
     "Tested at least one hypothesis and reached the multi-agent review stage. This shows the run went "
     "through the whole pipeline, not that its work passed a quality bar.", 5),
    ("tested", "Tested, stopped before review",
     "Tested at least one hypothesis, then stopped before the multi-agent review stage.", 4),
    ("planned", "Planned, no test completed",
     "Wrote pre-registered hypotheses with decision rules, but no hypothesis test was completed. "
     "Its hypotheses are listed as not tested (run did not execute).", 3),
    ("ideation", "Ideation only",
     "Ended after surveying the field and proposing research directions, by design. "
     "Ideation-only runs do not nominate hypotheses.", 2),
    ("stopped", "Stopped before planning",
     "Stopped before writing any hypotheses: a dry-run test, a launch superseded by an immediate "
     "relaunch, a usage limit or a process failure.", 1),
]
STAGE_LABEL = {k: lbl for k, lbl, _, _ in STAGES}
STAGE_DEF = {k: d for k, _, d, _ in STAGES}
STAGE_DEPTH = {k: n for k, _, _, n in STAGES}

STOP_REASON_TEXT = {
    "INFRASTRUCTURE": (
        "This run stopped before the planning stage for an operational reason, not a scientific one. "
        "Runs in this group are dry-run tests, launches superseded by an immediate relaunch, runs that "
        "hit a usage limit, or one process failure. The released data do not say which of these applies "
        "to an individual run. No run in the campaign stopped before planning because data were unavailable."),
    "IDEATE_ONLY": (
        "This was an ideation-only run. By design it surveyed the field and proposed research directions, "
        "then ended. It was never meant to pre-register or test hypotheses, so it has none."),
}
STATUS_TEXT = {
    "done": "The run recorded a final status of done.",
    "halted": "The run recorded a final status of halted: it was closed without being marked done. "
              "A halted run can still have tested hypotheses and written a final report.",
    "in_progress": "The run stopped without recording a final status.",
}
CENSUS_INTRO = ("Census class is a label from an earlier, process-level census of the campaign. "
                "It does not map one-to-one onto the stages above.")

PDF_NOTE = ("The PDF is published exactly as released. It may call itself a \u201cpaper\u201d, call the "
            "system\'s internal multi-agent review \u201cpeer review\u201d, and cite internal stage folders "
            "by number.")
QUESTION_NOTE = ("The research question comes from the topic's current research brief. All attempts at a "
                 "topic share it; earlier attempts may have started from an earlier wording.")
TITLE_NOTE = ("Report titles are the system's own and can state a result more strongly than the "
              "report's verdicts support. Read the main conclusion and the verdicts with it.")

# Verbatim lead sentence for topics whose question does not open with a "?" sentence.
# (start phrase, end phrase) inside the research brief; "…" is added when the excerpt stops mid-sentence.
_LEAD_OVERRIDE = {
    "parkinson-da-vulnerability": ("This OmiCairn run formally tests whether", "TP53/NR2F2 upregulation"),
    "parkinson-gut-brain-axis": ("Despite a decade of", "sit on the mechanistic path."),
    "parkinson-lamda-multiregion": ("It has *never* been tested whether", "in the same donors."),
    "parkinson-tcell-foothold": ("The question is whether", "without TCR ground truth."),
    "pd-vatpase-lysosomal-compensation": ("This run PRE-REGISTERS", "cohorts and modalities."),
    "neurodeg-microglia-convergence": ("This run asks whether", "is, by contrast, AD-specific."),
    "parkinson-plasma-prodromal-panel": ("reported that an 8-protein plasma panel", "in their internal cohort."),
}

_ACRONYMS = {"pd": "PD", "ad": "AD", "fm": "FM", "pca": "PCA", "sn": "SN", "ko": "KO", "ec": "EC",
             "bbb": "BBB", "gwas": "GWAS", "prs": "PRS", "ppmi": "PPMI", "lincs": "LINCS",
             "snatac": "snATAC", "ldam": "LDAM", "apoe4": "APOE4", "lamda": "LAMDA", "rorb": "RORB",
             "vatpase": "V-ATPase", "asyn": "α-syn", "da": "DA", "scenic": "SCENIC", "celloracle": "CellOracle",
             "cellchat": "CellChat", "ligrec": "Ligand–receptor", "tcell": "T-cell", "neurodeg": "Neurodegeneration",
             "singlecell": "single-cell", "ideate": "Ideation:"}


# --------------------------------------------------------------------------
# Small text helpers
# --------------------------------------------------------------------------
def _dehyphenate(s: str) -> str:
    """Undo line-wrap hyphen breaks of the brief ('lipid-droplet- accumulating'). Conservative:
    keeps 'RORB- neurons', 'high- vs low-', 'pre- and post-'."""
    s = re.sub(r"(?<=[a-z])- (?!(?:and|or|to|vs|versus|nor)\b)(?=[a-z])", "-", s)
    return re.sub(r"(?<=\d)- (?=\d)", "-", s)


def _inline_md(esc, s: str) -> str:
    """Escape, then render **bold**, *em* and `code` (the only markup in the sources)."""
    h = esc(s)
    h = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", h)
    h = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<em>\1</em>", h)
    h = re.sub(r"`([^`]+)`", r"<code>\1</code>", h)
    return h


def _run_text(esc, s: str) -> str:
    """Hypothesis-level text (quote, note): a run's output is a report, never a "paper".
    Two adjudication notes still say "paper" after tools/scrub.py; reword them for display."""
    return _inline_md(esc, re.sub(r"\bpaper\b", "report", s or ""))


def _plain(s: str) -> str:
    return re.sub(r"\*{1,2}([^*]+)\*{1,2}", r"\1", s).replace("`", "")


def _brief_paragraphs(q: str) -> list[str]:
    return [_dehyphenate(p.strip()) for p in q.split("\n\n") if p.strip()]


def key_question(topic: str, q: str | None) -> str | None:
    """One verbatim sentence that states the run's question (see _LEAD_OVERRIDE)."""
    if not q:
        return None
    paras = []
    for p in _brief_paragraphs(q):
        if re.match(r"(?i)^hypotheses\b", p):
            break
        if re.match(r"^Direction d\d+ from\b", p):
            continue
        paras.append(p)
    if topic in _LEAD_OVERRIDE:
        start, end = _LEAD_OVERRIDE[topic]
        text = " ".join(paras)
        i = text.find(start)
        j = text.find(end, i)
        if i < 0 or j < 0:
            raise ValueError(f"campaign: lead sentence for {topic} not found in its research brief")
        out = text[i:j + len(end)]
        if out[0].islower():
            out = "…" + out
        if out[-1] not in ".?!":
            out += " …"
        return out
    for p in paras:
        k = p.find("?")
        if k >= 0:
            head = p[:k + 1]
            starts = [m.end() for m in re.finditer(r"[.!?]\s+(?=[A-Z])", head[:-1])
                      if not re.search(r"(\bal|\b[A-Z]|\bvs|\bNat|\bSci)\.$", head[:m.start() + 1])]
            return head[starts[-1] if starts else 0:].strip()
    m = re.match(r"^(.{40,}?[.;])\s", paras[0]) if paras else None
    return (m.group(1) if m else (paras[0] if paras else None))


def topic_title(topic: str) -> str:
    words = [_ACRONYMS.get(w, w) for w in topic.split("-")]
    t = " ".join(words)
    return t[:1].upper() + t[1:]


def stage_of(run: dict, review: set) -> str:
    if run["stop_reason"] == "IDEATE_ONLY":
        return "ideation"
    if run["stop_reason"] == "INFRASTRUCTURE":
        return "stopped"
    if not run["n_hypotheses"]:
        raise ValueError(f"campaign: {run['run']} has no stop reason and no hypotheses")
    if run["evaluated"] == 0:
        return "planned"
    return "pipeline" if run["run"] in review else "tested"


def _kb(n: int) -> str:
    return f"{round(n / 1024):,} KB" if n < 1024 * 1024 else f"{n / 1024 / 1024:.1f} MB"


# --------------------------------------------------------------------------
# Data model shared by the overview and the run pages
# --------------------------------------------------------------------------
class Model:
    def __init__(self, ctx):
        self.ctx = ctx
        self.runs = ctx.load_json("runs")
        self.hyps = ctx.load_json("hypotheses")
        self.camp = ctx.load_json("campaign")
        self.V = self.camp["verified"]
        O = ctx.outcomes
        self.O = O
        names = [r["run"] for r in self.runs]
        if names != sorted(names) or len(set(names)) != len(names):
            raise ValueError("campaign: runs.json must be sorted by run id without duplicates")
        review = set(_REVIEW_RUNS)
        missing = review - set(names)
        if missing:
            raise ValueError(f"campaign: review subset names unknown runs {sorted(missing)}")
        self.by_run = {r["run"]: r for r in self.runs}
        self.hyps_by_run = defaultdict(list)
        for h in self.hyps:
            self.hyps_by_run[h["run"]].append(h)
        self.stage = {r["run"]: stage_of(r, review) for r in self.runs}
        self.lead = {r["run"]: key_question(r["topic"], r["question"]) for r in self.runs}
        # An ideation brief ("not a data-analysis task") misdescribes an ideation run that went on
        # to plan and test hypotheses: describe what it did instead, from its first hypothesis.
        self.lead_from_brief = {rid: bool(q) for rid, q in self.lead.items()}
        for r in self.runs:
            if r["topic"].startswith("ideate-") and r["n_hypotheses"]:
                first = self.hyps_by_run[r["run"]][0]["hypothesis"]
                self.lead[r["run"]] = (f'Started as an ideation run, then planned and tested '
                                       f'{r["n_hypotheses"]} hypotheses of its own, beginning with: {first}')
                self.lead_from_brief[r["run"]] = False
        self.topics = defaultdict(list)
        for r in self.runs:
            self.topics[r["topic"]].append(r)
        for t in self.topics.values():
            t.sort(key=lambda r: r["attempt"])
        self._check()
        self.derived = self._derive()

    def _derive(self) -> dict:
        """Numbers the overview prose quotes that are not stored in campaign.json.
        All are sums or shares of campaign.json outcomes (the README states the same values)."""
        oc, pct = self.camp["outcomes"], self.ctx.components.pct
        ev = self.V["hypotheses_evaluated"]
        neg = oc["not_supported"] + oc["not_testable"]
        upper = oc["supported"] + oc["partial"] + oc["inconclusive"]
        return {
            "supported_pct": pct(oc["supported"], ev),
            "not_supported_or_untestable": neg,
            "not_supported_or_untestable_pct": pct(neg, ev),
            "upper_bound_support": upper,
            "upper_bound_support_pct": pct(upper, ev),
            "not_testable_pct": pct(oc["not_testable"], ev),
            "reports_without_review": self.reports_without_review,
            "topics": len(self.topics),
        }

    def _check(self):
        """Every derived number must agree with the verified campaign numbers."""
        V, c = self.V, Counter(self.stage.values())
        rep = {r["run"] for r in self.runs if r["report"]}
        checks = {
            "runs_launched": len(self.runs),
            "completed_pipeline": c["pipeline"],
            "completed_a_test": c["pipeline"] + c["tested"],
            "reached_planning": c["pipeline"] + c["tested"] + c["planned"],
            "ideation_only_runs": c["ideation"],
            "final_reports": len(rep),
            "hypotheses_nominated": len(self.hyps),
            "hypotheses_evaluated": sum(r["evaluated"] for r in self.runs),
        }
        bad = {k: (v, V[k]) for k, v in checks.items() if V[k] != v}
        if c["stopped"] != V["dry_run_or_superseded"] + V["stopped_at_scoping"]:
            bad["stopped"] = (c["stopped"], V["dry_run_or_superseded"] + V["stopped_at_scoping"])
        rev = [r for r in self.runs if self.stage[r["run"]] == "pipeline"]
        if not all(r["report"] for r in rev):
            bad["review runs without report"] = [r["run"] for r in rev if not r["report"]]
        sub = {"hypotheses": sum(r["evaluated"] for r in rev),
               "supported": sum(r["counts"]["supported"] for r in rev)}
        if sub != _REVIEW_SUBSET:
            bad["review subset"] = (sub, _REVIEW_SUBSET)
        for r in self.runs:
            hc = Counter(h["outcome"] for h in self.hyps_by_run[r["run"]])
            if any(hc.get(k, 0) != r["counts"][k] for k in self.O.OUTCOME_KEYS):
                bad[f"counts {r['run']}"] = (dict(hc), r["counts"])
        if bad:
            raise ValueError(f"campaign: derived numbers disagree with campaign.json: {bad}")

    @property
    def reports_without_review(self) -> int:
        return sum(1 for r in self.runs if r["report"] and self.stage[r["run"]] != "pipeline")

    def stage_counts(self) -> Counter:
        return Counter(self.stage.values())

    def card_order(self) -> list[dict]:
        """Default grid order: runs with a final report first, then deepest stage, then run id."""
        return sorted(self.runs, key=lambda r: (0 if r["report"] else 1,
                                                -STAGE_DEPTH[self.stage[r["run"]]], r["run"]))


# --------------------------------------------------------------------------
# Shared fragments
# --------------------------------------------------------------------------
def stage_pill(key: str) -> str:
    return (f'<span class="cmp-stage cmp-stage--{key}" title="{STAGE_DEF[key]}">'
            f'<span class="cmp-stage__dots" aria-hidden="true">'
            + "".join('<i class="on"></i>' if i < STAGE_DEPTH[key] else "<i></i>" for i in range(5))
            + f'</span>{STAGE_LABEL[key]}</span>')


def run_summary(run: dict) -> str:
    total = sum(run["counts"].values())
    if run["evaluated"]:
        s = f'{run["evaluated"]} evaluated'
        s += f' · {run["counts"]["supported"]} supported'
        return s
    if run["stop_reason"]:
        return "No hypotheses"
    return f"{total} planned, none tested"


def run_card(m: Model, run: dict) -> str:
    c, e = m.ctx.components, m.ctx.esc
    rid, st, rep = run["run"], m.stage[run["run"]], run["report"]
    lead = m.lead[rid]
    if rep:
        fit = " cmp-thumb--fit" if rep["kind"] == "html" else ""
        thumb = (f'<img class="run-card__thumb{fit}" src="{e(rep["thumb"])}" alt="" loading="lazy" '
                 f'decoding="async" width="600" height="450">')
    else:
        thumb = ('<div class="run-card__thumb run-card__thumb--none" aria-hidden="true">'
                 '<span>No final report</span></div>')
    title = (_inline_md(e, lead) if lead else
             f'{e(topic_title(run["topic"]))} <span class="muted">(no research question released)</span>')
    total = sum(run["counts"].values())
    bar = c.stacked_bar(run["counts"], size="sm", label=f"Hypotheses of {rid}") if total else ""
    rep_tag = (f'<span class="cmp-rep">{"PDF report" if rep["kind"] == "pdf" else "Report"}</span>'
               if rep else "")
    search = " ".join([rid, _plain(lead or ""), m.O.DISEASE_LABEL[run["disease"]]]).lower()
    return (
        f'<article class="run-card cmp-card" id="run-{e(rid)}" data-run="{e(rid)}" '
        f'data-disease="{e(run["disease"])}" data-stage="{st}" data-report="{1 if rep else 0}" '
        f'data-evaluated="{run["evaluated"]}" data-supported="{run["counts"]["supported"]}" '
        f'data-depth="{STAGE_DEPTH[st]}" data-text="{e(search)}">'
        f'<a class="run-card__link" href="{e(run["page"])}">{thumb}'
        f'<div class="run-card__body"><p class="run-card__id mono">{e(rid)}</p>'
        f'<h3 class="run-card__title cmp-card__q">{title}</h3></div></a>'
        f'<div class="run-card__foot">{c.disease_tag(run["disease"])}{stage_pill(st)}{rep_tag}'
        f'<span class="run-card__summary">{e(run_summary(run))}</span>{bar}</div>'
        f'</article>')


# --------------------------------------------------------------------------
# Overview slots
# --------------------------------------------------------------------------
def slot_outcomes(m: Model) -> str:
    c, O = m.ctx.components, m.O
    oc = m.camp["outcomes"]
    ev = {k: oc[k] for k in O.EVALUATED_KEYS}
    total = sum(ev.values())
    if total != m.V["hypotheses_evaluated"]:
        raise ValueError("campaign: outcome counts do not sum to hypotheses_evaluated")
    rows = "".join(
        f'<li class="cmp-ol__item"><span class="cmp-ol__n num">{ev[k]}</span>'
        f'<span class="cmp-ol__pct num">{c.pct(ev[k], total)}</span>'
        f'<span class="cmp-ol__label">{c.swatch(k)}{O.LABEL[k]}</span>'
        f'<span class="cmp-ol__def">{O.DEFINITION[k]}</span></li>'
        for k in O.EVALUATED_KEYS)
    return (f'<!-- source: assets/data/campaign.json outcomes (counts per verdict over hypotheses.csv); '
            f'percentages = count / {total} -->'
            f'<div class="cmp-outcomes">'
            f'{c.stacked_bar(ev, keys=O.EVALUATED_KEYS, size="lg", show_values=True, label="Verdicts of the evaluated hypotheses")}'
            f'<ol class="cmp-ol">{rows}</ol></div>')


def slot_by_disease(m: Model) -> str:
    c, O, e = m.ctx.components, m.O, m.ctx.esc
    bd = m.camp["by_disease"]
    order = ["PD", "AD", "CROSS"]
    bars, trs = [], []
    for d in order:
        x = bd[d]
        bars.append(
            f'<div class="stackbar-row"><span class="stackbar-row__label">{e(x["label"])}'
            f'<span class="cmp-sub">{x["runs_with_tests"]} of {x["runs"]} run{"s" if x["runs"] != 1 else ""} tested hypotheses</span></span>'
            f'{c.stacked_bar(x["counts"], keys=O.EVALUATED_KEYS, label=x["label"])}'
            f'<span class="stackbar-row__total">{x["evaluated"]}</span></div>')
        tds = "".join(f'<td class="num">{x["counts"][k]}</td>' for k in O.EVALUATED_KEYS)
        trs.append(f'<tr><th scope="row">{e(x["label"])}</th><td class="num">{x["runs_with_tests"]}</td>'
                   f'{tds}<td class="num">{x["evaluated"]}</td><td class="num">{x["counts"]["not_run"]}</td></tr>')
    tot = {k: sum(bd[d]["counts"][k] for d in order) for k in O.OUTCOME_KEYS}
    tot_tested = sum(bd[d]["runs_with_tests"] for d in order)
    if tot_tested != m.V["completed_a_test"] or sum(tot[k] for k in O.EVALUATED_KEYS) != m.V["hypotheses_evaluated"]:
        raise ValueError("campaign: by_disease totals disagree with verified numbers")
    foot = (f'<tr><th scope="row">All</th><td class="num">{tot_tested}</td>'
            + "".join(f'<td class="num">{tot[k]}</td>' for k in O.EVALUATED_KEYS)
            + f'<td class="num">{m.V["hypotheses_evaluated"]}</td><td class="num">{tot["not_run"]}</td></tr>')
    heads = "".join(f'<th scope="col" class="num">{O.SHORT[k]}</th>' for k in O.EVALUATED_KEYS)
    return (
        '<!-- source: assets/data/campaign.json by_disease (counts split by the disease column) -->'
        f'<div class="cmp-disease" aria-describedby="cmp-disease-table">{"".join(bars)}</div>'
        f'{c.legend(O.EVALUATED_KEYS)}'
        '<details class="disclosure cmp-tabledisc"><summary>Show these numbers as a table</summary>'
        '<div class="disclosure__body">'
        '<div class="table-wrap" tabindex="0" role="region" aria-label="Verdicts by disease">'
        '<table class="data-table data-table--compact" id="cmp-disease-table">'
        '<caption>Hypotheses by disease and verdict. Runs = runs that completed at least one test. '
        'Not run = hypotheses of runs that never executed them (not counted as evaluated).</caption>'
        f'<thead><tr><th scope="col">Disease</th><th scope="col" class="num">Runs</th>{heads}'
        '<th scope="col" class="num">Evaluated</th><th scope="col" class="num">Not run</th></tr></thead>'
        f'<tbody>{"".join(trs)}</tbody><tfoot>{foot}</tfoot></table></div></div></details>')


def slot_funnel(m: Model) -> str:
    c, V = m.ctx.components, m.V
    extra = m.reports_without_review
    rows = [
        ("Runs launched", V["runs_launched"], None),
        ("Genuine runs", V["genuine_runs"],
         f'{V["dry_run_or_superseded"]} dry-run tests or launches superseded by an immediate relaunch removed'),
        ("Reached pre-registered planning", V["reached_planning"],
         f'{V["ideation_only_runs"]} ideation-only runs and {V["stopped_at_scoping"]} stopped at or shortly after scoping'),
        ("Executed analyses", V["executed_analyses"], None),
        ("Completed at least one hypothesis test", V["completed_a_test"], None),
        ("Completed the pipeline", V["completed_pipeline"], "reached the multi-agent review stage"),
    ]
    # Final reports (23) are not a funnel step: they include runs that stopped before review,
    # so the bar would be wider than the one above it. Shown as a callout, as on the home page.
    reports = (f'<div class="funnel-aside"><p class="funnel-aside__n num">{V["final_reports"]}</p>'
               f'<p class="funnel-aside__text"><strong>runs produced a final research report</strong>: the '
               f'{V["completed_pipeline"]} that completed the pipeline, plus {extra} that stopped before review. '
               f'A final report is therefore not a step of the funnel.</p></div>')
    return ('<!-- source: assets/data/campaign.json verified (campaign README funnel). '
            f'"plus {extra}" = runs with a final report that are not in the review subset of HYPOTHESES.md -->'
            + c.funnel(rows) + reports)


def slot_stages(m: Model) -> str:
    sc = m.stage_counts()
    V = m.V
    items = []
    for key, label, defin, _ in STAGES:
        note = ""
        if key == "stopped":
            note = (f' The released data group these {sc[key]} runs together: {V["dry_run_or_superseded"]} dry-run '
                    f'tests or superseded launches and {V["stopped_at_scoping"]} that stopped at or shortly after '
                    'scoping (3 usage limits, 1 process failure).')
        if key == "planned":
            note = (f' {V["reached_planning"] - V["executed_analyses"]} of these {sc[key]} never started its analyses; '
                    'the release does not say which.')
        items.append(f'<div><dt>{stage_pill(key)}<span class="cmp-dl-n num">{sc[key]} runs</span></dt>'
                     f'<dd>{defin}{note}</dd></div>')
    return ('<!-- source: per-run stage derived in generators/campaign.py from runs.json (preplan_stop_reason, '
            'evaluated) and the review subset of HYPOTHESES.md; totals checked against campaign.json -->'
            f'<dl class="deflist cmp-stages">{"".join(items)}</dl>')


def slot_census(m: Model) -> str:
    e = m.ctx.esc
    lab = m.camp["labels"]["census_class"]
    cc = Counter(r["census_class"] for r in m.runs)
    lis = []
    for k in ("SUCCESS", "PARTIAL", "EARLY"):
        st = Counter(m.stage[r["run"]] for r in m.runs if r["census_class"] == k)
        parts = ", ".join(f'{n} {STAGE_LABEL[s].lower()}' for s, n in
                          sorted(st.items(), key=lambda x: -STAGE_DEPTH[x[0]]))
        lis.append(f'<li><strong>{e(lab[k])}</strong> ({cc[k]} runs): {parts}.</li>')
    return ('<!-- source: runs.json census_class crossed with the derived stage -->'
            f'<ul class="cmp-census">{"".join(lis)}</ul>')


# OmiCairn manuscript, Results, campaign section (sections/body.tex): sentence-level audit split.
_AUDIT = {"runs_audited": 21, "auto_corrected": 149, "flagged_for_humans": 91}


def slot_checks(m: Model) -> str:
    c, V = m.ctx.components, m.V
    if _AUDIT["auto_corrected"] + _AUDIT["flagged_for_humans"] != V["claim_integrity_issues"]:
        raise ValueError("campaign: audit split does not add up to claim_integrity_issues")
    return ('<!-- source: assets/data/campaign.json verified; audit split (21 runs, 149 corrected, 91 flagged) '
            'from the OmiCairn manuscript, Results, campaign section -->'
            '<div class="stat-grid cmp-checks">'
            + c.stat(f'{V["runs_reexecuted_after_checks"]} of {V["executed_analyses"]}',
                     "executing runs re-ran analyses",
                     "in response to deterministic cross-check errors or review findings")
            + c.stat(f'{V["claim_review_sentences_audited"]:,}', "report sentences audited",
                     f'by the claim-review agent, across the {_AUDIT["runs_audited"]} runs that reached sentence-level auditing')
            + c.stat(f'{V["claim_integrity_issues"]}', "claim-integrity issues detected",
                     f'{_AUDIT["auto_corrected"]} corrected automatically; {_AUDIT["flagged_for_humans"]} flagged for human revision')
            + '</div>')


def slot_filters(m: Model) -> str:
    O, e = m.O, m.ctx.esc
    dc = Counter(r["disease"] for r in m.runs)
    sc = m.stage_counts()
    nrep = sum(1 for r in m.runs if r["report"])
    dchips = "".join(
        f'<button type="button" class="chip" aria-pressed="false" data-filter="disease" data-value="{d}" '
        f'title="{e(O.DISEASE_LABEL[d])}">{e(O.DISEASE_LABEL[d])} <span class="chip__count">{dc[d]}</span></button>'
        for d in ("PD", "AD", "CROSS"))
    schips = "".join(
        f'<button type="button" class="chip" aria-pressed="false" data-filter="stage" data-value="{k}">'
        f'{e(lbl)} <span class="chip__count">{sc[k]}</span></button>'
        for k, lbl, _, _ in STAGES)
    return (
        '<form class="filter-bar cmp-filter" role="search" aria-label="Filter runs" data-cmp-filter>'
        '<fieldset class="filter-group"><legend>Disease</legend>'
        f'<div class="chips">{dchips}</div></fieldset>'
        '<fieldset class="filter-group"><legend>How far the run got</legend>'
        f'<div class="chips">{schips}</div></fieldset>'
        '<div class="filter-bar__row">'
        '<label class="search"><span class="visually-hidden">Search runs</span>'
        '<svg class="icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><circle cx="11" cy="11" r="6.5"/>'
        '<path d="M16 16l4.5 4.5"/></svg>'
        '<input class="input input--search" type="search" name="q" placeholder="Search run id or question" '
        'autocomplete="off" data-cmp-q></label>'
        f'<button type="button" class="chip" aria-pressed="false" data-filter="report" data-value="1">'
        f'Has a final report <span class="chip__count">{nrep}</span></button>'
        '<label class="cmp-sort"><span class="label">Sort</span><select class="select" data-cmp-sort>'
        '<option value="report">Final report first</option>'
        '<option value="depth">How far the run got</option>'
        '<option value="supported">Most supported hypotheses</option>'
        '<option value="evaluated">Most hypotheses evaluated</option>'
        '<option value="run">Run id (A–Z)</option>'
        '</select></label>'
        '<button type="button" class="button button--ghost button--small" data-cmp-reset>Clear filters</button>'
        f'<p class="filter-bar__count" aria-live="polite" data-cmp-count>Showing <strong>{len(m.runs)}</strong> '
        f'of {len(m.runs)} runs</p>'
        '</div></form>')


def slot_grid(m: Model) -> str:
    cards = "".join(run_card(m, r) for r in m.card_order())
    return ('<!-- source: assets/data/runs.json; one card per run, sorted: final report first, '
            'then stage depth, then run id -->'
            f'<div class="grid grid--3 cmp-grid" data-cmp-grid>{cards}</div>'
            '<p class="cmp-empty" data-cmp-empty hidden>No run matches these filters. '
            '<button type="button" class="button button--small" data-cmp-reset>Clear filters</button></p>')


SLOTS = {
    "outcomes": slot_outcomes,
    "by-disease": slot_by_disease,
    "funnel": slot_funnel,
    "stages": slot_stages,
    "census": slot_census,
    "checks": slot_checks,
    "filters": slot_filters,
    "grid": slot_grid,
}

_URL_ATTR_RE = re.compile(r'\b(href|src)="(/[^"/][^"]*|/)"')


def fill_overview(ctx, m: Model) -> None:
    if PAGE not in ctx.pages:
        raise ValueError("campaign: /campaign/ was not rendered from content/campaign/index.html")
    out = ctx.out_path(PAGE)
    html = out.read_text(encoding="utf-8")

    def slot(mm):
        name = mm.group(1)
        if name not in SLOTS:
            raise ValueError(f"campaign: unknown slot {name!r} in content/campaign/index.html")
        block = SLOTS[name](m)
        # The layout already rewrote the page's links; do the same for generated blocks.
        return _URL_ATTR_RE.sub(lambda a: f'{a.group(1)}="{ctx.rel(PAGE, a.group(2))}"', block)

    html, n_slots = re.subn(r"<!--oc-slot:([a-z-]+)-->", slot, html)
    if n_slots != len(SLOTS):
        raise ValueError(f"campaign: expected {len(SLOTS)} slots in content/campaign/index.html, found {n_slots}")

    def num(mm):
        path = mm.group(2).split(".")
        v = {"derived": m.derived, **m.camp}
        for p in path:
            if p not in v:
                raise ValueError(f"campaign: data-oc-n path {mm.group(2)!r} not in campaign.json")
            v = v[p]
        if isinstance(v, int):
            v = f"{v:,}"
        return f'{mm.group(1)}{v}</span>'

    html = re.sub(r'(<span[^>]*\bdata-oc-n="([a-z_.]+)"[^>]*>)[^<]*</span>', num, html)
    out.write_text(html, encoding="utf-8")


# --------------------------------------------------------------------------
# Run pages
# --------------------------------------------------------------------------
def _hyp_table(m: Model, run: dict) -> str:
    e, c, O = m.ctx.esc, m.ctx.components, m.O
    hs = m.hyps_by_run[run["run"]]
    if not hs:
        return ""
    # Runs that never executed share one quote and note across all rows: show them once.
    shared = (len(hs) > 1 and len({(h["evidence_quote"], h["adjudication_note"]) for h in hs}) == 1)
    lead = ""
    if shared:
        h0 = hs[0]
        lead = c.callout("note", "Why none of these hypotheses was tested",
                         f'<p class="cmp-ev__label">Evidence (verbatim from the run outputs)</p>'
                         f'<blockquote class="cmp-quote">{_run_text(e, h0["evidence_quote"])}</blockquote>'
                         + (f'<p class="cmp-ev__label">Adjudication note</p><p>{_link_runs(m, _run_text(e, h0["adjudication_note"]), run["run"])}</p>'
                            if h0["adjudication_note"] else ""))
    bodies = []
    for h in hs:
        hid = h["hypothesis_id"]
        origin = m.camp["labels"]["origin"][h["origin"]]
        detail = ""
        if not shared:
            q = (f'<div><p class="cmp-ev__label">Evidence (verbatim from the run outputs)</p>'
                 f'<blockquote class="cmp-quote">{_run_text(e, h["evidence_quote"])}</blockquote></div>'
                 if h["evidence_quote"] else "")
            note = (f'<div><p class="cmp-ev__label">Adjudication note</p><p>{_link_runs(m, _run_text(e, h["adjudication_note"]), run["run"])}</p></div>'
                    if h["adjudication_note"] else
                    '<div><p class="cmp-ev__label">Adjudication note</p><p class="muted">None recorded.</p></div>')
            detail = (f'<tr class="cmp-hyp__ev"><td colspan="3"><div class="cmp-ev">{q}{note}</div></td></tr>')
        bodies.append(
            f'<tbody class="cmp-hyp" id="h-{e(hid)}">'
            f'<tr class="cmp-hyp__main"><th scope="row" class="cmp-hyp__id"><a href="#h-{e(hid)}" class="mono">{e(hid)}</a>'
            f'<span class="cmp-hyp__origin">{e(origin)}</span></th>'
            f'<td class="cmp-hyp__text">{_run_text(e, h["hypothesis"])}</td>'
            f'<td class="cmp-hyp__verdict">{c.outcome_badge(h["outcome"], short=True)}'
            f'<a class="cmp-hyp__x small" href="{EXPLORER}#h={e(h["id"])}">In the explorer</a></td></tr>'
            f'{detail}</tbody>')
    return (
        f'{lead}<div class="table-wrap cmp-hyp-wrap" tabindex="0" role="region" aria-label="Hypotheses of {e(run["run"])}">'
        f'<table class="data-table cmp-hyp-table"><caption>Each hypothesis as pre-registered (a condensed statement '
        f'with its decision rule), the adjudicated verdict, the verbatim evidence and the adjudicator\'s note.</caption>'
        f'<thead><tr><th scope="col">ID</th><th scope="col">Hypothesis and decision rule</th>'
        f'<th scope="col">Verdict</th></tr></thead>{"".join(bodies)}</table></div>')


def _link_runs(m: Model, html: str, current: str) -> str:
    """Turn mentions of other campaign run ids (e.g. 'superseded by x-r4') into links."""
    def sub(mm):
        rid = mm.group(0)
        if rid == current or rid not in m.by_run:
            return rid
        return f'<a class="mono" href="{m.by_run[rid]["page"]}">{rid}</a>'
    return re.sub(r"\b[a-z0-9]+(?:-[a-z0-9]+)+-r\d+\b", sub, html)


def _question_block(m: Model, run: dict) -> str:
    e = m.ctx.esc
    q = run["question"]
    if not q:
        return ('<p class="muted">No research question is available for this topic: its research brief is not '
                'part of the released inputs.</p>')
    paras = []
    for p in _brief_paragraphs(q):
        lines = [ln.strip() for ln in p.split("\n") if ln.strip()]
        if lines and all(ln.startswith("- ") for ln in lines):
            paras.append("<ul>" + "".join(f"<li>{_inline_md(e, ln[2:])}</li>" for ln in lines) + "</ul>")
        elif p.startswith("- "):
            paras.append(f"<ul><li>{_inline_md(e, p[2:])}</li></ul>")
        else:
            paras.append(f"<p>{_inline_md(e, p)}</p>")
    if m.lead_from_brief[run["run"]]:
        intro = '<p class="cmp-intro">The sentence under the run id is quoted from this brief.</p>'
    elif m.lead[run["run"]]:
        intro = ('<p class="cmp-intro">This run started from the ideation brief below, which asked for research '
                 'directions rather than data analysis. It then went on to plan and test the hypotheses listed on '
                 'this page.</p>')
    else:
        intro = ""
    return (f'{intro}<details class="disclosure cmp-brief"><summary>Full research brief given to the run</summary>'
            f'<div class="disclosure__body prose">{"".join(paras)}'
            f'<p class="small muted">{QUESTION_NOTE}</p></div></details>')


def _report_aside(m: Model, run: dict) -> str:
    e = m.ctx.esc
    rep = run["report"]
    if not rep:
        return ('<section class="cmp-side card" aria-labelledby="side-report"><h2 class="cmp-side__h" id="side-report">'
                'Final report</h2><p class="muted mb-0">This run did not produce a final report.</p></section>')
    if rep["kind"] == "pdf":
        cta = f'Open the final report <span class="cmp-meta">(PDF, {_kb(rep["bytes"])})</span>'
    else:
        cta = "Read the final report"
    fit = " cmp-thumb--fit" if rep["kind"] == "html" else ""
    return (
        '<section class="cmp-side card cmp-report" aria-labelledby="side-report">'
        '<h2 class="cmp-side__h" id="side-report">Final report</h2>'
        f'<a class="cmp-report__thumb{fit}" href="{e(rep["url"])}"><img src="{e(rep["thumb"])}" '
        f'alt="First page of the final report of {e(run["run"])}" loading="lazy" decoding="async" width="600" height="450"></a>'
        f'<p class="cmp-ev__label">Title (as written by the system)</p>'
        f'<p class="cmp-report__title">{e(rep["title"])}</p>'
        f'<p class="cmp-ev__label">Main conclusion</p><p class="cmp-report__concl">{_inline_md(e, rep["main_conclusion"])}</p>'
        f'<p class="small muted">{TITLE_NOTE} The main conclusion was written during release review and keeps the '
        f'report\'s own numbers and verdicts.</p>'
        + (f'<p class="small muted">{PDF_NOTE}</p>' if rep["kind"] == "pdf" else "") +
        f'<p class="mb-0"><a class="button button--primary cmp-report__cta" href="{e(rep["url"])}">{cta}</a></p>'
        '</section>')


REP_TAG = ' <span class="cmp-rep">Report</span>'


def _attempts_aside(m: Model, run: dict) -> str:
    e = m.ctx.esc
    sibs = m.topics[run["topic"]]
    if len(sibs) < 2:
        return ""
    lis = []
    for s in sibs:
        cur = s["run"] == run["run"]
        name = (f'<span class="mono" aria-current="page">{e(s["run"])}</span>' if cur else
                f'<a class="mono" href="{e(s["page"])}">{e(s["run"])}</a>')
        lis.append(f'<li class="{"is-current" if cur else ""}">{name}{stage_pill(m.stage[s["run"]])}'
                   f'{REP_TAG if s["report"] else ""}</li>')
    return ('<section class="cmp-side card" aria-labelledby="side-attempts">'
            f'<h2 class="cmp-side__h" id="side-attempts">All {len(sibs)} attempts at this topic</h2>'
            f'<ol class="cmp-attempts">{"".join(lis)}</ol>'
            '<p class="small muted mb-0">Attempts are numbered in launch order. A topic was relaunched when an '
            'earlier attempt stopped or was superseded.</p></section>')


def _status_block(m: Model, run: dict) -> str:
    e = m.ctx.esc
    L = m.camp["labels"]
    st = m.stage[run["run"]]
    rows = [("How far it got", f'{stage_pill(st)}<p>{STAGE_DEF[st]}</p>')]
    if run["stop_reason"]:
        rows.append(("Why it stopped", f'<p>{STOP_REASON_TEXT[run["stop_reason"]]}</p>'))
    if run["n_hypotheses"]:
        nr = run["counts"]["not_run"]
        txt = (f'{run["n_hypotheses"]} nominated; {run["evaluated"]} evaluated'
               + (f'; {nr} not tested because the run did not execute them' if nr else ""))
        rows.append(("Hypotheses", f'<p>{e(txt)}.</p>'))
    rows.append(("Recorded status", f'<p><strong>{e(L["final_status"][run["final_status"]])}.</strong> '
                                    f'{STATUS_TEXT[run["final_status"]]}</p>'))
    rows.append(("Census class", f'<p><strong>{e(L["census_class"][run["census_class"]])}.</strong> {CENSUS_INTRO} '
                                 f'<a href="{PAGE}#stages">How the classes compare</a>.</p>'))
    dl = "".join(f'<div><dt>{k}</dt><dd>{v}</dd></div>' for k, v in rows)
    return f'<dl class="deflist cmp-status">{dl}</dl>'


def _pager(m: Model, i: int) -> str:
    e = m.ctx.esc
    runs = m.runs
    prev_r = runs[i - 1] if i > 0 else None
    next_r = runs[i + 1] if i < len(runs) - 1 else None
    def cell(r, cls, label):
        if not r:
            return f'<span class="cmp-pager__{cls} cmp-pager__none"></span>'
        return (f'<a class="cmp-pager__{cls}" href="{e(r["page"])}" rel="{"prev" if cls == "prev" else "next"}">'
                f'<span class="cmp-pager__lbl">{label}</span><span class="mono">{e(r["run"])}</span></a>')
    return (f'<nav class="cmp-pager" aria-label="Previous and next run">'
            f'{cell(prev_r, "prev", "Previous run")}'
            f'<a class="cmp-pager__all" href="{PAGE}#runs">All {len(runs)} runs</a>'
            f'{cell(next_r, "next", "Next run")}</nav>')


def run_page(m: Model, i: int) -> str:
    e, c, O = m.ctx.esc, m.ctx.components, m.O
    run = m.runs[i]
    rid, st = run["run"], m.stage[run["run"]]
    lead = m.lead[rid]
    total = sum(run["counts"].values())
    short = st in ("stopped", "ideation")
    sibs = m.topics[run["topic"]]
    attempt = f'Attempt {run["attempt"]} of {len(sibs)} at this topic' if len(sibs) > 1 else "Single attempt at this topic"

    head_q = (f'<p class="lede cmp-lead">{_inline_md(e, lead)}</p>' if lead else
              f'<p class="lede cmp-lead muted">{e(topic_title(run["topic"]))}. No research question was released for this topic.</p>')
    actions = []
    if run["report"]:
        actions.append(f'<a class="button button--primary" href="{e(run["report"]["url"])}">'
                       f'{"Open the final report (PDF)" if run["report"]["kind"] == "pdf" else "Read the final report"}</a>')
    if total:
        actions.append(f'<a class="button" href="{EXPLORER}#run={e(rid)}">This run in the hypothesis explorer</a>')
    summary = ""
    if total:
        legend_keys = [k for k in O.OUTCOME_KEYS if run["counts"][k]]
        summary = (f'<div class="cmp-runbar"><!-- source: runs.json counts for {e(rid)} -->'
                   + (c.stacked_bar(run["counts"], size="lg", show_values=True,
                                    label=f"Verdicts of the hypotheses of {rid}") if run["evaluated"] else "")
                   + f'{c.legend(legend_keys, counts=run["counts"])}</div>')

    head = (f'<header class="page-head cmp-runhead">'
            f'<p class="kicker">Campaign run · {e(O.DISEASE_LABEL[run["disease"]])}</p>'
            f'<h1 class="cmp-runid">{e(rid)}</h1>'
            f'<div class="report-meta">{c.disease_tag(run["disease"])}{stage_pill(st)}'
            f'<span>{e(attempt)}</span></div>'
            f'{head_q}{summary}'
            + (f'<div class="cluster cmp-actions">{"".join(actions)}</div>' if actions else "")
            + '</header>')

    main = [f'<section class="cmp-sec" aria-labelledby="status"><h2 id="status">Status</h2>{_status_block(m, run)}</section>']
    if short:
        main.append(c.callout("note", "Why this page is short",
                              f'<p>This run produced no hypotheses, so there are no verdicts to show. It is listed '
                              f'so that the campaign\'s {len(m.runs)} launches are all accounted for, including the ones '
                              f'that did not get far. <a href="{PAGE}#funnel">See where it sits in the campaign funnel</a>.</p>'))
    main.append(f'<section class="cmp-sec" aria-labelledby="question"><h2 id="question">Research question</h2>'
                f'{_question_block(m, run)}</section>')
    if total:
        main.append(
            f'<section class="cmp-sec" aria-labelledby="hypotheses"><h2 id="hypotheses">Hypotheses and verdicts</h2>'
            f'<p class="cmp-intro">Each hypothesis was written with its decision rule before any analysis '
            f'(or, for on-the-fly hypotheses, recorded during execution). AI adjudication agents applied that rule '
            f'to the run\'s latest outputs and quoted the evidence verbatim. Where the data did not meet the rule, the '
            f'verdict follows the data, even if the run\'s own label or report claimed support.</p>'
            f'{_hyp_table(m, run)}</section>')

    side = [_report_aside(m, run) if not short else "", _attempts_aside(m, run)]
    side_html = "".join(s for s in side if s)
    layout = (f'<div class="cmp-runlayout{" cmp-runlayout--short" if not side_html else ""}">'
              f'<div class="cmp-runmain">{"".join(main)}</div>'
              + (f'<aside class="cmp-runside" aria-label="Report and related runs">{side_html}</aside>' if side_html else "")
              + '</div>')
    return (f'<link rel="stylesheet" href="/assets/css/pages/campaign.css">'
            f'<div class="container cmp-run">{head}{layout}{_pager(m, i)}</div>')


def _description(m: Model, run: dict) -> str:
    st = m.stage[run["run"]]
    d = f'Campaign run {run["run"]} ({m.O.DISEASE_LABEL[run["disease"]]}): {STAGE_LABEL[st].lower()}'
    if run["evaluated"]:
        d += f'; {run["evaluated"]} hypotheses evaluated, {run["counts"]["supported"]} supported'
    return d + "."


def generate(ctx):
    m = Model(ctx)
    for i, run in enumerate(m.runs):
        ctx.render_page(run["page"], run["run"], run_page(m, i),
                        description=_description(m, run), section="campaign", layout="wide",
                        page_title=f'{run["run"]} · Campaign run · OmiCairn',
                        breadcrumb=[("Campaign", PAGE), ("Runs", PAGE + "#runs"), (run["run"], None)],
                        source="generators/campaign.py")
    fill_overview(ctx, m)
