from typing import Dict, Any

from src.core.llm_provider import LLMProvider
from src.telemetry.metrics import tracker


class BaselineChatbot:
    """Simple one-shot chatbot baseline without tools or iterative reasoning."""

    def __init__(self, llm: LLMProvider):
        self.llm = llm

    def get_system_prompt(self) -> str:
        return (
            "You are a helpful chatbot assistant. "
            "Answer directly in Vietnamese. "
            "Do not use tools and do not mention internal reasoning. "
            "Format the answer as clean plain text only. "
            "Do not use Markdown, do not use **, *, #, -, bullet lists, or code fences. "
            "Use short section titles in plain text when needed."
        )

    def run(self, user_input: str) -> Dict[str, Any]:
        result = self.llm.generate(user_input, system_prompt=self.get_system_prompt())
        tracker.track_request(
            provider=result.get("provider", "unknown"),
            model=self.llm.model_name,
            usage=result.get("usage", {}),
            latency_ms=result.get("latency_ms", 0),
        )
        return result

    def run_with_metadata(self, user_input: str) -> Dict[str, Any]:
        result = self.run(user_input)
        usage = result.get("usage", {})
        return {
            "mode": "baseline",
            "answer": result.get("content", ""),
            "provider": result.get("provider", "unknown"),
            "model": self.llm.model_name,
            "latency_ms": result.get("latency_ms", 0),
            "tool_calls": [],
            "trace": [],
            "usage": usage,
            "steps": 1,
        }
