Act as a Principal Systems Architect. We are upgrading our local RAG Agent to a "Principal Architect" architecture (Level 5). We are injecting self-healing, syntax validation, and self-review protocols.

Implement the following 3 phases precisely.

### PHASE 1: The Syntax Sentinel (Add `check_syntax` in `agent_tools.py`)
Current Issue: The LLM frequently makes indentation or syntax errors during `edit_file` but doesn't realize it until a runtime crash occurs.
Action:
1. In `agent_tools.py`, create a new tool: `check_syntax(session: AgentSession, filepath: str) -> ToolResult`.
2. Logic: 
   - If it's a `.py` file, use Python's built-in `ast.parse()` or `py_compile.compile()` to check for valid syntax. If it fails, catch the `SyntaxError` or `IndentationError` and return the exact line number and error message in the `ToolResult`.
   - If it's a `.js`, `.json`, or `.html` file, you can attempt a lightweight check (e.g., `json.loads` for JSON), or return "Syntax check not natively supported for this extension yet."
   - If successful, return "Syntax is valid."
3. Register this tool in `TOOL_REGISTRY` and `openai_style_agent_tool_schemas`.

### PHASE 2: The Self-Review Protocol (Add `get_session_diff` in `agent_tools.py`)
Current Issue: After many iterations, the agent forgets exactly what it changed across multiple different files.
Action:
1. In `agent_tools.py`, create a new tool: `get_session_diff(session: AgentSession) -> ToolResult`.
2. Logic: Iterate through `session.backed_up` (files edited) and `session.created_files`. 
3. Use Python's `difflib.unified_diff` to compare the original backed-up file with the current workspace file. 
4. Return a compiled string of all diffs. This acts as the agent's "Pull Request" review.
5. Register this tool in `TOOL_REGISTRY` and `openai_style_agent_tool_schemas`.

### PHASE 3: The Revert Tool and Principal Prompt (Update `gui_backend.py` & `agent_tools.py`)
Current Issue: If the agent breaks a file, it gets stuck trying to fix it. It needs a way to undo a single mistake without rolling back the entire session.
Action:
1. In `agent_tools.py`, create `revert_file(session: AgentSession, filepath: str) -> ToolResult`. It should restore that specific file from `session._backup_dir` if it exists. Register it.
2. In `gui_backend.py`, locate `build_agent_system_prompt()`.
3. Update the "Workflow" section to enforce the Principal Protocol:
   - "5. VALIDATE: After EVERY `edit_file` or `create_file` on a code file, you MUST immediately run `check_syntax` on that file. Do not proceed until syntax is valid."
   - "6. REVIEW: Before you emit `<task_complete>`, you MUST run `get_session_diff` to review your overall changes. If you realize you made a catastrophic error in a specific file, use `revert_file` to undo it, then try again."

REQUIREMENTS:
- Do not break the native JSON tool calling previously implemented for Anthropic/DeepSeek.
- Do not break the circuit breaker or roadmap logic implemented in previous steps.