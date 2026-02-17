"""
rules.py — Validation rules and patterns for Skill verifier.
"""
import re

# ── Structure Rules ────────────────────────────────────────────────

REQUIRED_FIELDS = ["name", "description"]
MAX_DESCRIPTION_LENGTH = 200
MIN_DESCRIPTION_LENGTH = 10
MIN_BODY_LENGTH = 50  # Very short body might indicate unfinished skill

# ── Style Warnings (Anti-Slop / Quality) ───────────────────────────

# Regex patterns to flag "lazy" or "generic" AI language.
# We focus on phrases that indicate the model is "chatting" rather than "acting".
STYLE_WARNINGS = {
    r"(?i)\bsom (en )?AI(?:\-)?(sprog)?model": "Avoid self-referencing as an AI. Just be the persona.",
    r"(?i)\bher er (en )?liste": "Avoid announcing lists ('Here is a list'). Just provide the list.",
    r"(?i)\blad os (dykke|kigge) (ned )?i": "Avoid filler intro phrases ('Let's dive in'). Start directly.",
    r"(?i)\bhusk (altid )?at": "Avoid preaching ('Remember to'). Use imperative instructions.",
    r"(?i)\bdet er vigtigt at": "Avoid padding ('It is important to'). State the requirement directly.",
    r"(?i)\bjeg (kan|vil) (godt )?hjælpe": "Avoid stating ability ('I can help'). Just help.",
    r"(?i)\bvelkommen til": "Avoid 'Welcome to' in skill instructions. It's a tool, not a website.",
}

# ── Security Rules ─────────────────────────────────────────────────

# Paths that look like they're trying to escape the directory
PATH_TRAVERSAL_PATTERN = re.compile(r"\.\.[/\\]")

# Potential hardcoded secrets (simplistic check)
SECRET_PATTERNS = {
    r"(?i)api[_-]?key\s*[:=]\s*['\"][a-zA-Z0-9_\-]{20,}['\"]": "Possible hardcoded API key",
    r"(?i)password\s*[:=]\s*['\"][^'\"]{8,}['\"]": "Possible hardcoded password",
}
