"""Language splits, regex chunkers, tree-sitter AST chunks, Scheme, sentence windows."""

from __future__ import annotations

import ast
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, FrozenSet, List, Optional, Set, Tuple

from langchain_text_splitters import Language, RecursiveCharacterTextSplitter

from ingest_kit.concepts import format_concepts_field
from ingest_kit.chunking.shared import _file_preamble_block_comment, _ts_comment_prefix
from ingest_kit.treesitter import TreeSitterFallbackDisallowedError, _ts_parser_for

logger = logging.getLogger("ingest")

def language_split(
    path: Path, content: str, lang: Language, size: int = 2000
) -> List[Tuple[str, Dict[str, str]]]:
    splitter = RecursiveCharacterTextSplitter.from_language(
        language=lang, chunk_size=size, chunk_overlap=200
    )
    docs = splitter.create_documents([content], metadatas=[{"path": str(path)}])
    return [
        (
            d.page_content,
            {
                "chunk_strategy": "language",
                "chunk_type": "fragment",
                "chunk_name": path.stem,
                "chunk_index": str(i),
            },
        )
        for i, d in enumerate(docs)
    ]


def generic_split(content: str, path: Path, size: int = 2000) -> List[Tuple[str, Dict[str, str]]]:
    splitter = RecursiveCharacterTextSplitter(chunk_size=size, chunk_overlap=200)
    docs = splitter.create_documents([content], metadatas=[{"path": str(path)}])
    return [
        (
            d.page_content,
            {
                "chunk_strategy": "generic",
                "chunk_type": "fragment",
                "chunk_name": path.stem,
                "chunk_index": str(i),
            },
        )
        for i, d in enumerate(docs)
    ]


# Regex-assisted boundaries for languages without tree-sitter in this pipeline (leading whitespace allowed).
# Compiled with re.MULTILINE — do not embed per-branch (?m) flags (invalid when patterns are OR-joined).
_REGEX_CODE_PATTERNS: Dict[str, List[str]] = {
    ".go": [r"^\s*func\s+", r"^\s*type\s+\w+\s+struct\b"],
    ".rs": [
        r"^\s*(?:pub\s+)?(?:unsafe\s+)?fn\s+",
        r"^\s*(?:pub\s+)?struct\s+",
        r"^\s*(?:pub\s+)?enum\s+",
        r"^\s*(?:pub\s+)?impl\b",
        r"^\s*(?:pub\s+)?trait\s+",
    ],
    ".rb": [r"^\s*class\s+", r"^\s*module\s+", r"^\s*def\s+"],
    ".kt": [
        r"^\s*(?:public\s+|private\s+|internal\s+|protected\s+)?(?:open\s+|abstract\s+|sealed\s+)?fun\s+",
        r"^\s*class\s+",
        r"^\s*object\s+",
        r"^\s*interface\s+",
    ],
    ".kts": [r"^\s*fun\s+", r"^\s*class\s+", r"^\s*object\s+"],
    ".swift": [r"^\s*func\s+", r"^\s*class\s+", r"^\s*struct\s+", r"^\s*enum\s+", r"^\s*protocol\s+"],
    ".scala": [r"^\s*def\s+", r"^\s*class\s+", r"^\s*object\s+", r"^\s*trait\s+"],
    ".php": [r"^\s*function\s+", r"^\s*class\s+"],
    ".c": [
        r"^\w[\w\s\*]+\s+\w+\s*\([^;]*\)\s*\{",  # standard function definition
        r"^\s*struct\s+\w+\s*\{",
        r"^\s*typedef\s+",
        r"^\s*#\s*define\s+\w+",
    ],
    ".h": [
        r"^\w[\w\s\*]+\s+\w+\s*\([^;]*\);",
        r"^\s*struct\s+\w+\s*\{",
        r"^\s*typedef\s+",
        r"^\s*#\s*define\s+\w+",
    ],
    ".cpp": [
        r"^\w[\w\s\*:<>]+\s+[\w:]+\s*\([^;]*\)\s*(?:const\s*)?\{",
        r"^\s*class\s+\w+",
        r"^\s*struct\s+\w+\s*\{",
    ],
}


def _merge_small_regex_chunks(
    parts: List[str], min_chars: int = 200, max_chars: int = 12000
) -> List[str]:
    if not parts:
        return []
    merged: List[str] = []
    buf = parts[0]
    for p in parts[1:]:
        if len(buf) < min_chars and len(buf) + len(p) <= max_chars:
            buf = buf + "\n\n" + p
        else:
            merged.append(buf)
            buf = p
    merged.append(buf)
    return merged


def regex_code_split(content: str, path: Path, ext: str) -> List[Tuple[str, Dict[str, str]]]:
    """Split on language-typical top-level boundaries; fallback to generic_split."""
    patterns = _REGEX_CODE_PATTERNS.get(ext.lower())
    if not patterns:
        return generic_split(content, path, 1500)
    combined = "|".join(f"({p})" for p in patterns)
    try:
        rx = re.compile(combined, re.MULTILINE)
    except re.error:
        return generic_split(content, path, 1500)
    matches = list(rx.finditer(content))
    if not matches:
        return generic_split(content, path, 1500)
    starts = sorted({m.start() for m in matches})
    if starts[0] > 0:
        starts.insert(0, 0)
    raw_parts: List[str] = []
    for i, st in enumerate(starts):
        end = starts[i + 1] if i + 1 < len(starts) else len(content)
        seg = content[st:end].strip()
        if seg:
            raw_parts.append(seg)
    if not raw_parts:
        return generic_split(content, path, 1500)
    raw_parts = _merge_small_regex_chunks(raw_parts)
    return [
        (
            seg[:12000],
            {
                "chunk_strategy": "regex_code",
                "chunk_type": "fragment",
                "chunk_name": path.stem,
                "chunk_index": str(i),
            },
        )
        for i, seg in enumerate(raw_parts)
    ]


_SPICE_BLOCK_RE = re.compile(
    r"(?=^\s*\.(?:subckt|model|macro|control)\b)",
    re.MULTILINE | re.IGNORECASE,
)


def regex_spice_split(content: str, path: Path) -> List[Tuple[str, Dict[str, str]]]:
    """Split a SPICE netlist on top-level block boundaries.

    Splits before .subckt, .model, .macro, and .control directives so these
    blocks are never cut in half by a generic chunker. The leading preamble
    (title, .global, .param, etc.) is preserved as its own chunk.
    """
    raw_parts = [p.strip() for p in _SPICE_BLOCK_RE.split(content) if p.strip()]
    if not raw_parts:
        return generic_split(content, path, 2000)
    # min_chars=0: never merge across split boundaries — each part is a semantic block.
    # (min_chars=200 would merge multiple .subckt/.model sections when each is tiny.)
    raw_parts = _merge_small_regex_chunks(raw_parts, min_chars=0, max_chars=8000)
    SPICE_MAX_SEGMENT_CHARS = 50_000
    safe_parts: List[str] = []
    for seg in raw_parts:
        if len(seg) > SPICE_MAX_SEGMENT_CHARS:
            logger.warning(
                "regex_spice_split: segment for %s exceeds %d chars (%d) — "
                "sub-splitting with RecursiveCharacterTextSplitter.",
                path.name,
                SPICE_MAX_SEGMENT_CHARS,
                len(seg),
            )
            sub_splitter = RecursiveCharacterTextSplitter(
                chunk_size=SPICE_MAX_SEGMENT_CHARS,
                chunk_overlap=0,
                separators=["\n\n", "\n", " ", ""],
            )
            sub_docs = sub_splitter.create_documents([seg])
            for d in sub_docs:
                piece = d.page_content
                # Defense in depth: some splitter versions can exceed chunk_size on edge cases.
                if len(piece) <= SPICE_MAX_SEGMENT_CHARS:
                    safe_parts.append(piece)
                else:
                    for i in range(0, len(piece), SPICE_MAX_SEGMENT_CHARS):
                        safe_parts.append(piece[i : i + SPICE_MAX_SEGMENT_CHARS])
        else:
            safe_parts.append(seg)
    raw_parts = safe_parts
    return [
        (
            seg,
            {
                "chunk_strategy": "regex_spice",
                "chunk_type": "spice_block",
                "chunk_name": path.stem,
                "chunk_index": str(i),
            },
        )
        for i, seg in enumerate(raw_parts)
    ]
# Callee extraction (Story B) — C/C++
_C_STDLIB_CALLS: FrozenSet[str] = frozenset(
    {
        "malloc",
        "free",
        "calloc",
        "realloc",
        "printf",
        "fprintf",
        "sprintf",
        "snprintf",
        "vprintf",
        "vfprintf",
        "memcpy",
        "memset",
        "memmove",
        "memcmp",
        "strlen",
        "strcmp",
        "strncmp",
        "strcpy",
        "strncpy",
        "strcat",
        "strncat",
        "sizeof",
        "abs",
        "fabs",
        "sqrt",
        "log",
        "exp",
        "pow",
        "ceil",
        "floor",
        "assert",
        "exit",
        "abort",
        "perror",
        "strerror",
        "fopen",
        "fclose",
        "fread",
        "fwrite",
        "fseek",
        "ftell",
        "atoi",
        "atof",
        "strtol",
        "strtod",
    }
)

_C_KEYWORDS: FrozenSet[str] = frozenset(
    {
        "NULL",
        "nullptr",
        "true",
        "false",
        "int",
        "long",
        "short",
        "char",
        "unsigned",
        "signed",
        "float",
        "double",
        "void",
        "struct",
        "enum",
        "union",
        "return",
        "if",
        "else",
        "while",
        "for",
        "do",
        "switch",
        "case",
        "break",
        "continue",
        "goto",
        "static",
        "extern",
        "const",
        "volatile",
        "register",
        "typedef",
        "sizeof",
        "inline",
        "restrict",
    }
)

CALLS_METADATA_MAX = 50


def _format_calls_metadata(names: List[str]) -> str:
    """Pipe-delimited callee names; cap size and append __truncated__ when needed."""
    u = sorted({x.strip() for x in names if x and str(x).strip()})
    if not u:
        return ""
    if len(u) > CALLS_METADATA_MAX:
        u = u[:CALLS_METADATA_MAX] + ["__truncated__"]
    return format_concepts_field(u)


def _extract_c_calls_from_node(node, content: str) -> List[str]:
    """Extract function call and function pointer identifiers from a tree-sitter C/C++ node.

    Handles three patterns:
    - Direct call:          ``bar()``                  → call_expression
    - Assignment RHS:       ``dev.fn = myHandler``     → assignment_expression
    - Struct initializer:   ``{ funcA, funcB, NULL }`` → initializer_list
    """
    calls: Set[str] = set()

    def _add_if_valid(name: str) -> None:
        if name and name not in _C_STDLIB_CALLS and name not in _C_KEYWORDS and not name.startswith("__"):
            calls.add(name)

    def _walk_calls(n) -> None:
        if n.type == "call_expression":
            func_node = n.children[0] if n.children else None
            if func_node is not None:
                if func_node.type == "identifier":
                    _add_if_valid(content[func_node.start_byte : func_node.end_byte])
                elif func_node.type == "field_expression":
                    for ch in reversed(func_node.children):
                        if ch.type == "field_identifier":
                            _add_if_valid(content[ch.start_byte : ch.end_byte])
                            break
            for ch in n.children:
                _walk_calls(ch)
        elif n.type == "assignment_expression":
            # Capture function pointers on RHS: .DEVload = BSIM3v1load
            rhs = n.children[2] if len(n.children) >= 3 else None
            if rhs is not None and rhs.type == "identifier":
                _add_if_valid(content[rhs.start_byte : rhs.end_byte])
            for ch in n.children:
                _walk_calls(ch)
        elif n.type == "initializer_list":
            # Capture positional function pointers: { funcA, funcB, 0, NULL }
            for ch in n.children:
                if ch.type == "identifier":
                    _add_if_valid(content[ch.start_byte : ch.end_byte])
                else:
                    _walk_calls(ch)
        elif n.type == "initializer_pair":
            # Capture designated function pointers: .DEVmodDelete = BSIM3v1mDelete
            # Tree-Sitter children: [field_designator, "=", identifier]
            val = n.children[-1] if n.children else None
            if val is not None and val.type == "identifier":
                _add_if_valid(content[val.start_byte : val.end_byte])
            for ch in n.children:
                _walk_calls(ch)
        else:
            for ch in n.children:
                _walk_calls(ch)

    cs = next((ch for ch in node.children if ch.type == "compound_statement"), None)
    if cs is not None:
        _walk_calls(cs)
    else:
        for ch in node.children:
            _walk_calls(ch)

    return sorted(calls)


_PY_BUILTIN_CALLS: FrozenSet[str] = frozenset(
    {
        "print",
        "len",
        "range",
        "int",
        "float",
        "str",
        "bool",
        "list",
        "dict",
        "set",
        "tuple",
        "type",
        "isinstance",
        "issubclass",
        "getattr",
        "setattr",
        "hasattr",
        "super",
        "enumerate",
        "zip",
        "map",
        "filter",
        "sorted",
        "reversed",
        "min",
        "max",
        "sum",
        "any",
        "all",
        "abs",
        "round",
        "open",
        "iter",
        "next",
        "hash",
        "id",
        "repr",
        "format",
        "vars",
        "dir",
        "property",
        "staticmethod",
        "classmethod",
    }
)


def _extract_py_calls(func_node: ast.AST) -> List[str]:
    """Extract called function/method names from a Python function or async function body."""
    calls: Set[str] = set()
    for node in ast.walk(func_node):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                name = node.func.id
                if name not in _PY_BUILTIN_CALLS:
                    calls.add(name)
            elif isinstance(node.func, ast.Attribute):
                calls.add(node.func.attr)
    calls -= _PY_BUILTIN_CALLS
    return sorted(calls)


def ast_chunk_python(path: Path, content: str) -> List[Tuple[str, Dict[str, str]]]:
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return generic_split(content, path, 1500)
    chunks: List[Tuple[str, Dict[str, str]]] = []
    lines = content.splitlines()

    def slice_node(node: ast.AST) -> str:
        if hasattr(node, "lineno") and hasattr(node, "end_lineno"):
            start = max(0, node.lineno - 1)
            end = min(len(lines), node.end_lineno)
            return "\n".join(lines[start:end])
        seg = ast.get_source_segment(content, node)  # pragma: no cover
        return seg or ""  # pragma: no cover

    idx = 0
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            src = slice_node(node)
            if not src.strip():
                continue  # pragma: no cover
            nm = node.name
            ctype = "class" if isinstance(node, ast.ClassDef) else "function"
            calls_field = ""
            if ctype == "function":
                calls_field = _format_calls_metadata(_extract_py_calls(node))
            chunks.append(
                (
                    src,
                    {
                        "chunk_strategy": "ast_python",
                        "chunk_type": ctype,
                        "chunk_name": nm,
                        "chunk_index": str(idx),
                        "calls": calls_field,
                    },
                )
            )
            idx += 1
    if not chunks:
        return generic_split(content, path, 1500)
    return chunks


def _mask_c_macros_for_ast(content: str) -> str:
    """
    Replaces known disruptive C macros with spaces of the exact same length.
    This allows Tree-Sitter to parse the syntax tree without breaking the
    start_byte/end_byte character offsets mapping to the original content.
    """
    masked = content

    # 1. Mask __attribute__((...))
    masked = re.sub(
        r"__attribute__\s*\(\(.*?\)\)",
        lambda m: " " * len(m.group(0)),
        masked,
        flags=re.DOTALL,
    )

    # __declspec(...) — MSVC/Clang extension
    masked = re.sub(
        r"__declspec\s*\([\s\S]*?\)",
        lambda m: " " * len(m.group(0)),
        masked,
        flags=re.DOTALL,
    )

    # Ngspice-specific function-wrapping macros
    masked = re.sub(
        r"\b(?:COMPILER_PRAGMA|SPICE_IGNORE_WARNING|NG_IGNORE)\b\s*\([\s\S]*?\)",
        lambda m: " " * len(m.group(0)),
        masked,
        flags=re.DOTALL,
    )

    # Do not mask #if/#ifdef/#else/#endif: Tree-Sitter C grammar includes preprocessor
    # directives; blanking them mis-parses mutually exclusive regions and breaks large
    # functions (e.g. DCtran bodies spanning conditionals).

    # 2. Mask common Ngspice return wrappers or fast-aliasing macros
    # Example: SPICEdev struct instantiations or complex macro headers
    # Add any specific Ngspice macros here that break function definitions.
    # masked = re.sub(r'YOUR_MACRO_REGEX', lambda m: " " * len(m.group(0)), masked)

    return masked


# Common English / generic identifiers ending in ``set`` that are not Ngspice ``*set`` helpers.
_SETUP_ENDSET_DENY = frozenset(
    {
        "offset",
        "closet",
        "onset",
        "preset",
        "roset",
        "asset",
        "beset",
        "coset",
        "dataset",
    }
)


def _ngspice_setup_like_context(function_name: str, stem: str) -> bool:
    """Ngspice-style setup/init context for chunk typing and declaration preservation.

    The plan's ``\"set\" in name`` intent maps to ``*set`` suffix (e.g. ``MOS1set``,
    ``DIOset``) while avoiding false positives such as ``offset`` (also ``*set``).
    """
    fl = (function_name or "").lower()
    sl = (stem or "").lower()
    if "setup" in fl or "init" in fl or "alloc" in fl:
        return True
    if fl.endswith("set") and fl not in _SETUP_ENDSET_DENY:
        return True
    if "setup" in sl or "init" in sl:
        return True
    if sl.endswith("set") and sl not in _SETUP_ENDSET_DENY:
        return True
    return False


def _ts_find_function_identifier(node, content: str) -> Optional[str]:
    """Recursively traverse a function_declarator to find the function name identifier."""
    skip_types = frozenset({"parameter_list", "argument_list"})
    target_types = {"pointer_declarator", "parenthesized_declarator", "function_declarator"}
    for ch in node.children:
        if ch.type in skip_types:
            continue
        if ch.type == "identifier":
            return content[ch.start_byte : ch.end_byte]
        if ch.type in target_types:
            result = _ts_find_function_identifier(ch, content)
            if result:
                return result
    return None


_EXEMPT_CHUNK_TYPES = frozenset({"file_preamble", "core_constant"})
# ``declaration`` chunks below this length are usually variable lists / one-liners; keep longer
# blocks (large typedefs, grouped externs) that may still be useful.
_DECLARATION_MIN_KEEP_CHARS = 200


def _filter_tiny_code_chunks(
    out: List[Tuple[str, Dict[str, str]]],
) -> List[Tuple[str, Dict[str, str]]]:
    """Drop short code chunks (CODE_CHUNK_MIN_SIZE) and noisy short ``declaration`` AST nodes."""
    try:
        code_min = int(os.environ.get("CODE_CHUNK_MIN_SIZE", "50"))
    except ValueError:
        code_min = 50
    if code_min <= 0:
        return out
    filtered = []
    for text, meta in out:
        ctype = meta.get("chunk_type")
        n = len(text.strip())
        if ctype in _EXEMPT_CHUNK_TYPES:
            filtered.append((text, meta))
            continue
        if n < code_min:
            continue
        if ctype == "declaration" and n < _DECLARATION_MIN_KEEP_CHARS:
            continue
        filtered.append((text, meta))
    for i, (_, m) in enumerate(filtered):
        m["chunk_index"] = str(i)
    return filtered


def _ts_extract_chunks(path: Path, content: str, grammar: str) -> Optional[List[Tuple[str, Dict[str, str]]]]:
    mod_map = {
        "c": "tree_sitter_c",
        "cpp": "tree_sitter_cpp",
        "java": "tree_sitter_java",
    }
    if grammar not in mod_map:
        return None
    parser = _ts_parser_for(grammar, mod_map[grammar])
    if parser is None:
        return None  # pragma: no cover

    # Mask the content for the parser (C/C++ only); byte lengths preserved so offsets map to `content`.
    if grammar in ("c", "cpp"):
        ast_safe_content = _mask_c_macros_for_ast(content)
    else:
        ast_safe_content = content

    data = ast_safe_content.encode("utf-8", errors="replace")
    tree = parser.parse(data)

    targets = {
        "c": {
            "function_definition",
            "struct_specifier",
            "enum_specifier",
            "declaration",
            "preproc_def",
            "preproc_function_def",
            "type_definition",
        },
        "cpp": {"function_definition", "class_specifier", "struct_specifier", "enum_specifier"},
        "java": {"method_declaration", "class_declaration", "interface_declaration"},
    }[grammar]

    out: List[Tuple[str, Dict[str, str]]] = []
    device_family_val = _device_family_for_path(path)

    def node_text(node) -> str:
        # Always slice from the ORIGINAL content (parser ran on ast_safe_content).
        return content[node.start_byte : node.end_byte]

    def walk(node, classname: str = "", in_function: bool = False, current_func: str = ""):
        t = node.type
        chunk_name = ""  # set in ``if t in targets``; avoids UnboundLocalError on recurse paths
        is_setup_func = _ngspice_setup_like_context(current_func, path.stem)
        # Skip `declaration` nodes inside function bodies — they are local variable
        # declarations and would flood the index with useless chunks — except in
        # setup/init/alloc-style functions where locals matter for device modeling.
        if t == "declaration" and in_function and not is_setup_func:
            return
        # Skip function-local typedefs (unusual in Ngspice; avoids noisy inner chunks).
        if t == "type_definition" and in_function:
            return
        if t in targets:
            txt = node_text(node).strip()
            if not txt:
                return  # pragma: no cover
            cmt = _ts_comment_prefix(content, node.start_byte)
            if cmt:
                txt = cmt + txt  # pragma: no cover
            name = path.stem
            chunk_name = name
            if grammar in ("c", "cpp") and t == "function_definition":
                for ch in node.children:
                    if ch.type in ("function_declarator", "pointer_declarator"):
                        found = _ts_find_function_identifier(ch, content)
                        if found:
                            chunk_name = found
                            break
            if grammar == "java" and t == "method_declaration":
                for ch in node.children:
                    if ch.type == "identifier":
                        chunk_name = content[ch.start_byte : ch.end_byte]
                        break
            if grammar == "c" and t in ("preproc_def", "preproc_function_def"):
                for ch in node.children:
                    if ch.type == "identifier":
                        chunk_name = content[ch.start_byte : ch.end_byte]
                        break
            if grammar == "c" and t == "declaration":
                decl_named = False
                for ch in node.children:
                    if decl_named:
                        break
                    if ch.type == "identifier":
                        chunk_name = content[ch.start_byte : ch.end_byte]
                        decl_named = True
                        break
                    if ch.type == "init_declarator":
                        for g in ch.children:
                            if g.type not in ("identifier", "pointer_declarator", "declarator"):
                                continue
                            inner = g
                            while inner.type in ("pointer_declarator", "declarator"):
                                nxt = next(
                                    (
                                        x
                                        for x in inner.children
                                        if x.type in ("identifier", "pointer_declarator", "declarator")
                                    ),
                                    None,
                                )
                                if nxt is None:
                                    break
                                inner = nxt
                            if inner.type == "identifier":
                                chunk_name = content[inner.start_byte : inner.end_byte]
                                decl_named = True
                                break
            if grammar == "c" and t == "type_definition":
                last_tid = None
                for ch in node.children:
                    if ch.type == "type_identifier":
                        last_tid = ch
                if last_tid is not None:
                    chunk_name = content[last_tid.start_byte : last_tid.end_byte]
            if classname and grammar in ("cpp", "java"):
                chunk_name = f"{classname}::{chunk_name}"
            # Semantic chunk typing for C function definitions.
            chunk_type = t
            if grammar == "c" and t == "function_definition":
                cn_lower = chunk_name.lower()
                txt_lower = txt.lower()
                setup_like = _ngspice_setup_like_context(chunk_name, path.stem)
                if "load" in cn_lower:
                    chunk_type = "device_load_function"
                elif setup_like:
                    chunk_type = "device_setup_function"
                elif "mna" in txt_lower or "smp" in txt_lower:
                    chunk_type = "matrix_solver_function"
            if grammar == "c" and t == "preproc_def" and path.name.casefold() in (
                "cktdefs.h",
                "devdefs.h",
            ):
                chunk_type = "core_constant"
            calls_list: List[str] = []
            if grammar in ("c", "cpp") and t in ("function_definition", "declaration"):
                calls_list = _extract_c_calls_from_node(node, content)
            calls_field = _format_calls_metadata(calls_list)
            out.append(
                (
                    txt[:100000],
                    {
                        "chunk_strategy": f"ast_{grammar}",
                        "chunk_type": chunk_type,
                        "chunk_name": chunk_name[:200],
                        "chunk_index": str(len(out)),
                        "device_family": device_family_val,
                        "calls": calls_field,
                    },
                )
            )
        # Recurse into children, propagating the in_function flag for C.
        enters_function = grammar == "c" and t == "function_definition"
        enters_type_def = grammar == "c" and t == "type_definition"
        if grammar == "cpp" and t == "class_specifier":
            cname = classname  # pragma: no cover
            for ch in node.children:  # pragma: no cover
                if ch.type == "type_identifier":  # pragma: no cover
                    cname = content[ch.start_byte : ch.end_byte]  # pragma: no cover
                    break  # pragma: no cover
            for ch in node.children:  # pragma: no cover
                walk(ch, cname or classname, False, current_func)  # pragma: no cover
        elif grammar == "java" and t in ("class_declaration", "interface_declaration"):
            cname = classname
            for ch in node.children:
                if ch.type == "identifier":
                    cname = content[ch.start_byte : ch.end_byte]
                    break
            for ch in node.children:
                walk(ch, cname or classname, False, current_func)
        elif enters_type_def:
            pass  # typedef text already emitted; skip inner struct_specifier duplicate chunk
        else:
            next_current = chunk_name if enters_function else current_func
            for ch in node.children:
                walk(ch, classname, in_function or enters_function, next_current)

    if grammar in ("c", "cpp"):
        preamble = _file_preamble_block_comment(content)
        if preamble:
            out.append(
                (
                    preamble.strip()[:12000],
                    {
                        "chunk_strategy": f"ast_{grammar}",
                        "chunk_type": "file_preamble",
                        "chunk_name": path.stem,
                        "chunk_index": "0",
                        "device_family": device_family_val,
                        "calls": "",
                    },
                )
            )

    walk(tree.root_node)
    if not out:
        return None
    # Empty list means "AST ran but nothing survived the size filter" — not ``None`` (parser / no-walk).
    return _filter_tiny_code_chunks(out)


def _ts_extract_chunks_or_language_split_c_cpp(
    path: Path,
    content: str,
    grammar: str,
    *,
    allow_language_split_fallback: bool,
) -> List[Tuple[str, Dict[str, str]]]:
    """AST chunks via tree-sitter, or language_split fallback with optional top file preamble.

    If the tree-sitter parser cannot be loaded, fallback runs only when
    *allow_language_split_fallback* is true (CLI ``--allow-language-split-fallback`` or env).
    If the parser loads but ``_ts_extract_chunks`` returns an empty list (e.g. unparseable
    file after masking), a warning is logged and the same fallback runs so files are not
    dropped entirely. ``None`` from ``_ts_extract_chunks`` (parser unavailable) skips the
    empty-list warning but still uses the fallback path below.
    """
    if grammar not in ("c", "cpp"):
        raise ValueError("grammar must be 'c' or 'cpp'")  # pragma: no cover
    mod_map = {"c": "tree_sitter_c", "cpp": "tree_sitter_cpp"}
    ts = _ts_extract_chunks(path, content, grammar)
    if ts is not None:
        if len(ts) == 0:
            logger.warning(
                "AST yielded 0 chunks for %s (%s), falling back to regex/text splitter.",
                path.name,
                grammar,
            )
            ext = path.suffix.lower()
            if ext in _REGEX_CODE_PATTERNS:
                regex_parts = regex_code_split(content, path, ext)
                if regex_parts:
                    logger.debug(
                        "Routed %s through regex_code_split (%d chunks).",
                        path.name,
                        len(regex_parts),
                    )
                    return regex_parts
        else:
            return ts
    parser = _ts_parser_for(grammar, mod_map[grammar])
    if parser is None and not allow_language_split_fallback:
        raise TreeSitterFallbackDisallowedError(
            "tree-sitter is not available for "
            f"{grammar.upper()} (install e.g. pip install tree-sitter tree-sitter-c). "
            "Re-run with --allow-language-split-fallback (or set "
            "INGEST_ALLOW_LANGUAGE_SPLIT_FALLBACK=1) to use text splitting instead."
        )
    lang = Language.C if grammar == "c" else Language.CPP
    parts = language_split(path, content, lang, size=50000)
    pre = _file_preamble_block_comment(content)
    if not pre:
        return parts
    preamble_chunk: Tuple[str, Dict[str, str]] = (
        pre.strip()[:12000],
        {
            "chunk_strategy": f"ast_{grammar}",
            "chunk_type": "file_preamble",
            "chunk_name": path.stem,
            "chunk_index": "0",
            "device_family": _device_family_for_path(path),
            "calls": "",
        },
    )
    out_ls: List[Tuple[str, Dict[str, str]]] = [preamble_chunk]
    for i, (text, meta) in enumerate(parts):
        m = dict(meta)
        m["chunk_index"] = str(i + 1)
        out_ls.append((text, m))
    return out_ls


def _ts_extract_chunks_or_language_split_java(
    path: Path,
    content: str,
    *,
    allow_language_split_fallback: bool,
) -> List[Tuple[str, Dict[str, str]]]:
    ts = _ts_extract_chunks(path, content, "java")
    if ts is not None:
        return ts
    parser = _ts_parser_for("java", "tree_sitter_java")
    if parser is None and not allow_language_split_fallback:
        raise TreeSitterFallbackDisallowedError(
            "tree-sitter is not available for Java (install e.g. pip install tree-sitter "
            "tree-sitter-java). Re-run with --allow-language-split-fallback (or set "
            "INGEST_ALLOW_LANGUAGE_SPLIT_FALLBACK=1) to use text splitting instead."
        )
    return language_split(path, content, Language.JAVA, size=2000)


def chunk_scheme(content: str, path: Path) -> List[Tuple[str, Dict[str, str]]]:
    try:
        parser = _ts_parser_for("scheme", "tree_sitter_scheme")
        if parser is not None:
            data = content.encode("utf-8", errors="replace")
            tree = parser.parse(data)
            out_ts: List[Tuple[str, Dict[str, str]]] = []

            def walk_scheme(n):
                if n.type == "list" and n.children:
                    first = n.children[0]
                    if first.type == "symbol" and content[first.start_byte : first.end_byte] == "define":
                        sym = n.children[1] if len(n.children) > 1 else None  # pragma: no cover
                        nm = (  # pragma: no cover
                            content[sym.start_byte : sym.end_byte].strip("()")
                            if sym
                            else path.stem
                        )
                        raw = content[n.start_byte : n.end_byte]  # pragma: no cover
                        cmt = _ts_comment_prefix(content, n.start_byte, 2)  # pragma: no cover
                        body = (cmt + raw) if cmt else raw  # pragma: no cover
                        out_ts.append(  # pragma: no cover
                            (
                                body[:100000],
                                {
                                    "chunk_strategy": "scheme",
                                    "chunk_type": "define",
                                    "chunk_name": nm[:200],
                                    "chunk_index": str(len(out_ts)),
                                },
                            )
                        )
                for ch in n.children:
                    walk_scheme(ch)

            walk_scheme(tree.root_node)
            if out_ts:
                return out_ts  # pragma: no cover
    except Exception:  # pragma: no cover
        pass  # pragma: no cover
    forms = re.split(r"(?m)(?=^\s*\(define\b)", content)
    out: List[Tuple[str, Dict[str, str]]] = []
    for f in forms:
        f = f.strip()
        if not f.startswith("(define"):
            continue
        m = re.match(r"^\s*\(define\s+(\S+)", f)
        name = m.group(1).strip("()") if m else path.stem
        out.append(
            (
                f[:100000],
                {
                    "chunk_strategy": "scheme",
                    "chunk_type": "define",
                    "chunk_name": name,
                    "chunk_index": str(len(out)),
                },
            )
        )
    if not out:
        return generic_split(content, path, 2000)  # pragma: no cover
    return out


def sentence_window(text: str, path: Path) -> List[Tuple[str, Dict[str, str]]]:
    """Small chunks for retrieval; wider context_window in metadata for prompt expansion."""
    chunk_size, overlap = 300, 60
    splitter = RecursiveCharacterTextSplitter.from_language(
        language=Language.MARKDOWN, chunk_size=chunk_size, chunk_overlap=overlap
    )
    docs = splitter.create_documents([text])
    out: List[Tuple[str, Dict[str, str]]] = []
    for i, d in enumerate(docs):
        content = d.page_content
        needle = content[: min(80, len(content))] if content else ""
        idx = text.find(needle) if needle else -1
        if idx < 0:
            idx = 0  # pragma: no cover
        half = 600
        ctx_start = max(0, idx - half)
        ctx_end = min(len(text), idx + len(content) + half)
        context_window = text[ctx_start:ctx_end]
        if len(context_window) > 12000:
            context_window = context_window[:12000]  # pragma: no cover
        out.append(
            (
                content,
                {
                    "chunk_strategy": "sentence_window",
                    "chunk_type": "fragment",
                    "chunk_name": path.stem,
                    "chunk_index": str(i),
                    "context_window": context_window,
                },
            )
        )
    return out


def _js_ts_lang(ext: str) -> Language:
    if ext in (".ts", ".tsx"):
        return getattr(Language, "TS", getattr(Language, "TYPESCRIPT", Language.HTML))
    return getattr(Language, "JS", getattr(Language, "JAVASCRIPT", Language.HTML))


def _device_family_for_path(path: Path) -> str:
    """Ngspice device subdir under .../devices/<family>/... or CORE."""
    for i, part in enumerate(path.parts):
        if part.casefold() == "devices" and i + 1 < len(path.parts):
            return path.parts[i + 1].upper()
    return "CORE"
