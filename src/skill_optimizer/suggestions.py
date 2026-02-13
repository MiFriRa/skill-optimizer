"""
Suggestions storage.

Stores all pending suggestions in a JSON file.
When apply() is called, suggestions are written to SKILL.md files.
"""

import json
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict
from datetime import datetime


@dataclass
class Suggestion:
    """A single suggestion for a skill."""
    skill_name: str
    category: str  # "correction", "preference", "trigger", "improvement"
    content: str
    reason: Optional[str] = None
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    org: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    applied: bool = False
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "Suggestion":
        return cls(**data)


@dataclass
class SkillMetrics:
    """Metrics for a single skill."""
    skill_name: str
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    total_exec_time_ms: int = 0
    last_used: Optional[str] = None
    
    @property
    def success_rate(self) -> float:
        if self.total_calls == 0:
            return 0.0
        return self.successful_calls / self.total_calls
    
    @property
    def avg_exec_time_ms(self) -> float:
        if self.total_calls == 0:
            return 0.0
        return self.total_exec_time_ms / self.total_calls
    
    def record(self, success: bool, exec_time_ms: int):
        self.total_calls += 1
        self.total_exec_time_ms += exec_time_ms
        if success:
            self.successful_calls += 1
        else:
            self.failed_calls += 1
        self.last_used = datetime.utcnow().isoformat()
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "SkillMetrics":
        return cls(**data)


class SuggestionStore:
    """
    Stores suggestions and metrics in JSON files.
    
    Files:
        - suggestions.json: Pending suggestions to apply
        - metrics.json: Skill usage metrics
    """
    
    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.suggestions_file = self.data_dir / "suggestions.json"
        self.metrics_file = self.data_dir / "metrics.json"
        
        self._suggestions: List[Suggestion] = []
        self._metrics: Dict[str, SkillMetrics] = {}
        
        self._load()
    
    def _load(self):
        """Load from disk."""
        # Load suggestions
        if self.suggestions_file.exists():
            try:
                with open(self.suggestions_file) as f:
                    data = json.load(f)
                self._suggestions = [Suggestion.from_dict(s) for s in data]
            except Exception as e:
                print(f"Warning: Could not load suggestions: {e}")
        
        # Load metrics
        if self.metrics_file.exists():
            try:
                with open(self.metrics_file) as f:
                    data = json.load(f)
                self._metrics = {k: SkillMetrics.from_dict(v) for k, v in data.items()}
            except Exception as e:
                print(f"Warning: Could not load metrics: {e}")
    
    def save(self):
        """Save to disk."""
        # Save suggestions
        with open(self.suggestions_file, "w") as f:
            json.dump([s.to_dict() for s in self._suggestions], f, indent=2)
        
        # Save metrics
        with open(self.metrics_file, "w") as f:
            json.dump({k: v.to_dict() for k, v in self._metrics.items()}, f, indent=2)
    
    # === SUGGESTIONS ===
    
    def add_suggestion(self, suggestion: Suggestion):
        """Add a new suggestion."""
        # Check for duplicates
        for existing in self._suggestions:
            if (existing.skill_name == suggestion.skill_name and 
                existing.category == suggestion.category and
                existing.content == suggestion.content and
                not existing.applied):
                return  # Already exists
        
        self._suggestions.append(suggestion)
        self.save()
    
    def add_suggestions(self, suggestions: List[Suggestion]):
        """Add multiple suggestions."""
        for s in suggestions:
            self.add_suggestion(s)
    
    def get_pending_suggestions(
        self,
        skill_name: Optional[str] = None,
        user_id: Optional[str] = None,
        org: Optional[str] = None,
    ) -> List[Suggestion]:
        """Get pending (not applied) suggestions, optionally filtered by skill, user, or org."""
        pending = [s for s in self._suggestions if not s.applied]
        if skill_name:
            pending = [s for s in pending if s.skill_name == skill_name]
        if user_id:
            pending = [s for s in pending if s.user_id == user_id]
        if org:
            pending = [s for s in pending if s.org == org]
        return pending
    
    def get_all_suggestions(self) -> List[Suggestion]:
        """Get all suggestions."""
        return self._suggestions.copy()
    
    def mark_applied(self, skill_name: str):
        """Mark all suggestions for a skill as applied."""
        for s in self._suggestions:
            if s.skill_name == skill_name and not s.applied:
                s.applied = True
        self.save()
    
    def clear_applied(self):
        """Remove all applied suggestions."""
        self._suggestions = [s for s in self._suggestions if not s.applied]
        self.save()
    
    # === METRICS ===
    
    def get_metrics(self, skill_name: str) -> SkillMetrics:
        """Get or create metrics for a skill."""
        if skill_name not in self._metrics:
            self._metrics[skill_name] = SkillMetrics(skill_name=skill_name)
        return self._metrics[skill_name]
    
    def record_usage(self, skill_name: str, success: bool, exec_time_ms: int):
        """Record a skill usage."""
        metrics = self.get_metrics(skill_name)
        metrics.record(success, exec_time_ms)
        self.save()
    
    def get_all_metrics(self) -> Dict[str, SkillMetrics]:
        """Get all metrics."""
        return self._metrics.copy()
    
    # === SUMMARY ===
    
    def summary(self) -> str:
        """Get a text summary."""
        lines = ["=" * 50, "SKILL OPTIMIZER STATUS", "=" * 50, ""]
        
        # Pending suggestions
        pending = self.get_pending_suggestions()
        lines.append(f"Pending Suggestions: {len(pending)}")
        
        if pending:
            by_skill: Dict[str, List[Suggestion]] = {}
            for s in pending:
                if s.skill_name not in by_skill:
                    by_skill[s.skill_name] = []
                by_skill[s.skill_name].append(s)
            
            for skill_name, suggestions in by_skill.items():
                lines.append(f"\n  {skill_name}:")
                for s in suggestions:
                    lines.append(f"    [{s.category}] {s.content[:50]}...")
        
        # Metrics
        lines.append(f"\nTracked Skills: {len(self._metrics)}")
        for name, m in self._metrics.items():
            lines.append(f"  {name}: {m.total_calls} calls, {m.success_rate:.0%} success, {m.avg_exec_time_ms:.0f}ms avg")
        
        return "\n".join(lines)
