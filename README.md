# Xiaomi SM8250 kernel — experimental KernelSU Next compatibility work

**EXPERIMENTAL / NOT RUNTIME VALIDATED / DO NOT FLASH.** This branch targets
Xiaomi Mi 10 (umi), Linux 4.19.325 and LineageOS 24.0. No stable release,
Android boot image or device verification is provided.

The upstream-tracking default branch lineage-24.0 remains unchanged at
6b34d24765327d746074c8e53b5ad0d24a51acc7. The experimental lineage-24.0-ksu
branch preserves the original integration history and replaces the v3.4.2
submodule pin with official v1.1.1 at
0d6bdc6364cbfc73517dcfdf7ab23b0ba8045553, plus an explicit auditable patch
queue in compat/kernelsu-next. This is a constrained alternative compile
candidate, not a recommendation to deploy an old release.

The v3.4.2 seccomp filter layout, mount API and file operations do not match
this 4.19 kernel. Official legacy's old-kernel seccomp-disable workaround is
not adopted. The candidate preserves inherited seccomp filters, keeps the su
SELinux domain enforcing, and retains Clang ThinLTO/CFI. Standard KernelSU
explicit policy rules still change Android policy. Root functionality and
security have not been validated on a device. Some app-origin root operations
may be blocked by the preserved syscall filters.

See [build report](docs/BUILD.md) for the actual complete build/link result,
config, artifact inventory, toolchain provenance, failed-attempt logs and
unresolved runtime limitations. The final fresh build uses official Android
Clang 22.0.2 / r596125, selected by LineageOS 24.0 cp2a release flags, with a
verified binary hash lock. The build script compiles Image, modules and dtbs;
DTB/DTBO intermediates are assembled using the pinned AOSP tool and public
LineageOS rules.

Initialize with git submodule update --init --recursive, then follow the
Clang build instructions in docs/BUILD.md. tools/prepare-ksu.sh applies the
tracked compatibility patches locally to the fixed upstream submodule;
that expected local submodule diff does not require an unpublished commit.
The old tools/check-umi-config.sh is only a GCC configuration diagnostic.

Stage 3 pins and cryptographically verifies the official non-spoofed v1.1.1
Manager (12851) and arm64 daemons, and adds protocol, bounds, provenance and
read-only boot format tests. The empty embed_ksud.c is not a daemon installer.
**Ordinary app su with the official daemon is unsupported under the retained
Android app Seccomp filter** (unconditional setgroups/setresgid). Manager's
prctl bootstrap remains an untested candidate, not working Root evidence.
Stage 4 replaces profile pointers/caches with immutable RCU records and snapshots,
and removes broad SELinux grants. Package identity, durable revocation, credential
hook context and complete target policy verification remain deployment blockers.

See [stage 3 results](docs/STAGE3-VALIDATION.md),
[userland audit](docs/KERNELSU-USERLAND.md),
[Root security](docs/ROOT-SECURITY.md), [boot format](docs/BOOT-FORMAT.md) and
[manual device test plan](docs/DEVICE-TEST-PLAN.md). No matching ROM Boot image
has been supplied; no phone operation is performed. Compilation, offline
protocol/cryptography, static security regressions and real-device results
are distinct: **device boot and device Root remain UNVERIFIED**. See [maintenance](docs/MAINTENANCE.md) for
manual maintenance constraints. PR #1 remains a draft; no CI, automatic sync,
release or flashing workflow is added.

Stage 4 conclusion: **NO-GO for ordinary-app general Root with the current
v1.1.1 direct-su architecture under the required unchanged App Seccomp.** The
official shell repeats blocked identity syscalls; avoiding those calls would
still leave mount/chroot/reboot and other operations filtered. No privileged IPC
service is added. Manager bootstrap is not ordinary-app Root evidence.

Patches 0009/0010 harden memory publication and remove 25 wildcard bootstrap
calls (including four unrestricted ioctl xperms). Only 22 source-reviewed kernel
metadata/store grants remain; root-only runtime policy injection is quarantined.
This limits functionality until a complete target policy is reviewed and is
**not a claim that the original Root goal was achieved**. LOS debug variants may
already mark su permissive; the patch explicitly requests an enforcing su domain.
Full ROM policy compilation/neverallow checks are still BLOCKED.

See [stage 4 results](docs/STAGE4-VALIDATION.md),
[Seccomp alternatives and service threat model](docs/SECCOMP-FEASIBILITY.md),
[permission matrix](docs/SELINUX-MATRIX.md) and the updated
[security audit](docs/ROOT-SECURITY.md). The readiness checker independently
reports compilation, offline compatibility, static security, target ROM policy,
exact Boot inputs, device boot and device Root. Missing evidence stays BLOCKED.
