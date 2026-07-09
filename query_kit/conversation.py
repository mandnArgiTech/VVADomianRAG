"""Multi-turn memory and query reformulation for REPL / chat."""

from __future__ import annotations

from typing import Dict, List

from query_kit.ollama_client import OLLAMA_LIB_AVAILABLE, _ollama_mod, ollama_chat


class ConversationMemory:
    def __init__(self, max_turns: int = 5) -> None:
        self.max_turns = max(1, max_turns)
        self.turns: List[Dict[str, str]] = []

    def add_turn(self, raw_query: str, reformulated: str, answer_summary: str) -> None:
        self.turns.append(
            {
                "query": raw_query,
                "reformulated": reformulated,
                "answer_summary": answer_summary[:500],
            }
        )
        if len(self.turns) > self.max_turns:
            self.turns = self.turns[-self.max_turns :]

    def clear(self) -> None:
        self.turns.clear()

    def is_empty(self) -> bool:
        return not self.turns

    def recent_context_text(self, n: int = 2) -> str:
        if not self.turns:
            return ""
        lines: List[str] = []
        for t in self.turns[-n:]:
            q = t["reformulated"] or t["query"]
            lines.append(f"Q: {q}")
            if t.get("answer_summary"):
                lines.append(f"A: {t['answer_summary']}")
        return "\n".join(lines)

    def show(self) -> str:
        if not self.turns:
            return "(no conversation history)"
        lines: List[str] = []
        for i, t in enumerate(self.turns, 1):
            q = t["query"]
            r = t["reformulated"]
            extra = f"  → search: {r}" if r and r != q else ""
            lines.append(f"  {i}. {q}{extra}")
        return "\n".join(lines)

    def history_messages_for_llm(self) -> List[Dict[str, str]]:
        out: List[Dict[str, str]] = []
        for t in self.turns[-3:]:
            out.append({"role": "user", "content": t["reformulated"] or t["query"]})
            if t.get("answer_summary"):
                out.append({"role": "assistant", "content": t["answer_summary"]})
        return out


def reformulate_query(raw_query: str, memory: ConversationMemory, llm_model: str) -> str:
    if memory.is_empty():
        return raw_query
    if len(raw_query.split()) > 8:
        return raw_query
    if not OLLAMA_LIB_AVAILABLE or _ollama_mod is None:
        return raw_query
    ctx = memory.recent_context_text(2)
    prompt = (
        "Rewrite this follow-up into ONE standalone search query (under 20 words) "
        "that someone could type without prior context.\n\n"
        f"Prior turns:\n{ctx}\n\nFollow-up: {raw_query}\n\nStandalone query:"
    )
    try:
        resp = ollama_chat(
            model=llm_model,
            messages=[{"role": "user", "content": prompt}],
            stream=False,
            options={"num_predict": 80},
        )
        msg = getattr(resp, "message", None) or (
            resp.get("message") if isinstance(resp, dict) else None
        )
        text = ""
        if isinstance(msg, dict):
            text = str(msg.get("content") or "").strip()
        else:
            text = str(getattr(msg, "content", None) or "").strip()
        text = text.split("\n")[0].strip().strip('"').strip("'")
        if 3 < len(text) < 200:
            return text
    except Exception:
        pass
    return raw_query
