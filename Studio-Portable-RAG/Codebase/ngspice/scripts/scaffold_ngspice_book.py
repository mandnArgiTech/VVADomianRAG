#!/usr/bin/env python3
"""Pass 1: create docs/ngspice_book/ tree with YAML stubs (no body from rag_index)."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BOOK = ROOT / "docs" / "ngspice_book"
MANIFEST = BOOK / "_meta" / "inventory_manifest.json"

def slug_title(section_id: str) -> str:
    s = section_id.split("_", 1)[-1] if "_" in section_id else section_id
    return section_id.replace("_", " ").title()


def chapter_title(ch_id: str) -> str:
    return ch_id.replace("_", " ").title()


def mission_for_chapter(ch_id: str) -> tuple[str, list[str]]:
    kernel = {
        "00_foundations", "01_architecture_overview", "02_numerical_kernel_core",
        "03_analysis_drivers", "04_convergence_aids", "05_numerical_integration",
        "06_sparse_solver", "07_device_model_contract", "08_passive_devices",
        "09_source_devices", "10_diode_and_bjt_models", "11_mosfet_models",
        "12_jfet_mesfet_models", "13_xspice_mixed_signal", "22_nodalai_kernel_reimplementation",
        "23_canonical_chains_reference",
    }
    design = {
        "14_netlist_grammar", "15_parser_and_expansion", "16_command_interpreter",
        "17_output_and_results", "18_options_and_tolerances", "19_circuit_design_patterns",
        "20_debugging_workflows", "24_glossary",
    }
    both = {"21_validation_with_regression_suite"}
    if ch_id in kernel:
        return "kernel_reimplementation", ["circuit_design_validation"]
    if ch_id in design:
        return "circuit_design_validation", ["kernel_reimplementation"]
    if ch_id in both:
        return "both", []
    return "both", ["kernel_reimplementation", "circuit_design_validation"]


def section_stub_yaml(
    ch_id: str,
    section_file: str,
    section_slug: str,
    sec_num: str,
) -> str:
    pri, sec = mission_for_chapter(ch_id)
    topic = section_slug
    anchor = re.sub(r"[^a-z0-9]+", "-", section_slug.lower()).strip("-")
    title_h = slug_title(section_slug)
    return f"""---
title: "{title_h}"
chapter: "{ch_id}"
section: "{section_slug}"
section_number: "{sec_num}"
topic: "{topic}"
mission_primary: "{pri}"
mission_secondary: {json.dumps(sec)}
related_files: []
related_chapters: []
domain_concepts: []
canonical_chain_tags: []
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience: ["NodalAI reimplementer", "ngspice core developer"]
estimated_reading_minutes: 10
last_updated_from_source_at: "2026-05-05T00:00:00Z"
---

# {title_h} {{#{anchor}}}

## Overview {{#overview}}

**TODO:** Replace with source-grounded prose per `doument_prompt.md`. Every substantive paragraph must cite `src/...` line ranges after reading sources.

<!-- scaffold: not yet authored from source -->

## Source Files {{#source-files}}

(To be filled from source trace.)

## Related Chapters {{#related-chapters}}

(To be cross-linked.)
"""


def readme_stub(ch_id: str, sections: list[str]) -> str:
    pri, sec = mission_for_chapter(ch_id)
    lines = [
        "---",
        f'title: "Chapter: {chapter_title(ch_id)}"',
        f'chapter: "{ch_id}"',
        'type: "chapter_index"',
        f'mission_primary: "{pri}"',
        f"mission_secondary: {json.dumps(sec)}",
        "---",
        "",
        f"# {chapter_title(ch_id)}",
        "",
        "## Chapter summary",
        "",
        "**TODO:** 2–3 paragraphs after sections are authored.",
        "",
        "## Sections",
        "",
    ]
    for i, s in enumerate(sections, start=1):
        fn = f"{s}.md"
        lines.append(f"{i}. [{slug_title(s)}]({fn})")
    lines.extend(["", "## Prerequisites", "", "(Links to prior chapters.)", ""])
    return "\n".join(lines) + "\n"


def main() -> None:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    BOOK.mkdir(parents=True, exist_ok=True)
    (BOOK / "_meta").mkdir(parents=True, exist_ok=True)

    for ch in data["chapters"]:
        ch_id = ch["id"]
        cdir = BOOK / ch_id
        cdir.mkdir(parents=True, exist_ok=True)
        sections_out: list[str] = []
        for i, sec in enumerate(ch["sections"], start=1):
            sections_out.append(sec)
            fname = f"{sec}.md"
            sec_num = f"{ch_id.split('_')[0]}.{i}"
            body = section_stub_yaml(ch_id, fname, sec, sec_num)
            (cdir / fname).write_text(body, encoding="utf-8")
        (cdir / "README.md").write_text(readme_stub(ch_id, sections_out), encoding="utf-8")

    idx = """---
title: "ngspice: Architecture, Numerical Kernel, and Circuit Design Reference"
type: "book_index"
generated_at: "2026-05-05T00:00:00Z"
total_chapters: 25
total_sections: 0
---

# ngspice book (scaffold)

**TODO:** Expand to 1500–3000 words per `doument_prompt.md`. Dual-mission TOC and reading paths.

## Coverage notes

- **BSIM6:** Not present in this tree — section file omitted from `11_mosfet_models`.
- **Chapter 23:** Thirteen canonical chains (matches `rag_index.json`).

See `_meta/inventory_manifest.json` and `_meta/path_registry.md`.
"""
    (BOOK / "INDEX.md").write_text(idx, encoding="utf-8")
    print(f"Scaffolded under {BOOK}")


if __name__ == "__main__":
    main()
