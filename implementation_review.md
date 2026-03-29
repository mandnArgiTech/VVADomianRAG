# Universal Domain RAG — Cursor Implementation Review

## Overall Verdict

Cursor did a solid job. The major architecture is all there — multi-collection,
multi-mode CLI, all 11 chunking strategies, concept tagging, content-type detection,
deterministic IDs, stale cleanup, embedding retry, Rally API, Confluence API (v1+v2),
MIB regex parser, sanitizer, feed_domain_doc as both MCP tool and standalone function,
and the status dashboard. No missing pillars.

The issues below are refinements and robustness, not missing phases.

---

## Issues by File

### ingest.py

#### Issue #1 — CRITICAL: Missing IGNORED_DIRS / IGNORED_EXTS for code mode

**Location:** Lines 1700-1720 (file iteration for code mode)

**Problem:** The code-mode skip list only filters a handful of binary extensions
(.png, .jpg, .gif, .zip, .exe, .dll, .bin, .pdb, .obj, .o, .a, .lib). Your
original script had comprehensive ignore sets:

```python
# ORIGINAL (missing from new version):
IGNORED_DIRS = {
    ".git", "node_modules", "build", "dist", "target", "__pycache__",
    "bin", "obj", "vendor", ".idea", ".vs", ".venv", "venv", ".tox",
}

IGNORED_EXTS = {
    ".exe", ".dll", ".so", ".o", ".class", ".jar", ".zip", ".tar",
    ".gz", ".7z", ".rar", ".png", ".jpg", ".jpeg", ".gif", ".svg",
    ".ico", ".webp", ".pdf", ".bin", ".wasm", ".lock",
}
```

**Impact:** Running `--mode code` on the NMS codebase will try to ingest:
- .git objects (thousands of binary files)
- node_modules (if any JS tooling exists)
- build artifacts, virtualenvs
- __pycache__ bytecode files

This will massively slow down ingestion and pollute the vector store with garbage.

**Fix:**
```python
# Add near the top of ingest.py, after constants:

IGNORED_DIRS = {
    ".git", ".svn", ".hg", "node_modules", "build", "dist", "target",
    "__pycache__", "bin", "obj", "vendor", ".idea", ".vs", ".vscode",
    ".venv", "venv", ".tox", ".eggs", ".mypy_cache", ".pytest_cache",
    "CMakeFiles", "Debug", "Release", "x64", "x86",
}

IGNORED_EXTS = {
    ".exe", ".dll", ".so", ".o", ".a", ".lib", ".class", ".jar",
    ".zip", ".tar", ".gz", ".7z", ".rar", ".bz2", ".xz",
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".webp", ".bmp",
    ".pdf", ".bin", ".wasm", ".lock", ".pyc", ".pyo", ".pdb",
    ".woff", ".woff2", ".ttf", ".eot", ".map",
    ".mp3", ".mp4", ".avi", ".mov", ".wmv",
    ".db", ".sqlite", ".sqlite3",
}
```

Then update `iter_files()` to respect them when source_type is "code":

```python
def iter_files(root: Path, exts: Optional[set] = None, 
               skip_dirs: Optional[set] = None) -> List[Path]:
    if root.is_file():
        return [root]
    out: List[Path] = []
    for dirpath, dirnames, files in os.walk(root):
        if skip_dirs:
            dirnames[:] = [d for d in dirnames if d not in skip_dirs]
        for fn in files:
            p = Path(dirpath) / fn
            if exts and p.suffix.lower() not in exts:
                continue
            if skip_dirs and p.suffix.lower() in IGNORED_EXTS:
                continue
            out.append(p)
    return sorted(out)
```

And in `ingest_run()` where code files are collected (~line 1702):

```python
if args.mode == "code":
    skip = IGNORED_EXTS
    paths = iter_files(root, None, skip_dirs=IGNORED_DIRS)
    paths = [p for p in paths if p.suffix.lower() not in skip]
```

---

#### Issue #2 — LOW: Module-level queue globals shared across modes

**Location:** Lines 272-277

**Problem:** `chunk_q` and `result_q` are module-level globals. If
`feed_domain_document()` is called from the MCP server while a separate CLI
ingestion is running, they could collide.

**Impact:** In practice this doesn't trigger because the MCP `feed_domain_doc`
tool uses its own direct embedding path (lines 2190-2198) rather than the
queue-based pipeline. But it's a latent bug if someone calls `ingest_run()`
from a library context.

**Fix (optional, for robustness):**
Move queue creation inside `ingest_run()` and pass as parameters to workers,
rather than using module globals. Low priority — only matters if you start
using ingest.py as an importable library beyond `feed_domain_document`.

---

#### Issue #3 — INFO: Checkpoint format changed (expect full re-ingest on first run)

**Location:** Lines 1644-1651

**Problem:** Original checkpoint format was `{filepath: md5_hash}` as a flat dict.
New format is `{collection_name::checkpoint: json_string_of_hashes}`. Old
checkpoints won't be recognized.

**Impact:** The first run after upgrade will re-ingest everything. This is expected
behavior, not a bug — but on a large NMS codebase, this could take hours.

**Mitigation:** Plan for it. Run the first post-upgrade ingestion overnight.
Or add a migration function that reads the old format and converts it:

```python
def migrate_old_checkpoint(db_path: Path, collection_name: str) -> None:
    """One-time migration from v1 flat checkpoint to v2 per-collection format."""
    old_path = db_path / "ingestion_checkpoint.json"
    new_path = db_path / "ingest_checkpoint.json"
    if old_path.exists() and not new_path.exists():
        try:
            with open(old_path, encoding="utf-8") as fh:
                old_data = json.load(fh)
            # Old format: {filepath: md5_hash}
            # New format: {collection::checkpoint: json({filepath: md5_hash})}
            new_data = {f"{collection_name}::checkpoint": json.dumps(old_data)}
            with open(new_path, "w", encoding="utf-8") as fh:
                json.dump(new_data, fh, indent=2)
            logger.info("Migrated old checkpoint (%d files) to new format", len(old_data))
        except Exception as exc:
            logger.warning("Checkpoint migration failed: %s", exc)
```

---

#### Issue #4 — LOW: sentence_window lost context_window metadata

**Location:** Lines 1208-1224

**Problem:** Original script had a clever approach: 200-char chunks for retrieval
with a ~1000-char context window stored in metadata for query-time prompt expansion.
The new version is a standard RecursiveCharacterTextSplitter with 1200-char chunks
and no context window.

**Impact:** Minor. This only affects .md/.txt files within code repos (README files,
inline docs). The markdown_domain strategy handles domain docs properly.

**Fix (nice-to-have):**
Restore the original context_window approach if you valued it. Otherwise leave as-is.

---

#### Issue #5 — MEDIUM: "why" triggers false positive rationale tagging

**Location:** Lines 183-189 (CONTENT_TYPE_SIGNALS → "rationale")

**Problem:** The single word "why" appears in the signal list. This matches
virtually any text that asks or answers a question:
- Code comments: `// check why this returns null`
- Bug descriptions: `Investigating why the connection drops`
- Any explanatory text

This causes many chunks to be incorrectly tagged as "rationale" content type.

**Fix:**
Replace single-word "why" with multi-word phrases that actually signal rationale:

```python
"rationale": [
    "the reason why",
    "that's why we",
    "rationale",
    "design decision",
    "trade-off",
    "tradeoff",
    "motivation for",
    "we chose",
    "was chosen because",
    "instead of",
    "the thinking behind",
    "decided to",
],
```

Also consider similar issue with "because" — very common word. Should be
"because we", "because this", or just removed from the signal list.

---

### mcp_server.py

#### Issue #6 — MEDIUM: $contains substring matching for concepts

**Location:** Line 466

**Problem:** ChromaDB's `$contains` operator does substring matching on strings.
Concepts are stored as comma-separated values like `"stp,forwarding_table,vlan"`.

Searching for concept `"stp"` works correctly. But searching for `"st"` would
also match — false positive. And searching for `"table"` would match
`"forwarding_table"` — also a false positive.

**Impact:** For v1 this is acceptable because concept IDs tend to be distinct
enough that accidental substring matches are rare. But as the concept registry
grows, this becomes a real problem.

**Fix (v2):** Two options:
1. Pad concepts with delimiters: store as `"|stp|forwarding_table|vlan|"` and
   search with `$contains: "|stp|"` — prevents substring matches.
2. Use ChromaDB metadata arrays when available (ChromaDB is adding list-type
   metadata support).

For now, add delimiter padding in `extract_concepts()` and the search tool:

```python
# In extract_concepts():
return "|" + "|".join(sorted(found)) + "|" if found else ""

# In search_concepts tool:
where={"concepts": {"$contains": f"|{concept}|"}}
```

---

#### Issue #7 — LOW: Dynamic import of ingest.py has side-effect risk

**Location:** Lines 496-507

**Problem:** `_load_ingest_module()` uses `importlib` to dynamically import
ingest.py at runtime. If ingest.py has module-level side effects (global
queues, threading events), they'll be created during the MCP tool call.

**Impact:** Low. The signal handlers in `main()` are gated behind
`if __name__ == "__main__"` so they won't fire. The module-level
`shutdown_event = threading.Event()` (line 270) creates an event but
it's harmless. The `_embed_lock` (line 271) could theoretically conflict
if both MCP and CLI are running in the same process, but they aren't.

**Fix (optional):** Move `feed_domain_document()` to a separate module
(e.g., `domain_feeder.py`) that imports only what it needs from ingest.py,
rather than importing the entire module.

---

### build.ps1

#### Issue #8 — LOW: tree-sitter-scheme requires git on PATH

**Location:** Line 124

**Problem:** `pip install "git+https://github.com/6cdh/tree-sitter-scheme.git@..."`
requires git to be installed and on PATH. On locked-down corporate machines,
git may not be available.

**Impact:** The validation step (line 168) catches the failure gracefully and
shows a warning. Scheme chunking falls back to regex. Only affects gEDA/Lepton-EDA
ingestion.

**Fix:** Add a check before attempting the git-based install:

```powershell
# Check if git is available before trying git+https install
$gitAvailable = $false
try {
    & git --version 2>$null | Out-Null
    $gitAvailable = ($LASTEXITCODE -eq 0)
} catch {}

if ($gitAvailable) {
    & "$BaseDir\Python\Scripts\pip.exe" install "git+https://github.com/6cdh/tree-sitter-scheme.git@c6cb7c7d7a04b3f5d999c28e2e9c0c31b2d50ece"
} else {
    Write-Host "      git not found — skipping tree-sitter-scheme (Scheme will use regex fallback)" -ForegroundColor DarkYellow
}
```

---

### run.ps1

#### Issue #9 — HIGH: Default source folder wrong for non-code modes

**Location:** Lines 80-86

**Problem:** When SOURCE_FOLDER is not set, the script defaults to
`$BaseDir\Codebase` for ALL modes except status/rally/wiki. This means:

```powershell
.\run.ps1 -Mode domain -Domain nms     # → tries to ingest domain docs from Codebase/
.\run.ps1 -Mode rfc                    # → tries to ingest RFCs from Codebase/
.\run.ps1 -Mode mib -Domain nms        # → tries to ingest MIBs from Codebase/
```

All of these will find code files, not the intended content.

**Fix:** Map mode to the correct default source folder:

```powershell
# Replace lines 80-86 with:
$modeDefaultSources = @{
    "code"          = "Codebase"
    "domain"        = "DomainDocs"
    "rfc"           = "RFCs"
    "mib"           = "MIBs"
    "community"     = "CommunityData"
    "release-notes" = "Codebase"       # usually lives alongside code
    "theory"        = "DomainDocs"     # or create a separate Theory folder
    "customer"      = "CommunityData"  # or create CustomerTickets folder
}

if ($Mode -ne "status" -and $Mode -ne "rally" -and $Mode -ne "wiki" -and $env:SOURCE_FOLDER -eq "") {
    $defaultFolder = $modeDefaultSources[$Mode]
    if (-not $defaultFolder) { $defaultFolder = "Codebase" }
    $defaultSrc = Join-Path $BaseDir $defaultFolder
    if (Test-Path -LiteralPath $defaultSrc) {
        $env:SOURCE_FOLDER = (Resolve-Path -LiteralPath $defaultSrc).Path
        Write-Host " Default source  : $env:SOURCE_FOLDER (for mode=$Mode)" -ForegroundColor Gray
    }
}
```

Also add the extra default folders to build.ps1 if not already present (they are — 
line 65-68 already creates DomainDocs, RFCs, MIBs, CommunityData).

---

### sanitizer.py

#### Issue #10 — MEDIUM: Hostname regex too aggressive

**Location:** Line 10 (the FQDN pattern)

**Problem:** The pattern matches any multi-part domain-like string:
```regex
\b(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}\b
```

This matches legitimate technical terms in customer tickets about networking:
- `ieee802.1d` → replaced with [hostname]
- `rfc4188.txt` → replaced with [hostname]
- `layer2.forwarding` → replaced with [hostname]
- `snmp.polling` → replaced with [hostname]
- `cisco.com` → correctly replaced (this is a real hostname)

In NMS customer tickets, technical dotted notation is common and meaningful.

**Fix:** Narrow the pattern to require at least 3 parts (subdomain.domain.tld)
or use a TLD whitelist:

```python
# Option A: Require 3+ parts (subdomain.domain.tld)
(
    r"\b(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.){2,}[a-zA-Z]{2,}\b",
    "[hostname]",
),

# Option B: TLD whitelist (more precise, more maintenance)
# Only match if the last part is a known TLD
(
    r"\b(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+(?:com|net|org|edu|gov|io|co|us|uk|de|in)\b",
    "[hostname]",
),
```

Option A is simpler and catches most real hostnames while preserving two-part
technical terms like `ieee802.1d` and `layer2.forwarding`.

---

## Priority Summary

| Priority | Issue | File | Fix Effort | Description |
|----------|-------|------|------------|-------------|
| **HIGH** | #1 | ingest.py | 15 min | Missing IGNORED_DIRS/EXTS for code mode |
| **HIGH** | #9 | run.ps1 | 10 min | Default source folder wrong for non-code modes |
| **MEDIUM** | #5 | ingest.py | 5 min | "why"/"because" false positive rationale tags |
| **MEDIUM** | #10 | sanitizer.py | 5 min | Hostname regex too aggressive |
| **MEDIUM** | #6 | mcp_server.py | 15 min | $contains substring matching for concepts |
| **LOW** | #3 | ingest.py | 20 min | Checkpoint migration (or just plan for full re-ingest) |
| **LOW** | #4 | ingest.py | 15 min | Restore context_window in sentence_window |
| **LOW** | #8 | build.ps1 | 5 min | Check for git before tree-sitter-scheme install |
| **LOW** | #2 | ingest.py | 30 min | Module-level queue globals |
| **LOW** | #7 | mcp_server.py | 10 min | Dynamic import side-effect risk |

## Recommended Action

Fix #1 and #9 before first use — these will cause real problems on the NMS codebase.
Fix #5 and #10 soon after — they affect tagging quality.
The rest can be addressed as you encounter them.

---

## What's Working Well

- **All 11 chunking strategies** implemented and correctly dispatched
- **Multi-collection routing** works as designed
- **Rally API** with filtering, pagination, CSV fallback
- **Confluence API** with v2→v1 fallback, label filtering, stub skipping
- **MIB parser** handles OBJECT-TYPE, NOTIFICATION-TYPE, MODULE-IDENTITY, TEXTUAL-CONVENTION
- **Deterministic IDs** + upsert (Fix 1 from spec ✓)
- **Stale cleanup** with --clean-stale flag (Fix 2 ✓)
- **Embedding retry** with backoff and batch splitting (Fix 3 ✓)
- **Per-strategy size limits** (Fix 4 ✓)
- **feed_domain_document()** works both as MCP tool and standalone function
- **Status dashboard** shows all collections with concept coverage
- **Ingestion manifest** appends to JSONL for lineage tracking
- **build.ps1 mcp.json merge** preserves existing MCP servers
- **build.ps1 validation smoke test** catches missing dependencies
- **run.ps1** passes all new parameters correctly to ingest.py
- **sanitizer.py** handles IP, email, phone, MAC with configurable company names
- **Graceful degradation** for optional deps (tree-sitter, requests, beautifulsoup4, pysmi)
