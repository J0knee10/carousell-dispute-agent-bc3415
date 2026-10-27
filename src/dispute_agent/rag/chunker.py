"""Split the Carousell policy pages into citable clauses.

Each policy file in data/policy/ starts with its URL on line 1 and its title on
line 2, followed by the article text as copied from the help centre. Sections
are found from heading-like lines; short sections are merged into the previous
one so every clause has enough context, and long ones are split.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from ..config import load_config, path
from ..schemas import RetrievedClause

DOC_CODES = {
    "buyer_protection_refund_policy": "BPR",
    "what_is_buyer_protection": "WBP",
    "dispute_process_overview": "DPO",
    "refund_return_request": "RRR",
}

IMAGE_LINE = re.compile(r"\.(png|jpe?g|gif|webp)\s*$", re.IGNORECASE)
NOT_HEADINGS = ("updated as of", "read up more", "read more", "refer to")
BULLET_START = re.compile(r"^([✘•*\-–]|\d+\.|[a-z]\.|[ivx]+\.)\s", re.IGNORECASE)


@dataclass
class PolicyDoc:
    stem: str
    code: str
    title: str
    url: str
    lines: list[str]


@dataclass
class Clause:
    clause_id: str
    doc_title: str
    url: str
    section: str
    body_lines: list[str] = field(default_factory=list)

    @property
    def text(self) -> str:
        return "\n".join(self.body_lines).strip()

    def as_retrieved(self) -> RetrievedClause:
        return RetrievedClause(
            clause_id=self.clause_id, doc_title=self.doc_title, section=self.section, url=self.url, text=self.text
        )

    def embedding_text(self) -> str:
        return f"{self.doc_title} | {self.section}\n{self.text}"


def doc_code(stem: str) -> str:
    if stem in DOC_CODES:
        return DOC_CODES[stem]
    return "".join(part[0] for part in stem.split("_") if part).upper()[:4] or "DOC"


def load_docs(policy_dir: Path | None = None) -> list[PolicyDoc]:
    policy_dir = policy_dir or path("rag.policy_dir")
    docs = []
    for file in sorted(policy_dir.glob("*.txt")):
        lines = file.read_text(encoding="utf-8").splitlines()
        if len(lines) < 3 or not lines[0].startswith("http"):
            raise ValueError(f"{file.name}: first line must be the page URL, second line the title")
        docs.append(
            PolicyDoc(stem=file.stem, code=doc_code(file.stem), url=lines[0].strip(), title=lines[1].strip(), lines=lines[2:])
        )
    return docs


def is_heading(raw: str) -> bool:
    if not raw.strip() or raw[:1].isspace():
        return False  # indented lines are list items in the copied pages
    t = raw.strip()
    if len(t) > 60 or len(t.split()) > 9:
        return False
    if t.endswith((".", ":", ",", ";")) or "$" in t or BULLET_START.match(t):
        return False
    if t.startswith("*"):
        return t.endswith("*")  # "*Advisory*" is a heading, "*only applicable..." a footnote
    if t.lower().startswith(NOT_HEADINGS):
        return False
    first = t[0]
    return first.isupper() or not first.isalnum()  # allows emoji-led headings like "📝 How to..."


def _sections(doc: PolicyDoc) -> list[tuple[str, list[str]]]:
    sections: list[tuple[str, list[str]]] = []
    heading_parts: list[str] = []
    body: list[str] = []
    for raw in doc.lines:
        if not raw.strip() or IMAGE_LINE.search(raw.strip()):
            continue
        if is_heading(raw):
            if body:
                sections.append((" > ".join(heading_parts) or "Introduction", body))
                heading_parts, body = [], []
            heading_parts.append(raw.strip())
            heading_parts = heading_parts[-2:]
        else:
            body.append(raw.rstrip())
    if body:
        sections.append((" > ".join(heading_parts) or "Introduction", body))
    return sections


def chunk_doc(doc: PolicyDoc, max_chars: int, min_chars: int) -> list[Clause]:
    clauses: list[Clause] = []

    def new_clause(section: str) -> Clause:
        c = Clause(clause_id=f"{doc.code}-{len(clauses) + 1:02d}", doc_title=doc.title, url=doc.url, section=section)
        clauses.append(c)
        return c

    for section, body in _sections(doc):
        size = sum(len(line) + 1 for line in body)
        prev = clauses[-1] if clauses else None
        if prev and size < min_chars and len(prev.text) + size <= max_chars:
            prev.body_lines.append(f"[{section}]")
            prev.body_lines.extend(body)
            continue
        current = new_clause(section)
        for line in body:
            if current.body_lines and len(current.text) + len(line) > max_chars:
                current = new_clause(f"{section} (cont.)")
            current.body_lines.append(line)
    return clauses


@lru_cache(maxsize=4)
def load_clauses(policy_dir: str | None = None) -> tuple[Clause, ...]:
    cfg = load_config()["rag"]
    docs = load_docs(Path(policy_dir) if policy_dir else None)
    out: list[Clause] = []
    for doc in docs:
        out.extend(chunk_doc(doc, cfg["chunk_max_chars"], cfg["chunk_min_chars"]))
    return tuple(out)


def clauses_by_id() -> dict[str, Clause]:
    return {c.clause_id: c for c in load_clauses()}


def find_clause_id(doc_stem: str, contains: str) -> str | None:
    """Find the clause in one document whose text contains a phrase (case-insensitive)."""
    code = doc_code(doc_stem)
    needle = contains.lower()
    for c in load_clauses():
        if c.clause_id.startswith(code + "-") and needle in (c.section + "\n" + c.text).lower():
            return c.clause_id
    return None
