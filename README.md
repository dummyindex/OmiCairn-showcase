# OmiCairn showcase

**Website: https://omicairn.github.io/**

A static website that presents what OmiCairn produced: the 57-run
neurodegeneration research campaign (136 hypotheses evaluated, 15 supported,
every null, negative and untestable result published), the three case studies
of the OmiCairn manuscript (in preparation), how the system works, and the
platform it grew from.

## OmiCairn repositories

This repository is one of five released with the OmiCairn manuscript:

| Repository | Contents | License |
|---|---|---|
| [`OmiCairn`](https://github.com/dummyindex/OmiCairn) | Academic code release: single-machine implementation of the OmiCairn research pipeline, with the benchmark and case-study materials | MIT |
| [`OmiCairn-engineering`](https://github.com/dummyindex/OmiCairn-engineering) | Engineering release: source code of the OmiCairn web platform (web interface, backend, computation worker and agent runner) | MIT |
| [`OmiCairn-early`](https://github.com/dummyindex/OmiCairn-early) | Early-stage research release: the earliest research prototype of OmiCairn (analysis trees of containerized function blocks) | MIT |
| [`OmiCairn-neurodegeneration-campaign`](https://github.com/dummyindex/OmiCairn-neurodegeneration-campaign) | Research outputs: hypothesis-level outcomes and final reports of the 57-run neurodegeneration research campaign | CC BY 4.0 |
| [`OmiCairn-showcase`](https://github.com/dummyindex/OmiCairn-showcase) (this repository) | Source of the showcase website ([live site](https://omicairn.github.io/)) | MIT (code), CC BY 4.0 (content) |

The site is plain HTML, CSS and JavaScript. It makes no external requests at
runtime (no CDNs, web fonts, analytics or iframes), and every link between pages is
relative, so it works on GitHub Pages, from any S3 prefix and straight from `file://`.

## Layout

```
content/       page fragments (HTML with a front-matter comment), one per page
generators/    Python modules that render data-driven pages (generate(ctx))
assets/        CSS, JS, images, data files, PDF reports (copied as-is)
data/          prepared campaign data and markdown reports (build inputs)
tools/         build.py, policy.py, components.py, gen_styleguide.py
site/          build output (not committed)
CONTRACT.md    the page/component/data contract for contributors
```

## Build

Requires Python 3.10+ with `markdown`.

```bash
python3 tools/build.py                 # -> site/
python3 tools/build.py --out /tmp/x    # build somewhere else
python3 tools/build.py --strict        # release build: fail if any planned page is a stub
open site/index.html                   # review locally from file://
```

The build fails (exit code 1) on broken internal links or images, missing anchors,
external resources, un-rewritten root-relative links, images without `alt`, pages
without exactly one `<h1>`, and release-policy patterns (see `tools/policy.py`).
`data/` and `assets/{data,reports,img}` are pre-generated from the public campaign
release and committed.

## Deploy

### GitHub Pages (live site)

The live site is built from this repository's `main` branch by the workflow in
[OmiCairn/omicairn.github.io](https://github.com/OmiCairn/omicairn.github.io), which
publishes it at https://omicairn.github.io/ (on demand and once a day). After pushing
here, run that workflow to publish immediately:
`gh workflow run deploy.yml -R OmiCairn/omicairn.github.io`.

### Alternative: S3 + CloudFront

```bash
python3 tools/build.py --strict --base-url https://<your-domain>/
aws s3 sync site/ s3://<bucket>/ --delete \
  --exclude '*.webp' --cache-control 'public, max-age=300'
# aws s3 takes Content-Type from the host's MIME tables, which often lack .webp:
aws s3 cp site/ s3://<bucket>/ --recursive --exclude '*' --include '*.webp' \
  --content-type image/webp --metadata-directive REPLACE --cache-control 'public, max-age=86400'
```

- Set the CloudFront distribution's **default root object** to `index.html`.
- All internal links point at explicit `.../index.html` files, so the site does not
  need directory-index resolution. If you want pretty URLs such as `/campaign/` to
  work when typed by hand, add a CloudFront Function (viewer request) that appends
  `index.html` to URIs ending in `/`.
- `--base-url` adds absolute `og:url`, `og:image` and `canonical` tags (without it,
  `og:image` is omitted), and a `<base href>` on `/404.html` so its links work at any depth.
  Use it for releases.
- Error page: the build writes `/404.html`. With an S3 REST origin, add CloudFront
  **custom error responses** for 403 and 404 → response page `/404.html`, HTTP status 404
  (S3 returns 403 for missing keys when the bucket is private). With S3 website hosting,
  set the bucket's error document to `404.html` instead.
- Check after the upload that `.webp`, `.svg`, `.mp4`, `.pdf`, `.csv` and `.json` files carry
  the right `Content-Type` (`image/webp`, `image/svg+xml`, `video/mp4`, `application/pdf`,
  `text/csv`, `application/json`).

## Licenses

- Code (tools, generators, CSS, JS, templates): **MIT**.
- Content (page text, data, reports, figures): **CC BY 4.0**.

See `LICENSE`. Questions and corrections: please open a GitHub issue on the
OmiCairn repository.
