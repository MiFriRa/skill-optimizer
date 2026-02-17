"""
verifier.py — Logic for verifying skill quality and structure.
"""
import re
import yaml
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any

from .rules import (
    REQUIRED_FIELDS,
    MAX_DESCRIPTION_LENGTH,
    MIN_DESCRIPTION_LENGTH,
    MIN_BODY_LENGTH,
    STYLE_WARNINGS,
    PATH_TRAVERSAL_PATTERN,
    SECRET_PATTERNS,
)

@dataclass
class VerificationIssue:
    code: str
    message: str
    line: Optional[int] = None
    severity: str = "warning"  # "error", "warning", "info"

@dataclass
class VerificationResult:
    skill_name: str
    valid: bool = True
    issues: List[VerificationIssue] = field(default_factory=list)

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "warning")

class SkillVerifier:
    def verify_file(self, file_path: Path) -> VerificationResult:
        """Run all checks on a SKILL.md file."""
        run_result = VerificationResult(skill_name=file_path.parent.name)
        
        if not file_path.exists():
            run_result.issues.append(VerificationIssue(
                code="FILE_MISSING",
                message=f"File not found: {file_path}",
                severity="error"
            ))
            run_result.valid = False
            return run_result

        content = file_path.read_text(encoding="utf-8")
        
        # 1. Structure Checks (Frontmatter)
        frontmatter, body, offset = self._parse_frontmatter(content, run_result)
        
        if frontmatter:
            self._check_metadata(frontmatter, run_result)
        
        # 2. Content Checks (Body)
        if body is not None:
             self._check_body(body, run_result, offset)

        # 3. Security Checks
        self._check_security(content, run_result)

        run_result.valid = run_result.error_count == 0
        return run_result

    def _parse_frontmatter(self, content: str, result: VerificationResult) -> tuple[Optional[Dict], Optional[str], int]:
        """Extract YAML frontmatter and body."""
        if not content.startswith("---"):
            result.issues.append(VerificationIssue(
                code="NO_FRONTMATTER",
                message="File must start with YAML frontmatter (---)",
                line=1,
                severity="error"
            ))
            return None, content, 0

        try:
            parts = content.split("---", 2)
            if len(parts) < 3:
                result.issues.append(VerificationIssue(
                    code="INVALID_FRONTMATTER",
                    message="Frontmatter not closed properly with ---",
                    line=1,
                    severity="error"
                ))
                return None, None, 0
            
            yaml_content = parts[1]
            body_content = parts[2]
            # Calculate line offset for body (number of lines in frontmatter + 2 fences)
            offset = yaml_content.count("\n") + 2
            
            try:
                data = yaml.safe_load(yaml_content)
                if not isinstance(data, dict):
                    result.issues.append(VerificationIssue(
                        code="INVALID_YAML",
                        message="Frontmatter must be a dictionary/map",
                        line=2,
                        severity="error"
                    ))
                    return None, body_content, offset
                return data, body_content, offset
            except yaml.YAMLError as e:
                result.issues.append(VerificationIssue(
                    code="YAML_SYNTAX",
                    message=f"YAML syntax error: {e}",
                    line=2,
                    severity="error"
                ))
                return None, body_content, offset

        except Exception as e:
            result.issues.append(VerificationIssue(
                code="PARSE_ERROR",
                message=f"Failed to parse file: {e}",
                severity="error"
            ))
            return None, None, 0

    def _check_metadata(self, data: Dict, result: VerificationResult):
        """Validate frontmatter fields."""
        for field in REQUIRED_FIELDS:
            if field not in data:
                result.issues.append(VerificationIssue(
                    code="MISSING_FIELD",
                    message=f"Missing required field: '{field}'",
                    line=2,
                    severity="error"
                ))
        
        if "description" in data:
            desc = data["description"]
            if len(desc) > MAX_DESCRIPTION_LENGTH:
                result.issues.append(VerificationIssue(
                    code="DESC_TOO_LONG",
                    message=f"Description length {len(desc)} > {MAX_DESCRIPTION_LENGTH}",
                    line=2, # Approximate
                    severity="warning"
                ))
            if len(desc) < MIN_DESCRIPTION_LENGTH:
                result.issues.append(VerificationIssue(
                    code="DESC_TOO_SHORT",
                    message=f"Description is too short (<{MIN_DESCRIPTION_LENGTH} chars)",
                    line=2,
                    severity="warning"
                ))
            
            # Check for trigger format issues (simple heuristics)
            if "when" in desc.lower() and len(desc) < 50:
                 result.issues.append(VerificationIssue(
                    code="DESC_VAGUE",
                    message="Description might be too vague. Use specific trigger keywords.",
                    line=2,
                    severity="info"
                ))

    def _check_body(self, body: str, result: VerificationResult, offset: int):
        """Validate the main content of the skill."""
        if len(body.strip()) < MIN_BODY_LENGTH:
             result.issues.append(VerificationIssue(
                code="BODY_TOO_SHORT",
                message="Skill body is suspiciously short. Add more instructions or examples.",
                line=offset + 1,
                severity="warning"
            ))

        # Check usage of headers
        if not re.search(r"^##\s+", body, re.MULTILINE):
             result.issues.append(VerificationIssue(
                code="NO_SECTIONS",
                message="No '## Section' headers found. Structure your skill with sections.",
                line=offset + 1,
                severity="warning"
            ))

        # Style / Anti-Slop Checks
        lines = body.split("\n")
        for i, line in enumerate(lines):
            for pattern, reason in STYLE_WARNINGS.items():
                if re.search(pattern, line):
                    result.issues.append(VerificationIssue(
                        code="STYLE_WARNING",
                        message=f"Style: {reason} (matched '{pattern}')",
                        line=offset + 1 + i,
                        severity="warning"
                    ))

    def _check_security(self, content: str, result: VerificationResult):
        """Scan for security issues."""
        if PATH_TRAVERSAL_PATTERN.search(content):
            result.issues.append(VerificationIssue(
                code="PATH_TRAVERSAL",
                message="Potential path traversal detected ('../').",
                severity="error"
            ))
        
        for pattern, msg in SECRET_PATTERNS.items():
            if re.search(pattern, content):
                result.issues.append(VerificationIssue(
                    code="POSSIBLE_SECRET",
                    message=msg,
                    severity="error"
                ))
