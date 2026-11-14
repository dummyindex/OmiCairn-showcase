"""Release-policy checks run by build.py on every built text file.

Generic patterns live here. Additional private patterns (e.g. names that must never be
published) are read from tools/policy_terms.local when that file exists; it is gitignored
and holds one "name<TAB>regex" per line. The build fails on any hit.
"""
from __future__ import annotations

import re
from pathlib import Path

POLICY_PATTERNS: list[tuple[str, re.Pattern]] = [
    # The first version's former product name must not appear anywhere on the site.
    ("former product name", re.compile(r"(?i)rag[\s_-]*omics")),
    ("run timestamp", re.compile(r"\b20\d{6}[-_]\d{4,6}\b")),
    ("ISO datetime", re.compile(r"\b20\d\d-\d\d-\d\dT\d\d:\d\d")),
    ("workspace path", re.compile(r"workspaces/")),
    ("local path", re.compile(r"/Users/|/home/[a-z]")),
]

_LOCAL = Path(__file__).with_name("policy_terms.local")
if _LOCAL.exists():
    for line in _LOCAL.read_text(encoding="utf-8").splitlines():
        if line.strip() and not line.startswith("#"):
            name, rx = line.split("\t", 1)
            POLICY_PATTERNS.append((name.strip(), re.compile(rx.strip())))


def policy_violations(text: str, path: str | None = None) -> list[tuple[str, str]]:
    """Return [(rule, snippet)] for every blocking pattern found in ``text``.
    ``path`` (relative to the site root) is accepted for callers that report it."""
    hits = []
    for name, pat in POLICY_PATTERNS:
        for m in pat.finditer(text):
            s = max(0, m.start() - 40)
            hits.append((name, text[s:m.end() + 40].replace("\n", " ")))
    return hits
