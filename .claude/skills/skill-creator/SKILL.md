---
name: skill-creator
description: Guidance for creating, updating, and optimizing Agent Skills — modular skill folders (a SKILL.md plus optional scripts/references/assets) that give an agent procedural knowledge for a specific task or domain. Use this whenever someone wants to build a new skill, turn a repeated workflow into a reusable skill, improve or refactor an existing skill, fix a skill that isn't triggering reliably, or write and critique a SKILL.md and its description — even if they don't say the word "skill" explicitly. Prefer updating a closely related existing skill over creating a near-duplicate.
---

# Skill Creator

Guidance for creating effective skills, and for improving them by reflecting on what you wrote.

This skill is deliberately **harness-agnostic**: it relies on no specific runtime, CLI, or
vendor tooling. The optional helper scripts in `scripts/` use only the Python standard library,
and every step has a plain "do it by hand" fallback, so any agent in any harness can follow it.

## About skills

A skill is a modular, self-contained folder that extends an agent's capabilities with
specialized knowledge, workflows, or tools — an "onboarding guide" for a task or domain that
turns a general-purpose agent into one equipped with procedural knowledge no model fully holds.

A skill typically provides one or more of: a multi-step workflow, instructions for a specific
file format or API, domain knowledge (schemas, policies, conventions), or bundled resources
(scripts, references, assets) that save the agent from reinventing them each time.

## Core principles

### Concise is key

The context window is a shared resource: a skill competes for it with the system prompt, the
conversation, other skills' metadata, and the actual request. **Assume the agent is already
capable** — add only what it doesn't already know. Challenge every line: *does the agent really
need this, and does it justify its token cost?* Prefer a short concrete example over a paragraph
of explanation.

### Set appropriate degrees of freedom

Match how prescriptive you are to how fragile the task is. Think of the agent walking a path:

- **High freedom (prose guidance)** — when many approaches work and the right choice depends on
  context. Describe the goal and the heuristics, not exact steps.
- **Medium freedom (pseudocode / parameterized scripts)** — when a preferred pattern exists but
  some variation is fine.
- **Low freedom (specific scripts, few parameters)** — when the operation is fragile, error-prone,
  or must be done one exact way. Give guardrails.

A narrow bridge with cliffs needs rails; an open field doesn't. The clearest low-freedom case is
**fragile numeric work** — formulas, unit conversions, aggregations — which should live in a
bundled `scripts/` file rather than trusting the model's in-head arithmetic.

### Writing style

Explain the **why**, not just the **what**. Today's models have good theory of mind: when they
understand *why* a step matters, they handle the cases your instructions didn't enumerate. If you
catch yourself writing `ALWAYS` / `NEVER` in caps or building rigid scaffolding, treat it as a
yellow flag — usually you can reframe it as a short explanation of the underlying reason, which is
more robust and more humane to the reader.

Write for reuse, not for one example. A skill that only works on the cases you tested is nearly
useless; aim for a general procedure. Draft it, then re-read it with fresh eyes and improve.

Phrase instructions in the imperative/infinitive, addressed to the agent that will run the skill
("Extract the table…", "To rotate a page, …") — not as narration about a user.

### Communicating with the user

Skill authors range from non-technical to expert. Read context cues and calibrate: terms like
"workflow" or "example" are safe; terms like "frontmatter", "schema", or "assertion" may need a
one-line gloss unless the user has signaled familiarity. When in doubt, briefly define a term.

## Anatomy of a skill

```
skill-name/
├── SKILL.md            (required)
│   ├── YAML frontmatter   (name, description — required)
│   └── Markdown body      (instructions)
└── (optional)
    ├── scripts/        executable code for deterministic/repeated work
    ├── references/     docs loaded into context as needed (schemas, API docs, domain notes)
    └── assets/         files used in the produced output (templates, images, fonts, boilerplate)
```

**Progressive disclosure** — skills load in three levels, so design for the cheapest one that works:

1. **Metadata** (`name` + `description`) — always in context. This is the trigger.
2. **SKILL.md body** — loaded only once the skill triggers. Keep it lean (aim under ~500 lines).
3. **Bundled resources** — loaded or executed only when a step needs them (effectively unlimited;
   scripts can run without being read into context).

Keep the core workflow and selection guidance in SKILL.md; push variant-specific detail into
`references/`, and link to those files with a clear note on *when* to read each. Keep references
one level deep (link them directly from SKILL.md), and give any file over ~100 lines a short
table of contents at the top. When a skill spans several domains or variants, organize references
by variant (e.g. `references/aws.md`, `references/gcp.md`) so the agent reads only the relevant one.
Give each fact exactly one home — don't repeat content in both SKILL.md and a reference file, or
the two copies drift apart (prefer the reference for anything detailed).

## The workflow

Follow these in order, skipping a step only when there's a clear reason it doesn't apply.

### 1. Understand the skill with concrete examples

Get a clear picture of how the skill will actually be used before writing anything. Gather (or
propose, then confirm) concrete example requests: *"What should this enable? Can you give a few
examples of what a user would say to trigger it? What's the expected output?"* Ask the most
important questions first rather than overwhelming the user. Conclude once the intended
functionality is clear.

### 2. Discover existing skills — update over create

Before scaffolding anything new, check whether a similar skill already exists. A near-duplicate is
harmful: when two skills cover the same ground, the agent can't tell which to invoke (triggering
gets diluted), and the same knowledge drifts out of sync across both.

Run the discovery helper against the directory where skills live:

```bash
python scripts/discover_skills.py "<proposed name or one-line intent>" --skills-dir <skills-dir>
```

(Fallback without scripts: list the skills directory and skim each `SKILL.md`'s name and
description.)

- If a listed skill is **the same capability**, **update it in place** — keep its `name` and
  folder, extend its SKILL.md / resources to cover the new need, and **add the new need's trigger
  phrases to the description** (broaden it, never narrow): a consolidated skill must still trigger
  on everything its merged parts would have, or the consolidation silently loses coverage. Then
  continue to step 5.
- If matches are merely adjacent (related but a genuinely different capability), proceed to create
  a new one.

Use judgment: the score is only a hint. "Same capability, broader scope" → update. "Shares
keywords but a different job" → new skill.

### 3. Plan reusable contents

For each concrete example, ask: how would the agent do this from scratch, and what would help if it
had to do it repeatedly? **Bundle resources generously — a skill that adds only prose often fails to
beat the baseline.** This surfaces:

- **`scripts/` — executable code for anything fragile, multi-step, or done one exact way. The
  highest-value resource, and the most under-used.** In particular, **work that has to be exact
  belongs in a script, not in prose** — a calculation or formula, a unit/format/date conversion, a
  multi-step parse or aggregation: anything where a model doing it in its head drifts or silently
  picks the wrong convention. A script does it the same way every time. Write it to take the inputs
  and return the result (e.g. `scripts/compute.py --inputs ...`), and **test it on a worked example
  with a known answer before shipping.**
- **`references/` — the exact specs the agent (and any script) must agree on**: the precise
  definition or convention a task hinges on (which formula variant, rounding rule, boundary, or
  edge-case handling), schemas, domain rules. Keep the authoritative version here, not paraphrased
  in prose.
- **`assets/`** — templates, boilerplate, images, fonts used verbatim in the output.

**Handle conventions explicitly.** Many exact operations have more than one accepted convention — a
formula variant, a rounding or tie-breaking rule, a sort order, a date/boundary convention — and a
request often names the one it wants. Don't hardcode a single convention: make it a **parameter** the
script accepts (covering the common variants), **catalog the variants in `references/`** with how to
recognize which one a request is asking for, and have the **SKILL.md detect the requested convention
and pass it to the script**. Silently assuming one convention is a leading cause of close-but-wrong
answers — the script runs fine, but computes the wrong variant.

If a skill performs an exact operation (a calculation, a transform, a formatted output) and ships no
script for it, treat it as a yellow flag — the agent will re-derive it, and can mis-derive it, every run.

### 4. Scaffold (new skills only)

Create the folder and a SKILL.md skeleton:

```bash
python scripts/scaffold_skill.py <skill-name> --path <dir> [--resources scripts,references,assets]
```

(Fallback without scripts: create the folder and a SKILL.md with `name` + `description`
frontmatter directly — that's all the scaffolder does.)

### 5. Write the SKILL.md and resources

Build the resources first (and test any scripts by actually running them — a representative
sample is enough when there are many similar ones), then write the body that ties them together.
Remember you're writing for another agent instance: include the non-obvious procedural knowledge,
and skip what a capable agent already knows.

**Frontmatter** (`name`, `description`):

- `name` — hyphen-case, lowercase letters/digits/hyphens, ≤64 chars; name the folder to match.
  Prefer a short, verb-led phrase that names the action (e.g. `rotate-pdf`, `summarize-thread`),
  and namespace by tool when it sharpens triggering (e.g. `gh-address-comments`).
- `description` — the **primary trigger**, and the *only* thing the model sees when deciding whether
  to invoke the skill. It is matched against the user's words, not read for understanding, so it must
  contain the **literal phrases a matching request would use**. Put every "when to use" cue here (the
  body loads only after triggering). Models tend to *under*-trigger, so be pushy and concrete:
    - **Enumerate the literal trigger phrases — don't characterize abstractly.** List (ideally
      quoted) the exact terms, operations, file types, and identifiers a matching task would contain.
      For a PDF skill, write *"Use when a request says 'merge PDFs', 'split a PDF', 'rotate pages',
      or 'extract text from a PDF'"* — NOT *"use for PDF manipulation tasks"*. Both are accurate, but
      only the first matches the words a user actually types; abstract framing badly under-triggers
      and is the most common reason a skill silently never fires.
    - **Cover every capability the skill has.** If it does N things (especially after consolidating
      several into one skill), name trigger phrases for all N — a description that mentions only the
      first capability triggers only for the first.
    - **Add a short negative boundary** to stay precise — a *"Do NOT use for ..."* naming adjacent
      cases that should not fire (e.g. simple lookups).
  Descriptions are the one place to set aside "be concise / explain the why": completeness of
  concrete trigger cues beats elegance.

**Body** — instructions for using the skill, written per the Core principles above.

### 6. Validate

```bash
python scripts/validate_skill.py <path/to/skill-folder>
```

It checks the frontmatter format, required fields, and naming rules. (Fallback without scripts:
confirm by hand that SKILL.md opens with a `---` block, and that `name` is hyphen-case ≤64 chars
and `description` is ≤1024 chars with no angle brackets.) Fix anything it reports.

### 7. Self-reflect and optimize

This is the step that turns a first draft into a good skill, and it replaces any external
"optimization loop": do it **inline, yourself** — no subagents, no separate processes, nothing a
harness might skip. After drafting, re-read your own skill with fresh eyes and the deliberate
mindset of a skeptical reviewer who has never seen it, then revise. Work through these lenses, and
explain to yourself *why* each change helps rather than rubber-stamping:

1. **Triggering (fresh eyes) — usually the highest-leverage fix.** Reading *only* the `description`,
   write down 3 realistic requests that *should* invoke this skill and 2 near-misses that should
   *not*. Then check two things: (a) does the description contain the **literal words** those
   should-trigger requests use, not just an abstract description of them? If a request says
   "rotate the PDF 90 degrees" but the description only says "document tasks", it will miss — add the
   exact phrase. (b) Does it name trigger cues for **every** capability in the body?
   Walk the body's sections and confirm each has a matching cue in the description. Rewrite any
   abstract framing into concrete, quoted enumerations, and add/tighten a "Do NOT use for ..." line
   if a near-miss would fire. Re-check.
2. **Self-containment.** Read the body as a fresh agent with no prior context. Is every
   instruction actionable? Any unexplained assumption, dangling reference to a file that isn't
   there, or step where you'd stall? Fix it.
3. **Concision and altitude.** Cut anything a capable agent already knows or that doesn't earn its
   tokens. Replace any all-caps MUST/NEVER with a short explanation of the underlying reason.
   Delete rules that only make sense for the one example you had in mind.
4. **Progressive disclosure.** Is SKILL.md carrying detail that belongs in a `references/` file?
   Move it, and leave a clear pointer about when to read it. Is the body over ~500 lines?
5. **Degrees of freedom.** Does the specificity match each task's fragility — guardrails where the
   operation is fragile, room to maneuver where many paths are valid?
6. **Dry run — and for anything numeric, actually compute it.** Mentally execute the skill
   end-to-end on one realistic request; note wherever it stalls, loops, or produces the wrong shape
   of output. If the skill computes a number, don't eyeball the prose math — **run its bundled
   script (or the formula) on a worked example with known inputs and confirm the result is exactly
   right.** Prose math that "looks correct" is the most common silent failure; a skill that
   describes a multi-step calculation without a script is the signal to write one and verify it here.

Apply the revisions. If the pass turned up substantial issues, do it once more.

### 8. Iterate on real usage

Use the skill on real tasks and watch where it struggles or wastes effort. If several runs all
independently write the same helper script or take the same multi-step detour, that's a strong
signal to bundle that script (or fold that guidance) into the skill so future runs don't reinvent
it. Update SKILL.md or its resources and repeat.

## What not to include

A skill should contain only what an agent needs to do the job. Don't add auxiliary docs about the
skill's own creation — no `README.md`, `INSTALLATION.md`, `CHANGELOG.md`, or notes on your process
and testing. They add clutter and confusion without helping the agent execute.

## Principle of no surprise

Skills must not contain malware, exploit code, or anything that could compromise security, and a
skill's behavior should not surprise the user given its description. Don't build skills designed to
mislead or to enable unauthorized access or data exfiltration. (Benign role-play or persona skills
are fine.)
