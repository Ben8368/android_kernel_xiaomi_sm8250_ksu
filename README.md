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

Remaining limitations include an empty upstream embedded-daemon stub,
unvalidated matching userspace, old prctl ABI, unverified execveat coverage,
unavailable modern namespace profile modes and optional per-app unmount,
and no boot or runtime validation. See [maintenance](docs/MAINTENANCE.md) for
manual maintenance constraints. PR #1 remains a draft; no CI, automatic sync,
release or flashing workflow is added.
