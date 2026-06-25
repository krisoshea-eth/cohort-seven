#!/usr/bin/env python3
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dev_updates as du  # noqa: E402


def merge(base, ours, theirs):
    return du.merge_documents(base, ours, theirs)


def check(name, cond):
    if not cond:
        print(f"FAIL: {name}")
        sys.exit(1)
    print(f"ok: {name}")


SAMPLE = """# T

| Name/GH | Week 0 | Week 1 |
|---|---|---|
| [A](u/a) | [U0](x) |  |
| [B](u/b) |  | [U1](y) |
"""
f1 = du.do_format(SAMPLE)
f2 = du.do_format(f1)
check("format idempotent", f1 == f2)
check("format preserves content", "[U0](x)" in f1 and "[U1](y)" in f1)

base = "| Name/GH | Week 1 |\n|---|---|\n| [A](u/a) |  |\n"
ours = base
theirs = "| Name/GH | Week 1 |\n|---|---|\n| [A](u/a) | [U1](z) |\n"
m, c = merge(base, ours, theirs)
check("fill cell no conflict", not c)
check("fill cell value present", "[U1](z)" in m)

base = "| Name/GH | Week 0 |\n|---|---|\n| [A](u/a) | [U0](x) |\n"
ours = "| Name/GH | Week 0 |\n|---|---|\n| [A](u/a) | [U0](x) |\n| [B](u/b) | [U0](y) |\n"
theirs = "| Name/GH | Week 0 |\n|---|---|\n| [A](u/a) | [U0](x) |\n| [C](u/c) | [U0](z) |\n"
m, c = merge(base, ours, theirs)
check("both add rows no conflict", not c)
check("ours row kept", "[U0](y)" in m)
check("theirs row kept", "[U0](z)" in m)

base = "| Name/GH | Week 0 |\n|---|---|\n| [A](u/a) | [U0](x) |\n| [B](u/b) | [U0](y) |\n"
ours = "| Name/GH | Week 0 |\n|---|---|\n| [A](u/a) | [U0](x) |\n"
theirs = base
m, c = merge(base, ours, theirs)
check("deleted row restored from main", "[U0](y)" in m)

base = "| Name/GH | Week 1 |\n|---|---|\n| [A](u/a) |  |\n"
ours = "| Name/GH | Week 1 |\n|---|---|\n| [A](u/a) | [U1](OURS) |\n"
theirs = "| Name/GH | Week 1 |\n|---|---|\n| [A](u/a) | [U1](THEIRS) |\n"
m, c = merge(base, ours, theirs)
check("true conflict flagged", c)
check("conflict keeps both values", "OURS" in m and "THEIRS" in m)

base = "| Name/GH | Week 0 | Week 1 |\n|---|---|---|\n| [A](u/a) | [U0](x) |  |\n"
ours = "| Name/GH | Week 0 | Week 1 |\n| --- | --- | --- |\n| [A](u/a) | [U0](x) | |\n"
theirs = "| Name/GH | Week 0 | Week 1 |\n|---|---|---|\n| [A](u/a) | [U0](x) | [U1](z) |\n"
m, c = merge(base, ours, theirs)
check("reformat vs fill no conflict", not c)
check("reformat keeps filled cell", "[U1](z)" in m)

base = "Intro line.\n\n| Name/GH | Week 0 |\n|---|---|\n| [A](u/a) |  |\n"
ours = "Intro line edited.\n\n| Name/GH | Week 0 |\n|---|---|\n| [A](u/a) |  |\n"
theirs = base
m, c = merge(base, ours, theirs)
check("prose edit kept", "Intro line edited." in m and not c)

print("\nALL TESTS PASSED")
