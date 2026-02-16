"""Manual verification: scan Antigravity skills and dry-run on smagskombinator."""
import os, sys
os.environ.setdefault("GEMINI_API_KEY", "fake-for-scan")

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent / "src"))

from skill_optimizer import SkillOptimizer
from skill_optimizer.llm_client import LLMClient
from skill_optimizer.suggestions import Suggestion

class MockClient(LLMClient):
    async def generate(self, prompt): return ""
    def generate_sync(self, prompt): return ""

opt = SkillOptimizer(
    skills_dir=r"C:\Users\mikke\.gemini\antigravity\skills",
    api_key="fake",
    provider="gemini",
)
opt.client = MockClient()

print(f"\n{'='*60}")
print(f"  Skills found: {len(opt.skill_names)}")
print(f"{'='*60}")
for i, name in enumerate(sorted(opt.skill_names), 1):
    path = opt._skill_paths[name]
    print(f"  {i:2d}. {name:45s} ({path.parent.name}/)")

# -- Dry-run on smagskombinator --
opt.store.add_suggestion(Suggestion(
    skill_name="smagskombinator", category="preference",
    content="Brug altid sæsonens grøntsager som udgangspunkt",
    reason="Test dry-run", session_id="test", user_id="mikke",
))
opt.store.add_suggestion(Suggestion(
    skill_name="smagskombinator", category="trigger",
    content="madkombination",
    reason="Test trigger", session_id="test", user_id="mikke",
))

print(f"\n{'='*60}")
print("  Dry-run: smagskombinator")
print(f"{'='*60}")
changes = opt.apply("smagskombinator", dry_run=True)
print(f"  Result: {changes}")

content = opt._read_skill(opt._skill_paths["smagskombinator"])
new_content, _ = opt._update_skill_content(
    content, "smagskombinator", opt.get_suggestions("smagskombinator")
)
print(f"\n--- Preview of updated SKILL.md ---\n{new_content}--- End preview ---")

# cleanup
opt.store._suggestions.clear()
opt.store.save()
print("\nDone. Test suggestions cleaned up.")
