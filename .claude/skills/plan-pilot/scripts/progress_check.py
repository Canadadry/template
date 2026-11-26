#!/usr/bin/env python3
"""Check a change to progress.md, the checklist plan-pilot keeps at the root.

usage: progress_check.py <old> <new>   (old: "-" when the file is being created)

Every line is an item: `- [ ] <number> <text>` or `- [x] <number> <text>`,
indented by 2 spaces per level. The number is the item's place in the tree:
top-level items are 1, 2, 3...; the children of item 2.3 are 2.3.1, 2.3.2...
No hole: an [x] has every item before it [x], its ancestors excepted, and an
[x] with children has them all [x]. Against the old file: an [x] line is
kept as is; a [ ] line keeps its text and order, its number may change (an
item inserted before it shifts it), it may become [x]; a new line goes
after every old [x]; nothing goes back to [ ]; at least one new [x].
Exit 0 when the change is accepted, 1 with the reasons on stderr otherwise.
"""

import re
import sys

ITEM = re.compile(r"^((?:  )*)- \[([ x])\] (\d+(?:\.\d+)*) (\S.*)$")


class Refused(Exception):
    pass


def parse(text, name):
    """Return the items as dicts: depth, done, number, text, line, parent."""
    items, stack, counters = [], [], [0]
    for row, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        match = ITEM.match(line)
        if not match:
            raise Refused(f"{name} line {row} is not \"- [ ] <number> <text>\" indented by 2 spaces: {line}")
        depth = len(match.group(1)) // 2
        if depth > len(stack):
            raise Refused(f"{name} line {row} is indented more than one level below the previous item: {line}")
        del stack[depth:]
        del counters[depth + 1:]
        counters[depth] += 1
        parent = stack[-1] if stack else None
        expected = ((parent["number"] + ".") if parent else "") + str(counters[depth])
        if match.group(3) != expected:
            raise Refused(f"{name} line {row} should be numbered {expected}: {line}")
        item = {
            "depth": depth, "done": match.group(2) == "x", "number": match.group(3),
            "text": match.group(4), "line": line, "parent": parent, "children": [],
        }
        if parent:
            parent["children"].append(item)
        items.append(item)
        stack.append(item)
        counters.append(0)
    return items


def ancestors(item):
    while item["parent"]:
        item = item["parent"]
        yield item


def check_no_hole(items):
    for index, item in enumerate(items):
        if not item["done"]:
            continue
        if any(not child["done"] for child in item["children"]):
            raise Refused(f"{item['number']} is [x] while one of its children is [ ]")
        skip = {id(a) for a in ancestors(item)}
        for earlier in items[:index]:
            if not earlier["done"] and id(earlier) not in skip:
                raise Refused(f"{item['number']} is [x] while {earlier['number']}, before it, is [ ]")


def check_change(old, new):
    ticks, position, last_old_done = 0, 0, -1
    for item in old:
        while position < len(new) and new[position]["text"] != item["text"]:
            if new[position]["done"]:
                ticks += 1
            new[position]["new"] = True
            position += 1
        if position == len(new):
            raise Refused(f"a line was removed, renamed or moved: {item['line']}")
        match = new[position]
        if item["done"]:
            if match["line"] != item["line"]:
                raise Refused(f"an [x] line changed: {item['line']}")
            last_old_done = position
        elif match["done"]:
            ticks += 1
        position += 1
    ticks += sum(1 for item in new[position:] if item["done"])
    if any(item.get("new") for item in new[:last_old_done]):
        raise Refused("a new line was added before an existing [x]")
    if ticks == 0:
        raise Refused("the commit ticks no new [x]")


def main(argv):
    old_path, new_path = argv[1], argv[2]
    try:
        with open(new_path) as f:
            new = parse(f.read(), "progress.md")
        check_no_hole(new)
        if old_path != "-":
            with open(old_path) as f:
                old = parse(f.read(), "the committed progress.md")
            check_change(old, new)
    except Refused as error:
        print(f"progress.md: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
