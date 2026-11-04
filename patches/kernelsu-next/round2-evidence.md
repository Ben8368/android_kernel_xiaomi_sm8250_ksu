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


## Additional direct verification (2026-11-04)

`tests/m1/run.py` captures the direct child return code without shell pipelines,
refuses to overwrite evidence, and writes command, cwd, compiler SHA, source HEAD,
submodule diff SHA, patch SHA, config SHA and log SHA to a JSON record in
`out/m1-round2`. Earlier `targeted-final.exit` and `targeted-final2.exit`
were discovered to have invalid shell captures (`0` despite make Error 2).
They are retained as `.exit.invalid-shell-capture`, not counted as PASS.
The earlier `olddefconfig` shell wrapper failed after make had returned; use
`olddefconfig-final.exit` captured directly in Python instead.

Verified records:

- `clean-replay-v2.json`: exit 0, a fresh archive of the official commit plus
  the complete queue was compared with the live submodule: 438 regular files
  identical. First replay test failed because git apply inherited the parent
  repository root; the test was fixed to initialize an isolated repository.
  Both failed and successful logs remain preserved.
- `objects-direct.json`: exit 0; 9 KSU translation units plus native seccomp
  recompiled using preserved Kbuild command lines. Every command retains
  `-flto=thin` and `-fsanitize=cfi`. Sources, commands, outputs and individual
  return codes: `out/m1-round2/objects-direct-v1/results.json`.
- `host-semantics.json`: exit 0; extracted actual clone/dedupe/copy callbacks,
  4.19 cache branch and native seccomp detach helper compiled/run under host
  GCC with AddressSanitizer and UBSan. Source/output hashes are logged.
  These use mocked files/tasks and do not prove real FD lifetimes or races.

Compiler executable SHA-256:
`b50deb7c48633d03c02b15b6508d79768027e80422265d7a4a7f2f13d2f01d97`.

The downstream helper is built-in-only validated (`CONFIG_KSU=y`); no KSU LKM
loading, unloading or module export compatibility has been validated.
The upstream 786f73e6 mark-free fix is adapted via native 4.19
`fsnotify_destroy_group()`, which drains delayed mark free/SRCU itself.
Native detach already drops its group-list reference, so no additional
`freeing_mark` reference drop is installed. Queued task_work callback lifetime
and all observer allocation/registration rollback paths still need kernel
fault-injection tests. A failed task_work enqueue no longer scans inline while
holding fsnotify/rename locks; it warns instead. Stale Manager identity handling
on that failure is explicitly NOT established as fail-closed.

## Seccomp communication boundary

The native ARM64 `syscall_trace_enter()` in `arch/arm64/kernel/ptrace.c`
calls `secure_computing(NULL)` before `trace_sys_enter`. A filter denial of
`reboot` therefore prevents both the syscall trace dispatcher and the reboot
kprobe handler from being reached. Returning `-EOPNOTSUPP` from the cache API
does not fix that path and is not a communication PASS. No filter is removed
in the Manager/setuid cache call sites.

The official v3.4.2 Manager's `scan_driver_fd()` in
`manager/app/src/main/cpp/ksu.cc` scans `/proc/self/fd` and uses ioctl; it does
not need the reboot handshake when `ksu_handle_setresuid()` has already
successfully installed its authenticated Manager FD. That is a source-level
candidate communication path only: package/certificate identity, fd installation
success, close-on-exec and the ROM's ioctl filter policy remain unverified.
The official ksud also scans inherited descriptors, then falls back to
`SYS_reboot` if none exists. A filtered App without a valid inherited/session
FD still has a blocked path. Do not broaden filters for all Apps to solve it.
The native Seccomp helper is only called after the existing authorized root
profile credential commit; it cannot rescue the earlier denied handshake.
No changes were made to userspace protocol headers or UAPI version constants.

## Further link blockers already identified

Both `path_mount` and `path_umount` are referenced by KSU but are not defined
in the target kernel. The include correction in su_mount_ns only resolves a
compile error, not these linkage/API semantics. The target has do_mount and
ksys_umount with user-path lookup, security hooks, namespace ownership checks,
and mount/path reference consumption; casting kernel strings to user pointers
or omitting these checks is not an acceptable shim. These are mandatory future
link/namespace tasks alongside SELinux, not silently disabled features.
No vmlinux link has been reached, so further undefined symbols may follow.

## Required M2 safety gates (not completed)

1. Manager certificate and installation identity; fail closed on refresh failure.
2. UID reuse, uninstall/reinstall and Android multi-user authorization separation.
3. Concurrent authorization/profile query, mutation and revocation lifetime.
4. Groups/SELinux setup errors must abort, not still commit root creds; current
   upstream failure handling is NOT claimed safe by this compatibility work.
5. Atomic persistent updates, short-write/error checks, rollback and revocation ACK.
6. 32-bit compatibility and execveat dispatch, including CFI-correct signatures.
7. Kernel/Manager/ksud UAPI 5 and profile ABI 4 integration tests using pinned builds.
8. Actual ordinary-App and root-worker Seccomp behavior; negative reboot/ioctl
   policy tests and TSYNC/fork/exec races; no global filter suppression.
9. Real CFI and enforcing SELinux runtime tests, policy generation updates and AVC
   invalidation using the native latest_granting sequence (dev 48501dad semantics).
10. File reopen allocation failures, final fput/FD exhaustion, nested wrappers,
    async I/O and mmap lifetimes; observer registration rollback and queued work
    at shutdown. Host mocks are NOT replacements for these kernel tests.

Dev b462d4c1 was reviewed as hot-path logging cleanup, not an API adapter;
only new cache-unavailable messages are warn-once here. Full logging cleanup
was not transplanted. Dev 48501dad's generation fix is deliberately not copied
into a nonexistent modern policy container: native SS generation/publication
must be implemented together in the next SELinux adapter.


## Production configuration recreation

`production-config-replay.json` records an exit-0 fresh production configuration
build in a separate output directory. Recipe: vendor/kona-perf_defconfig,
then merge vendor/debugfs.config, vendor/xiaomi/sm8250-common.config and
vendor/xiaomi/umi.config, then olddefconfig. It reproduces the active build
`.config` byte for byte (SHA-256 recorded above). This preserves the original
full-build output and verifies both the production recipe and olddefconfig.
The WSL filesystem was checked with findmnt: ext4 on /dev/sdd, not /mnt/c.
Windows checkout was only read with git status: gen_headers_arm.bp,
gen_headers_arm64.bp and kernel_headers.py remain staged deletions.
