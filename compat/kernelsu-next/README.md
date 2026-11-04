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

0003-check-signature-errors-as-integers.patch treats the integer return from
ksu_sha256 as an integer, rather than passing it to IS_ERR. Short certificate
reads are rejected. The host fault-injection harness extracts the real patched
check_block function and verifies success, mismatch, crypto errors, short/error
reads and oversized certificates. It is not a device authentication test.

0004-fix-declarations-and-syscall-argument-types.patch includes existing
apk_sign.h and linux/namei.h declarations, supplies a real int object to the
execve callback, and marshals raw prctl argument addresses with the kernel's
u64_to_user_ptr API. Access still goes through copy_to_user/copy_from_user.
It removes the old ext4 sysfs unregister action instead of importing a hiding
feature or declaring an unchecked external function.

0005-fix-boot-hook-argument-contracts.patch supplies actual fd parameter
objects, uses compat_ptr/u64_to_user_ptr for argv addresses, and corrects the
read-count pointer declaration. This repairs caller/callee contracts; it does
not suppress integer/pointer diagnostics or reinterpret seccomp structures.

0006-use-native-selinux-avc-declaration.patch includes avc_ss.h, which declares
the real two-argument avc_ss_reset implementation in this kernel, and decodes
u64 user ABI address fields with u64_to_user_ptr. AVC invalidation and all
user-copy checks remain active. SELinux core is untouched.

0007-keep-su-selinux-domain-enforcing.patch removes upstream's automatic
permissive marking for the su domain. Standard KSU explicit allow rules still
change Android policy; neither their adequacy nor runtime confinement has been
validated. This experiment does not silently exchange enforced domains for
permissive ones to gain compatibility.

0008-bound-authorization-inputs.patch bounds the 128-entry prctl list copy,
validates exact profile ABI, signed UID/group bounds and NUL termination,
rejects short/wrong-version persistent records and corrects the temporary
CAP_DAC_READ_SEARCH bit mask. New allowlist files use mode 0600. It does not
fix concurrency/lifetime, atomic persistence or SELinux wildcard policy.
See docs/ROOT-SECURITY.md for blockers and host-only test limitations.

Preparation now validates the entire final tree, so overlapping patches do
not break repeat invocation. Only pristine base or complete verified queue
are accepted; partial/unknown changes are refused without a reset. Expected
-dirty is retained and explained in provenance, not suppressed.

## Stage 4 hardening (NO-GO for general Root)

0009 publishes immutable RCU authorization records, returns caller-owned profile
snapshots, removes divergent UID caches, and bounds allocation/publication. Host
liburcu/ASan/UBSan regressions cover concurrent replacement/prune/read/save/free.
Package/Manager identity generations, durable revocation and credential-hook
context remain blockers; this is not a complete lifecycle security claim.

0010 removes 25 wildcard bootstrap calls (including four all-ioctl xperms),
retains 22 source-reviewed finite kernel metadata/store grants, explicitly
enforces su even when the ROM debug policy made it permissive, and quarantines
runtime policy injection. No working su/init/PTY/module policy is claimed.
See docs/SELINUX-MATRIX.md and docs/SECCOMP-FEASIBILITY.md.
