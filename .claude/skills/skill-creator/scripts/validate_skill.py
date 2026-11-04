#!/usr/bin/env python3
"""
Quick validation for a skill folder — catches basic problems early.

Harness-agnostic and standard-library only (no PyYAML): it parses just enough of
the SKILL.md frontmatter to check the required fields and naming rules. If you
can't run scripts, the equivalent manual check is: SKILL.md exists, opens with a
`---` frontmatter block, has `name` (hyphen-case, <=64 chars) and `description`
(<=1024 chars, no angle brackets).

Usage:
    validate_skill.py <skill_directory>
"""

import argparse
import re
import sys
from pathlib import Path

MAX_SKILL_NAME_LENGTH = 64
MAX_DESCRIPTION_LENGTH = 1024
ALLOWED_PROPERTIES = {"name", "description", "license", "allowed-tools", "metadata"}


def parse_frontmatter(content):
    """Return (ok, frontmatter_dict_or_error). Minimal top-level YAML: inline
    `key: value`, quoted values, and `|`/`>` block scalars. Good enough to validate."""
    if not content.startswith("---"):
        return False, "No YAML frontmatter found"
    match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not match:
        return False, "Invalid frontmatter format (missing closing '---')"

    lines = match.group(1).split("\n")
    fm = {}
    i = 0
    while i < len(lines):
        line = lines[i]
        i += 1
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        # Only top-level keys (no leading indentation).
        m = re.match(r"^([A-Za-z][\w-]*):(.*)$", line)
        if not m:
            continue
        key, rest = m.group(1), m.group(2).strip()
        if rest in ("|", ">", "|-", ">-", "|+", ">+"):
            # Block scalar: collect subsequent indented lines.
            block = []
            while i < len(lines) and (not lines[i].strip() or lines[i].startswith((" ", "\t"))):
                block.append(lines[i].strip())
                i += 1
            joiner = "\n" if rest.startswith("|") else " "
            fm[key] = joiner.join(b for b in block).strip()
        else:
            fm[key] = rest.strip().strip("'\"")
    return True, fm


def validate_skill(skill_path):
    skill_path = Path(skill_path)
    skill_md = skill_path / "SKILL.md"
    if not skill_md.exists():
        return False, "SKILL.md not found"

    ok, fm = parse_frontmatter(skill_md.read_text())
    if not ok:
        return False, fm  # error string

    unexpected = set(fm) - ALLOWED_PROPERTIES
    if unexpected:
        return (False, f"Unexpected key(s) in frontmatter: {', '.join(sorted(unexpected))}. "
                       f"Allowed: {', '.join(sorted(ALLOWED_PROPERTIES))}")

    if "name" not in fm:
        return False, "Missing 'name' in frontmatter"
    if "description" not in fm:
        return False, "Missing 'description' in frontmatter"

    name = fm["name"].strip()
    if name:
        if not re.match(r"^[a-z0-9-]+$", name):
            return False, f"Name '{name}' should be hyphen-case (lowercase letters, digits, hyphens)"
        if name.startswith("-") or name.endswith("-") or "--" in name:
            return False, f"Name '{name}' cannot start/end with a hyphen or contain '--'"
        if len(name) > MAX_SKILL_NAME_LENGTH:
            return False, f"Name is too long ({len(name)} chars). Maximum is {MAX_SKILL_NAME_LENGTH}."

    description = fm["description"].strip()
    if description:
        if "<" in description or ">" in description:
            return False, "Description cannot contain angle brackets (< or >)"
        if len(description) > MAX_DESCRIPTION_LENGTH:
            return False, (f"Description is too long ({len(description)} chars). "
                           f"Maximum is {MAX_DESCRIPTION_LENGTH}.")

    return True, "Skill is valid!"


def main():
    ap = argparse.ArgumentParser(
        description="Validate a skill folder's SKILL.md frontmatter (required fields + naming).")
    ap.add_argument("skill_directory", help="Path to the skill folder containing SKILL.md")
    args = ap.parse_args()
    valid, message = validate_skill(args.skill_directory)
    print(message, file=sys.stdout if valid else sys.stderr)
    sys.exit(0 if valid else 1)


if __name__ == "__main__":
    main()
