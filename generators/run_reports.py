"""Render the markdown final reports to /campaign/runs/<run>/report/.

Source: data/reports/<run>.md (scrubbed by tools/prepare_data.py).
Figures: assets/img/reports/<run>/<name>.webp (converted from the report's figures/*.png).
"""
from __future__ import annotations

import re
from html import unescape


def _strip_tags(s: str) -> str:
    return unescape(re.sub(r"<[^>]+>", "", s)).strip()


def _render(ctx, run: dict, md_text: str) -> tuple[str, str, list]:
    e = ctx.esc
    rid = run["run"]
    lines = md_text.lstrip().splitlines()
    if not lines or not lines[0].startswith("# "):
        raise ValueError(f"report {rid}: first line must be a '# ' title")
    title = lines[0][2:].strip()
    body_md = "\n".join(lines[1:])
    # Pandoc-style superscripts (^26^, ^3,4^) -> <sup>.
    body_md = re.sub(r"\^([0-9][0-9,\u2013\-]*)\^", r"<sup>\1</sup>", body_md)
    html = ctx.markdown(body_md)

    # Figures: <p><img alt="Figure 1" src="figures/x.png" /></p> -> <figure class="figure">
    def fig(m):
        attrs = m.group(1)
        src = re.search(r'src="([^"]+)"', attrs).group(1)
        alt = unescape(re.search(r'alt="([^"]*)"', attrs).group(1))
        name = re.sub(r"\.(png|jpe?g)$", "", src.split("/")[-1])
        p = ctx.assets_dir / "img" / "reports" / rid / f"{name}.webp"
        if not p.exists():
            raise FileNotFoundError(f"report {rid}: figure {p} missing; run tools/prepare_data.py")
        # Prefer the legend heading text (e.g. "Figure 1. Study design ...") as alt text.
        num = re.match(r"^(Figure\s+\d+)\b", alt)
        if num:
            heads = re.findall(r"<h3[^>]*>(.*?)</h3>", html[: m.start()], re.S)
            after = re.match(r"\s*<p><strong>(.*?)</strong>", html[m.end():], re.S)
            if after and _strip_tags(after.group(1)).startswith(num.group(1)):
                alt = _strip_tags(after.group(1))
            elif heads and _strip_tags(heads[-1]).startswith(num.group(1)):
                alt = _strip_tags(heads[-1])
        return ('<figure class="figure"><img src="/assets/img/reports/%s/%s.webp" alt="%s" loading="lazy" decoding="async">'
                '<figcaption><span class="figure__credit">Figure from the final report of %s.</span></figcaption></figure>'
                % (rid, name, e(alt), e(rid)))
    html = re.sub(r"<p>\s*<img([^>]*)/?>\s*</p>", fig, html)
    # Plain links to figure files -> the converted figure.
    html = re.sub(r'href="figures/([^"/]+)\.(?:png|jpe?g)"',
                  lambda m: f'href="/assets/img/reports/{rid}/{m.group(1)}.webp"', html)
    # Tables scroll horizontally on small screens.
    html = re.sub(r"<table>", '<div class="table-wrap"><table class="data-table data-table--compact">', html)
    html = html.replace("</table>", "</table></div>")
    # Prefix heading ids to avoid clashes with layout ids.
    html = re.sub(r'<(h[2-4]) id="([^"]+)"', r'<\1 id="r-\2"', html)
    toc = [(m.group(1), _strip_tags(m.group(2)))
           for m in re.finditer(r'<h2 id="(r-[^"]+)">(.*?)</h2>', html, re.S)]
    return title, html, toc


def generate(ctx):
    runs = {r["run"]: r for r in ctx.load_json("runs")}
    O = ctx.outcomes
    for rid, run in sorted(runs.items()):
        rep = run.get("report")
        if not rep or rep["kind"] != "html":
            continue
        src = ctx.data_dir / "reports" / f"{rid}.md"
        if not src.exists():
            raise FileNotFoundError(f"missing {src}; run tools/prepare_data.py")
        title, html, toc = _render(ctx, run, src.read_text(encoding="utf-8"))
        e = ctx.esc
        c = ctx.components
        counts = run["counts"]
        badges = " ".join(c.outcome_badge(k, short=True, count=counts[k]) for k in O.OUTCOME_KEYS if counts[k])
        toc_html = "".join(f'<li><a href="#{a}">{e(t)}</a></li>' for a, t in toc)
        caution = c.callout(
            "caution", "How to read this report",
            "<p>This report was generated end to end by OmiCairn and is reproduced here as released, apart from "
            "removing run-internal file references. It is hypothesis-generating: it has not been reviewed by human "
            "experts, and its title can state a result more strongly than its own verdicts support. Read it with the "
            f'<a href="/campaign/runs/{rid}/">adjudicated hypothesis verdicts for this run</a>.</p>')
        # The page h1 is the run id (as on run pages); the system's own title is shown smaller and
        # labelled, after the verdicts and the reading note, so it does not read as the site's claim.
        body = f"""
<div class="container">
<header class="page-head report-head">
<p class="kicker">Final report · Campaign run</p>
<h1 class="report-head__id mono">{e(rid)}</h1>
<div class="report-meta">{c.disease_tag(run["disease"])}<span>{e(O.DISEASE_LABEL[run["disease"]])}</span><span aria-hidden="true">·</span><span>{run["evaluated"]} of {run["n_hypotheses"] or 0} hypotheses evaluated</span></div>
<p class="report-head__label">Adjudicated verdicts</p>
<div class="cluster">{badges}</div>
{caution}
<p class="report-head__label">Title as written by the system</p>
<p class="report-head__title">{e(title)}</p>
</header>
<div class="doc doc--toc section--tight">
<article class="report-body prose">
{html}
</article>
<nav class="toc" aria-label="Report sections"><div class="toc__inner"><p class="toc__title">Contents</p><ol>{toc_html}</ol>
<p class="mt-6"><a class="link-arrow" href="/campaign/runs/{rid}/">Run overview</a></p></div></nav>
</div>
</div>"""
        ctx.render_page(
            f"/campaign/runs/{rid}/report/", f"Final report of {rid}", body,
            description=f"Final report of OmiCairn run {rid}: {title}",
            page_title=f"Report · {rid} · OmiCairn",
            section="campaign", layout="wide",
            breadcrumb=[("Campaign", "/campaign/"), (rid, f"/campaign/runs/{rid}/"), ("Final report", None)],
            source="generators/run_reports.py")
