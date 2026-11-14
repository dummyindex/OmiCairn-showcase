"""HTML snippet helpers for generators (mirrors the components in CONTRACT.md).

Every helper returns an HTML string. Links are written root-relative
("/campaign/") and rewritten to relative paths by build.py.
Use these instead of hand-writing component markup so all pages stay consistent.
"""
from __future__ import annotations

from html import escape

from outcomes import EVALUATED_KEYS, LABEL, OUTCOME_KEYS, SHORT, DISEASE_LABEL


def esc(s) -> str:
    return escape("" if s is None else str(s), quote=True)


def pct(n: int, total: int, digits: int = 0) -> str:
    """Percentage string; 'n/a' when total is 0."""
    if not total:
        return "n/a"
    return f"{100 * n / total:.{digits}f}%"


def outcome_badge(key: str, short: bool = False, count: int | None = None) -> str:
    """<span class="badge badge--supported">Supported</span>."""
    if key not in LABEL:
        raise ValueError(f"unknown outcome key {key!r}")
    text = SHORT[key] if short else LABEL[key]
    num = f' <span class="badge__count">{count}</span>' if count is not None else ""
    title = f' title="{esc(LABEL[key])}"' if short else ""
    return f'<span class="badge badge--{key}"{title}>{esc(text)}{num}</span>'


def swatch(key: str) -> str:
    return f'<span class="swatch swatch--{key}" aria-hidden="true"></span>'


def legend(keys=None, counts: dict | None = None, short: bool = False) -> str:
    keys = keys or OUTCOME_KEYS
    items = []
    for k in keys:
        n = f' <span class="legend__count">{counts.get(k, 0)}</span>' if counts is not None else ""
        items.append(f'<li class="legend__item">{swatch(k)}{esc(SHORT[k] if short else LABEL[k])}{n}</li>')
    return f'<ul class="legend">{"".join(items)}</ul>'


def stacked_bar(counts: dict, keys=None, size: str = "", label: str | None = None,
                show_values: bool = False) -> str:
    """Horizontal stacked bar of outcome counts.

    counts: {outcome_key: int}. keys: which keys to include (default: all six;
    pass EVALUATED_KEYS to show only the 136 evaluated outcomes).
    size: "" | "sm" | "lg". show_values: print counts inside wide segments (lg only).
    The bar carries role="img" and an aria-label listing every count (text equivalent).
    """
    keys = keys or OUTCOME_KEYS
    total = sum(counts.get(k, 0) for k in keys)
    parts, desc = [], []
    for k in keys:
        n = counts.get(k, 0)
        desc.append(f"{LABEL[k]} {n}")
        if not n:
            continue
        w = 100 * n / total
        # Label any segment of at least 4% (a two-digit number fits; see .stackbar__val).
        val = f'<span class="stackbar__val">{n}</span>' if show_values and w >= 4 else ""
        parts.append(f'<span class="stackbar__seg seg--{k}" style="--w:{w:.3f}%" '
                     f'title="{esc(LABEL[k])}: {n}">{val}</span>')
    aria = esc((label + ": " if label else "") + "; ".join(desc) + f" (total {total})")
    cls = "stackbar" + (f" stackbar--{size}" if size else "")
    if not total:
        return f'<div class="{cls} stackbar--empty" role="img" aria-label="{aria}"></div>'
    return f'<div class="{cls}" role="img" aria-label="{aria}">{"".join(parts)}</div>'


def funnel(rows) -> str:
    """rows: [(label, value, note_or_None)]; widths are relative to the first row."""
    top = rows[0][1] or 1
    lis = []
    for label, value, note in rows:
        n = f'<span class="funnel__note">{esc(note)}</span>' if note else ""
        lis.append(
            f'<li class="funnel__row" style="--w:{100 * value / top:.3f}%">'
            f'<span class="funnel__label">{esc(label)}{n}</span>'
            f'<span class="funnel__track"><span class="funnel__bar"></span></span>'
            f'<span class="funnel__value">{value:,}</span></li>')
    return f'<ol class="funnel">{"".join(lis)}</ol>'


def stat(value, label: str, note: str | None = None, tone: str = "") -> str:
    """Stat tile. tone: "" | "accent" | an outcome key (adds a colored rule)."""
    cls = "stat" + (f" stat--{tone}" if tone else "")
    n = f'<p class="stat__note">{note}</p>' if note else ""
    return (f'<div class="{cls}"><p class="stat__value">{esc(value)}</p>'
            f'<p class="stat__label">{label}</p>{n}</div>')


def callout(kind: str, title: str | None, body_html: str) -> str:
    """kind: "note" | "caution". body_html is trusted HTML."""
    if kind not in ("note", "caution"):
        raise ValueError(kind)
    t = f'<p class="callout__title">{esc(title)}</p>' if title else ""
    return f'<aside class="callout callout--{kind}">{t}{body_html}</aside>'


def figure(src: str, alt: str, caption_html: str = "", credit: bool = True,
           note_html: str = "", wide: bool = False, width: int | None = None,
           height: int | None = None) -> str:
    """Figure with caption. credit=True adds the manuscript credit line."""
    if not alt:
        raise ValueError("figure needs alt text")
    dims = f' width="{width}" height="{height}"' if width and height else ""
    cred = ('<span class="figure__credit">Figure from the OmiCairn manuscript (in preparation).</span>'
            if credit else "")
    note = f'<span class="figure__note">{note_html}</span>' if note_html else ""
    cap = f"<figcaption>{caption_html}{note}{cred}</figcaption>" if (caption_html or credit or note) else ""
    cls = "figure" + (" figure--wide" if wide else "")
    return (f'<figure class="{cls}"><img src="{esc(src)}" alt="{esc(alt)}" loading="lazy" '
            f'decoding="async"{dims}>{cap}</figure>')


def disease_tag(code: str) -> str:
    return f'<span class="tag" title="{esc(DISEASE_LABEL.get(code, code))}">{esc(code)}</span>'


def run_card(run: dict) -> str:
    """Card for one run (an entry of assets/data/runs.json)."""
    rep = run.get("report")
    if rep:
        title = rep["title"]
    else:
        t = run["topic"].replace("-", " ")
        title = t[:1].upper() + t[1:]
    thumb = (f'<img class="run-card__thumb" src="{esc(rep["thumb"])}" alt="" loading="lazy" '
             f'decoding="async" width="600" height="450">' if rep else
             '<div class="run-card__thumb run-card__thumb--none" aria-hidden="true">'
             '<span>No final report</span></div>')
    counts = run["counts"]
    total = sum(counts.values())
    bar = stacked_bar(counts, size="sm", label=f"Hypotheses of {run['run']}") if total else ""
    if run["evaluated"]:
        summary = f'{run["evaluated"]} evaluated'
        if counts["supported"]:
            summary += f' · {counts["supported"]} supported'
    elif run.get("stop_reason"):
        summary = "Stopped before planning" if run["stop_reason"] == "INFRASTRUCTURE" else "Ideation only"
    else:
        summary = f"{total} planned, none tested"
    return (
        f'<article class="run-card">'
        f'<a class="run-card__link" href="{esc(run["page"])}">'
        f'{thumb}<div class="run-card__body">'
        f'<p class="run-card__id mono">{esc(run["run"])}</p>'
        f'<h3 class="run-card__title">{esc(title)}</h3>'
        f'</div></a>'
        f'<div class="run-card__foot">{disease_tag(run["disease"])}'
        f'<span class="run-card__summary">{esc(summary)}</span>{bar}</div>'
        f'</article>')


# --------------------------------------------------------------------------
# Case studies: one data list for every case card (home and /cases/) and the
# previous/next navigation at the end of each case page.
# --------------------------------------------------------------------------
CASES = [
    {"slug": "ccrcc", "n": 1, "short": "ccRCC", "eyebrow": "Case 1 · ccRCC",
     "title": "Spatial hypotheses for treatment resistance in clear cell renal cell carcinoma",
     "text": ("From an open-ended question, OmiCairn combined single-cell (n = 19), spatial (n = 24) "
              "and TCGA-KIRC (n = 613) data and nominated candidate resistance niches."),
     "meta": "Candidate combinations are hypotheses nominated for testing, not recommendations.",
     "img": "/assets/img/cases/ccrcc/card-workflow.webp"},
    {"slug": "fibrosis", "n": 2, "short": "Fibrosis", "eyebrow": "Case 2 · Fibrosis",
     "title": "A fuzzy and a comprehensive prompt for the same fibrosis question",
     "text": ("Both recovered conserved fibroblast matrix programs. They disagreed on the macrophage "
              "program and the three-cell niche; only 8 of 32 distinct findings were shared."),
     "meta": "Stricter, expert-specified criteria overturned a looser claim.",
     "img": "/assets/img/cases/fibrosis/card-prompts.webp"},
    {"slug": "astrocytoma", "n": 3, "short": "Astrocytoma", "eyebrow": "Case 3 · Astrocytoma",
     "title": "Expert feedback rounds raise concordance with a reference study",
     "text": ("As expert input grew over three rounds, concordance with 17 reference findings rose "
              "from 6/17 to 7/17 to 9/17. The gain measures use of feedback, not autonomous ability."),
     "meta": "Publicly available CGGA subset (DataSet ID CCell_4083).",
     "img": "/assets/img/cases/astrocytoma/card-rounds.webp"},
]


def case_card(case: dict, h: str = "3") -> str:
    """Case card (a.case-card). h: heading level of the title ("2" or "3")."""
    return (f'<a class="case-card" href="/cases/{case["slug"]}/">'
            f'<div class="case-card__media"><img src="{esc(case["img"])}" alt="" loading="lazy" '
            f'decoding="async" width="800" height="450"></div>'
            f'<div class="case-card__body"><p class="kicker">{esc(case["eyebrow"])}</p>'
            f'<h{h} class="case-card__title">{esc(case["title"])}</h{h}>'
            f'<p class="case-card__text">{esc(case["text"])}</p>'
            f'<p class="case-card__meta">{esc(case["meta"])}</p></div></a>')


def case_cards(h: str = "3", cls: str = "") -> str:
    """The three case cards in a three-column grid. Include: <!--oc:include case-cards h=2-->."""
    extra = f" {cls}" if cls else ""
    return (f'<div class="grid grid--cases{esc(extra)}">' + "".join(case_card(c, h) for c in CASES)
            + "</div>")


def case_nav(current: str) -> str:
    """Previous / all cases / next links for the end of a case page.
    Include: <!--oc:include case-nav current=fibrosis-->."""
    idx = next((i for i, c in enumerate(CASES) if c["slug"] == current), None)
    if idx is None:
        raise ValueError(f"unknown case {current!r}")
    links = []
    if idx > 0:
        p = CASES[idx - 1]
        links.append(f'<a class="case-nextprev__prev" href="/cases/{p["slug"]}/"><small>Previous · Case {p["n"]}</small>'
                     f'<span>{esc(p["short"])}</span></a>')
    links.append('<a class="case-nextprev__all" href="/cases/"><small>All cases</small><span>Case studies overview</span></a>')
    if idx < len(CASES) - 1:
        n = CASES[idx + 1]
        links.append(f'<a class="case-nextprev__next" href="/cases/{n["slug"]}/"><small>Next · Case {n["n"]}</small>'
                     f'<span>{esc(n["short"])}</span></a>')
    return f'<nav class="case-nextprev" aria-label="Other case studies">{"".join(links)}</nav>'


# Build-time includes available to content fragments (see build.py expand_includes).
INCLUDES = {"case-cards": case_cards, "case-nav": case_nav}


__all__ = ["esc", "pct", "outcome_badge", "swatch", "legend", "stacked_bar", "funnel", "stat",
           "callout", "figure", "disease_tag", "run_card", "case_card", "case_cards", "case_nav",
           "CASES", "INCLUDES", "EVALUATED_KEYS", "OUTCOME_KEYS"]
