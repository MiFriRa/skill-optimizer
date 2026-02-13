"""
Session tracking.

Tracks an entire conversation session from start to end.
At session end, uses Claude AI to analyze the conversation and extract suggestions.
"""

import logging
import uuid
import time
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime

from anthropic import Anthropic

from .suggestions import SuggestionStore, Suggestion, SkillMetrics

logger = logging.getLogger(__name__)

# Max messages to send for analysis. Keeps the most recent messages
# where corrections and preferences are most likely to appear.
MAX_ANALYSIS_MESSAGES = 200


@dataclass
class Message:
    """A single message in the conversation."""
    role: str  # "user" or "assistant"
    content: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class SkillUsage:
    """Record of a skill being used."""
    skill_name: str
    exec_time_ms: int
    success: bool
    error: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class Session:
    """
    Tracks a single conversation session.
    
    Usage:
        session = optimizer.start_session()
        
        # During conversation
        session.add_message("user", "Create a document")
        session.track_skill("docx", exec_time_ms=1500, success=True)
        session.add_message("assistant", "Done!")
        session.add_message("user", "Actually use bullets")
        session.add_message("assistant", "Updated!")
        
        # End session - analyzes with AI
        await session.end()
    """
    
    def __init__(
        self,
        session_id: str,
        store: SuggestionStore,
        api_key: str,
        model: str = "claude-sonnet-4-20250514",
        user_id: Optional[str] = None,
        org: Optional[str] = None,
    ):
        self.session_id = session_id
        self.store = store
        self.api_key = api_key
        self.model = model
        self.user_id = user_id
        self.org = org
        
        self.messages: List[Message] = []
        self.skill_usages: List[SkillUsage] = []
        self.start_time = datetime.utcnow()
        self.ended = False
    
    def add_message(self, role: str, content: str):
        """Add a conversation message."""
        if self.ended:
            raise RuntimeError("Session already ended")
        self.messages.append(Message(role=role, content=content))
    
    def track_skill(
        self,
        skill_name: str,
        exec_time_ms: int,
        success: bool = True,
        error: Optional[str] = None,
    ):
        """Track a skill usage."""
        if self.ended:
            raise RuntimeError("Session already ended")
        
        self.skill_usages.append(SkillUsage(
            skill_name=skill_name,
            exec_time_ms=exec_time_ms,
            success=success,
            error=error,
        ))
        
        # Also record in store immediately
        self.store.record_usage(skill_name, success, exec_time_ms)
    
    async def end(self) -> List[Suggestion]:
        """
        End the session and analyze with AI.
        
        Returns list of suggestions extracted from the conversation.
        """
        if self.ended:
            return []
        
        self.ended = True
        
        # If no skills were used, nothing to analyze
        if not self.skill_usages:
            return []
        
        # If no conversation, nothing to learn from
        if len(self.messages) < 2:
            return []
        
        # Analyze with Claude
        suggestions = await self._analyze_conversation()
        
        # Store suggestions
        self.store.add_suggestions(suggestions)
        
        return suggestions
    
    def end_sync(self) -> List[Suggestion]:
        """Synchronous version of end()."""
        if self.ended:
            return []
        
        self.ended = True
        
        if not self.skill_usages or len(self.messages) < 2:
            return []
        
        suggestions = self._analyze_conversation_sync()
        self.store.add_suggestions(suggestions)
        
        return suggestions
    
    async def _analyze_conversation(self) -> List[Suggestion]:
        """Use Claude to analyze the conversation."""
        from anthropic import AsyncAnthropic

        client = AsyncAnthropic(api_key=self.api_key)
        prompt = self._build_analysis_prompt()

        try:
            response = await client.messages.create(
                model=self.model,
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}],
            )
        except Exception as e:
            logger.error(
                "Session %s: Claude API call failed: %s", self.session_id, e,
            )
            return []

        return self._parse_analysis_response(response.content[0].text)

    def _analyze_conversation_sync(self) -> List[Suggestion]:
        """Synchronous version of _analyze_conversation."""
        client = Anthropic(api_key=self.api_key)
        prompt = self._build_analysis_prompt()

        try:
            response = client.messages.create(
                model=self.model,
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}],
            )
        except Exception as e:
            logger.error(
                "Session %s: Claude API call failed: %s", self.session_id, e,
            )
            return []

        return self._parse_analysis_response(response.content[0].text)
    
    def _build_analysis_prompt(self) -> str:
        """Build the prompt for Claude to analyze the conversation."""
        
        # Truncate to last N messages if conversation is too long
        messages = self.messages
        truncated = False
        if len(messages) > MAX_ANALYSIS_MESSAGES:
            truncated = True
            messages = messages[-MAX_ANALYSIS_MESSAGES:]
            logger.info(
                "Session %s: truncated conversation from %d to %d messages for analysis",
                self.session_id, len(self.messages), MAX_ANALYSIS_MESSAGES,
            )

        # Build conversation text
        conversation_text = ""
        if truncated:
            conversation_text += f"[...truncated {len(self.messages) - MAX_ANALYSIS_MESSAGES} earlier messages...]\n"
        conversation_text += "\n".join([
            f"{m.role.upper()}: {m.content}"
            for m in messages
        ])
        
        # Build skills used text
        skills_used = list(set(u.skill_name for u in self.skill_usages))
        skills_text = ", ".join(skills_used)
        
        # Build skill performance text
        skill_perf = {}
        for u in self.skill_usages:
            if u.skill_name not in skill_perf:
                skill_perf[u.skill_name] = {"success": 0, "fail": 0, "times": []}
            if u.success:
                skill_perf[u.skill_name]["success"] += 1
            else:
                skill_perf[u.skill_name]["fail"] += 1
            skill_perf[u.skill_name]["times"].append(u.exec_time_ms)
        
        perf_text = "\n".join([
            f"- {name}: {p['success']} success, {p['fail']} fail, avg {sum(p['times'])//len(p['times'])}ms"
            for name, p in skill_perf.items()
        ])
        
        return f"""Analyze this conversation between a user and an AI assistant that uses skills.

SKILLS USED: {skills_text}

SKILL PERFORMANCE:
{perf_text}

CONVERSATION:
{conversation_text}

---

Analyze the conversation and extract any feedback about the skills used. Look for:

1. CORRECTIONS: User pointing out mistakes or asking for changes
   - "Actually, I wanted..."
   - "No, that's not right..."
   - "Can you change..."
   - Any indication the skill output wasn't what user wanted

2. PREFERENCES: User stating preferences for future use
   - "I prefer..."
   - "Always use..."
   - "Next time..."
   - Style/format preferences

3. NEW TRIGGERS: Phrases that should trigger a skill
   - "When I say X, I mean..."
   - Alternative ways to request the skill

4. IMPROVEMENTS: General improvements for the skill
   - Performance issues
   - Missing features
   - Better defaults

Return your analysis as JSON (only valid JSON, no other text):
{{
  "suggestions": [
    {{
      "skill_name": "skill name",
      "category": "correction|preference|trigger|improvement",
      "content": "the specific suggestion",
      "reason": "why this suggestion (based on conversation)"
    }}
  ]
}}

If no suggestions found, return: {{"suggestions": []}}

Important:
- Only include actionable, specific suggestions
- Each suggestion should be clear enough to update the SKILL.md file
- Focus on the skills that were actually used
- Be concise but complete"""
    
    def _parse_analysis_response(self, response_text: str) -> List[Suggestion]:
        """Parse Claude's analysis response."""
        import json
        
        # Try to extract JSON from response
        try:
            # Handle case where response has markdown code blocks
            if "```json" in response_text:
                start = response_text.index("```json") + 7
                end = response_text.index("```", start)
                response_text = response_text[start:end].strip()
            elif "```" in response_text:
                start = response_text.index("```") + 3
                end = response_text.index("```", start)
                response_text = response_text[start:end].strip()
            
            data = json.loads(response_text)
            suggestions = []
            
            for s in data.get("suggestions", []):
                suggestions.append(Suggestion(
                    skill_name=s.get("skill_name", "unknown"),
                    category=s.get("category", "improvement"),
                    content=s.get("content", ""),
                    reason=s.get("reason"),
                    session_id=self.session_id,
                    user_id=self.user_id,
                    org=self.org,
                ))
            
            return suggestions
            
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(
                "Session %s: could not parse AI response: %s", self.session_id, e,
            )
            return []
    
    @property
    def duration_seconds(self) -> float:
        """Get session duration in seconds."""
        end = datetime.utcnow() if not self.ended else datetime.fromisoformat(
            self.messages[-1].timestamp if self.messages else self.start_time.isoformat()
        )
        return (end - self.start_time).total_seconds()
