---
name: match-function
description: Internal — called by match-unit (and prd-autopilot implementers) for one function. Writes C or C++ that compiles to the original bytes of one function, proven by scripts/fncmp.py, within the budget it is given; changes nothing outside tmp/. keymon: a function of the byte-identical rebuild. MainUI (delta mode): a delta-map function already in C, edited until it compiles to its bytes in MainUI-285-clean.
---

# match-function

Writes C or C++ for **one** function of an original binary until the toolchain of the image compiles it to the same bytes. The caller (`match-unit`) integrates the result into `src/`; this skill only ever writes under `tmp/match/<binary>-<address>/`.

For MainUI the caller asks for **delta mode** (§ Delta mode, plan 3): the function is already in C, and the bytes to reach are those of the reference `MainUI-285-clean`. That section says what it replaces below; the rest holds in both modes.

## Inputs (from the caller)

- The binary and the function's address and size.
- The unit's **flags** (`layout.json` `units` `cflags`, or the caller's best guess), its **language** (`c` or `c++`) and the **driver**: `$CROSS`gcc on a `.c` file for C, on a `.cpp` file for C++ (gcc picks `cc1plus` from the suffix). A unit whose flags carry `-x c++` (keymon's cJSON) is compiled as its flags say, from a `.c` file.
- The **budget** as `N / M`: N attempts without progress, M attempts in all. None given → **12 / 40**.
- The **shared header** to include, if any (MainUI's C++ units: `src/mainui/mainui.h`; MainUI's C units include none; keymon's C units: `src/keymon/keymon.h`).
- The **rules text**, pasted by the caller (for MainUI: notes/mainui-units.md § Matching rules, verbatim). Read it first, before the disassembly: it holds what earlier steps learned (header word, dropped duplicates, key functions, `.dynsym` callees, naming sources, class layouts) and it overrides anything below that it contradicts.
- Known names: callees, globals, strings, classes the function uses, with their addresses (`layout.json` `names`, the unit's file, the shared header).
- Where to read: the original disassembly (`objdump -d --start-address=… --stop-address=…` on the extracted binary), Ghidra's C for it (`decomp/<tag>/<binary>.c` after `make decompile BIN=<binary>`, a starting point only), `notes/` for what is already known.

## The rule: only the bytes count

A function is matched when `scripts/fncmp.py <original> <object> <symbol>=<address>` prints `MATCH`, the object built with the given flags plus `-ffunction-sections`, nothing else. "Equivalent", "same logic", "only register allocation differs" is not a match.

Never put raw bytes in the source (`.inst`, `.word`, `asm()`, naked functions): `CLAUDE.md` § Matching decompilation. Never change the flags of the unit to match one function: flags belong to the original object, and every function of it shares them. If the flags look wrong, say so in the report.

## Method

1. **Read the target.** Disassemble it. Note the frame (`-O0`: frame pointer, every variable on the stack; optimized: scheduled, registers), the calls, the constants, the strings and globals it touches (`movw`/`movt` pairs, literal pools), the jump tables. In C++, note which calls go to the unit's instance run or the PLT (library members, template instances) and which `this` offsets it reads.
2. **First draft from the structure, not from Ghidra's text.** Ghidra's code has the right control flow and the wrong types. Write plain C or C++ as a developer would have: real types (`char`, `unsigned char`, `short`, `struct`, the class and its members), `if`/`for`/`switch` as they read, the original strings' contents in comments. Externals (callees, globals, strings) are declared with the names the caller gave; one whose name is unknown is named as § Naming says and goes in the report.
3. **Compile and compare.** `$CROSS`gcc `<flags> -ffunction-sections -c` (with `-I` of the header's directory when there is a header) into `tmp/match/…/`, then `scripts/fncmp.py`. In C++ the symbol compared is the **mangled** one, taken from `nm` of your object, never spelled by hand. Read the diff word by word against both disassemblies (`objdump -dr` on your object).
4. **Iterate on the cause of each difference**, one at a time, cheapest first:
   - instruction count differs → control flow or an expression is not the original's: loop form (`for`/`while`/`do`), early return vs. single exit, `?:` vs. `if`, an extra or missing temporary, a `switch` where an `if` chain was (or the reverse);
   - same count, different registers or order (optimized code) → declaration order, a temporary introduced or removed, a value reloaded instead of kept, `signed`/`unsigned`, an argument's type (a `char` parameter adds or drops a `uxtb`);
   - `-O0` code → it is literal: every variable is a stack slot in declaration order, every expression is computed as written. Match the slots (`[fp, #-N]`) to the declarations, and the evaluation order to the expression;
   - a constant differs → the type or the literal (`0x30` vs `'0'`, `sizeof`), or a struct field offset;
   - only relocated words differ → not a difference (`fncmp.py` masks them), but check the relocation targets are the right symbols (`objdump -dr`, and the C++ check below).
5. **Keep a log** in `tmp/match/…/log.md`: each attempt numbered, the words still differing, what it disproved, and both counts after it (attempts without progress, attempts in all). A change that does not reduce the differing words is reverted.

### C++ items

- **The header.** Include the shared header the caller named. A class, member or prototype it lacks is declared **in your attempt's copy only** (a copy of the header under `tmp/match/…/`, or the declaration in your `.cpp`): the caller decides what goes into the shared header. List every such declaration in the report.
- **Templates and inline members.** A template instance or an inline member is compiled through an explicit instantiation or a use, as § Matching rules says (no `extern template` except for literal-bearing callees). Compare the instance by its mangled symbol like any function.
- **Key functions.** Never define a provisional key function (§ Class layouts): it makes the object emit the vtable, typeinfo and name. If your object shows `_ZTV<class>` defined in `nm`, or a `.rodata` larger than the header word, undo what caused it.
- **Callees against `.dynsym`.** `fncmp.py` masks relocated fields, so a wrong callee (a const/non-const overload, the wrong constructor variant) still prints `MATCH`. Check each call relocation's target symbol against the original's `.dynsym` (an import) or the layout's `names` (a generated function); a target that is neither is a difference.
- **Callee map.** At `MATCH`, run `scripts/callee_map.py <object> <original> <symbol>=<address> --layout src/<binary>/layout.json` in the container. Its rows (every callee and called instance with its original address, each COMDAT group's other symbols) go into the report; a problem line it prints (count mismatch, conflict, unpaired, size differs) goes in too, never guessed around.

## Naming

- A name may come from an external source when it is cited: an RTTI typeinfo name (its address), a `Class::member` log string or a `__func__` (the string's address and the function loading it), Onion's source (`URL@commit:path:line`). The citation goes in the report next to the name.
- Without a source, the provisional forms of § Class layouts: `func_<addr>`, `g_<addr>`, `s_<addr>` (C and C++), `Class_<addr>`, `vfunc_<addr>` / `vfunc_<slot>`, `pad_<off>` / `<kind>_<off>` members. Never invent a name.

## Budget and the stop

Stop at `MATCH`. Otherwise stop after **N compile-compare attempts without progress** (no attempt reduced the differing words) or **M attempts in all**, whichever comes first, and report `NONMATCH`. N / M is the budget the caller gave, 12 / 40 when none. A non-match is a legitimate outcome: the function stays as generated assembly, and the caller records it.

## Report (final message)

Every report states the language, the flags, the symbol compared (mangled in C++), the budget, and the two counts from the log (attempts without progress at the stop, attempts in all).

- `MATCH: <symbol> @ <address>` — the source file path under `tmp/match/`; the externals it needs (name, address, kind); every callee and called instance with its original address (the `callee_map.py` rows in C++, with its problem lines); the declarations it added to its header copy; the names introduced and the source of each (a citation as § Naming says, or the evidence for a provisional name: a string, a call site, a register use), in a few lines.
- `NONMATCH: <symbol> @ <address>` — which limit stopped it (N without progress or M in all), the best source file, the words still differing (`fncmp.py` output), what the log disproved, and your best guess at what is left (flags, a missing struct, an inline function).
- `QUESTION:` — only for what blocks the method itself (the address is not a function start, the flags given cannot be right because neighbours match with others); the caller gets it answered.

## Delta mode (MainUI)

Plan 3 (`docs/plan-3.md` § 2): a MainUI function that differs from the reference `MainUI-285-clean` because Onion's base is another Miyoo build came out of a compiler, so it is matched against the reference's bytes. The function is already in C or C++ in `src/mainui/`, compiled from the 0628 version; what it lacks is the reference's bytes. The layout's addresses, `names` and function list are the 0628 original's; the reference's differ after the first moved function (−0x10 after `KeyTestWindow2::handleEvent`, −0x1f0 after the GPIO code). Never use a layout address against the reference. Everything above holds, except what this section replaces.

### Inputs (delta mode)

In place of § Inputs' first bullet (the binary, address and size):

- the **source file** (`src/mainui/<file>`), the **symbol** (the build's, mangled in C++), and its **0628 address and size**;
- the **reference** (`firmware/onion-v4.5-dev/MainUI-285-clean`, its sha256) and the function's **reference address and size**, from its pending row in `make mainui-check`'s output;
- the delta map's **evidence**: its row of the generated table of `notes/mainui-onion-delta.md` (the rewritten words, by reference address with the 0628 one in brackets) and its entry in § Miyoo build differences (the asm before / after).

The flags, language, driver, budget, header, rules text and paths to read as § Inputs. "Known names" are the unit's file and the header: no `names` entry is added for a delta port.

### The work

- **A copy of the whole unit.** Copy the unit's source file to `tmp/match/MainUI-285-clean-<reference address>/` (and `mainui.h` beside it, when the function needs a declaration the header lacks). Edit only the target function: the statics, the neighbours, the includes and the header compile as they do in the build.
- **Compile and compare.** `$CROSS`gcc `<flags> -ffunction-sections -I <your directory> -I src/mainui -c` on the copy into the same directory (the rules' `-I` notes hold, e.g. `unit_15b20`'s `cust_inc`), then `scripts/fncmp.py <reference> <object> <symbol>=<reference address>`. Only that `MATCH` counts here, never one against the 0628 original.
- **The first compare.** Attempt 1 is the unchanged copy: it gives the baseline differing words. It counts toward M, but it is not an attempt "without progress".
- **The method.** § Method applies, read target first. The delta map's evidence comes first: look for the source change a compiler would turn into that diff (a call removed, a condition or a constant changed, a statement moved). The 0628 disassembly of the same function (`objdump -d` of the 0628 original at its 0628 address) shows what the current C produces; the reference's, at the reference address, is the target. Diff the two before the first edit.
- **The callee check.** In place of § C++ items' callee map: `scripts/callee_map.py <object> <reference> <symbol>=<reference address>`, in the container, **without** `--layout` (its sizes are 0628's, and every function after 0x4e774 would report "size differs"). Its count and pairing problem lines go into the report. The `.dynsym` check of § C++ items is against the reference's `.dynsym`; a callee defined in the build is checked against `nm` of the unit's object or the build. A wrong call target is caught by the check's relocated fields (`make mainui-check`), not by you.
- **A hand patch is not ground against the budget.** Evidence no compiler explains (a NOP where the 0628 code has an instruction, a branch into a code cave, a constant or string edited in place with the code around it unchanged) → stop and report `NONMATCH` with a `HANDPATCH:` line.
- **Naming** is unchanged: no new name unless a new function appears.
- You still write nothing outside `tmp/`.

### Budget and the stop (delta mode)

As § Budget and the stop, except the last sentence: a non-match has no generated assembly to stay as; the caller rewrites it as a reviewed non-matching function or re-classes it as a hand patch.

### Report (delta mode)

As § Report, with the symbol at its reference address, and:

- `MATCH: <symbol> @ <reference address>` — also `patch.diff` in your directory: a unified diff of the function against the committed source file, at the repository root (`diff -u --label a/src/mainui/<file> --label b/src/mainui/<file> src/mainui/<file> <your copy>`), checked with `git apply --check`; the declarations added to your header copy, as today; the `callee_map.py` rows and problem lines.
- `NONMATCH: <symbol> @ <reference address>` — also the best source's `patch.diff`, and the behaviour the remaining difference implies (what the reference does that the best source does not: a path, a value, a call). Evidence of a hand patch goes in a `HANDPATCH: <reference address>: <evidence>` line.
