"""Small python-docx toolkit used by manuscript.py (department format: Times New Roman 12, justified, CSU header).

Markup inside text: **bold**, *italic*, [[placeholder]] (yellow highlight = something only the students can supply).
"""
from __future__ import annotations

import copy
import re

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_COLOR_INDEX, WD_TAB_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

FONT = "Times New Roman"
_TOKEN = re.compile(r"(\*\*.+?\*\*|\*[^*\s][^*]*?\*|\[\[.+?\]\])", re.S)


def _set_font(style, size=12, bold=None, italic=None, color=RGBColor(0, 0, 0)):
    style.font.name = FONT
    style.font.size = Pt(size)
    if bold is not None:
        style.font.bold = bold
    if italic is not None:
        style.font.italic = italic
    style.font.color.rgb = color
    rpr = style.element.get_or_add_rPr()
    rf = rpr.find(qn("w:rFonts"))
    if rf is None:
        rf = OxmlElement("w:rFonts")
        rpr.append(rf)
    for a in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rf.set(qn(a), FONT)
    for a in ("w:asciiTheme", "w:hAnsiTheme", "w:cstheme", "w:eastAsiaTheme"):
        if rf.get(qn(a)) is not None:
            del rf.attrib[qn(a)]


def _field(par, instr: str, cached: str = ""):
    """Insert a simple complex field (PAGE, TOC ...) with cached text."""
    def r(kind):
        run = par.add_run()
        el = OxmlElement("w:fldChar")
        el.set(qn("w:fldCharType"), kind)
        run._r.append(el)
        return run
    r("begin")
    run = par.add_run()
    it = OxmlElement("w:instrText")
    it.set(qn("xml:space"), "preserve")
    it.text = f" {instr} "
    run._r.append(it)
    r("separate")
    par.add_run(cached)
    r("end")


class Manuscript:
    def __init__(self):
        self.doc = Document()
        self.captions: list[tuple[str, str]] = []   # (kind, text)
        self.headings: list[tuple[int, str]] = []
        d = self.doc
        st = d.styles
        _set_font(st["Normal"], 12)
        st["Normal"].paragraph_format.space_after = Pt(0)
        for name, size, bold, italic in (("Heading 1", 14, True, False), ("Heading 2", 12, True, False),
                                         ("Heading 3", 12, True, True), ("Title", 14, True, False)):
            _set_font(st[name], size, bold, italic)
        for name in ("Heading 1", "Heading 2", "Heading 3"):
            pf = st[name].paragraph_format
            pf.keep_with_next = True
            pf.space_before = Pt(12)
            pf.space_after = Pt(6)
        st["Heading 1"].paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for nm in ("TableCaption", "FigureCaption"):
            s = st.add_style(nm, 1)
            s.base_style = st["Normal"]
            _set_font(s, 11, False, False)
            s.paragraph_format.space_before = Pt(8)
            s.paragraph_format.space_after = Pt(4)
        st["TableCaption"].paragraph_format.keep_with_next = True
        st["TableCaption"].paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
        st["FigureCaption"].paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
        sec = d.sections[0]
        sec.page_width, sec.page_height = Inches(8.5), Inches(11)
        sec.left_margin, sec.right_margin = Inches(1.5), Inches(1.0)
        sec.top_margin, sec.bottom_margin = Inches(1.1), Inches(1.0)
        self.cur = sec

    # ------------------------------------------------------------------ text
    def runs(self, par, text: str, size: float | None = None, bold=False, italic=False):
        for tok in _TOKEN.split(text):
            if not tok:
                continue
            if tok.startswith("[[") and tok.endswith("]]"):
                r = par.add_run("[" + tok[2:-2] + "]")
                r.font.highlight_color = WD_COLOR_INDEX.YELLOW
                r.bold = True
            elif tok.startswith("**") and tok.endswith("**") and len(tok) > 4:
                r = par.add_run(tok[2:-2])
                r.bold = True
                r.italic = italic or None
            elif tok.startswith("*") and tok.endswith("*") and len(tok) > 2:
                r = par.add_run(tok[1:-1])
                r.italic = True
                r.bold = bold or None
            else:
                r = par.add_run(tok)
                r.bold = bold or None
                r.italic = italic or None
            if size:
                r.font.size = Pt(size)
        return par

    def p(self, text: str, indent=True, align="j", spacing=1.5, after=6, size=None, bold=False, italic=False,
          keep_next=False, left=None):
        par = self.doc.add_paragraph()
        pf = par.paragraph_format
        pf.line_spacing = spacing
        pf.space_after = Pt(after)
        pf.alignment = {"j": WD_ALIGN_PARAGRAPH.JUSTIFY, "l": WD_ALIGN_PARAGRAPH.LEFT, "c": WD_ALIGN_PARAGRAPH.CENTER,
                        "r": WD_ALIGN_PARAGRAPH.RIGHT}[align]
        if indent:
            pf.first_line_indent = Inches(0.5)
        if left is not None:
            pf.left_indent = Inches(left)
        pf.keep_with_next = keep_next
        self.runs(par, text, size, bold, italic)
        return par

    def lst(self, items, numbered=False, spacing=1.15):
        for i, t in enumerate(items, 1):
            par = self.doc.add_paragraph()
            pf = par.paragraph_format
            pf.left_indent = Inches(0.75)
            pf.first_line_indent = Inches(-0.25)
            pf.line_spacing = spacing
            pf.space_after = Pt(4)
            pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            self.runs(par, (f"{i}. " if numbered else "• ") + t)

    def eq(self, text: str):
        par = self.p(text, indent=False, align="c", spacing=1.15, after=8, italic=True)
        return par

    def h(self, text: str, level=2, page_break=False, toc=True):
        if page_break:
            self.page_break()
        par = self.doc.add_heading(level=level)
        if "\n" in text:
            a, b = text.split("\n", 1)
            par.add_run(a).add_break()
            par.add_run(b)
        else:
            par.add_run(text)
        if toc:
            self.headings.append((level, text.replace("\n", " ")))
        return par

    def page_break(self):
        self.doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

    # ------------------------------------------------------------------ tables / figures
    def caption(self, kind: str, text: str):
        par = self.doc.add_paragraph(style="TableCaption" if kind == "Table" else "FigureCaption")
        m = re.match(r"((?:Table|Figure) [\d.A-Z]+\.?)\s*(.*)", text, re.S)
        lab, rest = (m.group(1), m.group(2)) if m else ("", text)
        r = par.add_run(lab + " ")
        r.bold = True
        self.runs(par, rest)
        self.captions.append((kind, text))
        return par

    def table(self, caption: str | None, header: list[str], rows: list[list[str]], widths: list[float] | None = None,
              size=10, note: str | None = None, bold_last=False, align_num=True, first_left=True):
        if caption:
            self.caption("Table", caption)
        t = self.doc.add_table(rows=1, cols=len(header))
        t.style = "Table Grid"
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        t.autofit = False
        for j, htxt in enumerate(header):
            c = t.rows[0].cells[j]
            c.text = ""
            self.runs(c.paragraphs[0], htxt, size, bold=True)
            c.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
            tcPr = c._tc.get_or_add_tcPr()
            sh = OxmlElement("w:shd")
            sh.set(qn("w:val"), "clear")
            sh.set(qn("w:color"), "auto")
            sh.set(qn("w:fill"), "D9D9D9")
            tcPr.append(sh)
        trPr = t.rows[0]._tr.get_or_add_trPr()
        th = OxmlElement("w:tblHeader")
        th.set(qn("w:val"), "true")
        trPr.append(th)
        for i, row in enumerate(rows):
            cells = t.add_row().cells
            for j, v in enumerate(row):
                cells[j].text = ""
                par = cells[j].paragraphs[0]
                self.runs(par, str(v), size, bold=(bold_last and i == len(rows) - 1))
                is_num = align_num and re.fullmatch(r"[-+−]?[\d.,]+%?|—|-", str(v).strip() or "x") is not None
                par.alignment = (WD_ALIGN_PARAGRAPH.CENTER if is_num or (j > 0 and len(str(v)) < 12)
                                 else WD_ALIGN_PARAGRAPH.LEFT)
        for row in t.rows:
            trPr = row._tr.get_or_add_trPr()
            cs = OxmlElement("w:cantSplit")
            trPr.append(cs)
            for j, c in enumerate(row.cells):
                if widths:
                    c.width = Inches(widths[j])
                for par in c.paragraphs:
                    par.paragraph_format.space_after = Pt(2)
                    par.paragraph_format.space_before = Pt(2)
                    par.paragraph_format.line_spacing = 1.0
        if note:
            self.p(note, indent=False, spacing=1.0, after=10, size=10, italic=False)
        else:
            self.p("", indent=False, spacing=1.0, after=6)
        return t

    def figure(self, path, caption: str, width=5.9):
        par = self.doc.add_paragraph()
        par.alignment = WD_ALIGN_PARAGRAPH.CENTER
        par.paragraph_format.keep_with_next = True
        par.paragraph_format.space_before = Pt(6)
        par.add_run().add_picture(str(path), width=Inches(width))
        self.caption("Figure", caption)

    # ------------------------------------------------------------------ sections / header / footer
    def new_section(self, numfmt: str | None = None, restart=False, header=True, start_new_page=True):
        sec = self.doc.add_section(WD_SECTION.NEW_PAGE if start_new_page else WD_SECTION.CONTINUOUS)
        self.cur = sec
        self._sectpr_pg(sec, numfmt, restart)
        self._header_footer(sec, header)
        return sec

    def first_section(self, header=False):
        sec = self.doc.sections[0]
        self.cur = sec
        self._header_footer(sec, header)

    @staticmethod
    def _sectpr_pg(sec, numfmt, restart):
        pg = sec._sectPr.find(qn("w:pgNumType"))
        if pg is None:
            pg = OxmlElement("w:pgNumType")
            nxt = next((c for c in sec._sectPr if c.tag in (qn("w:cols"), qn("w:formProt"), qn("w:vAlign"),
                                                              qn("w:noEndnote"), qn("w:titlePg"), qn("w:textDirection"),
                                                              qn("w:bidi"), qn("w:rtlGutter"), qn("w:docGrid"))), None)
            if nxt is not None:
                nxt.addprevious(pg)
            else:
                sec._sectPr.append(pg)
        if numfmt:
            pg.set(qn("w:fmt"), numfmt)
        if restart:
            pg.set(qn("w:start"), "1")

    def _header_footer(self, sec, header: bool):
        sec.header.is_linked_to_previous = False
        sec.footer.is_linked_to_previous = False
        hp = sec.header.paragraphs[0]
        for r in list(hp.runs):
            r._r.getparent().remove(r._r)
        fp = sec.footer.paragraphs[0]
        for r in list(fp.runs):
            r._r.getparent().remove(r._r)
        if header:
            hp.alignment = WD_ALIGN_PARAGRAPH.LEFT
            hp.paragraph_format.tab_stops.add_tab_stop(Inches(6.0), WD_TAB_ALIGNMENT.RIGHT)
            r = hp.add_run("CAGAYAN STATE UNIVERSITY CARIG CAMPUS\nCOLLEGE OF ENGINEERING AND ARCHITECTURE")
            r.font.size = Pt(9)
            r.bold = True
            hp.add_run("\t")
            _field(hp, "PAGE", "1")
            pPr = hp._p.get_or_add_pPr()
            bd = OxmlElement("w:pBdr")
            b = OxmlElement("w:bottom")
            for k, v in (("val", "single"), ("sz", "6"), ("space", "1"), ("color", "000000")):
                b.set(qn("w:" + k), v)
            bd.append(b)
            ps = pPr.find(qn("w:pStyle"))
            (ps.addnext(bd) if ps is not None else pPr.insert(0, bd))

    # ------------------------------------------------------------------ TOC fields (cached text, no page numbers)
    def toc(self, instr: str, entries: list[tuple[int, str]]):
        """One complex field spanning several paragraphs. Word fills in page numbers when the field is updated."""
        n = len(entries)
        for i, (lvl, txt) in enumerate(entries):
            par = self.doc.add_paragraph()
            pf = par.paragraph_format
            pf.left_indent = Inches(0.3 * (lvl - 1))
            pf.line_spacing = 1.0
            pf.space_after = Pt(3)
            if i == 0:
                for kind, text in (("begin", None), ("instr", instr), ("separate", None)):
                    run = par.add_run()
                    if kind == "instr":
                        it = OxmlElement("w:instrText")
                        it.set(qn("xml:space"), "preserve")
                        it.text = f" {text} "
                        run._r.append(it)
                    else:
                        fc = OxmlElement("w:fldChar")
                        fc.set(qn("w:fldCharType"), kind)
                        run._r.append(fc)
            par.add_run(txt)
            if i == n - 1:
                run = par.add_run()
                fc = OxmlElement("w:fldChar")
                fc.set(qn("w:fldCharType"), "end")
                run._r.append(fc)

    def update_fields_on_open(self):
        st = self.doc.settings.element
        uf = OxmlElement("w:updateFields")
        uf.set(qn("w:val"), "true")
        comp = st.find(qn("w:compat"))
        (comp.addprevious(uf) if comp is not None else st.append(uf))

    def copy_table(self, src_tbl):
        """Deep-copy a table element from another document (keeps shading); fonts are normalised."""
        el = copy.deepcopy(src_tbl._tbl)
        self.doc.element.body.insert(len(self.doc.element.body) - 1, el)
        return el
