"""Small helpers to edit the report in place with python-docx, keeping its styles."""
from __future__ import annotations

import copy

from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph


def body_items(doc):
    for el in doc.element.body.iterchildren():
        tag = el.tag.split("}")[1]
        if tag == "p":
            yield Paragraph(el, doc._body)
        elif tag == "tbl":
            yield Table(el, doc._body)


def _norm(s: str) -> str:
    return " ".join(s.split())  # also folds non-breaking spaces and tabs


def para(doc, start: str, style: str | None = None) -> Paragraph:
    hits = [p for p in doc.paragraphs if _norm(p.text).startswith(_norm(start)) and (style is None or p.style.name == style)]
    assert len(hits) == 1, (start, len(hits))
    return hits[0]


def table_after(doc, anchor_text: str, nth: int = 0) -> Table:
    """The nth table after the paragraph that starts with anchor_text."""
    seen = False
    count = 0
    for item in body_items(doc):
        if isinstance(item, Paragraph) and _norm(item.text).startswith(_norm(anchor_text)):
            seen = True
        elif seen and isinstance(item, Table):
            if count == nth:
                return item
            count += 1
    raise AssertionError(f"no table after {anchor_text!r}")


def set_runs(p: Paragraph, parts) -> Paragraph:
    """parts: str, or list of (text, bold). Keeps the first run's formatting."""
    if isinstance(parts, str):
        parts = [(parts, None)]
    runs = p.runs
    base = copy.deepcopy(runs[0]._r) if runs else None
    for r in runs:
        r._r.getparent().remove(r._r)
    for text, bold in parts:
        if base is not None:
            r_el = copy.deepcopy(base)
            for t in r_el.findall(qn("w:t")):
                r_el.remove(t)
            p._p.append(r_el)
            from docx.text.run import Run

            run = Run(r_el, p)
            run.text = text
        else:
            run = p.add_run(text)
        if bold is not None:
            run.bold = bold
    return p


def set_cell(table: Table, row: int, col: int, parts) -> None:
    cell = table.rows[row].cells[col]
    ps = cell.paragraphs
    for extra in ps[1:]:
        extra._p.getparent().remove(extra._p)
    set_runs(ps[0], parts)


def set_row(table: Table, row: int, values) -> None:
    for i, v in enumerate(values):
        if v is not None:
            set_cell(table, row, i, v)


def resize_rows(table: Table, n: int, template_row: int = -1) -> None:
    """Make the table have n rows (header included) by copying or deleting body rows."""
    rows = table._tbl.findall(qn("w:tr"))
    while len(rows) < n:
        new = copy.deepcopy(rows[template_row])
        rows[-1].addnext(new)
        rows = table._tbl.findall(qn("w:tr"))
    while len(rows) > n:
        rows[-1].getparent().remove(rows[-1])
        rows = table._tbl.findall(qn("w:tr"))


def insert_paragraph_after(anchor, template: Paragraph, parts) -> Paragraph:
    """Copy template (for its style) after anchor (a Paragraph or Table) and set its text."""
    new = copy.deepcopy(template._p)
    anchor_el = anchor._p if isinstance(anchor, Paragraph) else anchor._tbl
    anchor_el.addnext(new)
    p = Paragraph(new, template._parent)
    set_runs(p, parts)
    return p


def insert_table_after(anchor, template: Table, rows) -> Table:
    new = copy.deepcopy(template._tbl)
    anchor_el = anchor._p if isinstance(anchor, Paragraph) else anchor._tbl
    anchor_el.addnext(new)
    t = Table(new, template._parent)
    resize_rows(t, len(rows))
    for i, values in enumerate(rows):
        set_row(t, i, values)
    return t


def remove(item) -> None:
    el = item._p if isinstance(item, Paragraph) else item._tbl
    el.getparent().remove(el)


def update_fields_on_open(doc) -> None:
    settings = doc.settings.element
    el = settings.find(qn("w:updateFields"))
    if el is None:
        el = settings.makeelement(qn("w:updateFields"), {})
        settings.append(el)
    el.set(qn("w:val"), "true")


def set_widths(table: Table, inches: list[float]) -> None:
    """Set column widths (grid and every cell) so Word and Google Docs both honour them."""
    from docx.shared import Inches

    grid = table._tbl.tblGrid
    for gc, w in zip(grid.findall(qn("w:gridCol")), inches):
        gc.set(qn("w:w"), str(int(w * 1440)))
    for row in table.rows:
        for cell, w in zip(row.cells, inches):
            cell.width = Inches(w)


def keep_columns(table: Table, n: int) -> None:
    """Drop every column after the first n (grid and cells); the table has no merged cells."""
    for gc in table._tbl.tblGrid.findall(qn("w:gridCol"))[n:]:
        gc.getparent().remove(gc)
    for tr in table._tbl.findall(qn("w:tr")):
        for tc in tr.findall(qn("w:tc"))[n:]:
            tr.remove(tc)


def stripe_rows(table: Table, fill: str = "F2F5F9") -> None:
    """Shade every second body row (2, 4, ...) like the report's other tables; leave the header as it is."""
    for i, row in enumerate(table.rows[1:], start=1):
        for cell in row.cells:
            tc_pr = cell._tc.get_or_add_tcPr()
            for shd in tc_pr.findall(qn("w:shd")):
                tc_pr.remove(shd)
            if i % 2 == 0:
                shd = tc_pr.makeelement(qn("w:shd"), {qn("w:val"): "clear", qn("w:color"): "auto", qn("w:fill"): fill})
                tc_pr.append(shd)
