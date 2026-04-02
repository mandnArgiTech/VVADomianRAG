Act as a Principal Systems Architect. We are upgrading our local RAG Agent from a basic ReAct loop to an Advanced Cognitive Architecture (Level 3). 

Implement the following three phases precisely without breaking the existing native tool calling or rollback sandboxing.

### PHASE 1: The Telescope (Add `get_repo_map` Tool)
Current Issue: The agent relies entirely on RAG. It has no way to "look around" and see the holistic folder structure of the workspace.
Action in `agent_tools.py`:
1. Create a new tool: `get_repo_map(session: AgentSession, max_depth: int = 3) -> ToolResult`.
2. Logic: Use `pathlib` to recursively walk `session.workspace_root` up to `max_depth`. 
3. Formatting: Return a clean, tree-like string representation of the directory structure. 
4. Filtering: You MUST explicitly ignore common noise directories (`.git`, `__pycache__`, `node_modules`, `venv`, `.env`, `.rag_agent_backups`, `.vscode`).
5. Register it in `TOOL_REGISTRY` and `openai_style_agent_tool_schemas`.

### PHASE 2: The Cognitive System Prompt (Update `gui_backend.py`)
Current Issue: The agent fires tool calls reflexively without a scratchpad, leading to logical errors in complex codebases.
Action in `gui_backend.py`:
1. Locate `build_agent_system_prompt()`.
2. Rewrite the "Workflow" section to enforce strict Chain-of-Thought formatting. 
3. Instruct the agent: "Before every tool call, you MUST open a `<thinking>` tag to outline your logic, hypotheses, and plan. Close it with `</thinking>`, and THEN emit your tool call."
4. Add a rule for the new tool: "If you do not know the layout of the project, use `get_repo_map` before attempting to read or edit files."

### PHASE 3: The Human-in-the-Loop Protocol (Update `gui_backend.py`)
Current Issue: If the agent hits an ambiguous request or a failing test, it guesses until it hits `max_iterations` and rolls back.
Action in `gui_backend.py`:
1. In the system prompt, add a new instruction: "If a requirement is highly ambiguous, or you are failing to fix a bug after 3 attempts, DO NOT guess. End your turn by emitting `<ask_human>Your specific question</ask_human>`."
2. In the `execute_agent_step` function, add a regex parser to catch `<ask_human>(.*?)</ask_human>`.
3. If caught, yield a `step_result` with a new kind: `STEP_ASK_HUMAN`. 
4. In `agent_sse_stream`, handle this result by gracefully pausing the session (similar to `STEP_COMPLETE`), emitting an `agent_state` of `status: 'waiting_for_user'`, and saving the files WITHOUT triggering `session.rollback()`. 

REQUIREMENTS:
- Do not alter the native tool JSON routing we just built for Anthropic/DeepSeek.
- Ensure the `get_repo_map` tool is incredibly fast and strictly truncates output if the repository is massive (e.g., limit to 2000 lines).