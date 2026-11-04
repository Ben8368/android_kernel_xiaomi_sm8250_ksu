#!/usr/bin/env python3
"""Negative tests of provenance checks in disposable clones, not user sources."""
import pathlib, shutil, subprocess, tempfile
import ksu_audit as audit
ORIGINAL=audit.ROOT

def run(*args):subprocess.run(args,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
def reject(name):
    try:audit.prove_sources()
    except ValueError:print('PASS source proof rejects',name);return
    raise AssertionError('accepted '+name)
with tempfile.TemporaryDirectory(prefix='ksu-negative-proof-') as d:
    t=pathlib.Path(d);run('git','init','-q',str(t));shutil.copytree(ORIGINAL/'compat',t/'compat')
    k=t/'KernelSU-Next';run('git','clone','--shared','--quiet',str(ORIGINAL/'KernelSU-Next'),str(k))
    run('git','-C',str(k),'checkout','--quiet',audit.BASE)
    run('git','-C',str(t),'add','compat','KernelSU-Next')
    run('git','-C',str(t),'-c','user.name=Source proof test','-c','user.email=proof@example.invalid','commit','-qm','fixture')
    for patch in sorted((t/'compat/kernelsu-next').glob('*.patch')):run('git','-C',str(k),'apply',str(patch))
    audit.ROOT=t
    audit.prove_sources();print('PASS exact queue accepted in isolated clean parent checkout')
    target=k/'kernel/ksu.c';before=target.read_bytes();target.write_bytes(before+b'\n/* unexplained source */\n');reject('extra tracked source edit');target.write_bytes(before)
    extra=k/'kernel/unexplained.c';extra.write_text('/* extra file */\n');reject('extra untracked kernel file');extra.unlink()
    run('git','-C',str(k),'add','kernel/ksu.c','kernel/core_hook.c');reject('staged submodule changes');run('git','-C',str(k),'reset','--quiet','HEAD')
    f=t/'compat/kernelsu-next/README.md';before=f.read_bytes();f.write_bytes(before+b'\nmodified\n');reject('uncommitted parent source');f.write_bytes(before)
    audit.prove_sources();print('PASS source proof restored after all negative cases')
print('SCOPE: disposable host Git clones only; no phone access')
