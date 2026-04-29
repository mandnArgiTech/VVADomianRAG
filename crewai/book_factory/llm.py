"""DeepSeek LLM construction for CrewAI."""

from __future__ import annotations

from crewai import LLM

from .constants import DEEPSEEK_BASE, USE_FAST_RESEARCH


def build_llms(api_key: str) -> tuple[LLM, LLM, LLM]:
    """Return (reasoner, chat, research) LLM instances for one API key."""
    key = api_key or None
    reasoner = LLM(
        model="deepseek/deepseek-reasoner",
        api_key=key,
        base_url=DEEPSEEK_BASE,
        timeout=600.0,
    )
    chat = LLM(
        model="deepseek/deepseek-chat",
        api_key=key,
        base_url=DEEPSEEK_BASE,
        timeout=180.0,
        max_tokens=8192,
    )
    research = chat if USE_FAST_RESEARCH else reasoner
    return reasoner, chat, research
