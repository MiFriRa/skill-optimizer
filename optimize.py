#!/usr/bin/env python3
"""
optimize.py — CLI for Skill Optimizer.

Commands:
    status                    Show pending suggestions and skill metrics
    inject                    Add a suggestion programmatically
    apply                     Preview changes (dry-run by default)
    apply --confirm           Write changes to SKILL.md files
    demo                      Run a built-in demo session on Smagskombinator
    analyze --skill <name>    Analyze a conversation from file or stdin
    mine --conversation <id>  Analyze artifacts from a brain conversation

Usage examples:
    python optimize.py status
    python optimize.py inject --skill smagskombinator --category preference --content "Brug altid sesam"
    python optimize.py apply
    python optimize.py apply --confirm --skill smagskombinator
    python optimize.py demo
    python optimize.py analyze --skill proofreader --file conversation.txt
    python optimize.py mine --conversation cb7f013c-4c84-47c0-99de-9d8e7a013524
    python optimize.py mine --recent 7
"""

import argparse
import json
import os
import sys
import textwrap
from datetime import datetime, timedelta
from pathlib import Path

# ── Bootstrap ────────────────────────────────────────────────────
# Allow running from project root without pip install
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from dotenv import load_dotenv
load_dotenv()

from skill_optimizer import SkillOptimizer, Suggestion
from skill_optimizer.llm_client import create_client
from skill_optimizer.verifier import SkillVerifier

# ── Defaults ─────────────────────────────────────────────────────
DEFAULT_SKILLS_DIR = os.environ.get(
    "SKILLS_DIR",
    str(Path.home() / ".gemini" / "antigravity" / "skills"),
)
DEFAULT_BRAIN_DIR = os.environ.get(
    "BRAIN_DIR",
    str(Path.home() / ".gemini" / "antigravity" / "brain"),
)
DEFAULT_PROVIDER = os.environ.get("OPTIMIZER_PROVIDER", "gemini")


def get_optimizer(args) -> SkillOptimizer:
    """Create an optimizer instance from CLI args."""
    skills_dir = getattr(args, "skills_dir", None) or DEFAULT_SKILLS_DIR
    provider = getattr(args, "provider", None) or DEFAULT_PROVIDER

    opt = SkillOptimizer(
        skills_dir=skills_dir,
        provider=provider,
    )
    return opt


# ── Commands ─────────────────────────────────────────────────────

def cmd_status(args):
    """Show pending suggestions and skill metrics."""
    opt = get_optimizer(args)
    skill_filter = getattr(args, "skill", None)

    pending = opt.store.get_pending_suggestions(skill_name=skill_filter)
    print(f"\n{'='*60}")
    print(f"  Skill Optimizer Status")
    print(f"  Skills dir: {opt.skills_dir}")
    print(f"  Skills found: {len(opt.skill_names)}")
    print(f"{'='*60}")

    if pending:
        print(f"\n  📋 Pending suggestions: {len(pending)}\n")
        by_skill = {}
        for s in pending:
            by_skill.setdefault(s.skill_name, []).append(s)
        for name, suggestions in sorted(by_skill.items()):
            print(f"  {name}:")
            for s in suggestions:
                print(f"    [{s.category:12s}] {s.content[:70]}")
    else:
        print("\n  ✅ No pending suggestions.\n")

    metrics = opt.store.get_all_metrics()
    if metrics:
        print(f"\n  📊 Tracked skills: {len(metrics)}\n")
        for name, m in sorted(metrics.items()):
            print(f"    {name}: {m.total_calls} calls, "
                  f"{m.success_rate:.0%} success, "
                  f"{m.avg_exec_time_ms:.0f}ms avg")
    print()


def cmd_inject(args):
    """Add a suggestion programmatically."""
    opt = get_optimizer(args)

    if args.skill not in opt.skill_names:
        known = ", ".join(sorted(opt.skill_names))
        print(f"⚠️  Unknown skill '{args.skill}'. Known skills:\n  {known}")
        sys.exit(1)

    suggestion = Suggestion(
        skill_name=args.skill,
        category=args.category,
        content=args.content,
        reason=args.reason or "Injected via CLI",
        session_id="cli-inject",
        user_id=os.environ.get("USER", "unknown"),
    )
    opt.store.add_suggestion(suggestion)
    print(f"✅ Added [{args.category}] suggestion for '{args.skill}':")
    print(f"   {args.content}")


def cmd_apply(args):
    """Apply pending suggestions to SKILL.md files."""
    opt = get_optimizer(args)
    skill_filter = getattr(args, "skill", None)
    confirm = getattr(args, "confirm", False)
    apply_all = getattr(args, "all", False)

    if skill_filter:
        skills_to_process = [skill_filter]
    elif apply_all:
        skills_to_process = sorted(opt.skill_names)
    else:
        # Only skills with pending suggestions
        pending = opt.store.get_pending_suggestions()
        skills_to_process = sorted(set(s.skill_name for s in pending))

    if not skills_to_process:
        print("✅ No pending suggestions to apply.")
        return

    dry_run = not confirm
    mode_label = "DRY-RUN PREVIEW" if dry_run else "APPLYING CHANGES"

    print(f"\n{'='*60}")
    print(f"  {mode_label}")
    print(f"{'='*60}\n")

    for skill_name in skills_to_process:
        pending = opt.store.get_pending_suggestions(skill_name=skill_name)
        if not pending:
            continue

        print(f"  📝 {skill_name} ({len(pending)} suggestions)")
        for s in pending:
            print(f"     [{s.category:12s}] {s.content[:60]}")

        result = opt.apply(skill_name, dry_run=dry_run)
        if result:
            action = result.get(skill_name, result) if isinstance(result, dict) else result
            if dry_run:
                # Show what the updated file would look like
                skill_path = opt._skill_paths.get(skill_name)
                if skill_path and skill_path.exists():
                    content = opt._read_skill(skill_path)
                    new_content, _ = opt._update_skill_content(
                        content, skill_name, pending
                    )
                    print(f"\n     --- Preview ---")
                    for line in new_content.split("\n"):
                        print(f"     {line}")
                    print(f"     --- End preview ---\n")
            else:
                print(f"     ✅ Applied successfully\n")
        else:
            print(f"     (no changes)\n")

    if dry_run:
        print("  ℹ️  This was a dry-run. To apply, run:")
        print("     python optimize.py apply --confirm\n")


def cmd_demo(args):
    """Run a built-in demo session."""
    opt = get_optimizer(args)

    print(f"\n{'='*60}")
    print(f"  Demo: Smagskombinator session")
    print(f"{'='*60}\n")

    if "smagskombinator" not in opt.skill_names:
        print("⚠️  Smagskombinator not found in skills dir.")
        sys.exit(1)

    # Simulate suggestions that would come from a real conversation
    demo_suggestions = [
        Suggestion(
            skill_name="smagskombinator",
            category="preference",
            content="Foreslå altid en grøntsagsbaseret variant først",
            reason="Demo: bruger foretrækker grøntsager som udgangspunkt",
            session_id="demo-session",
            user_id="demo",
        ),
        Suggestion(
            skill_name="smagskombinator",
            category="trigger",
            content="hvad passer til",
            reason="Demo: bruger sagde 'hvad passer til butternut?'",
            session_id="demo-session",
            user_id="demo",
        ),
        Suggestion(
            skill_name="smagskombinator",
            category="correction",
            content="Undgå at foreslå kimchi i europæiske retter medmindre brugeren beder om det",
            reason="Demo: bruger sagde 'det er for asiatisk'",
            session_id="demo-session",
            user_id="demo",
        ),
    ]

    for s in demo_suggestions:
        opt.store.add_suggestion(s)
        print(f"  ➕ [{s.category:12s}] {s.content}")

    print(f"\n  Preview af ændringer:\n")

    content = opt._read_skill(opt._skill_paths["smagskombinator"])
    new_content, changes = opt._update_skill_content(
        content, "smagskombinator",
        opt.get_suggestions("smagskombinator"),
    )

    for line in new_content.split("\n"):
        print(f"  {line}")

    print(f"\n  Changes: {json.dumps(changes, indent=2, ensure_ascii=False)}")
    print(f"\n  ℹ️  Suggestions stored. Run 'python optimize.py apply --confirm "
          f"--skill smagskombinator' to write.\n")


def cmd_analyze(args):
    """Analyze a conversation from file or stdin."""
    opt = get_optimizer(args)

    if args.file:
        text = Path(args.file).read_text(encoding="utf-8")
    else:
        print("Paste conversation (Ctrl+Z to end on Windows, Ctrl+D on Unix):")
        text = sys.stdin.read()

    if not text.strip():
        print("⚠️  Empty input.")
        sys.exit(1)

    print(f"\n  Analyzing conversation for skill '{args.skill}'...")

    # Create a session and feed the conversation
    session = opt.start_session(user_id="cli-analyze")
    session.track_skill(args.skill, exec_time_ms=0, success=True)

    # Parse USER: / ASSISTANT: blocks
    current_role = None
    current_lines = []

    for line in text.split("\n"):
        stripped = line.strip()
        if stripped.upper().startswith("USER:"):
            if current_role and current_lines:
                session.add_message(current_role, "\n".join(current_lines))
            current_role = "user"
            current_lines = [stripped[5:].strip()]
        elif stripped.upper().startswith("ASSISTANT:"):
            if current_role and current_lines:
                session.add_message(current_role, "\n".join(current_lines))
            current_role = "assistant"
            current_lines = [stripped[10:].strip()]
        elif current_role:
            current_lines.append(stripped)

    if current_role and current_lines:
        session.add_message(current_role, "\n".join(current_lines))

    if not session.messages:
        print("⚠️  Could not parse any USER:/ASSISTANT: messages.")
        sys.exit(1)

    print(f"  Parsed {len(session.messages)} messages. Sending to LLM...")

    # End session (triggers LLM analysis)
    import asyncio
    asyncio.run(session.end())

    pending = opt.store.get_pending_suggestions(skill_name=args.skill)
    if pending:
        print(f"\n  📋 Generated {len(pending)} suggestions:\n")
        for s in pending:
            print(f"    [{s.category:12s}] {s.content}")
        print(f"\n  Run 'python optimize.py apply' to preview changes.")
    else:
        print("  No suggestions generated (conversation may not contain feedback).")


def cmd_mine(args):
    """Mine artifacts from brain conversations."""
    opt = get_optimizer(args)
    brain_dir = Path(getattr(args, "brain_dir", None) or DEFAULT_BRAIN_DIR)

    if not brain_dir.exists():
        print(f"⚠️  Brain directory not found: {brain_dir}")
        sys.exit(1)

    # Collect conversations to process
    conv_dirs = []
    if args.conversation:
        target = brain_dir / args.conversation
        if target.exists():
            conv_dirs = [target]
        else:
            print(f"⚠️  Conversation not found: {args.conversation}")
            sys.exit(1)
    elif args.recent:
        cutoff = datetime.utcnow() - timedelta(days=args.recent)
        for d in sorted(brain_dir.iterdir()):
            if d.is_dir() and d.name != "tempmediaStorage":
                # Check modification time of any file
                try:
                    newest = max(f.stat().st_mtime for f in d.iterdir() if f.is_file())
                    if datetime.utcfromtimestamp(newest) >= cutoff:
                        conv_dirs.append(d)
                except (ValueError, OSError):
                    pass
    else:
        print("⚠️  Specify --conversation <id> or --recent <days>")
        sys.exit(1)

    if not conv_dirs:
        print("  No conversations to process.")
        return

    print(f"\n  Mining {len(conv_dirs)} conversation(s)...\n")

    # Build a combined text from artifacts
    for conv_dir in conv_dirs:
        artifacts_text = []
        metadata_files = sorted(conv_dir.glob("*.metadata.json"))

        for mf in metadata_files:
            try:
                meta = json.loads(mf.read_text(encoding="utf-8"))
                artifact_name = mf.name.replace(".metadata.json", "")
                resolved = conv_dir / f"{artifact_name}.resolved"
                if resolved.exists():
                    content = resolved.read_text(encoding="utf-8")
                    summary = meta.get("summary", "")
                    artifacts_text.append(
                        f"[Artifact: {artifact_name}]\n"
                        f"Summary: {summary}\n"
                        f"Content:\n{content[:2000]}\n"
                    )
            except Exception:
                continue

        if not artifacts_text:
            continue

        print(f"  📂 {conv_dir.name}")
        print(f"     {len(artifacts_text)} artifacts found")

        # Use LLM to extract skill feedback from artifacts
        known_skills = ", ".join(sorted(opt.skill_names))
        prompt = f"""Analyze these artifacts from an AI conversation session.
Identify which of these skills were likely used: {known_skills}

For each skill used, extract feedback in these categories:
- correction: mistakes that should be fixed
- preference: user style preferences
- trigger: new phrases that should trigger the skill
- improvement: general improvements

ARTIFACTS:
{"---".join(artifacts_text)}

Return JSON only:
{{"suggestions": [{{"skill_name": "...", "category": "...", "content": "...", "reason": "..."}}]}}
If no suggestions, return: {{"suggestions": []}}"""

        try:
            response = opt.client.generate_sync(prompt)
            # Parse JSON from response
            json_start = response.find("{")
            json_end = response.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                data = json.loads(response[json_start:json_end])
                suggestions = data.get("suggestions", [])
                for s_data in suggestions:
                    if s_data.get("skill_name") in opt.skill_names:
                        opt.store.add_suggestion(Suggestion(
                            skill_name=s_data["skill_name"],
                            category=s_data.get("category", "improvement"),
                            content=s_data.get("content", ""),
                            reason=s_data.get("reason", "Mined from artifacts"),
                            session_id=f"mine-{conv_dir.name[:8]}",
                            user_id="artifact-mining",
                        ))
                print(f"     ➕ {len(suggestions)} suggestions extracted")
            else:
                print(f"     (no valid JSON in response)")
        except Exception as e:
            print(f"     ⚠️  LLM error: {e}")
    print(f"\n  Run 'python optimize.py status' to see all suggestions.\n")


def cmd_verify(args):
    """Verify skills against quality and security rules."""
    opt = get_optimizer(args)
    verifier = SkillVerifier()
    
    skill_filter = getattr(args, "skill", None)
    
    if skill_filter:
        if skill_filter not in opt.skill_names:
            print(f"⚠️  Skill '{skill_filter}' not found.")
            return
        skills_to_check = [skill_filter]
    else:
        skills_to_check = sorted(opt.skill_names)

    print(f"\n{'='*60}")
    print(f"  Skill Verification: {len(skills_to_check)} skills")
    print(f"{'='*60}\n")
    
    issues_found = 0
    clean_skills = 0
    
    for skill_name in skills_to_check:
        skill_path = opt._skill_paths.get(skill_name)
        if not skill_path:
            continue
            
        result = verifier.verify_file(skill_path)
        
        if result.valid and not result.issues:
            clean_skills += 1
            if args.verbose:
                 print(f"  ✅ {skill_name}")
        else:
            status_icon = "❌" if not result.valid else "⚠️ "
            print(f"  {status_icon} {skill_name}")
            for issue in result.issues:
                # Color code based on severity (simple ANSI)
                color = "\033[91m" if issue.severity == "error" else "\033[93m"
                reset = "\033[0m"
                loc = f" (line {issue.line})" if issue.line else ""
                print(f"     {color}[{issue.code}]{reset} {issue.message}{loc}")
            issues_found += len(result.issues)
            print()

    print(f"{'='*60}")
    print(f"Summary: {clean_skills} clean, {len(skills_to_check) - clean_skills} with issues.")
    if issues_found > 0:
        sys.exit(1)


# ── Argument Parser ──────────────────────────────────────────────

def build_parser():
    parser = argparse.ArgumentParser(
        prog="optimize.py",
        description="Skill Optimizer CLI — optimize Antigravity skills from conversations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
        Examples:
          python optimize.py status
          python optimize.py demo
          python optimize.py inject --skill smagskombinator --category preference --content "Brug sesam"
          python optimize.py apply
          python optimize.py apply --confirm --skill smagskombinator
          python optimize.py analyze --skill proofreader --file conversation.txt
          python optimize.py mine --recent 7
        """),
    )
    parser.add_argument("--skills-dir", help="Path to skills directory")
    parser.add_argument("--provider", help="LLM provider (gemini/anthropic)")
    parser.add_argument("--brain-dir", help="Path to brain directory")

    sub = parser.add_subparsers(dest="command", help="Command to run")

    # status
    p_status = sub.add_parser("status", help="Show pending suggestions and metrics")
    p_status.add_argument("--skill", help="Filter by skill name")

    # inject
    p_inject = sub.add_parser("inject", help="Add a suggestion programmatically")
    p_inject.add_argument("--skill", required=True, help="Skill name")
    p_inject.add_argument("--category", required=True,
                          choices=["correction", "preference", "trigger", "improvement"],
                          help="Suggestion category")
    p_inject.add_argument("--content", required=True, help="Suggestion content")
    p_inject.add_argument("--reason", help="Reason for suggestion")

    # apply
    p_apply = sub.add_parser("apply", help="Apply pending suggestions")
    p_apply.add_argument("--confirm", action="store_true",
                         help="Actually write changes (default is dry-run)")
    p_apply.add_argument("--skill", help="Only apply to this skill")
    p_apply.add_argument("--all", action="store_true",
                         help="Apply to all skills with pending suggestions")

    # demo
    sub.add_parser("demo", help="Run a built-in demo session")

    # analyze
    p_analyze = sub.add_parser("analyze", help="Analyze a conversation")
    p_analyze.add_argument("--skill", required=True, help="Skill to analyze for")
    p_analyze.add_argument("--file", help="Conversation file (or stdin)")

    p_mine = sub.add_parser("mine", help="Mine artifacts from brain conversations")
    p_mine.add_argument("--conversation", help="Conversation ID to analyze")
    p_mine.add_argument("--recent", type=int, help="Analyze last N days")

    # verify
    p_verify = sub.add_parser("verify", help="Verify skills against rules")
    p_verify.add_argument("--skill", help="Verify specific skill")
    p_verify.add_argument("--verbose", action="store_true", help="Show passed skills too")

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    commands = {
        "status": cmd_status,
        "inject": cmd_inject,
        "apply": cmd_apply,
        "demo": cmd_demo,
        "analyze": cmd_analyze,
        "mine": cmd_mine,
        "verify": cmd_verify,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
