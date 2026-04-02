Act as a Principal Systems Architect. We are upgrading our local RAG Agent to an advanced "Staff Engineer" architecture (Level 4). We are focusing on edit resilience, long-horizon task planning, and loop prevention.

Implement the following 3 phases precisely.

### PHASE 1: Surgical Edits (Upgrade `edit_file` in `agent_tools.py`)
Current Issue: `edit_file` requires an exact string match for `search_block`. LLMs frequently fail at exact indentation, causing edits to fail. 
Action:
1. In `agent_tools.py`, rewrite the `edit_file` function. 
2. Implement a "fuzzy whitespace" matching algorithm for the `search_block`. 
   - Logic: Strip leading/trailing whitespace from both the `search_block` lines and the target file lines when searching for a match. 
   - Once the correct block of lines is identified in the file, replace it with `replace_block`, but attempt to preserve the original base indentation of the matched block.
3. If multiple matches are found, return a `ToolResult` error asking the LLM to include more unique surrounding lines.
4. Update the `TOOL_DESCRIPTIONS` to reflect that `search_block` is now whitespace-flexible.

### PHASE 2: The Stateful Roadmap (Update `gui_backend.py`)
Current Issue: In tasks requiring 15+ iterations, the context window fills with terminal outputs, and the LLM forgets its original plan.
Action:
1. In `gui_backend.py`, locate `build_agent_system_prompt()`.
2. Update the "Workflow" section.
3. Add a strict instruction: "For any task requiring more than 2 steps, your FIRST action must be to use `create_file` to make a `.rag_agent_plan.md` file in the workspace containing a checklist (- [ ] Step 1). After completing a major step, use `edit_file` to check it off (- [x] Step 1)."
4. Add to the prompt: "Before writing any code, always use `read_file` to review your `.rag_agent_plan.md` to ground yourself on what is left to do."

### PHASE 3: The "Insanity" Circuit Breaker (Update `gui_backend.py`)
Current Issue: The LLM occasionally gets trapped in an infinite loop, repeating the exact same failing `run_terminal_command` or `edit_file` call until it hits `max_iterations`.
Action:
1. In `gui_backend.py` inside the `execute_agent_step` generator, introduce a lightweight history tracker (you can store this in the `messages` array metadata or pass a `history_tracker` dict into the step function).
2. Before dispatching a tool via `_dispatch_tool`, hash the `tool_name` and `kwargs`. 
3. If the EXACT same tool call with the EXACT same arguments has failed twice in a row, DO NOT execute it a third time. 
4. Instead, instantly return a mocked `ToolResult` error: "CIRCUIT BREAKER: You have attempted this exact action multiple times and it failed. DO NOT repeat it. You must either use <thinking> to formulate a completely new approach, use a different tool, or use <ask_human> for help."

REQUIREMENTS:
- Do not break the native JSON tool calling we implemented for Anthropic/DeepSeek in the previous step.
- Ensure the fuzzy matching in `edit_file` does not accidentally corrupt Python indentation logic (be careful with how you re-apply the base indent).