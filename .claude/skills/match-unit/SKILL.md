---
name: match-unit
description: Internal — called by plan-pilot for a "skill: match-unit" step. Matches the functions of one original translation unit in C or C++, in batches of up to 10 functions per commit, each batch landing only once the build proves it byte-identical (keymon). MainUI (delta mode): ports delta-map functions already in C to MainUI-285-clean, each batch proven by make rebuild then make mainui-check with exactly its pending rows removed.
---

# match-unit

Takes two arguments: a binary and a unit, as named in `src/<binary>/layout.json` `units` (one per original translation unit: its address ranges in `.text`, `.rodata`, `.data`, `.bss`, `.init_array`, its flags, its `language`), or several units, or `all units of <kind>` as the plan step says; and the **step's text**, verbatim, from which it reads the attempt budget and any override of the inputs below. Runs unattended, in place, in the plan-pilot session.

Each matched function moves from the generated assembly into the unit's source file, at its place in address order, and the rebuild stays byte-identical at every commit.

That is the **byte-identical mode**, for keymon: § Rules, § Loop and § Report. **MainUI** uses § Delta mode instead, which replaces those three for it: every MainUI function is already in C (no generated `.text` is left since plan 3 step 2.5) and `make mainui` can never be identical again, so a delta port edits a function in place until it compiles to its bytes in the reference `MainUI-285-clean`, proven by `make mainui-check`.

## Rules

- **The build is the only proof** (`CLAUDE.md` § Matching decompilation). A function counts as matched when the binary's build is identical with it in C or C++ (`make rebuild` for keymon), never on an agent's report or on `fncmp.py` alone. `make rebuild` (every binary) runs at each checkpoint.
- **Only you touch `src/`, `layout.json` and git.** `match-function` agents write under `tmp/match/` only.
- **One batch per commit**: up to **10** matched functions (`feat: match <n> functions in <binary>/<unit>`, each function named in the body), each with its `progress.md` child ticked (`- [x] <unit>: <name>`), so a failure later loses at most one batch. A batch of one is `feat: match <name> in <binary>/<unit>`.
- **Never change the unit's flags for one function.** Flags are the unit's; a function that only matches with other flags is a sign the unit boundaries are wrong: report it, don't split the unit yourself.
- **The rules section overrides this skill** where they disagree: it holds what the binary's earlier steps learned. Read it before the first integration.
- A `QUESTION:` from an agent goes to a fresh `guideline` agent, never to the user.

## Loop

### 0. Resolve the inputs
Per unit, from the layout and the step's text (the step's text wins when it names one); no new layout key. Write the resolved list into the unit's first commit message.

| Input | Resolves to |
|---|---|
| **Budget** | the step's `N / M` (`budget 5 / 15`; "same budget" → the earlier step's it refers to); none → **12 / 40** |
| **Language** | the unit's `language`; absent → `c`, unless its `cflags` carry `-x c++` (keymon's cJSON: C++ from a `.c` file) |
| **Flags** | the unit's `cflags`, never changed |
| **Source file** | the `source` of the unit's existing `c` entry (the one whose code lies in the unit's `.text` range: `unit_11628.c`, `unit_15b20.cpp`); none → `src/<binary>/<unit>.cpp` (language `c++`) or `<unit>.c` |
| **Header** | `src/<binary>/<dir>.h` (`<dir>` the binary's directory under `src/`). A binary with a `hash_table` (MainUI): its C++ units include it (`mainui.h`), its C units none. A binary without (keymon): every unit, as plan 1 (`keymon.h`) |
| **Rules section** | `notes/<dir>-units.md` § Matching rules, from its `##` heading to the next `##` |
| **Instances start** | the unit's `instances`, if any |

### 1. List the work
From `layout.json`: the unit's functions not yet in its source file (the `c` entries), smallest first — small functions give the names and types the big ones need. Record in `progress.md`, under the step's item, one `- [ ]` child per function, in that order, in the first commit of the step.

A unit whose list holds more than **100 functions** takes checkpoints (§ 3a).

### 2. Match, a few at a time
Spawn up to **3** fresh `match-function` agents in parallel, one function each, smallest first. Each prompt holds, in this order (`match-function` § Inputs): the binary, address, size; the flags, language and driver (`$CROSS`gcc on a `.c` or a `.cpp`); the budget `N / M`; the header to include (or none); every name and type already established (`layout.json` `names` and `comdat`, the unit's file, the header), with addresses; the paths to read (the original binary under `work/`, `decomp/<tag>/`, `notes/`); then the rules section **verbatim**:

```
awk '/^## /{f=/^## Matching rules$/} f' notes/<dir>-units.md
```

Save the prompt first as `tmp/match/<binary>-<address>/prompt.md`, then hand it to the agent. Independent functions only: a function whose callee is still unmatched can still be matched (callees are `extern`), so this is rarely a constraint.

### 3. Integrate a batch of MATCHes
Take up to **10** `MATCH`es that can land now, in address order, and integrate them together as one change: the steps below apply to each function of the batch, and the proof (build) and the commit are made once for the whole batch. A batch that does not prove identical is undone and **split in two halves**, each retried as a batch, down to single functions; only a single function's failure counts as its failed try (the two-tries rule below).

**C** (keymon's units):

1. Move the C into the unit's file at its place. Externals already defined in C become plain calls; new names go to `layout.json` `names` (addresses of functions and data still in assembly) or to the C file (what it now defines); declarations other units need go to `<unit>.h` beside it.
2. Update the unit's `c` entry in `layout.json` (its matched ranges).
3. `make test` and the binary's build (`make rebuild` for keymon). Identical → commit (`git-commit`, in place, you at the gate).

Either language: different, after the fixes the evidence points to (names, a missing `extern`, the range) → the integration is wrong, not the match; after **two failed tries**, put the function back as assembly and treat it as a `NONMATCH` with the reason "integration".

### 3a. Checkpoint (a unit of more than 100 functions)
Only for a unit whose § 1 list holds more than 100 functions. A function is *handled* once it is matched (§ 3) or recorded non-matching (§ 4). Take a checkpoint, numbered `<k>` from 1 within the unit:

- after every **100** functions handled since the previous checkpoint (or since the unit's start);
- at the **end of a class** — every function of the unit whose mangled name is a member of that class (from the `c` entry, `names` and `comdat`) handled — when at least **20** functions have been handled since the previous checkpoint (the floor keeps a unit of many small classes from a checkpoint per class).

In order:

1. **Collect the unit's lessons** since the start of the unit: from the agents' reports (`tmp/match/<binary>-<address>/`) and from the integrations (the fixes the evidence pointed to, the `names` the rebuild asked for, the literal and integration fallbacks). A lesson *seen more than once* (two or more functions, or two or more integrations) that the rules section does not already state becomes a rule.
2. **Write each such rule** as a bullet in the rules section under the running step's subsection, `### Units by dependency (step <s>)` (created at the first need), ending `(step <s>, <unit>, checkpoint <k>)`. Its evidence (addresses, attempt counts) goes to the step's own section of the units note, `## Units by dependency (step <s>)` › `### <unit> checkpoints`, never into the rules section. For a binary without a `hash_table` (keymon) the same, in `notes/keymon-units.md`.
3. **Compute the non-matching rate so far**: non-matched / handled in this unit, from `progress.md`'s ticked children of the unit (the `(nonmatching)` suffix).
4. **One `docs:` commit of its own** (`docs: checkpoint <k> of <unit> in <binary>`), after a full `make rebuild` identical (every binary), never mixed with a function's commit, through `git-commit`, in place: the rules added (or "no new rule"), the rate and the previous checkpoint's rate in the message.
5. **Print** for the caller: `CHECKPOINT: <unit> <k>: <handled> handled, <nonmatched> non-matching (<rate>%), previous <rate>%` (`previous none` at the first).

A checkpoint never stops the loop: reacting to a rate jump is the caller's decision. Prompts written after it carry its rules, since the rules section is extracted when each prompt is written (§ 2).

### 4. Record a NONMATCH
Keep the best attempt as `src/<binary>/nonmatching/<symbol>.cpp` (language `c++`) or `<symbol>.c` (otherwise, `-x c++` units included), `<symbol>` the object's symbol (mangled in C++); add `{"name": <symbol>, "start": <address>, "reason": <one line on what is left>}` to the unit's `nonmatching` list in `layout.json`; tick its `progress.md` child with ` (nonmatching)` appended to its text; one commit (`docs:`). `make nonmatching` must rebuild and compare it. The function stays as generated assembly. A non-match never stops the loop.

### 5. When every function of the unit is in its source file
**Binary without a `hash_table` (keymon).** Move the unit's data into C: its strings and constants (`.rodata`), initialized globals (`.data`), zeroed globals (`.bss`), in the order the original lays them out, then drop those ranges from the generated assembly. `make rebuild` identical → commit (`refactor: move <unit> data into C`). A difference → the boundary branch below.

**The boundary branch.** The data move and the switch prove the unit's boundaries; a difference there means a boundary is wrong:

1. Find which boundary from the first differing offsets (which section, which neighbour unit).
2. Correct it in the units note and `layout.json` (move the misplaced functions or data to the neighbour unit, with their flags), commit the correction (`fix: correct <unit> boundary`) with the evidence, and record it for the step note.
3. Redo the move or the switch for the affected units; functions already matched stay matched (they move with their range).
4. The same boundary failing a second time → stop: `UNIT-FAILED`, with both attempts and the differing offsets.

### 6. Loop
Back to step 2 until no function of the unit is left, taking each checkpoint (§ 3a) as it falls due. Then report.

## Report

`UNIT-DONE: <unit>` — the resolved inputs and the budget used; functions matched (with their attempt counts) and non-matched (with their one line and the limit that stopped them); names introduced; for keymon, whether the data moved into C; boundaries corrected; every `CHECKPOINT:` line, in order. Or `UNIT-FAILED: <unit>` — what failed (a boundary, an integration), the evidence, and what was committed before it. Never push: the caller decides.

## Delta mode (MainUI)

Plan 3 (`docs/plan-3.md` § 2): a MainUI function that differs from the reference because Onion's base is another Miyoo build came out of a compiler, so it is matched against the reference's bytes. The reference is `firmware/onion-v4.5-dev/MainUI-285-clean` (`make mainui-check`'s default `REF`). Its addresses are not the layout's: the layout's addresses, `names` and function list are the 0628 original's, and the reference's differ after the first moved function (−0x10 after `KeyTestWindow2::handleEvent`, −0x1f0 after the GPIO code). Never use a layout address against the reference.

### Rules (delta mode)

- **The net is the only proof** (`CLAUDE.md` § Matching decompilation): `make rebuild` identical (keymon), then `make mainui-check` against `MainUI-285-clean` with its allow-list (`src/mainui/check-allow.tsv`) and pending list (`src/mainui/check-pending.tsv`), exit 0. Read its output, not only its exit code. `fncmp.py`'s masked `MATCH` is a working aid, never the proof; an agent's report is not one either. Exit 2 is a tool or setup error, never a failed try.
- **The batch rule**: each commit removes from the pending list exactly the rows of the functions it ports, in the same commit. The check then proves the rest on its own: it fails any differing item that is on no list (no new failure) and any pending item that now matches (the list shrank by exactly this batch). `git diff src/mainui/check-pending.tsv` of the commit deletes exactly the batch's rows and adds none.
- **No list row or reference change hides a failure.** No row is added for the 0628 original: from the first port on, `make mainui-check REF=<0628 original>` fails on every ported function, by design (the tag `mainui-0628-identical` keeps the 0628 state).
- These bullets of § Rules hold unchanged: only you touch `src/`, `layout.json` and git (here also the two lists and the notes); never change the unit's flags for one function; the rules section overrides this skill; a `QUESTION:` goes to a fresh `guideline` agent.
- **Not in delta mode** (their premise, the identical link, is gone): moving code out of generated assembly; a per-function `c` entry or its growth; `names` for generated callees, dropped duplicate groups or `s_<addr>` literals; the literal-run claim; `prev/` and `make objcmp`; the `link-names.txt` delta and the headroom (`make mainui-progress`); `make mainui-order`; the switch to a whole object and its boundary branch; `src/mainui/nonmatching/` and `make nonmatching` (they compare against 0628); `callee_map.py --layout`; `make mainui-gate` (step 2.6's one-time gate, not the net). The per-function check covers what the neighbour check did, and more: every function and data row of the binary, relocations included.

### D0. Resolve the inputs

The scope is one of:

- a unit name (`unit_4c418`), or several;
- "the pending list's Miyoo-build differences": the units that hold § D1's work items.

The step's text may also name only-in-build functions to delete (§ D6). Per unit, § 0's rows **Budget**, **Language**, **Flags**, **Source file**, **Header** and **Rules section** resolve as there (the header: `mainui.h` for C++ units, none for C). Then, per function:

| Input | Resolves to |
|---|---|
| **Symbol** | the build symbol, mangled, from the `key` column of its row in `make mainui-check`'s output |
| **0628 address and size** | the delta map row's `old` and `old size` (§ D1) |
| **Reference** | `firmware/onion-v4.5-dev/MainUI-285-clean`, its sha256 from the check's `# reference sha256` line |
| **Reference address and size** | the reference columns of the function's pending row in `make mainui-check`'s output: the address the proof uses |
| **Unit, source file** | the map row's `unit` and `file`, cross-checked with the layout (§ D1) |
| **Evidence** | the map row's `evidence` column, and the function's entry in `notes/mainui-onion-delta.md` § Miyoo build differences |

Write the resolved list into the unit's first commit message.

### D1. List the work

Run the net once on the clean tree. `make mainui-check` exits 0 on the committed lists; keep its `# functions:` and `# data differences:` lines as the "before" lines of the first commit. Each line it prints for an item that is not matched is tab-separated: verdict, kind, key, build address, build size, reference address, reference size, detail, fnpair class, category, reason, note.

A **work item** is a pending row of kind `function` and category `code`, for the reference's sha256, joined with the delta map:

1. Its `pending` line in the check's output gives the build symbol, the build address and the reference address and size.
2. The delta map's generated function table (the block between `<!-- deltamap:begin -->` and `<!-- deltamap:end -->` of `notes/mainui-onion-delta.md`, as `make mainui-delta` writes it) has one row whose `new` is that reference address. It gives the class, the pairing, the 0628 address (`old`), `old size`, the unit, the file and the evidence.
3. The layout's `c` entry whose `source` is that file has `object` `<unit>.o` and a `start`–`end` that holds the 0628 address, and `nm build/mainui-check/MainUI/<unit>.o` defines the symbol.

The row is a work item when the map row's class is `miyoo-build` and its pairing `differing`. A pending `code` row whose map row has another class (`hand-patch`, `hand-patch-data`) belongs to step 3.2 or 3.3: not delta-mode work. A pending `code` row the join cannot place (no map row at its reference address, or a `c` entry or `nm` that disagrees) → `UNIT-FAILED` with the row named, never skipped. The `unpaired` rows are § D6's, and only when the step's text names their functions.

Order: the units in `notes/mainui-units.md` § Order (step 1.6) › Levels' sequence; within a unit, smallest first (0628 size). Record in `progress.md`, under the step's item, one `- [ ] <unit>: <name>` child per work item in that order, then one `- [ ] <unit>: delete <names>` child per deletion of § D6, in the first commit of the step. An empty work list with no deletion named → `UNIT-DONE` saying `no work item`.

A unit whose work list holds more than **100 functions** takes checkpoints (§ D3a).

### D2. Match, a few at a time

Spawn up to **3** fresh `match-function` agents in parallel, one work item each, smallest first, in its **delta mode**. Each prompt holds, in this order (`match-function` § Delta mode › Inputs): the source file, the symbol, the 0628 address and size; the reference's path and sha256, the reference address and size; the evidence (the map row, the § Miyoo build differences entry, verbatim); the flags, language and driver (`$CROSS`gcc on a `.c` or a `.cpp`); the budget `N / M`; the header to include (or none); the paths to read (the 0628 original under `work/`, the reference, `decomp/<tag>/`, `notes/`); then the rules section **verbatim**, extracted as § 2 says. Save the prompt first as `tmp/match/MainUI-285-clean-<reference address>/prompt.md`, then hand it to the agent.

### D3. Integrate a batch of MATCHes

Take up to **10** `MATCH`es, in address order, and integrate them together as one change on a clean tree:

1. **The change.** Apply each `MATCH`'s `patch.diff` to the unit's source file (`git apply`); move the declarations the agent added to its header copy into `mainui.h` (or the file, when only this unit needs them). No `layout.json` change, unless the build refuses without one: the build's message names it, and it goes in the commit.
2. **The lists.** Delete exactly the batch's rows from `src/mainui/check-pending.tsv`. Save the whole change (`git diff`) as `tmp/match-unit/<unit>/<address>.patch`, named by the batch's first reference address.
3. **The delta note.** Mark each function's entry in `notes/mainui-onion-delta.md` § Miyoo build differences as ported: the plan step, the change, the check's verdict.
4. **The proof.** `make test`, `make rebuild` identical, then `make mainui-check`: exit 0, no `FAIL` line, its `functions:` line with `matched` up by the batch's size, `pending` down by it, `allow-listed` unchanged and `0 failing`, its `data differences:` line unchanged; and `git diff src/mainui/check-pending.tsv` deleting exactly the batch's rows.
5. **A batch that fails** is undone with `git apply -R` of its saved patch and **split in two halves**, each retried as a batch, down to single functions. A single function's failure (its own item still failing, or any other item) counts as its failed try; after **two failed tries** it is a `NONMATCH` with the reason "integration" (§ D4).
6. **The commit**, through `git-commit`, in place (you at the gate): `feat: match <n> functions to MainUI-285-clean in MainUI/<unit>` (a batch of one: `feat: match <name> to MainUI-285-clean in MainUI/<unit>`). The body names each function with its 0628 and reference addresses and gives the check's `functions:` and `data differences:` lines before and after; the unit's first commit also carries the resolved inputs. Each function's `progress.md` child is ticked in the same commit.

### D3a. Checkpoint (a work list of more than 100 functions)

§ 3a, with these changes: a function is *handled* once it is matched (§ D3), rewritten (§ D4), re-classed (§ D5) or deleted (§ D6); the rules go under `### Delta matching (plan 3, step <s>)` in the rules section, each ending `(plan 3 step <s>, <unit>, checkpoint <k>)`; their evidence goes to `notes/mainui-units.md` `## Delta matching (plan 3, step <s>)` › `### <unit> checkpoints`; the rate counts the `(non-matching rewrite)` suffix; the `docs:` commit comes after the whole net green (`make rebuild` identical, then `make mainui-check` exit 0).

### D4. Out of budget: a reviewed non-matching rewrite

A `NONMATCH` (the budget, or "integration") without a confirmed `HANDPATCH:` line (§ D5) becomes C or C++ that does what the reference does (plan 3 § 2), and the run goes on. One commit per function:

1. **The rewrite.** The best source that does what the reference does, from the reference's disassembly and the delta map's evidence, starting from the agent's best source, goes into the unit's source file in place. Not under `nonmatching/`: `make nonmatching` compares against 0628, and the function has no generated copy to stay as.
2. **The review.** A fresh, read-only agent gets the rewrite's object (compiled under `tmp/match/MainUI-285-clean-<reference address>/review/` with the unit's flags plus `-ffunction-sections`), the reference's disassembly of the function and its 0628 disassembly. It compares the object against the reference path by path (every branch, call and its arguments, store, return value) and reports `SAME-BEHAVIOUR:` or `DIFFERENT: <the path>`. A `DIFFERENT:` goes back to the rewrite once, then to a new fresh reviewer; a second `DIFFERENT:` → `UNIT-FAILED`.
3. **The lists.** Delete the function's pending row; add an allow-list row for the 285-clean sha256: kind `function`, its symbol, category `hand-patch`, reason `Miyoo build difference out of match budget (N / M): non-matching rewrite, reviewed, notes/mainui-onion-delta.md` (`N / M` the budget; `integration` in its place for that reason). No new category. The first such row also changes, in the same commit, the test of `tests/test_makefile.py` that allows only `removed-by-decision` rows, to accept `hand-patch` for 285-clean.
4. **The note.** The function's entry in `notes/mainui-onion-delta.md` § Miyoo build differences: the asm before / after, the behaviour, why it is not matched (the agent's log: what is left), the review's verdict, and the counts updated. The map's class stays `miyoo-build`: its origin is still a compiler.
5. **The proof.** As § D3 step 4, except the check's line reads `matched` unchanged, `allow-listed` up by one, `pending` down by one, `0 failing`; the pending-list diff deletes exactly that row and the allow-list diff adds exactly its row.
6. **The commit**, through `git-commit`, in place: `feat: rewrite <name> as non-matching in MainUI/<unit>`, with the budget, both counts, the review's verdict and the check's lines before and after; its `progress.md` child ticked with ` (non-matching rewrite)` appended.

### D5. Found to be a hand patch

A `HANDPATCH:` line (a NOP, a branch into a code cave, a constant or string no source change explains) that you confirm against the reference's disassembly means the map misclassed the function. It is not ground against the budget and not rewritten here: it is ported with the other hand patches in step 3.2. One `docs:` commit, no source change (`docs: re-class <name> as a hand patch in the delta map`):

- its row in `notes/mainui-onion-delta-overrides.tsv` becomes class `hand-patch`, with the evidence as its reason;
- `make mainui-delta` regenerates the block of `notes/mainui-onion-delta.md`, and the prose counts are updated;
- its pending row stays, its reason updated to `delta map class hand-patch (<kind>): ported in plan 3 step 3.2`;
- the net green (the row is still pending, the check unchanged); its `progress.md` child ticked with ` (hand patch: step 3.2)` appended.

### D6. Delete an only-in-build function (set (b))

Only for functions the step's text names, on the pending list as `unpaired` (the check prints them `only in build`), after every work item of the scope is handled (their last callers are then ported away). One commit per unit holding them, in § Order:

1. `grep` the names in `src/mainui/`: a caller left → `UNIT-FAILED`, naming it.
2. Remove the definition, its prototype in the header (`mainui.h` or `<unit>.h`), and data only it used (at `-O0` its string literals go with it).
3. `make test`, `make rebuild` identical, then `make mainui-check`. It now fails with `unknown entry` on the deleted functions' `unpaired` rows and on the data rows that cleared with them (once a function is gone, fnpair has no row for it, so its list row names no item; a data row that clears has no item either — `scripts/mainui_check.py` `_listed()`). Remove exactly those rows; each one's reason must already name this step or this deletion. A row that clears without saying so is a `UNIT-FAILED`, never removed silently; any other failure → undo, `UNIT-FAILED`.
4. Rerun `make mainui-check`: exit 0, its `unpaired:` line down by the deleted functions; `git diff src/mainui/check-pending.tsv` deletes exactly the rows of step 3.
5. Commit through `git-commit`, in place: `refactor: delete <names> from MainUI/<unit>`, with the rows removed and the check's lines before and after; its `progress.md` child ticked.

### D7. Loop

Back to § D2 until no work item of the scope is left, taking each checkpoint (§ D3a) as it falls due; then § D6's deletions; then report.

### D8. Report (delta mode)

`UNIT-DONE: <unit>` (or the scope) — the resolved inputs and the budget used; the functions matched, each with its reference address and attempt counts; the out-of-budget rewrites (budget or integration, the review's verdict); the functions re-classed as hand patches; the deletions and the rows they cleared; every `CHECKPOINT:` line, in order; the check's `functions:`, `relocated fields:`, `unpaired:` and `data differences:` lines after the last commit. Or `UNIT-FAILED: <unit>` — what failed (a join, an integration, a review, a deletion), the evidence, and what was committed before it. Never push: the caller decides.
