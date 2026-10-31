# Interface Design for Testability

Good interfaces make testing natural. Names are illustrative.

1. **Accept inputs, don't look for them**

   ```python
   # Testable: the caller says where everything is
   def main(layout_path, elf_path, outdir): ...

   # Hard to test: hidden dependency on the repository layout
   def main(): elf = open("work/miyoo285_fw/fs/04_customer/app/keymon", "rb")
   ```

2. **Return results, don't only print them**

   A function that computes a comparison returns it (a list of differing offsets); the command-line layer prints it and sets the exit status.

3. **Small surface area**
   - Fewer entry points = fewer tests needed
   - Fewer parameters = simpler test setup

4. **Keep the core pure; push I/O to the top**

   Decoding, labeling and comparing work on bytes and dicts; reading files and running the toolchain happens in a thin top layer.

5. **Fail at the boundary**

   Every entry point checks what it requires (a known relocation type, an address inside a segment, a layout range that exists) and stops with a message naming the input, so a bad layout fails at once, not as a byte difference three steps later.
