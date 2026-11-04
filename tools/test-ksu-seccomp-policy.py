#!/usr/bin/env python3
"""Inspect pinned LOS generator inputs and demonstrate host filter inheritance.

No Android policy/BPF is changed. The host fixture adds a restrictive filter to
disposable children only. It is not an Android 17 execution or Root test.
"""
import hashlib, importlib.util, json, pathlib, re, signal, subprocess, sys, tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
d = ROOT / 'docs/validation/stage4'
for entry in json.loads((d / 'sources.lock.json').read_text()):
    data = (d / 'sources' / entry['file']).read_bytes()
    if hashlib.sha256(data).hexdigest() != entry['sha256']:
        raise ValueError('source snapshot changed: ' + entry['file'])
    blob = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
    if blob != entry['git_blob']:
        raise ValueError('upstream Git blob mismatch: ' + entry['file'])
sys.path.insert(0, str(d / 'sources'))
spec = importlib.util.spec_from_file_location('los_genseccomp', ROOT / 'docs/validation/stage3/sources/bionic-genseccomp.py')
gen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gen)
base = ROOT / 'docs/validation/stage3/sources'
for arch in ['arm64', 'arm']:
    names = gen.load_syscall_names_from_file(str(base / 'bionic-SYSCALLS.TXT'), arch)
    allowed, blocked = set(), set()
    for kind in ['COMMON', 'APP']:
        allowed |= gen.load_syscall_names_from_file(str(base / f'bionic-SECCOMP_ALLOWLIST_{kind}.TXT'), arch)
        blocked |= gen.load_syscall_names_from_file(str(base / f'bionic-SECCOMP_BLOCKLIST_{kind}.TXT'), arch)
    final = gen.merge_names(names, allowed, blocked)
    for name in ['setgroups' if arch == 'arm64' else 'setgroups32', 'setresgid' if arch == 'arm64' else 'setresgid32', 'mount', 'umount2', 'chroot', 'reboot']:
        if name in final:
            raise AssertionError(f'{arch}: unexpectedly allowed {name}')
    if 'prctl' not in final or ('setresuid' if arch == 'arm64' else 'setresuid32') not in final:
        raise AssertionError('expected Zygote/bootstrap syscalls absent')
    print('PASS pinned LOS generator merge:', arch, 'identity and privileged operations excluded; prctl/setresuid retained')
z = (d / 'sources/zygote.cpp').read_text()
start = z.index('if (setresgid(gid, gid, gid)')
end = z.index('if (setresuid(uid, uid, uid)', start)
if 'SetUpSeccompFilter(uid, is_child_zygote)' not in z[start:end]:
    raise AssertionError('Zygote filter installation order changed')
if 'SECCOMP_RET_TRAP' not in (base / 'bionic-seccomp_policy.cpp').read_text():
    raise AssertionError('blocked syscall action changed')
su = (ROOT / 'KernelSU-Next/userspace/ksud_magic/src/su.rs').read_text()
grant = su[su.index('pub fn grant_root('):su.index('fn print_usage(')]
if 'ksu_grant_root()' not in grant or 'set_identity(' in grant:
    raise AssertionError('Manager bootstrap path changed')
if 'set_identity(uid, gid, &groups)' not in su or 'set_thread_groups(' not in su or 'set_thread_res_gid(gid, gid, gid)' not in su:
    raise AssertionError('official ordinary su path changed')
print('PASS Zygote sets groups/GID before filtering and UID after; official su repeats blocked identity syscalls; Manager bootstrap differs')
c = r'''
#define _GNU_SOURCE
#include <stddef.h>
#include <stdio.h>
#include <unistd.h>
#include <sys/prctl.h>
#include <sys/syscall.h>
#include <linux/filter.h>
#include <linux/seccomp.h>
#include <string.h>
int main(int argc,char**argv){
 if(argc==1 || strcmp(argv[1],"child")){
  struct sock_filter f[]={BPF_STMT(BPF_LD|BPF_W|BPF_ABS,offsetof(struct seccomp_data,nr)),
   BPF_JUMP(BPF_JMP|BPF_JEQ|BPF_K,SYS_setgroups,0,1),
   BPF_STMT(BPF_RET|BPF_K,SECCOMP_RET_TRAP),BPF_STMT(BPF_RET|BPF_K,SECCOMP_RET_ALLOW)};
  struct sock_fprog p={.len=4,.filter=f};
  if(prctl(PR_SET_NO_NEW_PRIVS,1,0,0,0)||prctl(PR_SET_SECCOMP,SECCOMP_MODE_FILTER,&p))return 10;
  if(argc>1 && !strcmp(argv[1],"exec")){execl(argv[0],argv[0],"child",NULL);return 11;}
 }
 if(prctl(PR_GET_SECCOMP,0,0,0,0)!=2)return 12;
 syscall(SYS_setgroups,0,NULL);return 13;
}
'''
with tempfile.TemporaryDirectory(prefix='ksu-seccomp-inherit-') as tmp:
    tmp = pathlib.Path(tmp)
    (tmp / 'fixture.c').write_text(c)
    subprocess.run(['gcc', '-Wall', '-Werror', str(tmp / 'fixture.c'), '-o', str(tmp / 'fixture')], check=True)
    for args in [[], ['exec']]:
        result = subprocess.run([str(tmp / 'fixture'), *args])
        if result.returncode != -signal.SIGSYS:
            raise AssertionError(('expected SIGSYS, .ok() cannot catch TRAP', args, result.returncode))
print('PASS disposable host children receive SIGSYS before/after execve; .ok() cannot turn TRAP into a normal syscall error')
print('SCOPE: source generator merge and host inheritance only; exact-ROM generated filters and Android execution remain BLOCKED')
