"""Low-level STEP (ISO 10303-21) entity-graph parser.

This is deliberately minimal and geometry-free: it reads `#id=TYPE(args);`
records from the DATA section into a graph of typed records with parsed
arguments (entity refs, reals, ints, strings, enums, lists, '*'). Both kernels
build on this; they differ only in how they *interpret* the graph, not in how
they tokenize it.
"""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class Ref:
    id: int


@dataclass
class Record:
    id: int
    type: str
    args: list


_HEAD_RE = re.compile(r"^#(\d+)\s*=\s*([A-Za-z0-9_]+)\s*\((.*)\)\s*$", re.DOTALL)


def _split_statements(text: str) -> list[str]:
    """Split DATA text into statements at ';' outside strings/parens."""
    out, depth, cur, in_str = [], 0, [], False
    i = 0
    while i < len(text):
        c = text[i]
        if in_str:
            cur.append(c)
            if c == "'":
                if i + 1 < len(text) and text[i + 1] == "'":
                    cur.append(text[i + 1]); i += 2; continue
                in_str = False
        elif c == "'":
            in_str = True; cur.append(c)
        elif c == "(":
            depth += 1; cur.append(c)
        elif c == ")":
            depth -= 1; cur.append(c)
        elif c == ";" and depth == 0:
            out.append("".join(cur).strip()); cur = []
        else:
            cur.append(c)
        i += 1
    tail = "".join(cur).strip()
    if tail:
        out.append(tail)
    return out


def _split_top(s: str) -> list[str]:
    """Split a comma-separated arg string at top nesting level only."""
    out, depth, cur, in_str = [], 0, [], False
    i = 0
    while i < len(s):
        c = s[i]
        if in_str:
            cur.append(c)
            if c == "'":
                # STEP escapes a quote by doubling it
                if i + 1 < len(s) and s[i + 1] == "'":
                    cur.append(s[i + 1]); i += 2; continue
                in_str = False
        elif c == "'":
            in_str = True; cur.append(c)
        elif c == "(":
            depth += 1; cur.append(c)
        elif c == ")":
            depth -= 1; cur.append(c)
        elif c == "," and depth == 0:
            out.append("".join(cur)); cur = []
        else:
            cur.append(c)
        i += 1
    if cur:
        out.append("".join(cur))
    return [t.strip() for t in out]


def _parse_arg(tok: str):
    tok = tok.strip()
    if tok == "" or tok == "$":
        return None
    if tok == "*":
        return "*"
    if tok.startswith("#"):
        return Ref(int(tok[1:]))
    if tok.startswith("(") and tok.endswith(")"):
        inner = tok[1:-1].strip()
        if inner == "":
            return []
        return [_parse_arg(t) for t in _split_top(inner)]
    if tok.startswith("'") and tok.endswith("'"):
        return tok[1:-1].replace("''", "'")
    if tok.startswith(".") and tok.endswith("."):
        e = tok[1:-1]
        if e == "T":
            return True
        if e == "F":
            return False
        return ("ENUM", e)
    # numeric
    try:
        if any(ch in tok for ch in ".eE") and not tok.lstrip("+-").startswith("0x"):
            return float(tok)
        return int(tok)
    except ValueError:
        return tok


def parse_step(text: str) -> dict[int, Record]:
    """Parse STEP text into {record_id: Record}. Only the DATA section matters."""
    # isolate DATA section if present
    if "DATA;" in text:
        text = text.split("DATA;", 1)[1]
    if "ENDSEC;" in text:
        text = text.split("ENDSEC;", 1)[0]
    # strip block comments
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    records: dict[int, Record] = {}
    for stmt in _split_statements(text):
        m = _HEAD_RE.match(stmt)
        if not m:
            continue
        rid = int(m.group(1))
        rtype = m.group(2)
        body = m.group(3).strip()
        args = _split_top(body) if body else []
        records[rid] = Record(rid, rtype, [_parse_arg(a) for a in args])
    return records


def find_roots(records: dict[int, Record]) -> list[int]:
    """Return record ids of solid roots (MANIFOLD_SOLID_BREP / BREP_WITH_VOIDS)."""
    return [r.id for r in records.values()
            if r.type in ("MANIFOLD_SOLID_BREP", "BREP_WITH_VOIDS",
                          "ADVANCED_BREP_SHAPE_REPRESENTATION")]


def referenced_ids(records: dict[int, Record]) -> set[int]:
    """All record ids referenced by some other record (to find orphans)."""
    used: set[int] = set()

    def walk(v):
        if isinstance(v, Ref):
            used.add(v.id)
        elif isinstance(v, list):
            for x in v:
                walk(x)

    for r in records.values():
        walk(r.args)
    return used


# ------------------------------------------------------------------------------
# Serialization (records -> STEP text). Used by the perturbation/fixture stages
# to emit modified copies.
# ------------------------------------------------------------------------------
def _fmt(v) -> str:
    if isinstance(v, Ref):
        return f"#{v.id}"
    if isinstance(v, bool):
        return ".T." if v else ".F."
    if v is None:
        return "$"
    if isinstance(v, str):
        if v == "*":
            return "*"
        return "'" + v.replace("'", "''") + "'"
    if isinstance(v, tuple) and len(v) == 2 and v[0] == "ENUM":
        return f".{v[1]}."
    if isinstance(v, list):
        return "(" + ",".join(_fmt(x) for x in v) + ")"
    if isinstance(v, float):
        if v == int(v):
            return f"{v:.1f}"
        return repr(v)
    if isinstance(v, int):
        return str(v)
    return str(v)


def serialize(records: dict[int, Record], name: str = "brep-sentinel",
              extra_lines: list[str] | None = None) -> str:
    body_lines = []
    for rid in sorted(records):
        r = records[rid]
        args = ",".join(_fmt(a) for a in r.args)
        body_lines.append(f"#{rid}={r.type}({args});")
    if extra_lines:
        body_lines.extend(extra_lines)
    header = (
        "ISO-10303-21;\n"
        "HEADER;\n"
        "FILE_DESCRIPTION((''),'2;1');\n"
        f"FILE_NAME('{name}','2026-08-31T00:00:00',(''),(''),"
        "'brep-sentinel-writer','brep-sentinel','');\n"
        "FILE_SCHEMA(('AUTOMOTIVE_DESIGN'));\n"
        "ENDSEC;\nDATA;\n"
    )
    return header + "\n".join(body_lines) + "\nENDSEC;\nEND-ISO-10303-21;\n"


def max_id(records: dict[int, Record]) -> int:
    return max(records) if records else 0
