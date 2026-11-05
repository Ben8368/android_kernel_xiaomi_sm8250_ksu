#!/usr/bin/env python3
"""Rerun the actual Kbuild compiler command recorded in the round-four log."""
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parents[2]
log = root / "out/m1-round2/m1-round4-avtab-compat-keepgoing.log"
matches = [line.strip() for line in log.read_text().splitlines()
           if line.lstrip().startswith("clang ") and " -c -o " in line
           and line.rstrip().endswith("/selinux/sepolicy.c")]
assert len(matches) == 1, "expected exactly one recorded Kbuild compiler command"
print(matches[0], flush=True)
result = subprocess.run(matches[0], shell=True, cwd=root / "out/m1-umi")
sys.exit(result.returncode)
