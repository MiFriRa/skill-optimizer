# Skill Optimizer

AI-powered optimization of [Antigravity](https://antigravity.dev) SKILL.md files. Analyzes conversations using an LLM (Gemini or Anthropic) and automatically improves skills with corrections, preferences, new trigger phrases, and general improvements.

## Overview

Skill Optimizer watches how you interact with Antigravity skills and extracts actionable feedback:

| Category | What it captures | Example |
|----------|-----------------|---------|
| **correction** | Mistakes the AI made that should be fixed | "Brug **ikke** engelske udtryk" |
| **preference** | User style preferences | "Skriv altid på dansk" |
| **trigger** | New phrases that should activate a skill | "madkombination", "hvad passer til" |
| **improvement** | General improvements | "Tilføj eksempler i svar" |

## Installation

```bash
git clone <repo-url>
cd skill-optimizer

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate    # Windows
# source .venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -e .

# For Anthropic support (optional)
pip install -e ".[anthropic]"
```

### Configuration

Create a `.env` file in the project root:

```env
GEMINI_API_KEY=your-key-here
```

| Variable | Default | Description |
|----------|---------|-------------|
| `GEMINI_API_KEY` | — | API key for Google Gemini (required if using Gemini) |
| `ANTHROPIC_API_KEY` | — | API key for Anthropic Claude (required if using Anthropic) |
| `SKILLS_DIR` | `~/.gemini/antigravity/skills` | Path to the Antigravity skills directory |
| `BRAIN_DIR` | `~/.gemini/antigravity/brain` | Path to the Antigravity brain (conversation artifacts) |
| `OPTIMIZER_PROVIDER` | `gemini` | LLM provider: `gemini` or `anthropic` |

## Quick Start (CLI)

The primary interface is the `optimize.py` CLI:

```bash
# See status of all skills and pending suggestions
python optimize.py status

# Run a built-in demo with the Smagskombinator skill
python optimize.py demo

# Inject a suggestion manually
python optimize.py inject --skill smagskombinator --category preference --content "Brug altid sæsonens grøntsager"

# Preview changes (dry-run, default)
python optimize.py apply

# Write changes to SKILL.md files
python optimize.py apply --confirm

# Analyze a conversation from a file
python optimize.py analyze --skill proofreader --file conversation.txt

# Mine recent brain conversations for feedback
python optimize.py mine --recent 7
```

## How It Works

```
┌─────────────────────────────────────────────────────────────────┐
│                  INPUT (choose one)                             │
│                                                                 │
│  A) /optimize-skills workflow  → Antigravity self-reflects      │
│     and calls `inject` for each observation                     │
│                                                                 │
│  B) mine --recent 7           → Scans brain artifacts and       │
│     sends them to the LLM for analysis                          │
│                                                                 │
│  C) analyze --skill X --file  → Parses a USER:/ASSISTANT:       │
│     conversation and sends it to the LLM                        │
│                                                                 │
│  D) inject --skill X ...      → Adds a suggestion directly      │
│                                                                 │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
                  suggestions.json
                  (pending suggestions)
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                     APPLY (when ready)                          │
│                                                                 │
│  python optimize.py apply             ← dry-run preview         │
│  python optimize.py apply --confirm   ← write to SKILL.md      │
│                                                                 │
│  Updates SKILL.md files with:                                   │
│  - Trigger phrases in YAML description                          │
│  - User Preferences section                                     │
│  - Learned Corrections section                                  │
│  - Improvement notes                                            │
│  - Usage Metrics table                                          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Three Ways to Optimize Skills

### 🅰️ Self-Reflection via `/optimize-skills` (recommended)

Run the `/optimize-skills` workflow in Antigravity at the end of a session. The AI reflects on the conversation and injects suggestions automatically.

1. Use skills as normal (e.g., Smagskombinator, proofreader)
2. Say `/optimize-skills` — or trigger the workflow manually
3. Antigravity identifies which skills were used and what the user asked for
4. For each observation, it runs `optimize.py inject`
5. Review with `optimize.py apply` and confirm with `--confirm`

### 🅱️ Artifact Mining (batch)

Analyze historical conversations via artifacts stored in the brain directory:

```bash
# Analyze a specific conversation
python optimize.py mine --conversation cb7f013c-4c84-47c0-99de-9d8e7a013524

# Analyze the last 7 days of conversations
python optimize.py mine --recent 7
```

### 🅲️ Manual Analysis (ad-hoc)

Paste a conversation or point to a file:

```bash
# From file
python optimize.py analyze --skill proofreader --file conversation.txt

# From stdin (paste, end with Ctrl+Z on Windows / Ctrl+D on Unix)
python optimize.py analyze --skill proofreader
```

Expected conversation format:
```
USER: Kan du rette denne tekst?
ASSISTANT: Her er den rettede version...
USER: Nej, behold de danske anførselstegn
ASSISTANT: Beklager, her er teksten med danske anførselstegn...
```

## CLI Reference

| Command | Description |
|---------|-------------|
| `status [--skill X]` | Show pending suggestions and skill metrics |
| `inject --skill X --category Y --content "Z" [--reason R]` | Add a suggestion manually |
| `apply [--confirm] [--skill X] [--all]` | Preview or write changes to SKILL.md |
| `demo` | Run a built-in demo session on Smagskombinator |
| `analyze --skill X [--file F]` | Analyze a USER:/ASSISTANT: conversation |
| `mine --conversation ID` / `--recent N` | Mine brain artifacts for feedback |

### Global flags

| Flag | Description |
|------|-------------|
| `--skills-dir PATH` | Override the skills directory |
| `--provider NAME` | Override the LLM provider (`gemini` or `anthropic`) |
| `--brain-dir PATH` | Override the brain directory (used by `mine`) |

## File Structure

```
~/.gemini/antigravity/skills/
├── smagskombinator/
│   └── SKILL.md                ← Updated by optimizer
├── proofreader/
│   └── SKILL.md
├── ...
│
└── .optimizer/                  ← Created automatically
    ├── suggestions.json         ← Pending & applied suggestions
    └── metrics.json             ← Usage metrics per skill
```

## Python API

The CLI wraps a Python library that can also be used programmatically:

### SkillOptimizer

```python
from skill_optimizer import SkillOptimizer

optimizer = SkillOptimizer(
    skills_dir="~/.gemini/antigravity/skills",  # Path to skills
    provider="gemini",           # "gemini" (default) or "anthropic"
    api_key=None,                # Optional; falls back to .env / env vars
    data_dir=None,               # Optional; defaults to skills_dir/.optimizer
    model=None,                  # Optional; uses provider default if None
)

# View pending suggestions
suggestions = optimizer.get_suggestions()                      # All pending
suggestions = optimizer.get_suggestions("smagskombinator")     # For one skill
print(optimizer.get_suggestions_summary())                     # Text summary

# Apply suggestions
changes = optimizer.apply()                                    # Apply all
changes = optimizer.apply("smagskombinator")                   # One skill only
changes = optimizer.apply(dry_run=True)                        # Preview only

# Metrics
metrics = optimizer.get_metrics("smagskombinator")
all_metrics = optimizer.get_all_metrics()

# Manage applied suggestions
optimizer.store.clear_applied()    # Remove applied suggestions from JSON
```

### Session (programmatic conversation analysis)

```python
session = optimizer.start_session(user_id="user_123", org="acme-corp")

# Track conversation
session.add_message("user", "Create a document")
session.add_message("assistant", "Here's your document...")

# Track skill usage
session.track_skill(
    skill_name="proofreader",
    exec_time_ms=1500,
    success=True,
    error=None,       # Optional error message if failed
)

# End and analyze (choose one)
await session.end()      # Async
session.end_sync()       # Sync

# Properties
session.session_id       # Unique ID
session.user_id          # User identifier (optional)
session.org              # Organization identifier (optional)
session.messages         # List of Message objects
session.skill_usages     # List of SkillUsage objects
session.duration_seconds # Session duration
```

### Suggestion

```python
@dataclass
class Suggestion:
    skill_name: str                # Which skill this is for
    category: str                  # "correction", "preference", "trigger", "improvement"
    content: str                   # The actual suggestion text
    reason: Optional[str]          # Why (from conversation analysis)
    session_id: Optional[str]      # Which session it came from
    user_id: Optional[str]         # Which user created this session
    org: Optional[str]             # Which organization
    created_at: str                # ISO timestamp
    applied: bool                  # Whether it's been applied
```

### LLM Client

The optimizer supports multiple LLM providers through an abstract `LLMClient`:

```python
from skill_optimizer.llm_client import create_client

# Create a Gemini client (default, uses GEMINI_API_KEY from .env)
client = create_client("gemini")

# Create an Anthropic client
client = create_client("anthropic", api_key="sk-ant-...")

# Use directly
response = client.generate_sync("Analyze this text...")
response = await client.generate("Async analysis...")
```

| Provider | Default model | Env var for API key |
|----------|---------------|---------------------|
| `gemini` | `gemini-2.0-flash` | `GEMINI_API_KEY` |
| `anthropic` | `claude-sonnet-4-20250514` | `ANTHROPIC_API_KEY` |

## Safety Nets

- **Dry-run by default** — `apply` always shows a preview; use `--confirm` to write
- **Git-backed** — SKILL.md files live in Git, so you can always roll back
- **200-char description limit** — trigger phrases are capped to prevent Antigravity routing issues
- **Deduplication** — identical suggestions are never added twice

## License

MIT
