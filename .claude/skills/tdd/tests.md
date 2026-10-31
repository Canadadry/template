# Good and Bad Tests

Tests live in `tests/test_<module>.py`: `unittest.TestCase` classes, run by `make test` (`python3 -m unittest discover tests`). Prior art: `tests/test_sstar_unpack.py` builds a fake image with `tests/make_fake_image.py` and checks what the unpacker finds in it. Other names below are illustrative.

## Good Tests

**Integration-style**: test through the script's entry point or the functions it exposes, on an input the test builds.

```python
# GOOD: observable behavior, on a synthetic image
def test_fatload(self):
    _, parts = sstar_unpack.parse(build(PARTS, "fatload"))
    self.assertEqual([p.name for p in parts], ["sf_0x0", "KERNEL", "rootfs", "customer"])
```

Characteristics:

- Tests behavior callers care about (what lands in the output, what the build reports)
- Uses only what the script exposes
- Survives internal refactors
- Name describes WHAT, not HOW
- One logical assertion per test

For the generator and the comparison tools, build the input in the test: assemble a few lines with `$CROSS`-as into a `.o`, link a tiny ELF, then run the tool on it and check its output (a `MATCH`, a `DIFF` at the right offset, a `.s` that reassembles to the same bytes). Never read `work/` or `firmware/`.

## Bad Tests

**Implementation-detail tests**: coupled to internal structure.

```python
# BAD: asserts on a private helper's intermediate state
def test_labels_dict(self):
    src = elf2s.Source(layout, ".", elf, path)
    self.assertIn(0x12568, src.labels)
```

Red flags:

- Reaching into private helpers or intermediate data structures
- Asserting on call counts or call order
- Test breaks when refactoring without behavior change
- Test name describes HOW, not WHAT
- Verifying through a side channel instead of the output
- Depending on the firmware being extracted

## Assertions and Tests: Complementary Layers

Tests verify behavior from the outside. Assertions (`raise SystemExit` with a message, `assert` for internal invariants) enforce contracts from the inside. Both are needed.

```python
# Without a check: an unknown relocation is silently not masked, a diff appears later
masks[off] = FIELD.get(t, 0)

# With a check: fails at the violated contract
if t not in FIELD:
    raise SystemExit(f"{name}: unhandled relocation type {t} at {off:#x}")
```

Rule of thumb: if a test setup must respect a constraint to call a function, that constraint is checked inside the function.
