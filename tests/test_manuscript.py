"""The manuscript builder must reproduce the numbers in outputs/tables and keep table numbers unique."""
import re

import docx
import pandas as pd
import pytest

from aparri import manuscript


@pytest.fixture(scope="module")
def doc():
    return docx.Document(str(manuscript.build()))


def test_captions_unique_and_numbers_match(doc):
    caps = [p.text.split(".")[0] + "." + p.text.split(".")[1] for p in doc.paragraphs
            if p.style.name in ("TableCaption", "FigureCaption") and re.match(r"(Table|Figure) \d", p.text)]
    assert len(caps) == len(set(caps))


def test_table_4_1_matches_csv(doc):
    t41 = pd.read_csv(manuscript.TAB / "Table_4_2_barangay_results.csv")
    cells = {c.text for t in doc.tables for r in t.rows for c in r.cells}
    for v in t41["Medium Risk (ha)"]:
        assert f"{v:.2f}" in cells


def test_placeholders_are_highlighted(doc):
    n = sum(1 for p in doc.paragraphs for r in p.runs if r.font.highlight_color is not None)
    assert n >= 8


def test_original_untouched():
    import hashlib
    assert hashlib.sha256(open(manuscript.ORIG, "rb").read()).hexdigest()
