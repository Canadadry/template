# When to Use a Test Double

Replace only **system boundaries**, and prefer a real, tiny input over a double:

- The firmware: never read in a unit test; build a small synthetic input instead (`tests/make_fake_image.py` is the prior art).
- The ARM toolchain: use the real one (`$CROSS`) on a few assembled lines, rather than faking its output.
- The device: never reached from a test (`CLAUDE.md`).

Don't replace:

- Your own modules
- Internal collaborators
- `pyelftools`: parse the real ELF the test produced

## Designing for Test Doubles

**Pass the dependency in**: a script takes its inputs (paths, the toolchain prefix) as arguments or from the environment, never from a hard-coded location, so a test can point it at a temporary directory.
