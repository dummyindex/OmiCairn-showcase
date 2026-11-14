#!/usr/bin/env python3
"""Static site generator for the OmiCairn showcase.

  python3 tools/build.py [--out site/] [--strict] [--base-url https://example.org/prefix/]

1. Copies assets/ to <out>/assets/.
2. Renders every content/**/*.html fragment inside the shared layout.
3. Runs every generators/*.py module that exposes generate(ctx), in file-name order.
4. Adds stub pages for planned pages nobody rendered (a warning; an error with --strict).
5. Checks every built file: internal links/images resolve, no external requests,
   no un-rewritten root-relative links, alt text present, one <h1> per page,
   release-policy patterns absent. Any problem -> exit code 1.

Output is deterministic: same inputs, same bytes.
See CONTRACT.md for the page/front-matter/generator contract.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import posixpath
import re
import shutil
import sys
from dataclasses import dataclass, field
from html import escape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import components  # noqa: E402
import outcomes  # noqa: E402
from policy import policy_violations  # noqa: E402

SITE_NAME = "OmiCairn"
SITE_DESCRIPTION = ("Every hypothesis, every null result: outputs of OmiCairn, an accountable "
                    "multi-agent system for hypothesis-driven biomedical multi-omics analysis.")
REPO_BASE = "https://github.com/dummyindex"
REPOS = [
    ("OmiCairn", "Research pipeline code", "MIT"),
    ("OmiCairn-engineering", "Platform source code", "MIT"),
    ("OmiCairn-early", "Earliest research prototype", "MIT"),
    ("OmiCairn-neurodegeneration-campaign", "Campaign outcomes and reports", "CC BY 4.0"),
    ("OmiCairn-showcase", "This website's source", "MIT / CC BY 4.0"),
]
ISSUES_URL = f"{REPO_BASE}/OmiCairn/issues"

# Primary navigation: (section key, label, root-relative URL)
NAV = [
    ("campaign", "Campaign", "/campaign/"),
    ("hypotheses", "Hypotheses", "/campaign/hypotheses/"),
    ("cases", "Cases", "/cases/"),
    ("how-it-works", "How it works", "/how-it-works/"),
    ("platform", "Platform", "/platform/"),
    ("about", "About", "/about/"),
]
SECTIONS = {"home", "styleguide", "none"} | {n[0] for n in NAV}

# Pages the information architecture promises. Missing ones get a stub (error with --strict).
PLANNED_PAGES = ["/", "/campaign/", "/campaign/hypotheses/", "/cases/", "/cases/ccrcc/",
                 "/cases/fibrosis/", "/cases/astrocytoma/", "/how-it-works/", "/platform/", "/about/"]
PLANNED_SECTION = {"/campaign/": "campaign", "/campaign/hypotheses/": "hypotheses",
                   "/how-it-works/": "how-it-works", "/platform/": "platform", "/about/": "about"}

FRONT_MATTER_KEYS = {"title", "description", "section", "breadcrumb", "layout", "og_image",
                     "body_class", "page_title", "stylesheet"}
LAYOUTS = {"default", "wide", "prose", "bare"}
TEXT_EXTS = {".html", ".css", ".js", ".json", ".svg", ".txt", ".md", ".xml", ".csv"}
URL_ATTRS = ("href", "src", "poster", "action", "data-src", "data-href")


class BuildError(Exception):
    pass


# --------------------------------------------------------------------------
# Paths and links
# --------------------------------------------------------------------------
def site_file(path: str) -> str:
    """Map a site path to the output file, relative to out/. '/a/b/' -> 'a/b/index.html'."""
    if not path.startswith("/"):
        raise BuildError(f"page path must be root-relative, got {path!r}")
    if ".." in path.split("/"):
        raise BuildError(f"'..' not allowed in page path {path!r}")
    p = path.lstrip("/")
    if p == "" or p.endswith("/"):
        return p + "index.html"
    if not posixpath.splitext(p)[1]:
        raise BuildError(f"page path {path!r} must end with '/' (directory page) or a file name")
    return p


def rel_url(target: str, from_file: str) -> str:
    """Relative URL from the output file `from_file` (e.g. 'campaign/index.html') to the
    root-relative `target` (e.g. '/campaign/runs/x/#h2'). Directory targets get an explicit
    index.html so links work from file:// and from S3 without directory-index rewriting."""
    suffix = ""
    for sep in ("#", "?"):
        if sep in target:
            target, rest = target.split(sep, 1)
            suffix = sep + rest + suffix
    path = target.lstrip("/")
    if path == "" or path.endswith("/"):
        path += "index.html"
    from_dir = posixpath.dirname(from_file) or "."
    rel = posixpath.relpath(path, from_dir)
    return rel + suffix


_ATTR_RE = re.compile(r'(\s(?:' + "|".join(URL_ATTRS) + r')\s*=\s*)(["\'])(/(?!/)[^"\']*)\2')
_SRCSET_RE = re.compile(r'(\ssrcset\s*=\s*)(["\'])([^"\']*)\2')


def rewrite_links(html: str, from_file: str) -> str:
    html = _ATTR_RE.sub(lambda m: m.group(1) + m.group(2) + escape(rel_url(m.group(3), from_file), quote=False) + m.group(2), html)

    def _srcset(m):
        items = []
        for part in m.group(3).split(","):
            bits = part.strip().split()
            if bits and bits[0].startswith("/") and not bits[0].startswith("//"):
                bits[0] = rel_url(bits[0], from_file)
            items.append(" ".join(bits))
        return m.group(1) + m.group(2) + ", ".join(items) + m.group(2)
    return _SRCSET_RE.sub(_srcset, html)


def root_prefix(from_file: str) -> str:
    d = posixpath.dirname(from_file)
    return "" if not d else "../" * (d.count("/") + 1)


# --------------------------------------------------------------------------
# Front matter
# --------------------------------------------------------------------------
_FM_RE = re.compile(r"\A\s*<!--\s*\n(.*?)\n\s*-->\s*\n?", re.S)


def parse_front_matter(text: str, src: Path) -> tuple[dict, str]:
    m = _FM_RE.match(text)
    if not m:
        raise BuildError(f"{src}: missing front-matter comment block at top of file")
    meta = {}
    for ln in m.group(1).splitlines():
        if not ln.strip():
            continue
        if ":" not in ln:
            raise BuildError(f"{src}: bad front-matter line {ln!r} (expected 'key: value')")
        k, v = ln.split(":", 1)
        k = k.strip()
        if k not in FRONT_MATTER_KEYS:
            raise BuildError(f"{src}: unknown front-matter key {k!r}; allowed: {sorted(FRONT_MATTER_KEYS)}")
        meta[k] = v.strip()
    for req in ("title", "description"):
        if not meta.get(req):
            raise BuildError(f"{src}: front matter needs '{req}'")
    return meta, text[m.end():]


def parse_breadcrumb(spec) -> list[tuple[str, str | None]]:
    """'Campaign=/campaign/ > Hypotheses' -> [('Campaign','/campaign/'), ('Hypotheses', None)].
    Also accepts a list of (label, url_or_None) tuples."""
    if not spec:
        return []
    if isinstance(spec, (list, tuple)):
        return [(str(a), b) for a, b in spec]
    out = []
    for item in spec.split(" > "):
        item = item.strip()
        if "=" in item and item.rsplit("=", 1)[1].startswith("/"):
            label, url = item.rsplit("=", 1)
            out.append((label.strip(), url.strip()))
        else:
            out.append((item, None))
    return out


# --------------------------------------------------------------------------
# Layout
# --------------------------------------------------------------------------
THEME_INIT = ("(function(){var d=document.documentElement;d.className+=' js';var t=null;"
              "try{var m=/[?&]theme=(dark|light)\\b/.exec(location.search);"
              "t=m?m[1]:localStorage.getItem('oc-theme');}catch(e){}"
              "if(t==='dark'||t==='light'){d.setAttribute('data-theme',t);}})();")

# Official OmiCairn mark (assets/img/logo/omicairn-mark.svg); base stone follows the text color.
CAIRN_SVG = ('<svg class="brand__mark" viewBox="0 0 85 112" aria-hidden="true" focusable="false">'
             '<ellipse class="brand__base" cx="42.5" cy="96.5" rx="40" ry="12.8"/>'
             '<ellipse cx="39.3" cy="70.1" rx="30.4" ry="10.4" fill="#52796F"/>'
             '<ellipse cx="44.9" cy="47.7" rx="21.6" ry="8.8" fill="#84A98C"/>'
             '<circle cx="42.5" cy="19.3" r="12.8" fill="none" stroke="#E07A5F" stroke-width="9"/></svg>')
BRAND_NAME = '<span class="brand__name">Omi<b>Cairn</b></span>'

SVG_DEFS = ('<svg class="svg-defs" aria-hidden="true" focusable="false" width="0" height="0">'
            '<defs><pattern id="oc-hatch" width="6" height="6" patternUnits="userSpaceOnUse" '
            'patternTransform="rotate(45)"><rect class="hatch-bg" width="6" height="6"/>'
            '<rect class="hatch-line" width="2.2" height="6"/></pattern></defs></svg>')

ICON_SUN = ('<svg class="icon icon--sun" viewBox="0 0 24 24" aria-hidden="true" focusable="false">'
            '<circle cx="12" cy="12" r="4.2"/><path d="M12 2.5v2.2M12 19.3v2.2M2.5 12h2.2M19.3 12h2.2'
            'M5.3 5.3l1.6 1.6M17.1 17.1l1.6 1.6M5.3 18.7l1.6-1.6M17.1 6.9l1.6-1.6"/></svg>')
ICON_MOON = ('<svg class="icon icon--moon" viewBox="0 0 24 24" aria-hidden="true" focusable="false">'
             '<path d="M20 14.5A8.5 8.5 0 0 1 9.5 4a8.5 8.5 0 1 0 10.5 10.5z"/></svg>')
ICON_MENU = ('<svg class="icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false">'
             '<path d="M4 7h16M4 12h16M4 17h16"/></svg>')
ICON_INFO = ('<svg class="icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false">'
             '<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7.5v.5"/></svg>')


def render_layout(*, path: str, out_file: str, title: str, body_html: str, description: str,
                  section: str, breadcrumb, layout: str, og_image: str | None, body_class: str,
                  page_title: str | None, base_url: str | None, stylesheets=(), base_href: str | None = None) -> str:
    e = components.esc
    full_title = page_title or (f"{title} · {SITE_NAME}" if path != "/" else title)
    nav_items = []
    for key, label, url in NAV:
        cur = ""
        if url == path:
            cur = ' aria-current="page"'
        elif key == section:
            cur = ' aria-current="true"'
        nav_items.append(f'<li><a class="site-nav__link" href="{url}"{cur}>{e(label)}</a></li>')
    crumbs = parse_breadcrumb(breadcrumb)
    crumb_html = ""
    if crumbs:
        lis = ['<li><a href="/">Home</a></li>']
        for i, (label, url) in enumerate(crumbs):
            last = i == len(crumbs) - 1
            if url and not last:
                lis.append(f'<li><a href="{url}">{e(label)}</a></li>')
            else:
                lis.append(f'<li><span aria-current="page">{e(label)}</span></li>' if last
                           else f'<li><span>{e(label)}</span></li>')
        crumb_html = (f'<nav class="breadcrumb container" aria-label="Breadcrumb"><ol>{"".join(lis)}</ol></nav>')
    og = [f'<meta property="og:title" content="{e(title)}">',
          f'<meta property="og:description" content="{e(description)}">',
          '<meta property="og:type" content="website">',
          f'<meta property="og:site_name" content="{SITE_NAME}">',
          '<meta name="twitter:card" content="summary_large_image">']
    img = og_image or "/assets/img/og-default.png"
    if base_url:
        og.append(f'<meta property="og:url" content="{e(base_url.rstrip("/") + "/" + out_file.removesuffix("index.html"))}">')
        og.append(f'<meta property="og:image" content="{e(base_url.rstrip("/") + img)}">')
        og.append(f'<link rel="canonical" href="{e(base_url.rstrip("/") + "/" + out_file.removesuffix("index.html"))}">')
    # Without --base-url there is no absolute URL to give crawlers, so og:image is omitted.
    repo_links = "".join(
        f'<li><a href="{REPO_BASE}/{name}">{name}</a> <span class="muted">· {e(desc)} · {lic}</span></li>'
        for name, desc, lic in REPOS)
    explore = "".join(f'<li><a href="{url}">{e(label)}</a></li>' for _, label, url in NAV)
    body_cls = " ".join(x for x in (f"page--{section}", f"layout-{layout}", body_class) if x)
    return f"""<!doctype html>
<html lang="en" data-root="{root_prefix(out_file)}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
{f'<base href="{e(base_href)}">' + chr(10) if base_href else ""}<title>{e(full_title)}</title>
<meta name="description" content="{e(description)}">
<meta name="color-scheme" content="light dark">
<meta name="theme-color" content="#f7f5f0" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#121417" media="(prefers-color-scheme: dark)">
{chr(10).join(og)}
<link rel="icon" href="/assets/img/logo/favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="/assets/css/site.css">
{"".join(f'<link rel="stylesheet" href="{e(s)}">' + chr(10) for s in stylesheets)}<script>{THEME_INIT}</script>
<script src="/assets/js/site.js"></script>
</head>
<body class="{body_cls}">
{SVG_DEFS}
<a class="skip-link" href="#main">Skip to content</a>
<header class="site-header">
<div class="site-header__inner container">
<a class="brand" href="/">{CAIRN_SVG}{BRAND_NAME}</a>
<button class="nav-toggle" type="button" aria-expanded="false" aria-controls="site-nav" data-oc-nav-toggle>{ICON_MENU}<span class="visually-hidden">Menu</span></button>
<nav class="site-nav" id="site-nav" aria-label="Main">
<ul class="site-nav__list">{"".join(nav_items)}</ul>
</nav>
<button class="theme-toggle" type="button" data-oc-theme-toggle aria-label="Switch color theme">{ICON_SUN}{ICON_MOON}</button>
</div>
</header>
<main id="main" class="site-main" tabindex="-1">
{crumb_html}
{body_html}
</main>
<footer class="site-footer">
<div class="container site-footer__grid">
<div class="site-footer__about">
<a class="brand brand--footer" href="/">{CAIRN_SVG}{BRAND_NAME}</a>
<p>An accountable multi-agent system for hypothesis-driven biomedical multi-omics analysis. All outputs on this site are hypothesis-generating.</p>
<p class="muted">Questions or corrections: <a href="{ISSUES_URL}">open a GitHub issue</a>.</p>
</div>
<div><h2 class="site-footer__h">Explore</h2><ul class="site-footer__list">{explore}</ul></div>
<div><h2 class="site-footer__h">Repositories</h2><ul class="site-footer__list">{repo_links}</ul></div>
</div>
<div class="container site-footer__legal">
<p>Site code: <a href="https://opensource.org/license/mit">MIT License</a>. Text, data and figures: <a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a>. Manuscript figures are from the OmiCairn manuscript (in preparation). © The OmiCairn Authors.</p>
</div>
</footer>
</body>
</html>
"""


# --------------------------------------------------------------------------
# Build context
# --------------------------------------------------------------------------
@dataclass
class Context:
    """Passed to every generator's generate(ctx). See CONTRACT.md."""
    root: Path
    out_dir: Path
    base_url: str | None = None
    pages: dict = field(default_factory=dict)      # site path -> source description
    warnings: list = field(default_factory=list)

    @property
    def data_dir(self) -> Path:
        return self.root / "data"

    @property
    def assets_dir(self) -> Path:
        return self.root / "assets"

    components = components
    outcomes = outcomes
    esc = staticmethod(components.esc)

    def load_json(self, name: str):
        """Load assets/data/<name>.json (hypotheses, runs, campaign)."""
        p = self.assets_dir / "data" / f"{name}.json"
        if not p.exists():
            raise BuildError(f"missing data file {p}; run tools/prepare_data.py")
        return json.loads(p.read_text(encoding="utf-8"))

    def out_path(self, path: str) -> Path:
        """Filesystem path in the output for a site path ('/a/b/' -> out/a/b/index.html)."""
        return self.out_dir / site_file(path)

    def rel(self, from_path: str, to_path: str) -> str:
        """Relative URL from page `from_path` to root-relative `to_path`."""
        return rel_url(to_path, site_file(from_path))

    def copy_file(self, src: Path, site_path: str) -> None:
        """Copy a file into the output at a root-relative path (e.g. '/campaign/x.png')."""
        src = Path(src)
        if not src.is_file():
            raise BuildError(f"copy_file: missing source {src}")
        dst = self.out_dir / site_path.lstrip("/")
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)

    def write_text(self, site_path: str, text: str) -> None:
        """Write a non-page text file (e.g. JSON) into the output."""
        dst = self.out_dir / site_path.lstrip("/")
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(text, encoding="utf-8")

    def markdown(self, text: str) -> str:
        import markdown as md
        return md.markdown(text, extensions=["tables", "fenced_code", "sane_lists", "toc"],
                           extension_configs={"toc": {"permalink": False}}, output_format="html")

    def render_page(self, path: str, title: str, body_html: str, *, description: str,
                    section: str = "none", breadcrumb=None, layout: str = "default",
                    og_image: str | None = None, body_class: str = "", page_title: str | None = None,
                    source: str = "generator", stylesheet=None) -> Path:
        """Wrap body_html in the site layout and write it at `path` ('/campaign/runs/x/')."""
        if path in self.pages:
            raise BuildError(f"page {path} rendered twice (by {self.pages[path]} and {source})")
        if section not in SECTIONS:
            raise BuildError(f"{source}: unknown section {section!r}; allowed: {sorted(SECTIONS)}")
        if layout not in LAYOUTS:
            raise BuildError(f"{source}: unknown layout {layout!r}; allowed: {sorted(LAYOUTS)}")
        if not description:
            raise BuildError(f"{source}: page {path} needs a description")
        out_file = site_file(path)
        if isinstance(stylesheet, str):
            stylesheet = [s.strip() for s in stylesheet.split(",") if s.strip()]
        for s in stylesheet or ():
            if not s.startswith("/assets/css/"):
                raise BuildError(f"{source}: stylesheet must be under /assets/css/, got {s!r}")
        body_html = expand_includes(body_html, source)
        html = render_layout(path=path, out_file=out_file, title=title, body_html=body_html,
                             description=description, section=section, breadcrumb=breadcrumb,
                             layout=layout, og_image=og_image, body_class=body_class,
                             page_title=page_title, base_url=self.base_url,
                             stylesheets=stylesheet or ())
        html = rewrite_links(html, out_file)
        dst = self.out_dir / out_file
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(html, encoding="utf-8")
        self.pages[path] = source
        return dst

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)
        print(f"build: WARNING: {msg}")


# --------------------------------------------------------------------------
# Checks
# --------------------------------------------------------------------------
class _Scan(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.refs = []          # (tag, attr, value, skip)
        self.ids = set()
        self.h1 = 0
        self.imgs_no_alt = 0
        self.iframes = 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "id" in a and a["id"]:
            self.ids.add(a["id"])
        if tag == "a" and a.get("name"):
            self.ids.add(a["name"])
        if tag == "h1":
            self.h1 += 1
        if tag == "img" and "alt" not in a:
            self.imgs_no_alt += 1
        if tag in ("iframe", "embed", "object"):
            self.iframes += 1
        skip = a.get("data-linkcheck") == "skip"
        for k in URL_ATTRS:
            if a.get(k) is not None:
                self.refs.append((tag, k, a[k], skip, a.get("rel", "")))
        if a.get("srcset"):
            for part in a["srcset"].split(","):
                bits = part.strip().split()
                if bits:
                    self.refs.append((tag, "srcset", bits[0], skip, ""))

    handle_startendtag = handle_starttag


EXTERNAL_RE = re.compile(r"^(?:[a-z][a-z0-9+.-]*:|//)", re.I)


def check_site(out: Path, stub_files: set | None = None, page_files: set | None = None) -> list[str]:
    """Return a list of problems. stub_files: resolved paths of stub pages (anchors not checked).
    page_files: resolved paths of rendered pages (h1 rule applies only to these)."""
    errors = []
    out = out.resolve()
    stub_files = stub_files or set()
    scans = {}
    for f in sorted(out.rglob("*.html")):
        s = _Scan()
        s.feed(f.read_text(encoding="utf-8"))
        scans[f.resolve()] = s
    for f, s in scans.items():
        rf = f.relative_to(out).as_posix()
        if (page_files is None or f in page_files) and s.h1 != 1:
            errors.append(f"{rf}: has {s.h1} <h1> elements (need exactly 1)")
        if s.imgs_no_alt:
            errors.append(f"{rf}: {s.imgs_no_alt} <img> without alt attribute")
        if s.iframes:
            errors.append(f"{rf}: iframe/embed/object not allowed")
        for tag, attr, val, skip, rel in s.refs:
            if skip:
                continue
            v = val.strip()
            if not v or v.startswith("#") and len(v) == 1:
                if tag == "a" and attr == "href" and v == "#":
                    errors.append(f"{rf}: empty '#' link")
                continue
            if EXTERNAL_RE.match(v):
                scheme = v.split(":", 1)[0].lower()
                if v.startswith("//"):
                    errors.append(f"{rf}: protocol-relative URL {v}")
                elif scheme in ("mailto", "javascript", "data"):
                    if scheme == "mailto":
                        errors.append(f"{rf}: mailto links are not allowed ({v})")
                    elif scheme == "javascript":
                        errors.append(f"{rf}: javascript: URL")
                elif scheme in ("http", "https"):
                    # Absolute URLs that are not fetched: anchors, the canonical link and <base>.
                    nonfetch = (tag == "a" or tag == "base" or (tag == "link" and "canonical" in rel.split()))
                    if not (nonfetch and attr == "href"):
                        errors.append(f"{rf}: external resource <{tag} {attr}={v}> (no runtime requests allowed)")
                    elif v.startswith("http://"):
                        errors.append(f"{rf}: insecure http link {v}")
                continue
            if v.startswith("/"):
                errors.append(f"{rf}: root-relative URL left un-rewritten: {v}")
                continue
            path, frag = (v.split("#", 1) + [""])[:2]
            path = path.split("?", 1)[0]
            if path == "":
                target = f.resolve()
            else:
                target = (f.parent / unquote(path)).resolve()
                try:
                    target.relative_to(out.resolve())
                except ValueError:
                    errors.append(f"{rf}: link escapes the site root: {v}")
                    continue
                if path.endswith("/") or target.is_dir():
                    errors.append(f"{rf}: directory link {v} (write /dir/ root-relative; build adds index.html)")
                    continue
                if not target.exists():
                    errors.append(f"{rf}: broken link {v}")
                    continue
            if frag and "=" not in frag and target.suffix == ".html" and target not in stub_files:
                ts = scans.get(target.resolve())
                if ts is not None and unquote(frag) not in ts.ids:
                    errors.append(f"{rf}: missing anchor #{frag} in {target.relative_to(out).as_posix()}")
    # CSS url() references
    for css in sorted(out.rglob("*.css")):
        rf = css.relative_to(out).as_posix()
        for m in re.finditer(r"url\(\s*['\"]?([^'\")]+)['\"]?\s*\)", css.read_text(encoding="utf-8")):
            u = m.group(1)
            if u.startswith(("data:", "#")):
                continue
            if EXTERNAL_RE.match(u) or u.startswith("/"):
                errors.append(f"{rf}: CSS url() must be relative and local: {u}")
            elif not (css.parent / u.split("#")[0].split("?")[0]).exists():
                errors.append(f"{rf}: CSS url() target missing: {u}")
        if "@import" in css.read_text(encoding="utf-8"):
            errors.append(f"{rf}: @import not allowed")
    # JS must not fetch from the network
    for js in sorted(out.rglob("*.js")):
        t = js.read_text(encoding="utf-8")
        if re.search(r"""(fetch|import)\s*\(\s*['"`]https?:""", t) or re.search(r"""src\s*=\s*['"`]https?:""", t):
            errors.append(f"{js.relative_to(out).as_posix()}: script requests an external URL")
    # Release policy on every text file
    for p in sorted(out.rglob("*")):
        if p.is_file() and p.suffix in TEXT_EXTS:
            rp = p.relative_to(out).as_posix()
            text = p.read_text(encoding="utf-8")
            for rule, snip in policy_violations(text, path=rp):
                errors.append(f"{rp}: policy [{rule}]: …{snip}…")
            if rp.startswith("assets/data/hypotheses."):
                for m in re.finditer(r"\bpaper\b", text):
                    errors.append(f"{rp}: policy [run output called 'paper']: …{text[max(0, m.start() - 40):m.end() + 30]}…")
    return errors


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------
def safe_clean(out: Path) -> None:
    out = out.resolve()
    if out == Path("/") or out == Path.home() or out == ROOT or ROOT.is_relative_to(out):
        raise BuildError(f"refusing to clean {out}")
    if out.exists():
        if (out / ".git").exists() or (out / "tools" / "build.py").exists():
            raise BuildError(f"refusing to clean {out}: looks like a source tree")
        shutil.rmtree(out)
    out.mkdir(parents=True)


def load_generators():
    mods = []
    for p in sorted((ROOT / "generators").glob("*.py")):
        if p.name.startswith("_"):
            continue
        spec = importlib.util.spec_from_file_location(f"oc_gen_{p.stem}", p)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if not hasattr(mod, "generate"):
            raise BuildError(f"generators/{p.name} has no generate(ctx)")
        mods.append((p.name, mod))
    return mods


_COMMENT_RE = re.compile(r"<!--(?!\[if).*?-->\n?", re.S)
_RAWTEXT_RE = re.compile(r"(<(script|style|pre|textarea)\b.*?</\2>)", re.S | re.I)


def strip_comments(html: str) -> str:
    """Remove HTML comments outside <script>/<style>/<pre>/<textarea>. Source notes stay in
    content/ and generators/ for maintainers; the published pages do not carry them."""
    parts = _RAWTEXT_RE.split(html)
    out = []
    i = 0
    while i < len(parts):
        out.append(_COMMENT_RE.sub("", parts[i]))
        if i + 1 < len(parts):
            out.append(parts[i + 1])       # raw-text element, untouched
            i += 3                         # skip the tag-name capture group
        else:
            i += 1
    return "".join(out)


# Build-time includes: a content fragment may contain <!--oc:include NAME key=value ...-->,
# replaced by the output of components.INCLUDES[NAME](**kwargs).
_INCLUDE_RE = re.compile(r"<!--oc:include\s+([\w-]+)((?:\s+[\w-]+=[\w-]+)*)\s*-->")


def expand_includes(html: str, source: str) -> str:
    def _sub(m):
        fn = components.INCLUDES.get(m.group(1))
        if fn is None:
            raise BuildError(f"{source}: unknown include {m.group(1)!r}; known: {sorted(components.INCLUDES)}")
        kw = dict(kv.split("=", 1) for kv in m.group(2).split())
        return fn(**kw)
    return _INCLUDE_RE.sub(_sub, html)


def render_404(ctx: "Context") -> None:
    """/404.html is served for unknown keys at arbitrary depths, so relative links cannot work
    there. With --base-url the page gets <base href> and root-relative links resolve against it;
    without it, links are relative to the site root (correct for top-level misses only)."""
    body = ('<div class="container section"><div class="prose"><p class="kicker">Page not found</p>'
            '<h1>This page does not exist</h1>'
            '<p class="lede">The link may be mistyped, or the page may have moved. Every page of the '
            'site is reachable from the overview.</p>'
            '<ul><li><a href="/">Home</a></li><li><a href="/campaign/">Campaign overview</a></li>'
            '<li><a href="/campaign/hypotheses/">Hypothesis explorer</a></li>'
            '<li><a href="/cases/">Case studies</a></li><li><a href="/about/">About</a></li></ul></div></div>')
    base = (ctx.base_url.rstrip("/") + "/") if ctx.base_url else None
    html = render_layout(path="/404.html", out_file="404.html", title="Page not found", body_html=body,
                         description="This page does not exist.", section="none", breadcrumb=None,
                         layout="default", og_image=None, body_class="", page_title=None,
                         base_url=None, base_href=base)
    html = rewrite_links(html, "404.html")
    (ctx.out_dir / "404.html").write_text(html, encoding="utf-8")
    ctx.pages["/404.html"] = "build.py"


def stub_body(path: str, title: str) -> str:
    return (f'<div class="container section"><div class="prose"><p class="kicker">In preparation</p>'
            f'<h1>{components.esc(title)}</h1><p class="lede">This page is being written.</p>'
            f'<p><a class="link-arrow" href="/">Back to the overview</a></p></div></div>')


def build(out: Path, strict: bool, base_url: str | None) -> Context:
    safe_clean(out)
    ctx = Context(root=ROOT, out_dir=out.resolve(), base_url=base_url)
    # 1. assets
    shutil.copytree(ROOT / "assets", ctx.out_dir / "assets",
                    ignore=shutil.ignore_patterns(".DS_Store", "*.tmp", "Thumbs.db", "*.svg.html", "MANIFEST.md"))
    # 2. content fragments
    for src in sorted((ROOT / "content").rglob("*.html")):
        rel = src.relative_to(ROOT / "content").as_posix()
        meta, body = parse_front_matter(src.read_text(encoding="utf-8"), src)
        path = "/" + (rel[: -len("index.html")] if rel.endswith("index.html") else rel)
        ctx.render_page(path, meta["title"], body, description=meta["description"],
                        section=meta.get("section", "none"), breadcrumb=meta.get("breadcrumb"),
                        layout=meta.get("layout", "default"), og_image=meta.get("og_image"),
                        body_class=meta.get("body_class", ""), page_title=meta.get("page_title"),
                        stylesheet=meta.get("stylesheet"), source=f"content/{rel}")
    # 3. generators
    for name, mod in load_generators():
        mod.generate(ctx)
    # 4. stubs for planned pages
    runs = ctx.load_json("runs")
    planned = PLANNED_PAGES + [r["page"] for r in runs]
    missing = [p for p in planned if p not in ctx.pages]
    for p in missing:
        title = next((lbl for _, lbl, u in NAV if u == p), None) or p.strip("/").split("/")[-1] or "Home"
        ctx.render_page(p, title, stub_body(p, title), description=f"{title} (in preparation).",
                        section=PLANNED_SECTION.get(p, "campaign" if p.startswith("/campaign/") else
                                                    "cases" if p.startswith("/cases/") else "none"),
                        source="stub")
    if missing:
        msg = f"{len(missing)} planned pages are stubs: " + ", ".join(missing[:8]) + (" …" if len(missing) > 8 else "")
        if strict:
            raise BuildError(msg)
        ctx.warn(msg)
    # 5. 404 page (served by CloudFront/S3 at any path; see README)
    render_404(ctx)
    # 6. strip authoring comments (source notes, slot markers) from every built page
    for f in sorted(ctx.out_dir.rglob("*.html")):
        if f.relative_to(ctx.out_dir).parts[0] == "assets":
            continue
        txt = f.read_text(encoding="utf-8")
        new = strip_comments(txt)
        if new != txt:
            f.write_text(new, encoding="utf-8")
    # 7. checks
    errors = check_site(ctx.out_dir, {ctx.out_path(p).resolve() for p in missing},
                        {ctx.out_path(p).resolve() for p in ctx.pages})
    if errors:
        for e in errors[:200]:
            print(f"build: ERROR: {e}", file=sys.stderr)
        raise BuildError(f"{len(errors)} problems found in the built site")
    n_files = sum(1 for p in ctx.out_dir.rglob("*") if p.is_file())
    print(f"build: ok: {len(ctx.pages)} pages, {n_files} files -> {ctx.out_dir}"
          + (f" ({len(ctx.warnings)} warnings)" if ctx.warnings else ""))
    return ctx


def main():
    ap = argparse.ArgumentParser(description="Build the OmiCairn showcase site.")
    ap.add_argument("--out", default=str(ROOT / "site"), help="output directory (default: site/)")
    ap.add_argument("--strict", action="store_true", help="treat stub pages as errors (use for release)")
    ap.add_argument("--base-url", default=None,
                    help="absolute site URL for og:url/og:image/canonical (optional)")
    a = ap.parse_args()
    try:
        build(Path(a.out), a.strict, a.base_url)
    except BuildError as e:
        print(f"build: FAILED: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
