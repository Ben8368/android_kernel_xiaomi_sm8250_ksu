#!/usr/bin/env python3
"""Record real child return codes, exact commands and immutable build inputs."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parents[2]
p = argparse.ArgumentParser()
p.add_argument("--label", required=True)
p.add_argument("--compiler-dir", default="/home/xiaoluo/umi-ksu-stage2/toolchains/clang-r596125/bin")
p.add_argument("command", nargs=argparse.REMAINDER)
a = p.parse_args()
command = a.command[1:] if a.command[:1] == ["--"] else a.command
assert command, "no child command"
assert "/" not in a.label and a.label not in (".", "..")
out = root / "out/m1-round2"
out.mkdir(parents=True, exist_ok=True)
log = out / (a.label + ".log")
assert not log.exists(), f"refusing to overwrite {log}"
env = os.environ.copy()
env["PATH"] = a.compiler_dir + ":/usr/bin:/bin"
def git(*args, cwd=root):
    return subprocess.check_output(["git", *args], cwd=cwd, text=True).strip()
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
inputs = {"kernel_head": git("rev-parse", "HEAD"), "branch": git("branch", "--show-current"),
          "parent_status": git("status", "--short"),
          "gitlink": git("ls-files", "--stage", "KernelSU-Next"),
          "submodule_head": git("rev-parse", "HEAD", cwd=root / "KernelSU-Next"),
          "submodule_diff_sha256": hashlib.sha256(subprocess.check_output(["git", "diff", "HEAD"], cwd=root / "KernelSU-Next")).hexdigest(),
          "patch_sha256": sha(root / "patches/kernelsu-next/0001-linux-4.19-compat.patch"),
          "config_sha256_before": sha(root / "out/m1-umi/.config")}
record = {"cwd": str(root), "command": command, "PATH": env["PATH"], "inputs": inputs,
          "compiler_version": subprocess.check_output([a.compiler_dir + "/clang", "--version"], text=True),
          "compiler_sha256": sha(Path(a.compiler_dir) / "clang"),
          "start_utc": datetime.datetime.now(datetime.timezone.utc).isoformat()}
with log.open("wb") as f:
    rc = subprocess.run(command, cwd=root, env=env, stdout=f, stderr=subprocess.STDOUT).returncode
record.update({"exit_code": rc, "end_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
               "log_sha256": sha(log), "config_sha256_after": sha(root / "out/m1-umi/.config")})
(out / (a.label + ".exit")).write_text(str(rc) + "\n")
(out / (a.label + ".json")).write_text(json.dumps(record, indent=2) + "\n")
print(json.dumps(record, indent=2))
raise SystemExit(rc)
