# Changelog

## [0.4.0] — 2026-02-16 (Antigravity Fork)

### Changed
- Default LLM provider switched from Anthropic to **Google Gemini** (`gemini-2.0-flash`)
- Default skills directory changed to `~/.gemini/antigravity/skills`
- README.md fully rewritten to reflect current CLI-first workflow

### Added
- **CLI** (`optimize.py`) with 6 commands: `status`, `inject`, `apply`, `demo`, `analyze`, `mine`
- **Multi-provider LLM client** — supports both Gemini and Anthropic via `create_client()` factory
- **Artifact mining** (`mine` command) — extracts feedback from Antigravity brain conversations
- **Conversation analysis** (`analyze` command) — parses USER:/ASSISTANT: transcripts
- **Antigravity workflow** (`.agent/workflows/optimize-skills.md`) for in-session self-reflection
- **Danish user manual** (`doc/manual.md`)
- `.env.example` for onboarding
- `CONTRIBUTING.md`

### Fixed
- 200-character description length limit to prevent Antigravity routing issues
- OS-agnostic line ending handling in SKILL.md read/write
- Duplicate suggestion prevention

## [0.3.0] — 2025 (Original by Meet Patel)

- Initial release by [Meet Patel](https://github.com/meet-rocking)
- Claude/Anthropic-based session tracking and suggestion system
- Python library API with async/sync session management
- Suggestion store with JSON persistence
- Skill metrics tracking
