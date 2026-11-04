#!/usr/bin/env python3
"""
Skill initializer — scaffold a new skill folder from a template.

Harness-agnostic: depends only on the Python standard library, writes no
vendor-specific metadata. The output is a plain skill folder (SKILL.md +
optional resource dirs) that any agent harness can read.

Usage:
    scaffold_skill.py <skill-name> --path <dir> [--resources scripts,references,assets] [--examples]

Examples:
    scaffold_skill.py pdf-rotator --path ./skills
    scaffold_skill.py pdf-rotator --path ./skills --resources scripts,references
    scaffold_skill.py pdf-rotator --path ./skills --resources scripts --examples

If running scripts is not available in your harness, create the same files by
hand — this script is only a convenience, not a requirement.
"""

import argparse
import re
import sys
from pathlib import Path

MAX_SKILL_NAME_LENGTH = 64
ALLOWED_RESOURCES = {"scripts", "references", "assets"}

SKILL_TEMPLATE = """\
---
name: {skill_name}
description: [TODO: What the skill does AND when to use it. This is the primary trigger — \
include the concrete scenarios, file types, and task phrasings that should invoke it. Put all \
"when to use" information here, never only in the body (the body loads only after triggering).]
---

# {skill_title}

## Overview

[TODO: 1-2 sentences on what this skill enables an agent to do.]

## [TODO: first main section]

[TODO: Pick the shape that fits — a step-by-step workflow, a set of tasks/operations, a
reference/spec, or a list of capabilities — and write the core guidance here. Prefer concise
examples over long prose. Explain *why* a step matters rather than ordering it with all-caps MUSTs.
Point to any bundled scripts/references/assets and say when to read or run them.]

## Resources (optional — keep only what this skill actually needs)

- `scripts/`    — executable code for deterministic or repeated operations (runnable without
                  loading into context).
- `references/` — documentation loaded into context as needed (schemas, API docs, domain notes).
- `assets/`     — files used in the produced output (templates, images, fonts, boilerplate).

Delete this section and any unused directories before finishing.
"""

EXAMPLE_SCRIPT = '''\
#!/usr/bin/env python3
"""Example helper for {skill_name}. Replace with real logic or delete."""


def main():
    print("example script for {skill_name}")


if __name__ == "__main__":
    main()
'''

EXAMPLE_REFERENCE = """\
# Reference notes for {skill_title}

Placeholder for documentation the agent should consult while working
(schemas, API details, domain knowledge). Replace or delete.
"""

EXAMPLE_ASSET = """\
Placeholder asset. Assets are files used inside the output the agent produces
(templates, images, fonts, boilerplate) — not loaded into context. Replace or delete.
"""


def normalize_skill_name(skill_name):
    """Normalize a skill name to lowercase hyphen-case."""
    normalized = skill_name.strip().lower()
    normalized = re.sub(r"[^a-z0-9]+", "-", normalized)
    normalized = normalized.strip("-")
    normalized = re.sub(r"-{2,}", "-", normalized)
    return normalized


def title_case_skill_name(skill_name):
    """Convert a hyphenated skill name to Title Case for display."""
    return " ".join(word.capitalize() for word in skill_name.split("-"))


def parse_resources(raw_resources):
    if not raw_resources:
        return []
    resources = [item.strip() for item in raw_resources.split(",") if item.strip()]
    invalid = sorted({item for item in resources if item not in ALLOWED_RESOURCES})
    if invalid:
        allowed = ", ".join(sorted(ALLOWED_RESOURCES))
        print(f"error: unknown resource type(s): {', '.join(invalid)}", file=sys.stderr)
        print(f"       allowed: {allowed}", file=sys.stderr)
        sys.exit(1)
    deduped = []
    seen = set()
    for resource in resources:
        if resource not in seen:
            deduped.append(resource)
            seen.add(resource)
    return deduped


def create_resource_dirs(skill_dir, skill_name, skill_title, resources, include_examples):
    for resource in resources:
        resource_dir = skill_dir / resource
        resource_dir.mkdir(exist_ok=True)
        if resource == "scripts" and include_examples:
            example = resource_dir / "example.py"
            example.write_text(EXAMPLE_SCRIPT.format(skill_name=skill_name))
            example.chmod(0o755)
            print("  created scripts/example.py")
        elif resource == "references" and include_examples:
            (resource_dir / "reference.md").write_text(
                EXAMPLE_REFERENCE.format(skill_title=skill_title))
            print("  created references/reference.md")
        elif resource == "assets" and include_examples:
            (resource_dir / "example_asset.txt").write_text(EXAMPLE_ASSET)
            print("  created assets/example_asset.txt")
        else:
            print(f"  created {resource}/")


def init_skill(skill_name, path, resources, include_examples):
    """Create a new skill directory with a template SKILL.md. Returns the path or None."""
    skill_dir = Path(path).resolve() / skill_name

    if skill_dir.exists():
        print(f"error: skill directory already exists: {skill_dir}", file=sys.stderr)
        print("       to UPDATE an existing skill, edit it in place instead of re-initializing.",
              file=sys.stderr)
        return None

    try:
        skill_dir.mkdir(parents=True, exist_ok=False)
        print(f"  created {skill_dir}/")
    except Exception as e:
        print(f"error: could not create directory: {e}", file=sys.stderr)
        return None

    skill_title = title_case_skill_name(skill_name)
    skill_content = SKILL_TEMPLATE.format(skill_name=skill_name, skill_title=skill_title)
    try:
        (skill_dir / "SKILL.md").write_text(skill_content)
        print("  created SKILL.md")
    except Exception as e:
        print(f"error: could not create SKILL.md: {e}", file=sys.stderr)
        return None

    if resources:
        try:
            create_resource_dirs(skill_dir, skill_name, skill_title, resources, include_examples)
        except Exception as e:
            print(f"error: could not create resource directories: {e}", file=sys.stderr)
            return None

    print(f"\nskill '{skill_name}' initialized at {skill_dir}")
    print("next: fill in the SKILL.md TODOs (especially the description), add any resources,")
    print("      then run validate_skill.py on the folder.")
    return skill_dir


def main():
    parser = argparse.ArgumentParser(
        description="Create a new skill directory with a SKILL.md template.")
    parser.add_argument("skill_name", help="Skill name (normalized to hyphen-case)")
    parser.add_argument("--path", required=True, help="Output directory for the skill")
    parser.add_argument("--resources", default="",
                        help="Comma-separated subset of: scripts,references,assets")
    parser.add_argument("--examples", action="store_true",
                        help="Create placeholder example files in the selected resource dirs")
    args = parser.parse_args()

    raw_skill_name = args.skill_name
    skill_name = normalize_skill_name(raw_skill_name)
    if not skill_name:
        print("error: skill name must include at least one letter or digit.", file=sys.stderr)
        sys.exit(1)
    if len(skill_name) > MAX_SKILL_NAME_LENGTH:
        print(f"error: skill name '{skill_name}' is too long ({len(skill_name)} chars). "
              f"Maximum is {MAX_SKILL_NAME_LENGTH}.", file=sys.stderr)
        sys.exit(1)
    if skill_name != raw_skill_name:
        print(f"note: normalized skill name from '{raw_skill_name}' to '{skill_name}'.")

    resources = parse_resources(args.resources)
    if args.examples and not resources:
        print("error: --examples requires --resources to be set.", file=sys.stderr)
        sys.exit(1)

    print(f"initializing skill: {skill_name}")
    print(f"   location:  {args.path}")
    print(f"   resources: {', '.join(resources) if resources else 'none (create as needed)'}")
    print()

    result = init_skill(skill_name, args.path, resources, args.examples)
    sys.exit(0 if result else 1)


if __name__ == "__main__":
    main()
