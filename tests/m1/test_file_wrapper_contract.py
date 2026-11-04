#!/usr/bin/env python3
"""Host-side contract checks for Linux 4.19 file wrapper adaptation."""

from pathlib import Path
import re
import sys

source = Path(sys.argv[1]).read_text()

def body(name):
    match = re.search(r"static int " + name + r"\([^)]*\)\s*\{(.*?)\n\}", source, re.S)
    assert match, f"missing function: {name}"
    return match.group(1)

clone = body("ksu_wrapper_clone_file_range")
dedupe = body("ksu_wrapper_dedupe_file_range")
assert "ksu_unwrap_file(file_in)" in clone
assert "ksu_unwrap_file(file_out)" in clone
assert "src->f_op->clone_file_range(src, pos_in, dst, pos_out, len)" in clone
assert "-EOPNOTSUPP" in clone and "-EXDEV" in clone
assert "ksu_unwrap_file(file_in)" in dedupe
assert "ksu_unwrap_file(file_out)" in dedupe
assert "dst->f_op->dedupe_file_range(src, pos_in, dst, pos_out, len)" in dedupe
assert "-EOPNOTSUPP" in dedupe
assert "#ifdef KSU_HAVE_FOP_IOPOLL" in source
assert "#ifdef KSU_HAVE_FOP_REMAP" in source
assert "fput(orig_file);" in source
assert "get_file(fp);" in source
print("PASS: callback direction, offsets, errors, refs, feature guards")
