---
name: setup
description: Sets up a new project made from this template — fills CLAUDE.md, wires make test and make check to the project's real tools, trims what the project doesn't need, proves both targets green, commits. Run once, right after creating the repository.
---

# setup

Turns this template into the user's project in one sitting. Interactive: the user answers, you write. Questions are asked **in plain text, one at a time** — `AskUserQuestion` is denied in `.claude/settings.json` (unattended runs must never block on it), so don't try it.

Explore before asking: a question the repository can answer (the language, the test runner, an existing CI file) is answered from it, and only confirmed with the user.

## 1. Read the current state

- `CLAUDE.md`: which sections still hold a `<placeholder>`.
- `Makefile`: `test` and `check` as the template ships them.
- The tree: languages, package manifests (`package.json`, `pyproject.toml`, `go.mod`, `Cargo.toml`, …), an existing test runner, linters, a CI workflow under `.github/workflows/`.
- `git log`, the current branch and the remote.

Report in a few lines what you found and what you'll ask about.

## 2. Ask, one question at a time

Skip any question the tree already answers; confirm the answer instead.

1. **The project**: what it is, in one or two sentences, and where a new reader should start.
2. **The fast loop**: the command that runs the unit tests in seconds, on the host, without network. None yet → propose the language's standard runner.
3. **The net**: the slower checks that must be green before a push — lint, type check, formatter check, integration or end-to-end tests, build. For each: its command and what it needs to run (a service, a container, credentials, a tool to install).
4. **Ground rules**: project-specific rules every change must respect, and the goal each one serves (`warn-review` flags violations, `guideline` decides by them). None is a valid answer.
5. **Language**: everything in the repository in English, the conversation in the user's language? Keep, or change.
6. **The plan pipeline** (`grill-me` → `plan-write` → `plan-converge` → `plan-pilot`, and its unattended helpers): keep it all, or only the interactive skills (`grill-me`, `fix-bug`, `git-commit`, `tdd`)?

## 3. Write

- **`CLAUDE.md`**: replace every placeholder with the answers, and drop the "Template not set up yet" line. § Checks names the real commands and what the net needs; § Ground rules lists the rules with their goals, or is deleted; § Language follows answer 5. Keep the sections the skills cite: § Checks, § Ground rules (if kept), § Language, § What we don't do, § Plans (if the pipeline is kept).
- **`Makefile`**: `test` runs the project's fast loop **and** `python3 -m unittest discover tests` (it covers `scripts/progress_*`, which `plan-pilot` relies on; drop it only with the pipeline). `check` depends on `test` and runs each slow check, one target per check so `make -k check` reports them all. Keep `help` in sync.
- **The pipeline dropped** (answer 6) → `git rm` `plan-write`, `plan-converge`, `plan-review`, `plan-pilot`, `prd-autopilot`, `to-prd`, `check-net`, `warn-review`, `guideline`, `plan-progress`, `scripts/progress_*`, `tests/test_progress_tidy.py`, and § Plans of `CLAUDE.md`. Then fix what still names them: `fix-bug` (its unattended mode), `git-commit` (§ `progress.md` and the unattended callers), `tdd`'s description. `fix-bug` then asks the user its sub-agents' questions directly instead of spawning `guideline`.
- **`.gitignore`**: add the language's build output and dependency directories.
- **`README.md`**: replace the template's text with the project's name and description; keep § Working with Claude.
- **CI** (only if the user wants it): a workflow that runs `make check` on pushes and pull requests.

## 4. Prove it

Run `make test`, then `make check`. Both must pass. A red target is reported to the user with its output: fix the setup with them (a missing tool, a wrong command), never by weakening a check. A target that cannot run in this session (a missing service) is said plainly, and how to run it is written in `CLAUDE.md` § Checks.

## 5. Commit

Run `git-commit` in place; the user holds the gate. One commit, `chore: set up <project name> from the template`.

Branch: never work on or push a `claude/*` branch (`CLAUDE.md` § What we don't do). If on one, create a branch named after the setup (`chore/setup`) and push that instead, only with the user's go-ahead.

## 6. Next

Print what to run next, in a new session:

```
/grill-me <what you want to build first>
```

then `/plan-write` at the end of the grilling, `/plan-converge docs/plan-1.md`, and `/plan-pilot docs/plan-1.md` — or, for a single bug, `/fix-bug <symptom>`.
