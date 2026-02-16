"""
Skill Optimizer
===============

AI-powered skill optimization based on conversation analysis.

Simple Usage:
    from skill_optimizer import SkillOptimizer
    
    # Initialize with API key
    optimizer = SkillOptimizer(
        skills_dir=".claude/skills",
        api_key="sk-ant-..."
    )
    
    # Start a session
    session = optimizer.start_session()
    
    # Track skill usage during conversation
    session.track_skill("docx", exec_time_ms=1500, success=True)
    session.track_skill("pdf", exec_time_ms=800, success=True)
    
    # Add conversation messages
    session.add_message("user", "Create a Word document for my report")
    session.add_message("assistant", "I've created the document...")
    session.add_message("user", "Actually, use bullet points not numbers")
    session.add_message("assistant", "Done, I've updated it with bullets")
    
    # End session - analyzes conversation with Claude AI
    await session.end()
    
    # View pending suggestions
    print(optimizer.get_suggestions())
    
    # Apply suggestions to SKILL.md files
    optimizer.apply()
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
