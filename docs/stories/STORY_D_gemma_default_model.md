# STORY D: Gemma 3/4 as Default Chat Model with SPICE-Optimized System Prompt

**Repository:** `mandnArgiTech/VVADomianRAG` branch `ngspice_rag`
**Priority:** High
**Depends on:** Story C (domain docs ingested — Gemma needs them as context)
**Estimated effort:** 3–4 hours
**Files to modify:** `query.py`, `gui_backend.py`, `mcp_server.py`, `run.sh`, `run.ps1`
**Files to create:** `tests/test_gemma_integration.py`, `system_prompts/spice_engineer.md`

---

## Business Context

The RAG currently defaults to `qwen2.5-coder:32b` for chat in the GUI and `llama3` for the query CLI. We want **Gemma 3 27B** (or Gemma 4 when available via Ollama) as the default chat model for all interfaces because:

1. **Context window**: Gemma 3 27B supports 128K tokens — critical when the RAG retrieves 10–20 chunks (each 500–2000 chars) plus call-graph expansion plus domain doc cross-references. qwen2.5-coder:32b's 32K context fills up fast.
2. **Multilingual math**: Gemma 3 handles LaTeX/math notation in the domain docs without mangling it.
3. **Fits the hardware**: 27B Q4 quantization runs well on the RTX A6000 48GB with room for embeddings.
4. **Instruction following**: Gemma 3 follows structured system prompts reliably, which we need for the SPICE-engineer persona.

This story also creates a **domain-optimized system prompt** that tells Gemma it's a SPICE kernel engineer, instructs it to cross-reference ngspice C patterns with NodalAI Python implementations, and teaches it to interpret the `source_c_files` metadata to connect domain docs to code.

---

## Scope

1. Change default LLM model from `qwen2.5-coder:32b` / `llama3` to `gemma3:27b` across all interfaces
2. Create a `system_prompts/spice_engineer.md` file with a domain-specific system prompt
3. Auto-load the system prompt when `--domain spice` is active
4. Keep backward compatibility — any model can still be used via `RAG_LLM_MODEL` env var or `--chat-model` CLI flag

---

## Acceptance Criteria

### AC-1: Default model changed to gemma3:27b

**Given** no `RAG_LLM_MODEL` env var is set,
**When** the user starts `query.py --chat` or opens the GUI dashboard,
**Then** the LLM model used is `gemma3:27b` (not `qwen2.5-coder:32b` or `llama3`).

Implementation points:
- `gui_backend.py` line 179: change default from `"qwen2.5-coder:32b"` to `"gemma3:27b"`
- `query.py` line 1908: change `default=` from `"llama3"` to `"gemma3:27b"`

### AC-2: Model availability check at startup

**Given** the user starts any chat interface,
**When** `gemma3:27b` is not pulled in Ollama,
**Then** the system:
1. Logs a warning: `"Default model gemma3:27b not found. Run: ollama pull gemma3:27b"`
2. Falls back to any available model from the priority list: `["gemma3:27b", "gemma3:12b", "qwen2.5-coder:32b", "llama3", "mistral"]`
3. Logs which fallback model was selected

### AC-3: SPICE engineer system prompt created

**Given** the file `system_prompts/spice_engineer.md`,
**When** loaded,
**Then** it contains a system prompt with these elements:

```markdown
You are a SPICE kernel engineer working on NodalAI, a Python reimplementation of the ngspice circuit simulator.

Your role:
- Compare ngspice C reference implementations with NodalAI Python code when answering questions
- When RAG context includes domain doc chunks with **ngspice source:** metadata, reference those specific C files
- When RAG context includes code chunks with `calls` metadata, explain the call chain
- Focus on numerical accuracy: Newton-Raphson convergence, device limiters (DEVpnjlim, DEVfetlim), Jacobian stamping, companion models
- Use precise terminology: MNA matrix, RHS vector, conductance stamp, Norton equivalent, GMIN stepping, source stepping, PTC

When debugging convergence failures:
1. Check if the device limiter math matches ngspice (especially junction voltage clamping thresholds)
2. Check if the Jacobian stamp is complete (all partial derivatives present)
3. Check if the companion model correctly computes Ieq = Id - gd*Vd
4. Check if GMIN/source stepping schedules match ngspice defaults

Always cite specific function names from both codebases (e.g., "ngspice's `DIOload()` vs NodalAI's `_nr_loop` diode stamp block").
```

### AC-4: System prompt auto-loaded for spice domain

**Given** `query.py` is run with `--domain spice --chat`,
**When** the chat session starts,
**Then** the system prompt from `system_prompts/spice_engineer.md` is automatically prepended to the LLM context.

**Given** `gui_backend.py` dashboard with domain set to `spice`,
**When** a chat message is sent,
**Then** the system prompt is included in the Ollama API call's `system` field.

### AC-5: System prompt is domain-switchable

**Given** the `system_prompts/` directory,
**When** a file named `{domain}.md` exists (e.g., `spice_engineer.md` for domain `spice`, or `kinematica.md` for domain `kinematica`),
**Then** that prompt is loaded. If no domain-specific prompt exists, use a generic default.

Convention: `system_prompts/spice_engineer.md` for `--domain spice`.

### AC-6: Gemma-specific Ollama API parameters

**Given** the model is `gemma3:*`,
**When** the Ollama `/api/chat` call is made,
**Then** these parameters are set:
- `num_ctx: 65536` (use 64K of the 128K window — leave room for response)
- `temperature: 0.1` (low creativity for technical accuracy)
- `top_p: 0.9`
- `repeat_penalty: 1.1`

For non-Gemma models, keep existing parameter defaults.

### AC-7: Backward compatibility

**Given** `RAG_LLM_MODEL=qwen2.5-coder:32b` env var is set,
**When** any interface starts,
**Then** qwen2.5-coder:32b is used, not gemma3:27b. The env var always overrides the default.

### AC-8: Run scripts updated

**Given** `run.sh` and `run.ps1`,
**When** this story is complete,
**Then** the scripts include a comment documenting:
```bash
# Default chat model: gemma3:27b (128K context, fits A6000 48GB at Q4)
# Override: export RAG_LLM_MODEL=qwen2.5-coder:32b
# Pull: ollama pull gemma3:27b
```

### AC-9: All existing tests pass

`pytest tests/` — 0 failures.

---

## Implementation Guide

### Step 1: Create system prompt file

**File:** `system_prompts/spice_engineer.md`

Write the full system prompt as specified in AC-3. Keep it under 2000 tokens — it will be prepended to every LLM call, so brevity matters.

### Step 2: System prompt loader

**File:** `query.py`

Add a function:

```python
def _load_system_prompt(domain: str) -> str:
    """Load domain-specific system prompt from system_prompts/ directory."""
    prompt_dir = Path(__file__).parent / "system_prompts"
    # Try domain-specific file first
    for name in [f"{domain}_engineer.md", f"{domain}.md"]:
        p = prompt_dir / name
        if p.is_file():
            return p.read_text(encoding="utf-8").strip()
    # Generic fallback
    generic = prompt_dir / "default.md"
    if generic.is_file():
        return generic.read_text(encoding="utf-8").strip()
    return ""
```

Call this in the chat initialization path and pass the result to the Ollama API `system` parameter.

### Step 3: Change defaults in query.py

**File:** `query.py`, line 1908

```python
# Before:
default=(os.environ.get("RAG_LLM_MODEL", "") or "").strip() or "llama3",

# After:
default=(os.environ.get("RAG_LLM_MODEL", "") or "").strip() or "gemma3:27b",
```

### Step 4: Change defaults in gui_backend.py

**File:** `gui_backend.py`, line 179

```python
# Before:
os.environ.get("RAG_LLM_MODEL", "").strip() or "qwen2.5-coder:32b"

# After:
os.environ.get("RAG_LLM_MODEL", "").strip() or "gemma3:27b"
```

### Step 5: Model availability check

Add to both `query.py` (chat startup) and `gui_backend.py` (first chat request):

```python
_FALLBACK_MODELS = ["gemma3:27b", "gemma3:12b", "qwen2.5-coder:32b", "llama3", "mistral"]

def _check_model_available(model: str, ollama_url: str = "http://127.0.0.1:11434") -> str:
    """Check if model is available in Ollama. Return available model or fallback."""
    try:
        resp = urllib.request.urlopen(f"{ollama_url}/api/tags", timeout=5)
        data = json.loads(resp.read())
        available = {m["name"].split(":")[0] for m in data.get("models", [])}
        available_full = {m["name"] for m in data.get("models", [])}
        
        # Check exact match first, then prefix match
        if model in available_full or model in available:
            return model
        
        logger.warning("Model %s not found in Ollama. Checking fallbacks...", model)
        for fb in _FALLBACK_MODELS:
            fb_base = fb.split(":")[0]
            if fb in available_full or fb_base in available:
                logger.info("Falling back to model: %s", fb)
                return fb
        
        logger.warning("No fallback model found. Using %s anyway (will fail at generation time).", model)
        return model
    except Exception:
        return model  # Can't reach Ollama — just use the requested model
```

### Step 6: Gemma-specific Ollama parameters

In the Ollama API call functions in both `query.py` and `gui_backend.py`, detect Gemma models and adjust parameters:

```python
def _ollama_options_for_model(model: str) -> dict:
    """Return Ollama options dict tuned for the model."""
    if model.startswith("gemma"):
        return {
            "num_ctx": 65536,
            "temperature": 0.1,
            "top_p": 0.9,
            "repeat_penalty": 1.1,
        }
    # Default for other models
    return {
        "temperature": 0.2,
        "top_p": 0.95,
    }
```

### Step 7: Update run scripts

Add comments to `run.sh` and `run.ps1` as specified in AC-8.

---

## Test Plan

### File: `tests/test_gemma_integration.py`

```
Test ID | Description | Approach
--------|-------------|----------
GM-01   | Default model is gemma3:27b in query.py | Import argparse defaults, assert "gemma3:27b" is the default
GM-02   | Default model is gemma3:27b in gui_backend.py | Check the RAG_LLM_MODEL fallback constant
GM-03   | RAG_LLM_MODEL env var overrides default | Set env var to "qwen2.5-coder:32b", verify it's used
GM-04   | _load_system_prompt finds spice prompt | Create temp system_prompts/spice_engineer.md, assert loaded
GM-05   | _load_system_prompt returns empty for unknown domain | Assert _load_system_prompt("nonexistent") returns ""
GM-06   | _load_system_prompt falls back to default.md | Create temp default.md only, assert it's loaded for any domain
GM-07   | _ollama_options_for_model returns Gemma-specific params | Assert gemma3:27b gets num_ctx=65536, temperature=0.1
GM-08   | _ollama_options_for_model returns defaults for non-Gemma | Assert qwen2.5-coder:32b gets temperature=0.2
GM-09   | _check_model_available returns model when present | Mock Ollama /api/tags with gemma3:27b listed. Assert returns "gemma3:27b"
GM-10   | _check_model_available falls back when model missing | Mock /api/tags without gemma3:27b but with llama3. Assert returns "llama3"
GM-11   | system_prompts/spice_engineer.md exists and is < 2000 tokens | Check file exists, rough token count (chars/4) < 2000
GM-12   | System prompt contains key SPICE terminology | Assert "Newton-Raphson", "Jacobian", "companion model", "NodalAI" all present in prompt
```

### Manual validation

After implementation:

```bash
# Pull Gemma 3
ollama pull gemma3:27b

# Ingest domain docs (Story C must be done first)
./run.sh --mode domain --domain spice --source ./Studio-Portable-RAG/DomainDocs/ngspice

# Start chat with domain docs as context
./query.sh semantic "how does ngspice clamp diode junction voltage during NR iteration" --domain spice --chat
```

**Expected behavior:**
- Gemma 3 is used (logged at startup)
- System prompt identifies as SPICE kernel engineer
- Response references both ngspice `DEVpnjlim` from the domain doc AND the C code chunk
- Response suggests comparing with NodalAI's `_limit_junction_voltage`
- LaTeX math from domain docs is interpreted correctly in the response

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Gemma 3 27B doesn't fit A6000 at Q4 with embeddings running | 27B Q4 ≈ 16GB VRAM. A6000 has 48GB. Embeddings (nomic-embed-text) use ~1GB. Plenty of room. If issues arise, fall back to gemma3:12b. |
| Gemma 3 hallucinates ngspice function names not in context | System prompt explicitly says "only reference functions present in the RAG context". Low temperature (0.1) reduces hallucination. |
| Gemma 4 releases on Ollama before this ships | The fallback chain checks `gemma3:27b` first. When Gemma 4 is available, add `gemma4:27b` to top of `_FALLBACK_MODELS` list — one-line change. |
| 65K context window is expensive per query (slow) | On A6000, Gemma 3 27B Q4 generates ~15 tok/s at 64K context. Acceptable for interactive debugging. For batch, user can override to smaller model. |
| System prompt takes tokens away from RAG context | System prompt is < 2000 tokens. With 65K context, this is < 3% overhead. |

---

## Definition of Done

- [ ] `system_prompts/spice_engineer.md` exists with domain-specific prompt
- [ ] Default LLM model is `gemma3:27b` in `query.py` and `gui_backend.py`
- [ ] `_load_system_prompt()` loads domain-specific prompts
- [ ] `_check_model_available()` with fallback chain implemented
- [ ] `_ollama_options_for_model()` sets Gemma-specific parameters
- [ ] `run.sh` and `run.ps1` document the new default
- [ ] `RAG_LLM_MODEL` env var still overrides everything
- [ ] All 12 new tests pass, all existing tests pass
