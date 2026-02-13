"""
Skill Optimizer - Main module.

Simple flow:
1. start_session() - Begin tracking a conversation
2. session.track_skill() - Record skill usage
3. session.add_message() - Add conversation messages
4. session.end() - AI analyzes and creates suggestions
5. apply() - Write suggestions to SKILL.md files
"""

import re
import uuid
import yaml
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

from .session import Session
from .suggestions import SuggestionStore, Suggestion, SkillMetrics


class SkillOptimizer:
    """
    Main Skill Optimizer class.
    
    Usage:
        # Initialize
        optimizer = SkillOptimizer(
            skills_dir=".claude/skills",
            api_key="sk-ant-..."
        )
        
        # Track a session
        session = optimizer.start_session()
        session.add_message("user", "Create a dashboard")
        session.track_skill("dashboard", exec_time_ms=2000, success=True)
        session.add_message("assistant", "Here's your dashboard...")
        session.add_message("user", "Use dark theme please")
        session.add_message("assistant", "Updated to dark theme!")
        await session.end()  # AI analyzes conversation
        
        # View suggestions
        print(optimizer.get_suggestions())
        
        # Apply to SKILL.md files
        optimizer.apply()
    """
    
    def __init__(
        self,
        skills_dir: str | Path,
        api_key: str,
        data_dir: Optional[str | Path] = None,
        model: str = "claude-sonnet-4-20250514",
    ):
        """
        Initialize the optimizer.
        
        Args:
            skills_dir: Path to skills directory (e.g., ".claude/skills")
            api_key: Anthropic API key
            data_dir: Path for data storage (default: skills_dir/.optimizer)
            model: Claude model to use for analysis
        """
        self.skills_dir = Path(skills_dir)
        self.api_key = api_key
        self.model = model
        
        # Data directory
        self.data_dir = Path(data_dir) if data_dir else self.skills_dir / ".optimizer"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize store
        self.store = SuggestionStore(self.data_dir)
        
        # Active sessions
        self._sessions: Dict[str, Session] = {}
        
        # Cache skill paths
        self._skill_paths: Dict[str, Path] = {}
        self._scan_skills()
    
    def _scan_skills(self):
        """Scan for SKILL.md files."""
        self._skill_paths.clear()
        
        if not self.skills_dir.exists():
            return
        
        for skill_file in self.skills_dir.rglob("SKILL.md"):
            name = self._get_skill_name(skill_file)
            if name:
                self._skill_paths[name] = skill_file
    
    def _get_skill_name(self, skill_file: Path) -> Optional[str]:
        """Extract skill name from SKILL.md."""
        try:
            content = skill_file.read_text()
            match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
            if match:
                frontmatter = yaml.safe_load(match.group(1))
                return frontmatter.get("name")
        except Exception:
            pass
        return skill_file.parent.name
    
    # =========================================================================
    # SESSION MANAGEMENT
    # =========================================================================
    
    def start_session(
        self,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        org: Optional[str] = None,
    ) -> Session:
        """
        Start a new tracking session.

        Args:
            session_id: Optional custom session ID
            user_id: Optional user identifier for tracking
            org: Optional organization identifier for tracking

        Returns:
            Session object to track conversation
        """
        if session_id is None:
            session_id = str(uuid.uuid4())

        session = Session(
            session_id=session_id,
            store=self.store,
            api_key=self.api_key,
            model=self.model,
            user_id=user_id,
            org=org,
        )
        
        self._sessions[session_id] = session
        return session
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """Get an active session by ID."""
        return self._sessions.get(session_id)
    
    # =========================================================================
    # SUGGESTIONS
    # =========================================================================
    
    def get_suggestions(
        self,
        skill_name: Optional[str] = None,
        user_id: Optional[str] = None,
        org: Optional[str] = None,
    ) -> List[Suggestion]:
        """Get pending suggestions, optionally filtered by skill, user, or org."""
        return self.store.get_pending_suggestions(skill_name, user_id=user_id, org=org)
    
    def get_suggestions_summary(self) -> str:
        """Get a text summary of pending suggestions."""
        suggestions = self.get_suggestions()
        
        if not suggestions:
            return "No pending suggestions."
        
        lines = [f"Pending Suggestions: {len(suggestions)}", ""]
        
        by_skill: Dict[str, List[Suggestion]] = {}
        for s in suggestions:
            if s.skill_name not in by_skill:
                by_skill[s.skill_name] = []
            by_skill[s.skill_name].append(s)
        
        for skill_name, skill_suggestions in by_skill.items():
            lines.append(f"=== {skill_name} ===")
            for s in skill_suggestions:
                lines.append(f"  [{s.category}] {s.content}")
                if s.reason:
                    lines.append(f"           Reason: {s.reason}")
            lines.append("")
        
        return "\n".join(lines)
    
    # =========================================================================
    # METRICS
    # =========================================================================
    
    def get_metrics(self, skill_name: str) -> SkillMetrics:
        """Get metrics for a skill."""
        return self.store.get_metrics(skill_name)
    
    def get_all_metrics(self) -> Dict[str, SkillMetrics]:
        """Get all metrics."""
        return self.store.get_all_metrics()
    
    # =========================================================================
    # APPLY SUGGESTIONS TO SKILL FILES
    # =========================================================================
    
    def apply(self, skill_name: Optional[str] = None, dry_run: bool = False) -> Dict[str, Any]:
        """
        Apply pending suggestions to SKILL.md files.
        
        Args:
            skill_name: Specific skill to apply, or None for all
            dry_run: If True, show what would change without modifying files
            
        Returns:
            Dict mapping skill names to changes made
        """
        suggestions = self.get_suggestions(skill_name)
        
        if not suggestions:
            return {}
        
        # Group by skill
        by_skill: Dict[str, List[Suggestion]] = {}
        for s in suggestions:
            if s.skill_name not in by_skill:
                by_skill[s.skill_name] = []
            by_skill[s.skill_name].append(s)
        
        changes = {}
        
        for skill, skill_suggestions in by_skill.items():
            result = self._apply_to_skill(skill, skill_suggestions, dry_run)
            if result:
                changes[skill] = result
                if not dry_run:
                    self.store.mark_applied(skill)
        
        return changes
    
    def _apply_to_skill(
        self,
        skill_name: str,
        suggestions: List[Suggestion],
        dry_run: bool,
    ) -> Optional[Dict[str, Any]]:
        """Apply suggestions to a single skill."""
        
        # Get or create skill file
        skill_path = self._skill_paths.get(skill_name)
        
        if not skill_path or not skill_path.exists():
            # Create new skill file
            skill_path = self.skills_dir / skill_name / "SKILL.md"
            if not dry_run:
                skill_path.parent.mkdir(parents=True, exist_ok=True)
            content = self._create_new_skill(skill_name, suggestions)
            if not dry_run:
                skill_path.write_text(content)
                self._skill_paths[skill_name] = skill_path
            return {"action": "created", "suggestions_applied": len(suggestions)}
        
        # Update existing skill
        content = skill_path.read_text()
        new_content, changes = self._update_skill_content(content, skill_name, suggestions)
        
        if new_content != content:
            if not dry_run:
                skill_path.write_text(new_content)
            return changes
        
        return None
    
    def _create_new_skill(self, skill_name: str, suggestions: List[Suggestion]) -> str:
        """Create a new SKILL.md file."""
        
        # Collect by category
        corrections = [s for s in suggestions if s.category == "correction"]
        preferences = [s for s in suggestions if s.category == "preference"]
        triggers = [s for s in suggestions if s.category == "trigger"]
        improvements = [s for s in suggestions if s.category == "improvement"]
        
        # Build description
        trigger_texts = [s.content for s in triggers]
        desc = f"Skill for {skill_name}."
        if trigger_texts:
            desc += " Triggers: " + ", ".join(trigger_texts[:3])
        
        content = f"""---
name: {skill_name}
description: "{desc}"
---

# {skill_name.replace("-", " ").title()} Skill

This skill was auto-generated based on usage patterns.

"""
        
        if preferences:
            content += "## User Preferences\n\n"
            for s in preferences:
                content += f"- {s.content}\n"
            content += "\n"
        
        if corrections:
            content += "## Learned Corrections\n\n"
            for s in corrections:
                content += f"- {s.content}\n"
            content += "\n"
        
        if improvements:
            content += "## Improvements\n\n"
            for s in improvements:
                content += f"- {s.content}\n"
            content += "\n"
        
        # Add metrics
        metrics = self.store.get_metrics(skill_name)
        content += self._generate_metrics_section(metrics)
        
        return content
    
    def _update_skill_content(
        self,
        content: str,
        skill_name: str,
        suggestions: List[Suggestion],
    ) -> tuple[str, Dict[str, Any]]:
        """Update existing SKILL.md content."""
        
        changes = {
            "action": "updated",
            "sections_modified": [],
            "suggestions_applied": len(suggestions),
        }
        
        # Collect by category
        corrections = [s for s in suggestions if s.category == "correction"]
        preferences = [s for s in suggestions if s.category == "preference"]
        triggers = [s for s in suggestions if s.category == "trigger"]
        improvements = [s for s in suggestions if s.category == "improvement"]
        
        # Update description with triggers
        if triggers:
            content = self._add_triggers_to_description(content, triggers)
            changes["sections_modified"].append("description")
        
        # Add/update preference section
        if preferences:
            content = self._add_or_update_section(
                content, "User Preferences",
                [s.content for s in preferences]
            )
            changes["sections_modified"].append("User Preferences")
        
        # Add/update corrections section
        if corrections:
            content = self._add_or_update_section(
                content, "Learned Corrections",
                [s.content for s in corrections]
            )
            changes["sections_modified"].append("Learned Corrections")
        
        # Add/update improvements section
        if improvements:
            content = self._add_or_update_section(
                content, "Improvements",
                [s.content for s in improvements]
            )
            changes["sections_modified"].append("Improvements")
        
        # Update metrics
        metrics = self.store.get_metrics(skill_name)
        content = self._update_metrics_section(content, metrics)
        
        return content, changes
    
    def _add_triggers_to_description(self, content: str, triggers: List[Suggestion]) -> str:
        """Add trigger phrases to the description, merging with any existing triggers."""
        match = re.match(r"^(---\n)(.*?)(\n---)", content, re.DOTALL)
        if not match:
            return content

        try:
            frontmatter = yaml.safe_load(match.group(2))
            current_desc = frontmatter.get("description", "")

            # Strip existing " Triggers: ..." suffix to avoid duplicates
            base_desc = re.split(r"\s*Triggers:\s*", current_desc)[0]

            # Collect existing triggers (if any) and merge with new ones
            existing_triggers = []
            if " Triggers: " in current_desc:
                existing_part = current_desc.split(" Triggers: ", 1)[1]
                existing_triggers = [t.strip() for t in existing_part.split(",")]

            new_triggers = [s.content for s in triggers]
            all_triggers = list(dict.fromkeys(existing_triggers + new_triggers))

            frontmatter["description"] = base_desc + " Triggers: " + ", ".join(all_triggers)
            new_frontmatter = yaml.dump(frontmatter, default_flow_style=False)
            content = match.group(1) + new_frontmatter.strip() + match.group(3) + content[match.end():]
        except Exception:
            pass

        return content
    
    def _add_or_update_section(self, content: str, section_name: str, items: List[str]) -> str:
        """Add or update a section."""
        section_header = f"## {section_name}"
        
        if section_header in content:
            # Update existing section
            pattern = rf"(## {re.escape(section_name)}\n\n)((?:- .+\n)*)"
            
            def replacer(m):
                existing = [line[2:].strip() for line in m.group(2).strip().split("\n") if line.startswith("- ")]
                all_items = list(dict.fromkeys(existing + items))  # Preserve order, remove dupes
                new_content = "\n".join(f"- {item}" for item in all_items) + "\n\n"
                return m.group(1) + new_content
            
            content = re.sub(pattern, replacer, content)
        else:
            # Add new section before Metrics or at end
            new_section = f"\n{section_header}\n\n"
            for item in items:
                new_section += f"- {item}\n"
            new_section += "\n"
            
            if "## Metrics" in content:
                content = content.replace("## Metrics", new_section + "## Metrics")
            else:
                content = content.rstrip() + "\n" + new_section
        
        return content
    
    def _update_metrics_section(self, content: str, metrics: SkillMetrics) -> str:
        """Update the metrics section."""
        metrics_section = self._generate_metrics_section(metrics)
        
        if "## Metrics" in content:
            pattern = r"## Metrics\n\n(?:.*\n)*?(?=\n## |\Z)"
            content = re.sub(pattern, metrics_section, content)
        else:
            content = content.rstrip() + "\n\n" + metrics_section
        
        return content
    
    def _generate_metrics_section(self, metrics: SkillMetrics) -> str:
        """Generate metrics section."""
        return f"""## Metrics

<!-- Auto-generated by skill-optimizer -->
| Metric | Value |
|--------|-------|
| Total Calls | {metrics.total_calls} |
| Success Rate | {metrics.success_rate:.1%} |
| Avg Exec Time | {metrics.avg_exec_time_ms:.0f}ms |
| Last Used | {metrics.last_used or 'Never'} |

"""
    
    # =========================================================================
    # UTILITY
    # =========================================================================
    
    def refresh(self):
        """Refresh skill list from disk."""
        self._scan_skills()
    
    @property
    def skill_names(self) -> List[str]:
        """Get list of known skill names."""
        return list(self._skill_paths.keys())
    
    def status(self) -> str:
        """Get overall status."""
        return self.store.summary()
    
    def save(self):
        """Force save all data."""
        self.store.save()
