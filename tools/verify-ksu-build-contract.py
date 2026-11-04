#!/usr/bin/env python3
"""Verify actual compiled manager trust/CFI flags and recorded artifact identity."""
import argparse, json, pathlib
from ksu_audit import ROOT, digest
ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',required=True,type=pathlib.Path);a=ap.parse_args();out=a.out
lock=json.loads((ROOT/'tools/ksu-userland.lock.json').read_text());p=json.loads((out/'provenance.json').read_text())
assert json.loads((out/'source-before.json').read_text())==p['source'],'pre/post source identity'
assert digest(out/'arch/arm64/boot/Image')==p['image_sha256'],'Image provenance mismatch'
assert digest(out/'vmlinux')==p['vmlinux_sha256'],'vmlinux provenance mismatch'
cmd=(out/'drivers/kernelsu/.apk_sign.o.cmd').read_text().splitlines()[0]
assert '-DEXPECTED_MANAGER_SIZE=0x3e6' in cmd and lock['certificate_sha256'] in cmd,'compiled Manager certificate differs from verified APK'
for flag in ['-flto=thin','-fsanitize=cfi','-fsanitize-cfi-cross-dso']:assert flag in cmd,flag
symbols=(out/'vmlinux-symbols.txt').read_text()
for sym in ['ksu_handle_prctl','ksu_task_prctl','escape_to_root','ksu_set_app_profile','ksu_handle_execve_sucompat','__arm64_sys_execve','__arm64_sys_execveat','__cfi_check']:
 assert any(line.split() and line.split()[-1]==sym for line in symbols.splitlines()),sym
print(json.dumps(dict(status='PASS',verifier_sha256=digest(pathlib.Path(__file__)),userland_lock_sha256=digest(ROOT/'tools/ksu-userland.lock.json'),built_source_commit=p['source']['custom_branch_sha'],image_sha256=p['image_sha256'],compiled_certificate_sha256=lock['certificate_sha256'],compiled_cfi=True,linked_ksu_paths_present=True,scope='artifact/static verification only, NOT runtime Root'),indent=2))
