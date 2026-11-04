#!/usr/bin/env python3
"""
Find existing skills similar to one you're about to create.

Run this BEFORE scaffolding a new skill. If a close match already exists, prefer
updating that skill in place over creating a near-duplicate — duplicates dilute
triggering (the agent can't tell which to invoke) and fragment maintenance.

Harness-agnostic, standard-library only. It scans the immediate subdirectories of
--skills-dir for SKILL.md files, reads each skill's name + description, and ranks
them by similarity to your query (name match + keyword overlap). The scores are a
heuristic to surface candidates — you make the final call on whether a match is
"the same capability".

If you can't run scripts, do the equivalent by hand: list the skills directory and
skim each SKILL.md's name/description for an existing skill that covers your intent.

Usage:
    discover_skills.py "<proposed name or one-line intent>" --skills-dir <dir>
    discover_skills.py "rotate and merge pdf files" --skills-dir ./skills --threshold 0.4 --json
"""

import argparse
import difflib
import json
import re
import sys
from pathlib import Path

_STOPWORDS = {
    "a", "an", "the", "and", "or", "of", "to", "for", "in", "on", "with", "this",
    "that", "it", "is", "are", "be", "use", "used", "using", "when", "skill", "new",
}


def parse_frontmatter(content):
    """Minimal top-level frontmatter parse -> dict (name/description only needed)."""
    if not content.startswith("---"):
        return {}
    m = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not m:
        return {}
    fm, lines, i = {}, m.group(1).split("\n"), 0
    while i < len(lines):
        line = lines[i]
        i += 1
        km = re.match(r"^([A-Za-z][\w-]*):(.*)$", line)
        if not km:
            continue
        key, rest = km.group(1), km.group(2).strip()
        if rest in ("|", ">", "|-", ">-", "|+", ">+"):
            block = []
            while i < len(lines) and (not lines[i].strip() or lines[i].startswith((" ", "\t"))):
                block.append(lines[i].strip())
                i += 1
            fm[key] = (" ".join(block)).strip()
        else:
            fm[key] = rest.strip("'\"")
    return fm


def tokens(text):
    return {t for t in re.split(r"[^a-z0-9]+", text.lower()) if len(t) > 2 and t not in _STOPWORDS}


def overlap(a, b):
    """Overlap coefficient: share of the SMALLER token set that's common. Asymmetric on purpose —
    a short query whose keywords mostly appear in a skill should score high regardless of how much
    extra that skill's description covers. Favors recall, which is what discovery wants."""
    if not a or not b:
        return 0.0
    return len(a & b) / min(len(a), len(b))


def score_skill(query, name, description):
    q = query.lower().strip()
    name_sim = difflib.SequenceMatcher(None, q, name.lower()).ratio()
    kw = overlap(tokens(query), tokens(f"{name} {description}"))
    return round(max(name_sim, kw), 3)


def find_similar(query, skills_dir):
    skills_dir = Path(skills_dir)
    results = []
    if not skills_dir.is_dir():
        return results
    for d in sorted(p for p in skills_dir.iterdir() if p.is_dir()):
        md = d / "SKILL.md"
        if not md.exists():
            continue
        fm = parse_frontmatter(md.read_text())
        name = fm.get("name") or d.name
        description = fm.get("description") or ""
        results.append({
            "name": name,
            "path": str(d),
            "description": description,
            "score": score_skill(query, name, description),
        })
    results.sort(key=lambda r: r["score"], reverse=True)
    return results


def main():
    ap = argparse.ArgumentParser(description="Find existing skills similar to a proposed one.")
    ap.add_argument("query", help="Proposed skill name or a one-line description of its intent")
    ap.add_argument("--skills-dir", default=".", help="Directory whose subfolders are skills")
    ap.add_argument("--threshold", type=float, default=0.4, help="Min score to report (0-1)")
    ap.add_argument("--json", action="store_true", help="Emit JSON instead of text")
    args = ap.parse_args()

    matches = [r for r in find_similar(args.query, args.skills_dir) if r["score"] >= args.threshold]

    if args.json:
        print(json.dumps(matches, indent=2))
        return

    if not matches:
        print(f"No existing skill scored >= {args.threshold} in {args.skills_dir}.")
        print("=> No close match: proceed to create a new skill.")
        return

    print(f"Possible matches in {args.skills_dir} (score >= {args.threshold}):\n")
    for r in matches:
        desc = r["description"]
        if len(desc) > 140:
            desc = desc[:137] + "..."
        print(f"  [{r['score']:.2f}] {r['name']}  ({r['path']})")
        if desc:
            print(f"         {desc}")
    print("\n=> If one of these is the SAME capability, UPDATE it in place instead of "
          "creating a near-duplicate. Otherwise, create a new skill.")


if __name__ == "__main__":
    main()
