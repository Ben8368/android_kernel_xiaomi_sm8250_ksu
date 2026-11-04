#!/usr/bin/env python3
"""Replay the complete queue in a fresh archive; never modify the live submodule."""
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile

root = Path(__file__).resolve().parents[2]
sub = root / "KernelSU-Next"
base = "4c706b5938665866ebe16944a481a7b91e3396af"
dest = Path(sys.argv[1]).resolve()
dest.mkdir(parents=True, exist_ok=False)
assert subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=sub, text=True).strip() == base
archive = subprocess.check_output(["git", "archive", base], cwd=sub)
with tarfile.open(fileobj=io.BytesIO(archive)) as tf:
    tf.extractall(dest, filter="data")
# Isolate apply's repository root from the parent kernel worktree.
subprocess.run(["git", "init", "--quiet", str(dest)], check=True)
queue = root / "patches/kernelsu-next"
for name in (queue / "series").read_text().splitlines():
    if not name or name.startswith("#"):
        continue
    patch = queue / name
    for args in (["--check"], []):
        subprocess.run(["git", "apply", *args, str(patch)], cwd=dest, check=True)
files = subprocess.check_output(["git", "ls-tree", "-r", "--name-only", base], cwd=sub, text=True).splitlines()
files += ["kernel/infra/task_work_compat.h"]
manifest = {}
for name in sorted(set(files)):
    source, replay = sub / name, dest / name
    if not replay.is_file() or replay.is_symlink():
        continue
    expected, actual = source.read_bytes(), replay.read_bytes()
    assert expected == actual, f"replay differs: {name}"
    manifest[name] = hashlib.sha256(actual).hexdigest()
print(json.dumps({"base": base, "destination": str(dest), "archive_sha256": hashlib.sha256(archive).hexdigest(),
                  "compared_files": len(manifest), "manifest_sha256": hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()}, indent=2))
print("PASS: clean official archive + complete queue equals live submodule files")
