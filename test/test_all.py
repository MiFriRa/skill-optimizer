"""
Test script for skill-optimizer.

Usage:
    Set your GEMINI_API_KEY in .env, then run:
        python test/test_all.py

    Or pass provider and key as arguments:
        python test/test_all.py gemini AIza...
        python test/test_all.py anthropic sk-ant-api03-...
"""

import sys
import os
import logging
import shutil
from pathlib import Path

# ── Setup paths so we can import from src/ without installing ──
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from skill_optimizer import SkillOptimizer, Session, Suggestion
from skill_optimizer.llm_client import LLMClient, create_client

# ── Logging – shows the logs we added (truncation, API errors, parse warnings) ──
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

# ── Resolve paths ──
TEST_DIR = Path(__file__).resolve().parent
SKILLS_DIR = TEST_DIR / "skills"
DATA_DIR = TEST_DIR / "data"     # keeps test data separate from skills

# Original SKILL.md content so we can reset between runs
ORIGINAL_SKILL_MD = """---
name: dashboard
description: "Create interactive data dashboards with charts and visualizations"
---

# Dashboard Skill

Creates interactive dashboards for data visualization.

## Instructions

- Use clean, modern styling
- Include axis labels on all charts
- Default to responsive layouts
"""


class MockLLMClient(LLMClient):
    """Fake LLM client for offline tests."""

    async def generate(self, prompt: str) -> str:
        raise RuntimeError("MockLLMClient: should not be called in offline tests")

    def generate_sync(self, prompt: str) -> str:
        raise RuntimeError("MockLLMClient: should not be called in offline tests")


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────
def separator(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def clean_data():
    """Remove previous test data and reset SKILL.md so each run starts fresh."""
    if DATA_DIR.exists():
        shutil.rmtree(DATA_DIR)
    # Also remove .optimizer inside skills if it leaked
    opt = SKILLS_DIR / ".optimizer"
    if opt.exists():
        shutil.rmtree(opt)
    # Reset SKILL.md to original state
    skill_file = SKILLS_DIR / "dashboard" / "SKILL.md"
    skill_file.parent.mkdir(parents=True, exist_ok=True)
    skill_file.write_text(ORIGINAL_SKILL_MD)


# ─────────────────────────────────────────────
# 1. Offline tests (no API key needed)
# ─────────────────────────────────────────────
def test_init_and_skill_scan():
    separator("1. Init & Skill Scan")

    optimizer = SkillOptimizer(
        skills_dir=str(SKILLS_DIR),
        api_key="fake-key",
        data_dir=str(DATA_DIR),
        provider="gemini",
    )
    # Override with mock client so no real API key is needed
    optimizer.client = MockLLMClient()

    print(f"Skills found: {optimizer.skill_names}")
    assert "dashboard" in optimizer.skill_names, "dashboard skill not found"
    print("PASSED: dashboard skill detected\n")


def test_session_user_org():
    separator("2. Session user_id / org fields")

    optimizer = SkillOptimizer(
        skills_dir=str(SKILLS_DIR),
        api_key="fake-key",
        data_dir=str(DATA_DIR),
        provider="gemini",
    )
    optimizer.client = MockLLMClient()

    session = optimizer.start_session(user_id="user_42", org="acme-corp")

    assert session.user_id == "user_42", f"Expected user_42, got {session.user_id}"
    assert session.org == "acme-corp", f"Expected acme-corp, got {session.org}"
    print(f"session.session_id = {session.session_id}")
    print(f"session.user_id    = {session.user_id}")
    print(f"session.org        = {session.org}")
    print("PASSED: user_id and org stored on session\n")

    # Session without user_id / org (backward compat)
    session2 = optimizer.start_session()
    assert session2.user_id is None
    assert session2.org is None
    print("PASSED: session without user_id/org still works\n")


def test_suggestion_user_org_fields():
    separator("3. Suggestion user_id / org fields")

    s = Suggestion(
        skill_name="dashboard",
        category="preference",
        content="Use dark theme by default",
        reason="User requested dark theme",
        session_id="sess-1",
        user_id="user_42",
        org="acme-corp",
    )

    d = s.to_dict()
    assert d["user_id"] == "user_42"
    assert d["org"] == "acme-corp"
    print(f"to_dict(): user_id={d['user_id']}, org={d['org']}")

    s2 = Suggestion.from_dict(d)
    assert s2.user_id == "user_42"
    assert s2.org == "acme-corp"
    print(f"from_dict(): user_id={s2.user_id}, org={s2.org}")
    print("PASSED: Suggestion round-trips with user_id/org\n")

    # Backward compat – old data without user_id/org
    old_data = {
        "skill_name": "dashboard",
        "category": "correction",
        "content": "Add title to charts",
        "reason": "User complained",
        "session_id": "old-sess",
        "created_at": "2025-01-01T00:00:00",
        "applied": False,
    }
    s3 = Suggestion.from_dict(old_data)
    assert s3.user_id is None
    assert s3.org is None
    print("PASSED: Old suggestion data (no user_id/org) loads fine\n")


def test_suggestion_filtering():
    separator("4. Suggestion filtering by user_id / org")

    from skill_optimizer.suggestions import SuggestionStore

    store = SuggestionStore(DATA_DIR)

    store.add_suggestion(Suggestion(
        skill_name="dashboard", category="preference",
        content="Dark theme", user_id="alice", org="acme",
    ))
    store.add_suggestion(Suggestion(
        skill_name="dashboard", category="correction",
        content="Fix axis labels", user_id="bob", org="acme",
    ))
    store.add_suggestion(Suggestion(
        skill_name="dashboard", category="improvement",
        content="Add export button", user_id="alice", org="globex",
    ))

    all_pending = store.get_pending_suggestions()
    print(f"All pending: {len(all_pending)}")
    assert len(all_pending) == 3

    by_user = store.get_pending_suggestions(user_id="alice")
    print(f"alice's suggestions: {len(by_user)}")
    assert len(by_user) == 2
    assert all(s.user_id == "alice" for s in by_user)

    by_org = store.get_pending_suggestions(org="acme")
    print(f"acme org suggestions: {len(by_org)}")
    assert len(by_org) == 2
    assert all(s.org == "acme" for s in by_org)

    by_both = store.get_pending_suggestions(user_id="alice", org="acme")
    print(f"alice + acme: {len(by_both)}")
    assert len(by_both) == 1
    assert by_both[0].content == "Dark theme"

    by_skill_user = store.get_pending_suggestions(skill_name="dashboard", user_id="bob")
    print(f"dashboard + bob: {len(by_skill_user)}")
    assert len(by_skill_user) == 1

    print("PASSED: all filter combinations work\n")


def test_truncation():
    separator("5. Conversation truncation")

    from skill_optimizer.session import MAX_ANALYSIS_MESSAGES

    optimizer = SkillOptimizer(
        skills_dir=str(SKILLS_DIR),
        api_key="fake-key",
        data_dir=str(DATA_DIR),
        provider="gemini",
    )
    optimizer.client = MockLLMClient()

    session = optimizer.start_session(user_id="user_1", org="test-org")

    # Add more messages than the limit
    num_messages = MAX_ANALYSIS_MESSAGES + 50
    for i in range(num_messages):
        role = "user" if i % 2 == 0 else "assistant"
        session.add_message(role, f"Message number {i}")

    session.track_skill("dashboard", exec_time_ms=100, success=True)

    # Build prompt and verify truncation happened
    prompt = session._build_analysis_prompt()

    assert f"[...truncated 50 earlier messages...]" in prompt
    # The first kept message should be message number 50 (0-indexed)
    assert "Message number 50" in prompt
    # The very first message should NOT be in the prompt
    assert "Message number 0\n" not in prompt
    # The last message should be present
    assert f"Message number {num_messages - 1}" in prompt

    print(f"Total messages added: {num_messages}")
    print(f"MAX_ANALYSIS_MESSAGES: {MAX_ANALYSIS_MESSAGES}")
    print(f"Truncation marker found in prompt: YES")
    print(f"Old messages excluded: YES")
    print(f"Recent messages included: YES")
    print("PASSED: truncation works correctly\n")


def test_metrics_tracking():
    separator("6. Metrics tracking")

    optimizer = SkillOptimizer(
        skills_dir=str(SKILLS_DIR),
        api_key="fake-key",
        data_dir=str(DATA_DIR),
        provider="gemini",
    )
    optimizer.client = MockLLMClient()

    session = optimizer.start_session(user_id="user_1", org="test-org")
    session.track_skill("dashboard", exec_time_ms=1500, success=True)
    session.track_skill("dashboard", exec_time_ms=2000, success=True)
    session.track_skill("dashboard", exec_time_ms=500, success=False, error="timeout")

    metrics = optimizer.get_metrics("dashboard")
    print(f"Total calls: {metrics.total_calls}")
    print(f"Success rate: {metrics.success_rate:.0%}")
    print(f"Avg exec time: {metrics.avg_exec_time_ms:.0f}ms")

    assert metrics.total_calls >= 3
    assert metrics.successful_calls >= 2
    assert metrics.failed_calls >= 1
    print("PASSED: metrics recorded correctly\n")


def test_api_failure_logging():
    separator("7. API failure logging (fake key)")

    optimizer = SkillOptimizer(
        skills_dir=str(SKILLS_DIR),
        api_key="fake-key",
        data_dir=str(DATA_DIR),
        provider="gemini",
    )
    optimizer.client = MockLLMClient()

    session = optimizer.start_session(user_id="user_1", org="test-org")
    session.add_message("user", "Create a dashboard")
    session.track_skill("dashboard", exec_time_ms=1000, success=True)
    session.add_message("assistant", "Here's your dashboard")

    # This should NOT crash – it should log the error and return []
    suggestions = session.end_sync()
    assert suggestions == [], f"Expected empty list, got {suggestions}"
    print("PASSED: API failure handled gracefully, returned []\n")
    print("(Check logs above for the error message)\n")


# ─────────────────────────────────────────────
# 8. Live API test (requires real key)
# ─────────────────────────────────────────────
def test_live_session(provider: str, api_key: str):
    separator("8. Live API test (real key)")

    optimizer = SkillOptimizer(
        skills_dir=str(SKILLS_DIR),
        api_key=api_key,
        data_dir=str(DATA_DIR),
        provider=provider,
    )

    session = optimizer.start_session(user_id="test_user", org="test_org")

    # Simulate a conversation where user corrects the skill output
    session.add_message("user", "Create a sales dashboard for Q4 revenue")
    session.track_skill("dashboard", exec_time_ms=2000, success=True)
    session.add_message("assistant",
        "Here's your Q4 revenue dashboard with pie charts showing "
        "revenue breakdown by region."
    )
    session.add_message("user",
        "Actually, I prefer bar charts for revenue comparisons, not pie charts. "
        "Also, always use dark theme for dashboards."
    )
    session.add_message("assistant",
        "Updated! Switched to bar charts and applied dark theme."
    )
    session.add_message("user",
        "Perfect. Next time when I say 'sales report', I mean this kind of dashboard."
    )
    session.add_message("assistant", "Got it, I'll remember that!")

    print("Sending conversation to Claude for analysis...")
    suggestions = session.end_sync()

    print(f"\nFound {len(suggestions)} suggestions:")
    for s in suggestions:
        print(f"  [{s.category}] {s.skill_name}: {s.content}")
        print(f"    reason: {s.reason}")
        print(f"    user_id: {s.user_id}, org: {s.org}")
        print()

    # Verify user_id/org carried through
    for s in suggestions:
        assert s.user_id == "test_user", f"Expected test_user, got {s.user_id}"
        assert s.org == "test_org", f"Expected test_org, got {s.org}"
        assert s.session_id == session.session_id

    if suggestions:
        print("PASSED: suggestions returned with correct user_id/org\n")
    else:
        print("WARNING: no suggestions returned (AI may not have found any)\n")

    # Show filtering
    separator("8b. Filtering suggestions")
    all_sugg = optimizer.get_suggestions()
    user_sugg = optimizer.get_suggestions(user_id="test_user")
    org_sugg = optimizer.get_suggestions(org="test_org")
    print(f"All pending: {len(all_sugg)}")
    print(f"By user_id='test_user': {len(user_sugg)}")
    print(f"By org='test_org': {len(org_sugg)}")

    # Show full status
    separator("8c. Optimizer status")
    print(optimizer.status())

    # Dry-run apply
    separator("8d. Dry-run apply")
    changes = optimizer.apply(dry_run=True)
    for skill, change in changes.items():
        print(f"  {skill}: {change}")
    if not changes:
        print("  (no changes to apply)")

    # Actual apply
    separator("8e. Apply suggestions to SKILL.md")
    changes = optimizer.apply()
    for skill, change in changes.items():
        print(f"  {skill}: {change}")
    if not changes:
        print("  (no changes to apply)")

    # Show updated SKILL.md
    skill_file = SKILLS_DIR / "dashboard" / "SKILL.md"
    if skill_file.exists():
        separator("8f. Updated SKILL.md")
        print(skill_file.read_text())

    print("PASSED: live test complete\n")


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────
def main():
    # Get provider and API key from args or env
    provider = "gemini"
    api_key = None

    if len(sys.argv) > 2:
        provider = sys.argv[1]
        api_key = sys.argv[2]
    elif len(sys.argv) > 1:
        api_key = sys.argv[1]
    else:
        # Try env vars
        from dotenv import load_dotenv
        load_dotenv()
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
        if os.environ.get("ANTHROPIC_API_KEY") and not os.environ.get("GEMINI_API_KEY"):
            provider = "anthropic"

    clean_data()

    # Offline tests (always run)
    test_init_and_skill_scan()
    test_session_user_org()
    test_suggestion_user_org_fields()
    test_suggestion_filtering()

    clean_data()  # reset for next batch

    test_truncation()
    test_metrics_tracking()
    test_api_failure_logging()

    # Live test (only if key provided)
    if api_key:
        clean_data()
        test_live_session(provider, api_key)
    else:
        separator("SKIPPED: Live API test")
        print("No API key provided. To run the live test:")
        print("  python test/test_all.py gemini AIza...")
        print("  python test/test_all.py anthropic sk-ant-api03-...")
        print("  or set GEMINI_API_KEY in .env\n")

    separator("ALL TESTS DONE")


if __name__ == "__main__":
    main()
