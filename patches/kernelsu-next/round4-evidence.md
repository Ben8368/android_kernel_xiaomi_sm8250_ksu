# M1 Round 4 evidence

Scope: Linux 4.19.325 SELinux avtab bucket compatibility only. Active policy publication and all policy mutation paths remain blocked and are not enabled by this patch.

## Changes

- Added `KernelSU-Next/kernel/selinux/avtab_compat.h` with flex_array bucket get/set, bucket iteration, and node transfer into a native avtab release table.
- Updated KSU avtab iteration and node removal to use the compatibility helpers; node/xperms destruction continues through Linux 4.19's native `avtab_destroy()`.
- Did not modify Linux SELinux structure layouts. Modern filename-transition and type-index writes remain unadapted.

## Verification

- `cc -std=gnu11 -Wall -Wextra -Werror -o out/m1-round3/avtab_compat_test tests/m1/avtab_compat_test.c && out/m1-round3/avtab_compat_test`: exit 0. The test includes the production helper header and checks empty/out-of-range buckets, single/multi-node iteration, head/middle detach, present/absent/repeated detach, allocation failure preserving source state, and xperms bit-array bounds.
- \`python3 tests/m1/extract_avtab_destroy_test.py\`: exit 0. The test extracts the exact target Linux 4.19 \`avtab_destroy()\` body, compiles it with tracked allocator counters, verifies regular-node and xperms frees, then calls destroy again to prove the native null-table guard prevents repeated frees.
- Insertion remains the target kernel's native \`avtab_insert_nonunique()\` path and was not reimplemented; the added tests exercise bucket access/traversal/detach and destruction, not a standalone insertion allocation test.
- Standard build: `make -C /home/xiaoluo/umi-ksu-v3 O=/home/xiaoluo/umi-ksu-v3/out/m1-umi ARCH=arm64 LLVM=1 LLVM_IAS=1 -j1 V=1 Image modules dtbs`: exit 2. First error in `KernelSU-Next/kernel/selinux/rules.c:54`: 4.19 `selinux_state` has no `policy_mutex`; subsequent errors reference missing `selinux_state.policy` and incomplete `struct selinux_policy`. Log: `out/m1-round2/m1-round4-avtab-compat.log`.
- Diagnostic keep-going build was started with `-k`; its terminal session ended with Hangup before the recorder emitted an exit file. The preserved log shows no errors in `avtab_compat.h` or the new avtab call sites. Later `sepolicy.c` errors are at filename-transition and type-index/attribute-map code (lines 574-729), not the avtab helpers. Log: `out/m1-round2/m1-round4-avtab-compat-keepgoing.log`.
- The retained config has `CONFIG_LTO_CLANG=y`, `CONFIG_CFI_CLANG=y`, `CONFIG_SECCOMP_FILTER=y`, and `CONFIG_SECURITY_SELINUX=y`; `CONFIG_SECURITY_SELINUX_DISABLE` is unset.

The full strategy publication path remains BLOCKED: active policy publication, transaction locking, SID table consistency, AVC generation/policyload notification, and rollback. No Root path is wired to unverified policy mutation.
