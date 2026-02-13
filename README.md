# Skill Optimizer

AI-powered skill optimization using Claude to analyze conversations and automatically improve SKILL.md files.

## Installation

```bash
pip install skill-optimizer
```

## Quick Start

```python
from skill_optimizer import SkillOptimizer

# Initialize with your API key
optimizer = SkillOptimizer(
    skills_dir=".claude/skills",
    api_key="sk-ant-api03-..."
)

# Start a session (with optional user/org tracking)
session = optimizer.start_session(user_id="user_123", org="acme-corp")

# Track the conversation
session.add_message("user", "Create a sales dashboard")
session.track_skill("dashboard", exec_time_ms=2000, success=True)
session.add_message("assistant", "Here's your dashboard with pie charts...")
session.add_message("user", "Actually, can you use bar charts instead?")
session.add_message("assistant", "Updated to bar charts!")

# End session - Claude AI analyzes the conversation
session.end_sync()  # or: await session.end()

# View pending suggestions
print(optimizer.get_suggestions_summary())

# Apply suggestions to SKILL.md files
changes = optimizer.apply()
print(f"Updated: {list(changes.keys())}")
```

## How It Works

### Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         SESSION                                 │
│                                                                 │
│  1. start_session()                                             │
│         │                                                       │
│         ▼                                                       │
│  2. During conversation:                                        │
│     session.add_message("user", "...")                          │
│     session.track_skill("docx", exec_time_ms=1500)              │
│     session.add_message("assistant", "...")                     │
│         │                                                       │
│         ▼                                                       │
│  3. session.end()                                               │
│         │                                                       │
│         ▼                                                       │
│     ┌─────────────────────────────────────┐                     │
│     │ Claude AI analyzes conversation:    │                     │
│     │ - Finds corrections                 │                     │
│     │ - Extracts preferences              │                     │
│     │ - Identifies new triggers           │                     │
│     │ - Suggests improvements             │                     │
│     └─────────────────────────────────────┘                     │
│         │                                                       │
│         ▼                                                       │
│     suggestions.json (pending suggestions)                      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     APPLY (when ready)                          │
│                                                                 │
│  optimizer.apply()                                              │
│         │                                                       │
│         ▼                                                       │
│  Updates SKILL.md files with:                                   │
│  - New trigger phrases in description                           │
│  - User Preferences section                                     │
│  - Learned Corrections section                                  │
│  - Updated Metrics                                              │
│         │                                                       │
│         ▼                                                       │
│  Marks suggestions as applied (kept in JSON as history)         │
│  Use optimizer.store.clear_applied() to clean up                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## File Structure

```
.claude/skills/
├── dashboard/
│   └── SKILL.md              ← Updated by optimizer
├── docx/
│   └── SKILL.md
│
└── .optimizer/               ← Created automatically
    ├── suggestions.json      ← Pending suggestions
    └── metrics.json          ← Usage metrics
```

## API Reference

### SkillOptimizer

```python
optimizer = SkillOptimizer(
    skills_dir=".claude/skills",  # Path to skills
    api_key="sk-ant-...",         # Anthropic API key
    data_dir=None,                # Optional: custom data directory
    model="claude-sonnet-4-20250514"  # Model for analysis
)

# Session management
session = optimizer.start_session()
session = optimizer.start_session(session_id="custom-id")
session = optimizer.start_session(user_id="user_123", org="acme-corp")

# View suggestions
suggestions = optimizer.get_suggestions()                        # All pending
suggestions = optimizer.get_suggestions("dashboard")            # For one skill
suggestions = optimizer.get_suggestions(user_id="user_123")     # For one user
suggestions = optimizer.get_suggestions(org="acme-corp")        # For one org
print(optimizer.get_suggestions_summary())                      # Text summary

# Apply suggestions (marks them as applied, writes to SKILL.md)
changes = optimizer.apply()                    # Apply all
changes = optimizer.apply("dashboard")         # Apply one skill
changes = optimizer.apply(dry_run=True)        # Preview only

# Applied suggestions stay in suggestions.json as history.
# They won't appear in get_suggestions() anymore.
# To permanently remove applied suggestions from the file:
optimizer.store.clear_applied()

# Metrics
metrics = optimizer.get_metrics("dashboard")
all_metrics = optimizer.get_all_metrics()

# Status
print(optimizer.status())
```

### Session

```python
session = optimizer.start_session(user_id="user_123", org="acme-corp")

# Track conversation
session.add_message("user", "Create a document")
session.add_message("assistant", "Here's your document...")

# Track skill usage
session.track_skill(
    skill_name="docx",
    exec_time_ms=1500,
    success=True,
    error=None  # Optional error message if failed
)

# End and analyze (choose one)
await session.end()      # Async
session.end_sync()       # Sync

# Properties
session.session_id       # Unique ID
session.user_id          # User identifier (optional)
session.org              # Organization identifier (optional)
session.messages         # List of messages
session.skill_usages     # List of skill usages
session.duration_seconds # Session duration
```

### Suggestion

```python
@dataclass
class Suggestion:
    skill_name: str      # Which skill this is for
    category: str        # "correction", "preference", "trigger", "improvement"
    content: str         # The actual suggestion
    reason: str          # Why (from conversation analysis)
    session_id: str      # Which session it came from
    user_id: str         # Which user created this session
    org: str             # Which organization the user belongs to
    created_at: str      # Timestamp
    applied: bool        # Whether it's been applied
```

## Integration Example

```python
from skill_optimizer import SkillOptimizer

optimizer = SkillOptimizer(".claude/skills", api_key="...")

async def handle_conversation(messages: list, skills_used: list):
    """Handle a complete conversation."""
    
    # Start session with user/org tracking
    session = optimizer.start_session(user_id="user_42", org="acme-corp")

    # Add all messages
    for msg in messages:
        session.add_message(msg["role"], msg["content"])
    
    # Add skill usage
    for skill in skills_used:
        session.track_skill(
            skill_name=skill["name"],
            exec_time_ms=skill["time_ms"],
            success=skill["success"]
        )
    
    # Analyze with AI
    suggestions = await session.end()
    
    print(f"Found {len(suggestions)} suggestions")
    return suggestions


# Later: apply all pending suggestions
def daily_optimization():
    changes = optimizer.apply()
    for skill, change in changes.items():
        print(f"Updated {skill}: {change}")
```

## What Claude Analyzes

When `session.end()` is called, Claude looks for:

| Category | Examples |
|----------|----------|
| **Corrections** | "Actually, I wanted...", "That's not right...", "Can you change..." |
| **Preferences** | "I prefer...", "Always use...", "Next time..." |
| **Triggers** | "When I say X, I mean...", alternative phrasings |
| **Improvements** | Performance issues, missing features, better defaults |

## Example Updated SKILL.md

After `optimizer.apply()`:

```markdown
---
name: dashboard
description: "Create dashboards. Triggers: 'analytics', 'charts', 'visualization'"
---

# Dashboard Skill

Creates interactive dashboards.

## User Preferences

- Use bar charts instead of pie charts for comparisons
- Dark theme by default
- Include date range selector

## Learned Corrections

- Always include a title on charts
- Export button should be visible

## Metrics

| Metric | Value |
|--------|-------|
| Total Calls | 47 |
| Success Rate | 91.5% |
| Avg Exec Time | 1850ms |
| Last Used | 2025-02-05T10:30:00 |
```

## License

MIT
