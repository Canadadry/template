# Template

A project template for working with Claude Code: a set of skills that take a
change from a conversation to a pushed, verified branch — planning, PRDs,
test-driven implementation, bug fixing with proven causes, and commits.

## Quickstart

1. Create a repository from this template and clone it.
2. Open Claude Code at its root and run:

   ```
   /setup
   ```

   It asks a few questions, one at a time, then fills `CLAUDE.md`, wires
   `make test` and `make check` to your project's tools, trims what you don't
   need, proves both targets green and commits.
3. Start your first piece of work, in a new session:

   ```
   /grill-me <what you want to build>
   ```

## Conventions the skills rely on

| What | Where |
|------|-------|
| `make test` — the fast loop: unit tests, on the host, in seconds | `Makefile`, `CLAUDE.md` § Checks |
| `make check` — the net: everything that must be green before a push | `Makefile`, `CLAUDE.md` § Checks |
| Project rules every change must respect | `CLAUDE.md` § Ground rules |
| Plans, PRDs | `docs/plan-<N>.md`, `docs/prd/triage/` |
| A running plan's checklist | `progress.md`, guarded by `scripts/progress_check.sh` |
| Throwaway files | `tmp/` (git-ignored) |

`.claude/settings.json` denies merging pull requests (merging is the
owner's job) and `AskUserQuestion` (unattended runs must never block on a
question: a `guideline` agent answers instead).

## Working with Claude

### Skills you run

| Skill | Use it to |
|-------|-----------|
| `/setup` | Configure a new project made from this template (once) |
| `/grill-me` | Get interviewed about a plan or design until every decision is made |
| `/plan-write` | Turn that conversation into `docs/plan-<N>.md` |
| `/plan-converge <plan>` | Sharpen the plan with review rounds until they come back empty |
| `/plan-pilot <plan>` | Implement the whole plan unattended, step by step, then open the PR |
| `/fix-bug <symptom>` | Fix one bug: proven cause, failing test, minimal fix, independent check |

Run `plan-converge` and `plan-pilot` each in a **new session**: the plan file
is all they know, so everything decided while grilling must be in it.

### Skills the others call

`to-prd` (one PRD per plan step), `prd-autopilot` (implements the PRD queue),
`tdd` (red-green-refactor), `check-net` (runs `make check`, drives failures
back to green), `help-me-debug` (proves a bug's cause), `git-commit`,
`plan-review`, `warn-review` (design smells at each phase end), `guideline`
(the stand-in human during unattended runs).

### The plan-progress plugin

`.claude/skills/plan-progress` shows `progress.md` in a pane and the status
line, adds a `/progress` command, and installs the git hook that refuses a
commit ticking nothing in `progress.md` while a plan runs.
