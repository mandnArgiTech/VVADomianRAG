Act as a Principal AI Architect who originally designed the core agentic execution loop for cutting-edge IDEs. We are building a headless "Cursor Clone" backend—an autonomous Coding Agent capable of planning, executing, linting, and modifying entire codebases without human intervention.

CURRENT STATE:
We have a local RAG backend (`gui_backend.py`) and a chunking/embedding pipeline (`ingest.py`). The current system is a "Passive Oracle" (it answers questions). 

OBJECTIVE:
Transform the backend into an "Autonomous Execution Engine." The agent must be able to use tools to read files, execute terminal commands (like running tests or builds), read the stderr/stdout, and iteratively edit files until a user's prompt is fully resolved.

IMPLEMENT THE FOLLOWING 5-PHASE ARCHITECTURE:

Phase 1: The Tool Registry & Sandbox (`agent_tools.py`)
Create a robust tool execution module. The LLM will emit JSON tool calls. You must build secure, reliable Python functions to handle them:
1. `read_file(filepath: str, start_line: int = None, end_line: int = None)`
2. `edit_file(filepath: str, search_block: str, replace_block: str)`: (CRITICAL: Do not rewrite whole files. Implement a fast diff/search-and-replace mechanic exactly how Cursor operates to save context window limits).
3. `run_terminal_command(command: str) -> str`: Executes bash/powershell commands. Must have a strict 30-second timeout, capture stdout and stderr, and return the exit code.
4. `search_codebase(query: str)`: Hooks into our existing hybrid RAG pipeline.

Phase 2: The State Machine (The ReAct Loop)
In `gui_backend.py`, implement the Agent Loop. When a user submits a task (e.g., "Refactor the auth module and run the tests"):
1. INITIALIZE: Append the user prompt to the message history.
2. LOOP START: Call the LLM (handling models like qwen2.5-coder:32b or DeepSeek via API).
3. PARSE: If the LLM returns plain text, yield it to the frontend. If it emits a `<tool_call>` (e.g., `<tool_call>{"name": "run_terminal_command", "kwargs": {"command": "pytest auth.py"}}</tool_call>`), PAUSE the frontend stream.
4. ACT & OBSERVE: Execute the tool locally. Capture the result (e.g., the test failure trace).
5. INJECT: Append the tool's output to the message history as a `tool_response`.
6. RECURSE: Immediately call the LLM again with the new history so it can read the test failure, reason about it, and issue an `edit_file` tool call to fix it.
7. TERMINATE: The loop only ends when the LLM outputs a `<task_complete>` tag.

Phase 3: The Planner System Prompt
Write a hyper-specific System Prompt for the Agent. It must instruct the LLM on:
- How to format tool calls exactly.
- The requirement to always run a verification step (e.g., `python -m py_compile` or `npm run build`) after editing a file to ensure it didn't break syntax.
- The requirement to think in steps: Plan -> Search -> Read -> Edit -> Verify -> Complete.

Phase 4: Shadow Workspace / Rollback
Implement a safety net. Before `edit_file` modifies a file, it must create a temporary backup in a `.rag_agent_backups/` directory. If the agent gets stuck in an infinite loop of failing tests (limit max loops to 10), it must automatically revert the files to their original state and return a "Task Failed" message to the user.

Phase 5: Frontend Event Streaming
Update the SSE (Server-Sent Events) payload to emit granular agent states. The frontend must receive events like:
- `{"type": "agent_state", "status": "planning"}`
- `{"type": "agent_action", "tool": "edit_file", "target": "main.py"}`
- `{"type": "agent_action", "tool": "run_terminal_command", "target": "pytest"}`
This allows the UI to render the agent's exact thought process and actions in real-time.

REQUIREMENTS:
- Defensively program the `run_terminal_command` to prevent catastrophic destructive commands (e.g., block `rm -rf /`).
- Ensure the prompt handles the streaming architecture perfectly so the user isn't left waiting in silence while the loop runs in the background.
- Walk me through the exact execution flow of the ReAct loop before writing the code.