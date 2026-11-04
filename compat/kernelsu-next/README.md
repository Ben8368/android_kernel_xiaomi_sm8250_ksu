# Audited Linux 4.19 candidate

Base: official KernelSU-Next v1.1.1, commit
0d6bdc6364cbfc73517dcfdf7ab23b0ba8045553 (2,651 commits at this tag;
upstream version formula gives 12851). This is an experimental alternative,
not a claim that this old release is maintained or safe for production.

The v3.4.2 source at 4c706b5938665866ebe16944a481a7b91e3396af
uses a seccomp filter layout absent in this kernel, and modern VFS operations.
An official legacy implementation skips cache operations below 5.10, but also
calls disable_seccomp(current) for manager/su-allowed app UIDs on old kernels.
That workaround is rejected under this experiment's security requirements.
The v1.1.1 prctl transport avoids the reboot/cache dependency entirely. It has
no modern su mount namespace mode API and cannot be used with a v3 manager by
assuming ABI compatibility. Use only matching userspace for future testing.

0001-deterministic-kbuild.patch removes build-time network access and automatic
source edits (including a synthetic seccomp filter_count member). It keeps the
upstream version number deterministic and retains type/implicit declaration
errors. Since 4.19 has no path_umount API, the optional per-app unmount feature
is unavailable; neither VFS nor SELinux is rewritten to enable it.

0002-preserve-seccomp-and-path-references.patch preserves all caller seccomp
filters even after an authorized su request, and releases the path reference
when unmount is unsupported. This is deliberately stricter than upstream
KernelSU: an app-created root session retains its app syscall restrictions.
Commands blocked by those filters may fail. Compilation cannot validate root
functionality or establish a replacement security policy. No cache bypass,
filter layout copy, filter_count imitation, or mount API declaration is added.

Apply with tools/prepare-ksu.sh; tools/build-umi.sh runs it automatically.
Patches live in the parent repository and are replayed against the immutable
submodule. The submodule's expected local changes are intentional, not an
unpublished submodule commit. Do not commit the patched submodule as a gitlink
to an unreachable local commit. To audit, use git -C KernelSU-Next diff and
compare it with this queue. Conflicting edits cause preparation to fail.

Upstream sources: the two pinned KernelSU commits; official tag
v3.4.0-legacy (kernel/infra/seccomp_cache.c, kernel/hook/setuid_hook.c,
kernel/compat/kernel_compat.c); LineageOS kernel
6b34d24765327d746074c8e53b5ad0d24a51acc7 (kernel/seccomp.c,
arch/arm64/kernel/ptrace.c, fs/namespace.c).
Full source links and validation results are recorded in docs/BUILD.md.
