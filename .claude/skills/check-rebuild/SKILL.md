---
name: check-rebuild
description: Internal — called by prd-autopilot after each PRD, and by plan-pilot after a "skill:" step. Runs make rebuild and make mainui-check and drives every failure back to green through fix-bug, one at a time.
---

# check-rebuild

`make test` is the dev loop: unit tests of the tooling, on the host, seconds. The net is two commands, in the container, run once, at the end — here (`CLAUDE.md` § Matching decompilation):

- `make rebuild` proves `keymon` byte-identical: rebuilt and its sha256 compared to the original's (`src/keymon/layout.json`).
- `make mainui-check` proves `MainUI` per function, relocated fields included, and per data row, in both of Onion's variants: the plain build against `REF` (Onion's `MainUI-285-clean`, `firmware/onion-v4.5-dev/`, since plan 3 step 2.6), then the `MAINUI_EXPERT=1` build against `EXPERT_REF` (Onion's `MainUI-285-expert`, since plan 3 step 4.1), each summary under a `>> mainui-check: <variant> against <reference>` banner, expert run even when clean fails, with the committed allow-list (`src/mainui/check-allow.tsv`) and pending list (`src/mainui/check-pending.tsv`: items still to port, empty since plan 3 step 3.3; a pending item that now matches fails until its row goes). Exit 0 all pass, 1 a failing item, 2 a tool error; the target's exit is the worse of the two variants'. fncmp's masked MATCH is a working aid, not the gate: a MainUI function is proven only by `make mainui-check`.

Both must be green. A non-identical keymon or a failing `make mainui-check` item is always a bug. Never edit an expected sha256, never drop a C file back to assembly to get green without saying so, never weaken a check. Never add, edit or remove a row of `check-allow.tsv` or `check-pending.tsv`, never change the check's references (`REF`, `EXPERT_REF`) or their defaults, never weaken a verdict of the check, to get green: those lists change only in the step that makes the deliberate change, with its reason — never here, nor in the `fix-bug` driven from here.

Every rebuild bug in the tooling leaves behind a unit test that catches it in `make test`, when the bug is in the tooling (`scripts/`). A bug in a C file (a function that no longer matches) is caught by the net itself; no unit test is needed for it.

## Before the loop: the environment

`make rebuild` needs the Docker daemon, the `miyoo-re` image and the extracted firmware (`work/`); `make mainui-check` also needs the extracted Mini+ 0628 tree (the sources' base) and its two reference binaries, Onion's `MainUI-285-clean` and `MainUI-285-expert` (`make fetch-onion`, `firmware/onion-v4.5-dev/`). If one is missing, set it up (`notes/next-session.md`, `CLAUDE.md` § Cloud sessions) before anything else. A missing environment is not a failure: never send it to `fix-bug`. `make mainui-check` exit 2 naming a missing input is this case; any other exit 2 is a tooling bug, one failure handed to `fix-bug` like the others.

## Rule #1 — never wait on the human

No one answers during this loop. A `QUESTION:` from any sub-agent goes to a fresh `guideline` agent, never to the user. The only way back to the human is the stop after 3 failed attempts (step 5).

## Rule #2 — you are the human at fix-bug's commit gate

`fix-bug` stops once, at its `git-commit` proposal, for a human go-ahead. Here, you give or refuse it, after running the checks of step 4 yourself. Never accept on the strength of an agent's report.

## Loop

### 1. Run the net
Run `make rebuild`, then `make mainui-check` (both variants, even when the first is red, so that every failure is known). keymon byte-identical and `make mainui-check` exit 0 → report `REBUILD-GREEN:` with the list of `fix:` commits made during this run, and stop.

### 2. Split the red into failures
One failure = one binary `make rebuild` reports `DIFFERENT`, or one (variant, item) pair: an item `make mainui-check` names failing under the `clean` or the `expert` banner (a function, an unpaired function, a data row; a retargeted or unmapped relocated field is its function's failure), or that variant's tool error. The same item failing in both variants is two failures, each with its own symptom. Keep the full output: for a binary, the first differing offsets (`cmp -l build/<binary>/<binary> <original> | head`); for a check item, its variant's banner, summary and that item's lines.

Order: keymon's rebuild failure first (the cheapest to diagnose: fewest differing bytes); then clean's tool error, failing functions and data rows, then expert's in the same order (a shared cause is fixed on the clean side first); within a variant, functions before data rows (a data row often follows from code), lowest reference address first. Handle it alone; the others wait for the next run of the net, since a fix often repairs more than one.

### 3. Invoke fix-bug on it
Invoke the `fix-bug` skill in place. Its argument is a bug report you write, containing:

- **Symptom**, verbatim: the `make rebuild` output for this failure and the first `cmp -l` lines, or the variant's `>> mainui-check:` banner, its summary and the failing item's lines on stderr (with the relocated-field verdict, if any), nothing paraphrased.
- **Reproduction**: `make rebuild`, or the failing variant's own target, `make mainui-check-clean` or `make mainui-check-expert` (the full `make mainui-check` at the commit gate), plus the commands that map a differing offset or address to a section and a function (`readelf -S`, `objdump -d --start-address`) and `scripts/fncmp.py` for a single function or pair (its masked MATCH does not prove relocated fields).
- **Constraints on the fix**, to be carried into every stage:
  - A bug in `scripts/` gets a RED **unit test run by `make test`** (`tests/test_*.py`), on a synthetic input built by the test itself, never on the firmware. It runs well under 100 ms.
  - A bug in a C file under `src/` is fixed in that file; the proof is `make rebuild` going identical again (keymon) or the variant's target passing the item (MainUI).
  - The fix turns `make test`, `make rebuild` and `make mainui-check` green.
  - Never edit an expected sha256 or `layout.json` ranges, never add, edit or remove a row of `check-allow.tsv` or `check-pending.tsv`, never change the check's references (`REF`, `EXPERT_REF`) or their defaults, to hide a difference.
- **Already eliminated**, on a retry (step 5): every hypothesis the previous attempts disproved, and why their commit was refused.

### 4. The commit gate — check, then accept or refuse
When `fix-bug` proposes its commit, check each point yourself, with commands you run:

1. A fix in `scripts/` adds (or extends) a test under `tests/` that `make test` runs, and the test does not read `work/` or `firmware/`.
2. That test **fails on the pre-fix code**: in a throwaway `git worktree` of `HEAD` under `tmp/`, apply only the diff's `tests/` changes and run it — it must fail. Then it passes on the working tree.
3. `make test`, `make rebuild` and `make mainui-check` are green, and the failure you handed over no longer appears.
4. The diff does not touch an expected sha256, nor remove a C file from a build, unless the bug report said that was the cause, and does not touch `check-allow.tsv`, `check-pending.tsv` or the check's references (`REF`, `EXPERT_REF`).

All hold → accept: `fix-bug` commits (folded into `HEAD` when `progress.md` exists, see `git-commit`). Remove the worktree.
Any one fails → refuse, with the reason. Nothing is committed; restore the working tree to `HEAD` before the next attempt.

### 5. Count the attempt
An attempt fails when you refuse the commit, or when `fix-bug` stops on its own (cause unproven after two debug agents, verification failing twice).

- Fewer than 3 failed attempts on this failure → back to step 3 with the same failure, the bug report extended with what was eliminated and why the last attempt failed.
- 3 failed attempts → stop. Report `REBUILD-FAILED:` to the user: the failure, the three attempts, what each eliminated, and which observation is missing. This is the only moment this skill hands back to the human.

### 6. Loop
After an accepted commit, back to step 1: `make rebuild` and `make mainui-check` from the top.

## Output

- `REBUILD-GREEN:` + the `fix:` commits made, or folded into `HEAD` (possibly none).
- `REBUILD-FAILED:` + the report of step 5. The working tree is back at `HEAD`, nothing half-fixed is left behind.

Never push: the caller decides.
