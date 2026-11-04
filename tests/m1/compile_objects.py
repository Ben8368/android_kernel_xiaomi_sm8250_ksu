#!/usr/bin/env python3
"""Recompile exact affected translation units using preserved Kbuild commands.
Does not bypass a whole-kernel failure and does not replace final linking.
"""
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
import sys

root = Path(__file__).resolve().parents[2]
objtree = root / "out/m1-umi"
dest = Path(sys.argv[1]).resolve()
dest.mkdir(parents=True, exist_ok=False)
units = ["infra/file_wrapper", "infra/seccomp_cache", "infra/su_mount_ns", "hook/setuid_hook",
         "manager/pkg_observer", "policy/allowlist", "policy/app_profile", "sulog/event", "supercall/supercall"]
records = []
for unit in units + ["native-seccomp"]:
    native = unit == "native-seccomp"
    rel = Path(unit)
    cmdfile = objtree / ("kernel/.seccomp.o.cmd" if native else "KernelSU-Next/kernel" + "/" + str(rel.parent / ("." + rel.name + ".o.cmd")))
    template = False
    if not cmdfile.exists():
        cmdfile = objtree / "KernelSU-Next/kernel/infra/.file_wrapper.o.cmd"
        template = True
    tokens = shlex.split(cmdfile.read_text().splitlines()[0].split(":=", 1)[1].strip())
    assert "-flto=thin" in tokens and "-fsanitize=cfi" in tokens
    output = dest / (unit.replace("/", "-") + ".o")
    for i, token in enumerate(tokens):
        if token.startswith("-Wp,-MD,"):
            tokens[i] = "-Wp,-MD," + str(output.with_suffix(".d"))
    tokens[tokens.index("-o") + 1] = str(output)
    source = root / ("kernel/seccomp.c" if native else "KernelSU-Next/kernel/" + unit + ".c")
    tokens[-1] = str(source)
    if template:
        tokens = [t for t in tokens if not t.startswith("-DKBUILD_BASENAME=")]
        tokens.insert(1, '-DKBUILD_BASENAME="' + rel.name + '"')
    record = {"unit": unit, "command": tokens, "cwd": str(objtree), "template_cmdfile": str(cmdfile),
              "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest()}
    proc = subprocess.run(tokens, cwd=objtree, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    record["exit_code"] = proc.returncode
    log = output.with_suffix(".log")
    log.write_bytes(proc.stdout)
    record["diagnostics"] = proc.stdout.decode(errors="replace")
    record["output_sha256"] = hashlib.sha256(output.read_bytes()).hexdigest() if output.exists() else None
    print(unit, "exit", proc.returncode, record["output_sha256"], flush=True)
    if proc.returncode:
        print(record["diagnostics"], flush=True)
    records.append(record)
(dest / "results.json").write_text(json.dumps(records, indent=2) + "\n")
raise SystemExit(1 if any(r["exit_code"] for r in records) else 0)
