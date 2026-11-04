#!/usr/bin/env python3
"""Accept only pristine base or the complete verified queue, never mixed edits."""
import io, subprocess, tarfile, tempfile, pathlib
from ksu_audit import ROOT, BASE, git, prove_sources
ksu=ROOT/'KernelSU-Next'
if git(ksu,'rev-parse','HEAD')!=BASE: raise SystemExit('Unexpected KernelSU revision')
try:
    proof=prove_sources(False)
except ValueError:
    if git(ksu,'status','--porcelain','--untracked-files=all'):
        raise SystemExit('Refusing partial/unknown KSU changes; audit them in a separate clean checkout')
else:
    print('Already applied: complete verified queue '+proof['patch_queue_sha256']);raise SystemExit(0)
patches=sorted((ROOT/'compat/kernelsu-next').glob('*.patch'))
# Validate the complete ordered queue before touching the pristine submodule.
archive=subprocess.check_output(['git','-C',str(ksu),'archive','HEAD','kernel'])
with tempfile.TemporaryDirectory(prefix='ksu-preflight-') as tmp:
    with tarfile.open(fileobj=io.BytesIO(archive)) as t:t.extractall(tmp,filter='data')
    subprocess.run(['git','init','-q',tmp],check=True)
    for p in patches:subprocess.run(['git','-C',tmp,'apply',str(p)],check=True)
for p in patches:
    subprocess.run(['git','-C',str(ksu),'apply',str(p)],check=True);print('Applied:',p.name)
proof=prove_sources(False);print('Verified complete queue:',proof['patch_queue_sha256'])
