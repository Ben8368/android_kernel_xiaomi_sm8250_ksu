#!/usr/bin/env python3
"""Record pre/post build source identity; fail on unaccounted source changes."""
import argparse, json, pathlib, subprocess
from ksu_audit import ROOT, prove_sources, digest
ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',required=True,type=pathlib.Path);ap.add_argument('--clang',required=True,type=pathlib.Path);ap.add_argument('--phase',choices=['before','after'],required=True)
a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
source=prove_sources(); before=a.out/'source-before.json'
if a.phase=='before':
    if (a.out/'vmlinux').exists(): raise SystemExit('Refusing provenance claim for a reused build output')
    before.write_text(json.dumps(source,indent=2)+'\n');print(json.dumps(source,indent=2));raise SystemExit(0)
if source!=json.loads(before.read_text()): raise SystemExit('source changed during build')
report=dict(source=source,clang=subprocess.check_output([str(a.clang/'bin/clang'),'--version'],text=True),clang_sha256=digest(a.clang/'bin/clang-real'),toolchain_lock_sha256=digest(ROOT/'tools/umi-toolchain.lock.json'),kernel_release=(a.out/'include/config/kernel.release').read_text().strip(),config_sha256=digest(a.out/'.config'),image_sha256=digest(a.out/'arch/arm64/boot/Image'),vmlinux_sha256=digest(a.out/'vmlinux'),scope='build provenance, NOT device runtime verification')
(a.out/'provenance.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
