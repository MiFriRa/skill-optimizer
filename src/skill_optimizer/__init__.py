"""
Skill Optimizer
===============

AI-powered optimization of Antigravity SKILL.md files.
Analyzes conversations using an LLM (Gemini or Anthropic)
and automatically improves skills with corrections, preferences,
trigger phrases, and general improvements.

Quick start (CLI):
    python optimize.py status
    python optimize.py demo
    python optimize.py inject --skill smagskombinator --category preference --content "..."
    python optimize.py apply --confirm

Programmatic usage:
    from skill_optimizer import SkillOptimizer

    optimizer = SkillOptimizer(
        skills_dir="~/.gemini/antigravity/skills",
        provider="gemini",        # or "anthropic"
    )

    session = optimizer.start_session()
    session.add_message("user", "Kan du rette denne tekst?")
    session.add_message("assistant", "Her er den rettede version...")
    session.end_sync()

    print(optimizer.get_suggestions_summary())
    optimizer.apply(dry_run=True)
"""

__version__ = "0.3.0"

from .optimizer import SkillOptimizer
from .session import Session
from .suggestions import SuggestionStore, Suggestion
from .llm_client import LLMClient, GeminiClient, AnthropicClient, create_client

__all__ = [
    "SkillOptimizer",
    "Session",
    "SuggestionStore",
    "Suggestion",
    "LLMClient",
    "GeminiClient",
    "AnthropicClient",
    "create_client",
]
