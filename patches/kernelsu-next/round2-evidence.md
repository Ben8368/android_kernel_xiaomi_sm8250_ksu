# M1 Round 2 evidence

Status: `M1 PARTIAL`. Linux 4.19 compatibility edits and real builds were
performed. The complete Image/modules/dtbs build is blocked in KSU SELinux
policy adaptation. This is not evidence of device root functionality.

## Fixed inputs

- Kernel repository base: `6b34d24765327d746074c8e53b5ad0d24a51acc7`
- Development branch: `lineage-24.0-ksu-v3`
- Official submodule: `KernelSU-Next` at
  `4c706b5938665866ebe16944a481a7b91e3396af` (v3.4.2)
- Protocol: UAPI 5, profile ABI 4. No dev/UAPI 6 content is included.
- Compiler: Android Clang r596125, clang 22.0.2,
  `de03d430485c884861198b25459851f429cbdbad`.
- Output: `/home/xiaoluo/umi-ksu-v3/out/m1-umi` on WSL ext4.
- Final `.config` SHA-256:
  `6273cbddbef733338225897ee1ccfe61ff52d7c9cbc04ecd8305ed2c9ef67673`
- KSU compatibility queue SHA-256:
  `6d0016650e17967105ccf7edb111dd6bf581b6ba3e8b319e7242dc06333a5807`

The final config has `CONFIG_KSU=y`, `CONFIG_KPROBES=y`, `CONFIG_THINLTO=y`,
`CONFIG_CFI=y`, `CONFIG_SECCOMP_FILTER=y`, `CONFIG_SECURITY_SELINUX=y`,
`CONFIG_USB_PD=y`, and `CONFIG_PPS=y`.

## Commands and results

`olddefconfig` completed with exit code 0. Its log is
`out/m1-round2/olddefconfig-final.log` (SHA-256
`8dbd6d1ed056df371056dc8817c0dae5945ff51f2b3bf7861df0ffde71c24936`).

The final full command was:

```sh
PATH=/home/xiaoluo/umi-ksu-stage2/toolchains/clang-r596125/bin:$PATH \
make -C /home/xiaoluo/umi-ksu-v3 \
  O=/home/xiaoluo/umi-ksu-v3/out/m1-umi \
  ARCH=arm64 LLVM=1 LLVM_IAS=1 -j8 Image modules dtbs
```

Exit code: 2. Full log: `out/m1-round2/full-build-final2.log`, SHA-256
`7599e8ca462e9682747e0ea40027f4991199aa66868111e92833c5b6595a8252`.
No final Image/modules/dtbs set or vmlinux link was produced.

Host contract checks passed with:

```sh
tests/m1/verify_round2.sh
```

This script checks wrapper dispatch contracts, patch state, scoped Seccomp
release references, and security configuration. It does not test runtime
Seccomp behavior, Root authorization, CFI, or SELinux enforcement.

## First remaining blocker

Linux 4.19 `security/selinux/include/security.h::struct selinux_state` stores
the active server in `ss`; `struct selinux_ss` owns `policydb`, `sidtab`,
`policy_rwlock`, and `latest_granting`. It does not have the modern
`policy_mutex`/RCU `policy` container. The actual 4.19 `policydb` also uses
different `avtab.htable`, filename-transition, and type-index representations.
The first compile diagnostics are in `KernelSU-Next/kernel/selinux/sepolicy.c`
and `rules.c`. Replacing just the pointer/lock names would be unsafe: policy
publication must atomically coordinate policydb, SID table, AVC generation,
selinuxfs readers, and rollback. Keep SELinux enabled and treat KSU SELinux
policy mutation and root credential transition as blocked until that adapter
is designed and tested against this exact security server.

## Initial 11 diagnostics

- `file_wrapper.c` eight diagnostics: iopoll is now field-probed; Linux 4.19
  clone dispatches through the source callback and dedupe through the
  destination callback; both wrapper endpoints are unwrapped; unsupported
  callbacks fail with `-EOPNOTSUPP`; open reference accounting includes the
  upstream `c7e66ae0315857e96a0b547503630e278f4bec7e` fix. Relevant objects
  compiled in real `drivers` builds.
- `seccomp_cache.c` three diagnostics: no 4.19 filter/action-cache layout is
  invented; cache APIs return `-EOPNOTSUPP`; ordinary App filters are not
  disabled. Manager reboot-cache handshake remains unverified and may be
  blocked by the filter.

Newer diagnostics: 4.19 mount UAPI header mismatch was fixed; task_work bool
notify, fsnotify callback prototype/mark teardown, missing filter_count, and
4.19 native Seccomp filter release were adapted. The later 4.19 SELinux policy
schema mismatch is the remaining hard compile blocker. Manager identity,
multi-user/UID reuse, persistence atomicity, 32-bit/execveat, credential commit
failure handling, and runtime CFI/SELinux/Seccomp remain M2 safety blockers.
