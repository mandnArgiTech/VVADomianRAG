"""Markdown masking, math preservation, and small text helpers for chunkers."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

_BARE_MERMAID_STARTERS = re.compile(
    r"^(?:graph\s+(?:TD|TB|BT|RL|LR)|sequenceDiagram|classDiagram|stateDiagram"
    r"|erDiagram|gantt|pie|flowchart|journey|gitGraph|mindmap|timeline|quadrantChart"
    r"|sankey|xychart|block-beta|packet-beta|kanban|architecture-beta)\b",
    re.MULTILINE,
)

_DIAGRAM_TYPE_HINTS = {
    "graph": "Mermaid Flowchart",
    "flowchart": "Mermaid Flowchart",
    "sequencediagram": "Mermaid Sequence Diagram",
    "classdiagram": "Mermaid Class Diagram",
    "statediagram": "Mermaid State Diagram",
    "erdiagram": "Mermaid ER Diagram",
    "gantt": "Mermaid Gantt Chart",
    "pie": "Mermaid Pie Chart",
    "journey": "Mermaid User Journey",
    "gitgraph": "Mermaid Git Graph",
    "mindmap": "Mermaid Mind Map",
    "timeline": "Mermaid Timeline",
    "sankey": "Mermaid Sankey Diagram",
    "xychart": "Mermaid XY Chart",
    "@startuml": "PlantUML Diagram",
    "@startmindmap": "PlantUML Mind Map",
    "@startgantt": "PlantUML Gantt",
}


def _detect_diagram_type(block_text: str) -> str:
    """Return a human-readable diagram type label or empty string."""
    first_line = block_text.strip().split("\n", 1)[0].strip().lower()
    for opener in ("```mermaid", "```plantuml"):
        if first_line.startswith(opener):
            first_line = block_text.strip().split("\n", 2)[1].strip().lower() if "\n" in block_text else ""
            break
    first_token = re.split(r"[\s{(\[]", first_line, 1)[0].rstrip(":;").lower() if first_line else ""
    return _DIAGRAM_TYPE_HINTS.get(first_token, "")


@dataclass
class _MaskedBlock:
    text: str
    diagram_type: str


def _mask_markdown_fences_and_tables(text: str) -> Tuple[str, List[_MaskedBlock]]:
    """Replace fenced blocks, HTML diagram wrappers, bare Mermaid, and pipe-tables with placeholders."""
    vault: List[_MaskedBlock] = []

    def stash(m: re.Match, force_type: str = "") -> str:
        raw = m.group(0)
        dtype = force_type or _detect_diagram_type(raw)
        vault.append(_MaskedBlock(text=raw, diagram_type=dtype))
        return f"\n<<BLOCK{len(vault) - 1}>>\n"

    t = re.sub(r"(?ms)^```.*?^```", stash, text)

    t = re.sub(
        r"(?ms)<div\s[^>]*class\s*=\s*[\"'](?:mermaid|plantuml)[\"'][^>]*>.*?</div>",
        lambda m: stash(m, "Mermaid Diagram (HTML)"),
        t,
    )
    t = re.sub(
        r"(?ms)<details[^>]*>.*?</details>",
        lambda m: stash(m, "HTML Details Block"),
        t,
    )

    matches = list(_BARE_MERMAID_STARTERS.finditer(t))
    for m in reversed(matches):
        block_start = m.start()
        rest = t[block_start:]
        lines = rest.split("\n")
        block_lines = [lines[0]]
        for ln in lines[1:]:
            stripped = ln.strip()
            if not stripped:
                block_lines.append(ln)
                continue
            if stripped.startswith("```") or re.match(r"^#{1,6}\s", stripped):
                break
            block_lines.append(ln)
        block_text = "\n".join(block_lines).rstrip()
        dtype = _detect_diagram_type(block_text) or "Bare Diagram Block"
        vault.append(_MaskedBlock(text=block_text, diagram_type=dtype))
        placeholder = f"\n<<BLOCK{len(vault) - 1}>>\n"
        t = t[:block_start] + placeholder + t[block_start + len(block_text) :]

    t = re.sub(r"(?ms)(?:^\|[^\n]+\n)+", lambda m: stash(m, ""), t)
    return t, vault


def _unmask_markdown_with_meta(
    s: str, vault: List[_MaskedBlock]
) -> Tuple[str, bool, str]:
    """Restore placeholders. Returns (text, has_diagram, diagram_type_label)."""
    has_diagram = False
    diagram_types: List[str] = []
    for i, blk in enumerate(vault):
        placeholder = f"<<BLOCK{i}>>"
        if placeholder in s:
            if blk.diagram_type:
                has_diagram = True
                if blk.diagram_type not in diagram_types:
                    diagram_types.append(blk.diagram_type)
            s = s.replace(placeholder, blk.text)
    label = ", ".join(diagram_types) if diagram_types else ""
    if has_diagram and label:
        s = f"[Metadata: This chunk contains a {label}]\n\n{s}"
    return s, has_diagram, label


def _unmask_markdown(s: str, vault: List[_MaskedBlock]) -> str:
    """Backward-compatible unmask (used by callers that don't need diagram metadata)."""
    for i, blk in enumerate(vault):  # pragma: no cover
        s = s.replace(f"<<BLOCK{i}>>", blk.text)  # pragma: no cover
    return s  # pragma: no cover


def _extract_release_date_near_version(body: str) -> str:
    m = re.search(
        r"(?i)(?:released?|published|date)[:.\s]+(\d{4}-\d{2}-\d{2}|\d{1,2}\s+\w+\s+\d{4}|\w+\s+\d{1,2},?\s+\d{4})",
        body[:2500],
    )
    return m.group(1).strip() if m else ""


def _ts_comment_prefix(content: str, start_byte: int, max_lines: int = 20) -> str:
    """Prepend up to `max_lines` of // or /* */ comments immediately above node."""
    if start_byte <= 0:
        return ""
    prefix = content[:start_byte]
    lines = prefix.splitlines()
    if not lines:
        return ""  # pragma: no cover
    buf: List[str] = []
    i = len(lines) - 1
    lines_seen = 0
    while i >= 0 and lines_seen < max_lines:
        ln = lines[i].rstrip()
        stripped = ln.lstrip()
        if not stripped:
            i -= 1  # pragma: no cover
            continue  # pragma: no cover
        if stripped.startswith("//"):
            buf.append(ln)
            lines_seen += 1
            i -= 1
            continue
        if "*/" in stripped or stripped.startswith("/*") or stripped.startswith("*"):
            buf.append(ln)
            lines_seen += 1
            i -= 1
            continue
        break
    if not buf:
        return ""
    return "\n".join(reversed(buf)) + "\n"


def _file_preamble_block_comment(content: str, *, max_lines: int = 20) -> Optional[str]:
    """First /* ... */ in the first *max_lines* lines only, anchored to file start (whitespace/BOM ok).

    Regex runs on a bounded prefix so it cannot scan or greedily consume the whole file.
    """
    text = content[1:] if content.startswith("\ufeff") else content
    lines = text.splitlines(keepends=True)
    prefix = "".join(lines[:max_lines])
    m = re.search(r"/\*.*?\*/", prefix, re.DOTALL)
    if not m:
        return None
    if prefix[: m.start()].strip():
        return None
    return m.group(0)


_BLOCK_PLACEHOLDER_RE = re.compile(r"^<<BLOCK\d+>>$")


def _is_diagram_placeholder(para: str) -> bool:
    return bool(_BLOCK_PLACEHOLDER_RE.match(para.strip()))


_MATH_BLOCK_RE = re.compile(r"\\\[(?:.|\n)*?\\\]|\$\$(?:.|\n)*?\$\$", re.DOTALL)


def _protect_math_blocks(text: str) -> Tuple[str, List[str]]:
    """Replace ``\\[...\\]`` and ``$$...$$`` with placeholders so paragraph splits never cut equations."""
    vault: List[str] = []
    out_parts: List[str] = []
    pos = 0
    for m in _MATH_BLOCK_RE.finditer(text):
        out_parts.append(text[pos : m.start()])
        vault.append(m.group(0))
        out_parts.append(f"__MATH_BLOCK_{len(vault) - 1}__")
        pos = m.end()
    out_parts.append(text[pos:])
    return "".join(out_parts), vault


def _restore_math_blocks(segment: str, vault: List[str]) -> str:
    for i, block in enumerate(vault):
        segment = segment.replace(f"__MATH_BLOCK_{i}__", block)
    return segment


def _extract_source_c_files(text: str) -> str:
    """Extract C source file basenames from a ``**Source files:**`` block in domain markdown."""
    m = re.search(r"\*\*Source files:\*\*\s*\n((?:\s*-\s*.+\n?)*)", text)
    if not m:
        return ""
    basenames: List[str] = []
    for line in m.group(1).strip().split("\n"):
        line = line.strip().lstrip("- ").strip()
        line = line.strip("`").strip()
        if line:
            basenames.append(Path(line.replace("\\", "/")).name)
    return ", ".join(basenames)
