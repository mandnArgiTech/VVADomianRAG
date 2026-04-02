Act as a Principal AI Architect building an Enterprise Cognitive Agent. We are upgrading our local RAG dashboard (`gui_backend.py`, `agent_tools.py`, and `index.html`). 

CURRENT CAPABILITIES:
We have a basic ReAct loop, multi-model support (Ollama, Anthropic, DeepSeek), and a robust RAG ingestion pipeline (`ingest.py` / `domain_feeder.py`).

OBJECTIVE:
Transform the system into a Continuous Learning Architecture with "Cursor-style" Auto-Context, Web Search, and Long-Term RAG Memory (Self-Ingestion).

IMPLEMENT THE FOLLOWING 4 PHASES:

Phase 1: The New Skills (`agent_tools.py`)
Add two powerful new tools to the tool registry:
1. `web_search(query: str) -> str`: Implement a lightweight web search function (using DuckDuckGo's `ddg-search` Python package, or a generic requests scraper if an API key like Tavily isn't provided). It must return a clean, markdown-formatted summary of the top 3 results.
2. `remember_concept(title: str, content: str, domain: str = "general") -> str`: This is the Long-Term Memory tool. 
   - Logic: It must write the `content` to a new markdown file in the `DomainDocs/` directory (e.g., `DomainDocs/{title}.md`).
   - RAG Feedback: Immediately after writing the file, it MUST import and call `feed_domain_document` from `domain_feeder.py` (which we already have in our repo) to instantly parse, chunk (using our markdown domain chunker), embed, and upsert this new file into ChromaDB. 
   - Return: "Successfully saved and ingested into VectorDB."

Phase 2: Multi-Model Tool Calling Abstraction (`gui_backend.py`)
- Action: Anthropic, DeepSeek, and Ollama all format tool calls differently. Create a universal `execute_agent_step(provider, messages, tools)` wrapper.
- Logic: This wrapper must translate our internal tool schema (read_file, write_file, web_search, remember_concept, search_codebase) into the native `tools` array expected by the respective provider's API. 
- Return: It must seamlessly catch the provider's tool execution request, run our Python function in `agent_tools.py`, and append the result to the `messages` array as a tool response.

Phase 3: Auto-Context & `@` Mentions (The Pre-Flight Check)
- Action: Before the ReAct loop starts, parse the user's raw `body.query`.
- Logic: Implement Regex triggers similar to Cursor.
   - If the query contains `@web`, automatically prepend the `web_search` tool output to the system prompt context before hitting the LLM.
   - If the query contains `@codebase`, automatically run the dense/BM25 `search_codebase` function and inject it.
   - If the query contains `@docs`, filter the RAG search specifically to the `domain_doc` source type.
- Goal: This gives the user explicitly configurable context, while saving the LLM a "reasoning step" by doing the retrieval instantly.

Phase 4: Frontend `@` Menu & Memory Badges (`index.html`)
- Action 1: In the `chatInput` textarea, implement a lightweight listener. If the user types `@`, pop up a small floating menu suggesting: `🌐 @web`, `📁 @codebase`, `📚 @docs`. (Use vanilla JS).
- Action 2: Update the `parseSSE` logic. When the backend emits the SSE event for `agent_status` regarding `remember_concept`, render a special gold/yellow badge in the chat UI: `[🧠 Agent saved new knowledge to RAG Database]`. 

REQUIREMENTS:
- For `remember_concept`, ensure the file path is heavily sanitized so it strictly writes to the designated `DomainDocs` or `Wiki` directories, preventing directory traversal attacks.
- Ensure the `domain_feeder.py` import is handled gracefully.
- Walk me through the exact logic of the `remember_concept` ingestion trigger before writing the code.