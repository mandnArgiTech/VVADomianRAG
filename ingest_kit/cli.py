"""CLI entrypoint for ``python ingest.py`` (lazy imports from ``ingest``)."""

from __future__ import annotations

import argparse
import logging
import os
import signal
from pathlib import Path
from typing import List, Optional

from ingest_kit.pipeline.orchestrator import ingest_run

logger = logging.getLogger("ingest")

_NGSPICE_GITIGNORE_ENTRIES = [
    "src/frontend/",
    "src/x11/",
    "src/misc/",
    "src/compat/",
    "src/spicelib/devices/hisim*",
    "src/spicelib/devices/soi*",
    "src/spicelib/devices/adms/",
    "src/spicelib/devices/numd*",
    "src/spicelib/devices/nbjt*",
    "src/spicelib/devices/numos*",
    "src/ciderlib/",
    "tests/",
    "*.txt",
]


def _handle_sig(*_args):
    import ingest as ing

    ing.shutdown_event.set()  # pragma: no cover


def build_arg_parser() -> argparse.ArgumentParser:
    import ingest as ing

    p = argparse.ArgumentParser(description="Universal domain RAG ingestion")
    p.add_argument(
        "--mode",
        choices=[
            "code",
            "domain",
            "rfc",
            "rally",
            "customer",
            "mib",
            "wiki",
            "release-notes",
            "theory",
            "community",
            "status",
        ],
        default=os.environ.get("INGEST_MODE", "").strip() or None,
    )
    p.add_argument("--source", default=os.environ.get("SOURCE_FOLDER", "").strip() or None)
    p.add_argument("--domain", default=os.environ.get("INGEST_DOMAIN", "general"))
    p.add_argument("--collection", default=os.environ.get("CHROMA_COLLECTION", "").strip() or None)
    p.add_argument(
        "--db-path",
        default=os.environ.get("DB_PATH", "").strip() or ing._default_vector_db_dir(),
    )
    p.add_argument("--rally-project", default=os.environ.get("RALLY_PROJECT", "").strip() or None)
    p.add_argument("--rally-filter", default=os.environ.get("RALLY_FILTER", "").strip() or None)
    p.add_argument("--confluence-space", default=os.environ.get("CONFLUENCE_SPACE", "").strip() or None)
    p.add_argument("--concept-registry", default=str(ing.SCRIPT_DIR / "concept_registry.json"))
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--force", action="store_true")
    p.add_argument(
        "--recreate-collection",
        action="store_true",
        help=(
            "If the target Chroma collection's embedding dimension does not match the "
            "current model, delete that collection and its checkpoint entry, then ingest "
            "fresh (destructive for that collection only)."
        ),
    )
    p.add_argument(
        "--clean-stale",
        action="store_true",
        help="Delete Chroma chunks for sources removed from disk (checkpoint always pruned)",
    )
    p.add_argument(
        "--mib-keep-deprecated",
        action="store_true",
        help="Ingest deprecated/obsolete MIB objects (default: skip)",
    )
    p.add_argument(
        "--confluence-label",
        default=os.environ.get("CONFLUENCE_LABEL", "").strip() or None,
        help="Filter wiki pages by label (Confluence API)",
    )
    p.add_argument(
        "--git-diff",
        action="store_true",
        help="Only ingest files changed vs --git-diff-base (git); deletes removed paths from Chroma",
    )
    p.add_argument(
        "--git-diff-base",
        default=os.environ.get("GIT_DIFF_BASE", "").strip() or None,
        help="Git ref to diff against (default: last stored ingest ref or HEAD~1)",
    )
    p.add_argument("--verbose", action="store_true")
    p.add_argument(
        "--write-ngspice-gitignore",
        action="store_true",
        help=(
            "Write (or update) a .gitignore in the --source directory that excludes "
            "Ngspice legacy boilerplate directories before ingestion begins."
        ),
    )
    p.add_argument(
        "--allow-language-split-fallback",
        action="store_true",
        help=(
            "When tree-sitter is not installed for C/C++/Java, allow RecursiveCharacterTextSplitter "
            "fallback instead of skipping those files. Same effect as INGEST_ALLOW_LANGUAGE_SPLIT_FALLBACK=1."
        ),
    )
    p.add_argument(
        "--enrich-metadata",
        action="store_true",
        help=(
            "Call local Ollama to add llm_summary, llm_tags, llm_relations, llm_physics_model per chunk "
            "(code source_type only)."
        ),
    )
    p.add_argument(
        "--enrich-model",
        default=os.environ.get("ENRICH_MODEL", "qwen2.5:0.5b"),
        help="Ollama model for --enrich-metadata (default: ENRICH_MODEL or qwen2.5:0.5b).",
    )
    p.add_argument(
        "--enrich-timeout",
        type=float,
        default=float(os.environ.get("ENRICH_OLLAMA_TIMEOUT", "180")),
        help=(
            "Seconds to wait per Ollama /api/generate call during enrichment "
            "(default: ENRICH_OLLAMA_TIMEOUT or 180). Raise if the model is slow or the GPU is busy with embeds."
        ),
    )
    return p


def write_ngspice_gitignore(source_dir: Path) -> None:
    """Create or update the .gitignore in *source_dir* with Ngspice boilerplate exclusions."""
    gi_path = source_dir / ".gitignore"
    existing: set = set()
    if gi_path.exists():
        try:
            existing = {ln.strip() for ln in gi_path.read_text(encoding="utf-8").splitlines()}
        except (OSError, UnicodeDecodeError) as exc:
            logger.warning("Could not read %s (%s); will append Ngspice entries", gi_path, exc)
            existing = set()
    to_add = [e for e in _NGSPICE_GITIGNORE_ENTRIES if e not in existing]
    if not to_add:
        logger.info("Ngspice .gitignore already up to date: %s", gi_path)
        return
    with gi_path.open("a", encoding="utf-8") as fh:
        fh.write("\n# Ngspice legacy boilerplate (auto-added by ingest.py --write-ngspice-gitignore)\n")
        for entry in to_add:
            fh.write(entry + "\n")
    logger.info("Wrote %d Ngspice .gitignore entries to %s", len(to_add), gi_path)


def main(argv: Optional[List[str]] = None) -> int:
    signal.signal(signal.SIGINT, _handle_sig)
    signal.signal(signal.SIGTERM, _handle_sig)
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    if getattr(args, "write_ngspice_gitignore", False):
        raw_src = args.source or os.environ.get("SOURCE_FOLDER", "").strip()
        if not raw_src:
            parser.error("--source is required when using --write-ngspice-gitignore")
        src = Path(raw_src).resolve()
        if not src.is_dir():
            parser.error(f"--source path does not exist or is not a directory: {src}")
        write_ngspice_gitignore(src)
        if not args.mode:
            return 0
    if not args.mode:
        if args.source or os.environ.get("SOURCE_FOLDER"):
            args.mode = "code"
            args.domain = args.domain or "general"
        else:
            parser.error("--mode is required unless SOURCE_FOLDER is set (legacy code ingest)")
    if args.mode != "status":
        if args.mode not in ("rally", "wiki") and not args.source and not os.environ.get("SOURCE_FOLDER"):
            parser.error("--source required for this mode (or set SOURCE_FOLDER)")  # pragma: no cover
    return ingest_run(args)
