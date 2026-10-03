"""Read-only helper: clean text blocks out of the department-format manuscript (the original is never modified).

The original docx was converted from PDF, so every printed page carries a pasted running header and long paragraphs are
split at page breaks. `blocks()` drops the headers/empties and re-joins split paragraphs.
"""
from __future__ import annotations

import re
from pathlib import Path

import docx

ORIG = Path("docs/thesis/CE-Project-Manuscript-Format.docx")
_HDR = ("CAGAYAN STATE UNIVERSITY CARIG", "COLLEGE OF ENGINEERING", "AND ARCHITECTURE")
_END = tuple('.?!:;)”"')


def _kind(style: str) -> str:
    return {"Heading 1": "h1", "Heading 2": "h2", "Heading 3": "h3", "List Paragraph": "list"}.get(style, "p")


def blocks(lo: int, hi: int, path: Path = ORIG) -> list[tuple[str, str]]:
    d = docx.Document(str(path))
    out: list[list[str]] = []
    gap = False                      # a pasted page header lies between the previous paragraph and this one
    for i, p in enumerate(d.paragraphs):
        if not lo <= i <= hi:
            continue
        t = re.sub(r"[ \t]+", " ", p.text).strip()
        if t.startswith(_HDR):
            gap = True
            continue
        if not t:
            continue
        k = _kind(p.style.name)
        if (out and gap and k == "p" and out[-1][0] == "p" and not out[-1][1].endswith(_END) and (t[0].islower() or t[0].isdigit() or t[0] in '(“')
                and not t.startswith(("Table ", "Figure "))):
            out[-1][1] += " " + t
        else:
            out.append([k, t])
        gap = False
    return [(k, t) for k, t in out]
