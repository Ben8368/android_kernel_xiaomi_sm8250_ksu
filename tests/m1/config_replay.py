#!/usr/bin/env python3
"""Recreate the production umi config separately, preserving the build config."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
root = Path(__file__).resolve().parents[2]
out = Path(sys.argv[1]).resolve()
out.mkdir(parents=True, exist_ok=False)
make = ["make", "-C", str(root), "O=" + str(out), "ARCH=arm64", "LLVM=1", "LLVM_IAS=1"]
commands = [make + ["vendor/kona-perf_defconfig"],
            ["bash", str(root / "scripts/kconfig/merge_config.sh"), "-m", "-O", str(out), str(out / ".config"),
             "arch/arm64/configs/vendor/debugfs.config", "arch/arm64/configs/vendor/xiaomi/sm8250-common.config",
             "arch/arm64/configs/vendor/xiaomi/umi.config"],
            make + ["olddefconfig"]]
for command in commands:
    print("COMMAND:", json.dumps(command), flush=True)
    subprocess.run(command, cwd=root, check=True)
actual = (out / ".config").read_bytes()
expected = (root / "out/m1-umi/.config").read_bytes()
print("config_sha256", hashlib.sha256(actual).hexdigest(), "expected", hashlib.sha256(expected).hexdigest())
assert actual == expected, "production recipe no longer equals the build config"
print("PASS: fresh kona-perf + debugfs + sm8250-common + umi + olddefconfig matches build config byte for byte")
