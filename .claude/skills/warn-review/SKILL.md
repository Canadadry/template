---
name: warn-review
description: Internal — called by plan-pilot at each phase end. Flags design smells and matching-decompilation rule violations as bare warnings, never fixes.
---

# Warn Review

Flags design smells as warnings only. Never suggests fixes, causes, or direction - just states what's wrong and where. The caller (plan-pilot, through plan-review) decides what to do about them.

## Scope

- Given paths (plan-pilot passes the code a phase touched): review only those.
- Given no argument: recursively scan the current working directory. Respect `.gitignore`. Skip build output, vendor/third-party code, binary assets, and `.git`. Restrict to the project's main detected language's source files.

## What to flag

Design smells only - never correctness bugs, never simplification/efficiency nitpicks. This is a smell, not a science: judge holistically, don't apply numeric thresholds or ratios.

Checklist (each is an outside-in hint that something is off):

1. No lib/utils/shared package despite repeated logic across files - whoever built this assumed nothing here would ever be reused.
2. A comment block longer than the code it explains, on a path that isn't inherently complex - if it needs a paragraph to explain, is the code itself too hard to follow?
3. A generic name (History, Manager, Handler, Utils, Data...) whose actual behavior doesn't match that concept - read the file and judge the mismatch yourself, don't just pattern-match the name.
4. A file dramatically larger than everything else, especially an entry point - what is this hiding that should've been split out?
5. A module required/imported by nearly everything else - a hidden hub nobody can avoid depending on.
6. Config values or magic numbers scattered inline with no central place - nobody expected this to need tuning or reuse.
7. Dependency direction should form a tree: main depends on specific modules, specific modules depend on generic ones from lib - never the reverse. Tangled or flat imports with no such layering is a smell.
8. The internal design should be readable from folder/file names alone. If you can't infer the architecture just by browsing the tree, that's the smell.
9. The largest or most complex file has little to no direct test coverage, relying only on broader end-to-end checks - the code most likely to hide bugs is the code least protected against them.
10. A systematic audit/sweep's completeness claim (e.g. "N sites, all handled") with no mechanism (test, CI check, or process step) to catch new code later recreating the exact pattern it swept for - the confidence is frozen at audit time while the codebase keeps moving.

## Project ground rules: matching decompilation

Check these too, on every run, in `src/`, `scripts/`, the `layout.json` files and MainUI's check lists (`src/mainui/check-allow.tsv`, `check-pending.tsv`). Unlike the checklist above they are rules, not smells: flag every violation, still as a bare warning.

Why they exist, and the only two goals they serve:

- **Trust**: a rebuild reported byte-identical (keymon, `make rebuild`) or a function reported matched (MainUI, `make mainui-check`) must be so because the C compiles to the original bytes, never because bytes were smuggled in, a check was bent or a list row hides it.
- **Readability**: the sources must end up readable by someone who never saw the binary: real names, real types, facts stated once.

The rules are the means, not the goal. If code breaks one in a case nobody anticipated and the result is clearly more trustworthy or clearer than following the rule, don't flag it as a violation: report it as `file[:line]: breaks rule N on purpose`, so the user can check the reasoning. Following a rule in a way that defeats trust or readability is the violation.

11. Raw bytes in a C file to force a match: `.inst`, `.word`, `asm()`, a naked function, a byte array executed as code.
12. A C file under `src/` whose flags are not those its `layout.json` entry states, or a `layout.json` C entry without `cflags`.
13. An absolute address used as a pointer in C (`*(int *)0x2f20c`) instead of a named symbol.
14. A Ghidra placeholder name (`FUN_`, `DAT_`, `local_`, `param_`, `uVar`, `undefined4`) in a unit the plan or its note declares finished.
15. A name or type that contradicts what the code or the strings show (a `get_` that writes, an `int` used as a pointer).
16. Overlapping or unsorted ranges in a `layout.json`, or a C entry whose range does not match the functions its file defines.
17. A changed expected sha256, a C file moved back to generated assembly, a rise in the `.inst` count the generator reports, an allow-list or pending-list row added without its reason, or a change to `make mainui-check`'s reference, in a change that does not say why.
18. A fact about one binary (an address, a section range, a library list) hard-coded in `scripts/` instead of that binary's `layout.json` or build file.

## Output format

Plain markdown list, one line per finding: `file[:line]: should not <do Y>`.

- Include a line number only when a specific line makes sense (e.g. items 2, 3, 6); omit it for whole-file/structural smells (e.g. items 1, 4, 5, 7, 8).
- State the bare rule only. No "why", no failure scenario, no suggested fix, no fix direction.
- No severity ranking - flat list, in the order found.
- If nothing is found, say so plainly.

## When a finding doesn't fit the checklist

Report it the same way, prefixed `[off-checklist]`, so the reader can tell it apart.
