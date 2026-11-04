#!/usr/bin/env python3
"""Conservative deployment gate. Exit 2 means known blockers, not a test failure."""
import json, pathlib, sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
ksu=ROOT/'KernelSU-Next'
rules=(ksu/'kernel/selinux/rules.c').read_text();allow=(ksu/'kernel/allowlist.c').read_text();su=(ksu/'userspace/ksud_magic/src/su.rs').read_text()
block=(ROOT/'docs/validation/stage3/sources/bionic-SECCOMP_BLOCKLIST_APP.TXT').read_text()
blockers=[]
if 'set_thread_groups(' in su and 'setgroups(int,' in block:
    blockers.append(dict(id='official-su-seccomp',detail='Official ksud root_shell unconditionally calls setgroups/setresgid; target app policy blocks them. Ordinary app su unsupported; keep seccomp.'))
if 'ksu_allow(db, KERNEL_SU_DOMAIN, ALL, ALL, ALL)' in rules or 'ksu_allow(db, ALL, KERNEL_SU_FILE, ALL, ALL)' in rules:
    blockers.append(dict(id='selinux-wildcards',detail='Enforcing is not least privilege: upstream wildcard su/ksu_file grants still require replacement and target policy review.'))
if 'TODO: use RCU!' in allow:
    blockers.append(dict(id='allowlist-concurrency',detail='Unlocked readers/writers and pruning/freeing need a coherent synchronization redesign before treating authorization as safe.'))
blockers.extend([dict(id='missing-rom-bundle',detail='No exact LineageOS 24.0 umi target-files/boot/ramdisk/DTBO/vbmeta/recovery supplied or validated.'),dict(id='runtime-unverified',detail='No Android 17 manager recognition, live kprobe registration, boot, charging or root test.')])
print(json.dumps(dict(status='BLOCKED',manual_device_test_ready=False,blockers=blockers,scope='static conservative gate; no phone access'),indent=2))
sys.exit(2)
