# umi / Linux 4.19.325 — stage two

This branch is an experimental compile-validation candidate, not a stable or
flash-ready release. Runtime support is not established. v3.4.2 was rejected
for this target under the requirement to preserve seccomp. The candidate pins
official KernelSU-Next v1.1.1 plus the separately maintained compatibility queue
in [compat/kernelsu-next](../compat/kernelsu-next/README.md).

## Diagnosis and implementation

| Issue | Source finding | Disposition |
| --- | --- | --- |
| Seccomp filter layout | kernel/seccomp.c owns a private struct with usage/log/prev/prog; no action_cache or native/compat allow bitmaps. seccomp_run_filters evaluates BPF directly. | Never define SECCOMP_ARCH_NATIVE_NR or copy a modern filter layout into 4.19. |
| Cache mutation | v3.4.2 sets ALLOW bits for reboot in manager/su-app handling. This is not needed for correctness of native 4.19 seccomp, and skipping it cannot guarantee KSU communication. arm64 syscall_trace_enter runs secure_computing before trace_sys_enter. | Use the official v1.1.1 prctl transport. Preserve existing seccomp filters for ALL tasks, including authorized su sessions. |
| Official legacy workaround | v3.4.0-legacy guards cache code at 5.10, but disables seccomp for manager/su-allowed UIDs below that threshold. | Rejected: ordinary app filters must not be removed to gain compatibility. |
| Mount header | Linux 4.19 defines MS_PRIVATE/MS_REC in include/uapi/linux/fs.h; uapi/linux/mount.h is genuinely absent. | No dummy header. The alternative version does not use the modern mount namespace profile API. |
| Mount implementation | path_mount is absent from this kernel. do_mount resolves a user path then performs LSM/capability/propagation checks. A prototype cannot supply the missing implementation. | No fake declaration or type cast. New mount namespace profile modes remain unsupported. A future port needs a reviewed real VFS refactor preserving all checks. |
| Legacy path_mount shim | Official legacy kernel_compat.c converts d_path back to do_mount under set_fs(KERNEL_DS). | Not adopted. A path-to-string/relookup bridge is not a substitute for auditing path identity, cwd/root semantics and concurrency. |
| Additional v3.4.2 VFS errors | Full-tree diagnostic fails in infra/file_wrapper.c: file_operations lacks iopoll/remap_file_range; REMAP_FILE_DEDUP is absent. | Complete diagnostic log retained. This is a broader backport, not a two-header fix. |
| SELinux flask.h | Full-tree build generates security/selinux/flask.h and av_permissions.h normally. Existing KSU include paths find generated headers. | No changes to SELinux core. The previous direct-subdirectory failure was not a valid full-build result. |
| v1.1.1 automatic edits | Upstream Makefile performs git fetch and sed edits of VFS/seccomp, including a dummy filter_count. | Patch 0001 removes these side effects and fixes the upstream version number at 12851. |
| Optional old per-app unmount | No native path_umount in 4.19. | No VFS injection. Return EOPNOTSUPP and release the looked-up path reference. This optional feature is unavailable. |

The kernel submodule remains at an official reachable upstream commit:
0d6bdc6364cbfc73517dcfdf7ab23b0ba8045553. The parent tracks the patch queue;
preparation applies them locally, so a dirty submodule after preparation is
expected. It does not depend on an unpublished local submodule commit.

The final patch also removes upstream's automatic permissive marking for the
su SELinux domain. Explicit KSU policy allow rules remain; their runtime
security properties have not been verified.

This is a security-constrained candidate: root credentials do not erase an
inherited app seccomp filter. App-origin root commands may therefore be denied
by the filter. Do not describe this as full runtime compatibility. v1.1.1 also
predates later upstream fixes; no production security endorsement is made.
Its active kprobe configuration hooks SYS_EXECVE_SYMBOL (__arm64_sys_execve);
coverage of userspace that uses execveat is not established. The presence of
execveat helper functions does not prove that the active kprobe invokes them.
Its checked-in embed_ksud.c is an empty CI stub. A matching verified userspace
and real daemon integration remain necessary before any device test. Do not
assume that a v3.4.2 manager speaks this older prctl ABI.

## Official toolchain provenance

Public LineageOS 24.0 source selection was checked on 2026-11-04. Immutable
source commits and snapshots are in [validation/stage2/sources](validation/stage2/sources/README.md).

1. android/default.xml: AOSP remote at android-17.0.0_r1, Clang host prebuilts.
2. vendor/lineage/vars/aosp_target_release: cp2a.
3. vendor/lineage/tools/get_clang_version.py chooses the vendor release flag first.
4. release/flag_values/cp2a/RELEASE_BUILD_CLANG_VERSION.textproto: clang-r596125.
5. envsetup.sh exports this as LLVM_AOSP_PREBUILTS_VERSION;
   config/BoardConfigKernel.mk uses it when there is no device override.
6. umi and sm8250-common public BoardConfig files contain no compiler override.

AOSP prebuilts commit: 29182889399818f97baa65ea238c80e8117981eb.
Compiler: Android Clang 22.0.2 (r596125, build 15071444), LLVM source
 de03d430485c884861198b25459851f429cbdbad; linker LLD 22.0.2.
The lock in tools/umi-toolchain.lock.json records upstream Git blob IDs and
SHA-256 hashes. Individual binaries are fetched from that fixed commit and
verified. Resource headers come from its fixed Gitiles archive. The build
script verifies pinned file hashes before make.

Soong's generic default clang-r584948 is overridden by cp2a. The earlier full
v3.4.2 build with r584948/Clang 22.0.0 is explicitly diagnostic and not the
formal toolchain result. Its log is v3.4.2-clang22-full-build.log. The initial
whole-toolchain archive was truncated; the formal r596125 download uses
individually verified Git blobs instead.

This standalone build uses Ubuntu host utilities and in-tree DTC, not the
complete AOSP hermetic host environment. Proprietary vendor BoardConfig was
not present; unseen overrides in a full vendor tree were not checked. No ROM
or boot/recovery/vendor_boot packaging is asserted.

## Reproduce in WSL Ubuntu

Run in /home/xiaoluo/umi-ksu-work-20261104 (or a Linux clone of this branch):

```bash
git submodule update --init --recursive
python3 tools/fetch-umi-toolchain.py \
  --destination /home/xiaoluo/umi-ksu-stage2/toolchains/clang-r596125
CLANG_DIR=/home/xiaoluo/umi-ksu-stage2/toolchains/clang-r596125 \
OUT_DIR=/home/xiaoluo/umi-ksu-stage2/build-final JOBS=8 \
  tools/build-umi.sh
```

The script configures vendor/kona-perf_defconfig, merges vendor/debugfs.config,
vendor/xiaomi/sm8250-common.config and vendor/xiaomi/umi.config in device order,
then runs olddefconfig. The full build command is:

```bash
make -C /home/xiaoluo/umi-ksu-work-20261104 \
  O=/home/xiaoluo/umi-ksu-stage2/build-final ARCH=arm64 LLVM=1 LLVM_IAS=1 \
  CLANG_TRIPLE=aarch64-linux-gnu- CROSS_COMPILE=aarch64-linux-gnu- \
  CROSS_COMPILE_ARM32=arm-linux-gnueabi- -j8 Image modules dtbs
```

Target GCC paths supply only explicit compatibility prefixes; LLVM=1 and LLVM_IAS=1 select Clang/LLVM tools. No GCC target objects are used. LTO/CFI remain enabled; no security setting is
removed to get past compiler errors. Build output and evidence are kept
outside the source tree. The script then assembles dtb.img by sorted concatenation and dtbo.img with
the fixed AOSP mkdtboimg.py using the public LineageOS kernel.mk rules. The
DTBO header, page padding and all 12 embedded entries are validated. The
33,554,432-byte DTBO partition limit is checked. These are intermediate DT
artifacts; no Android boot image is built.

No CI, scheduled synchronization, release workflow, flash script, SUSFS or
additional root-hiding feature is introduced. The former ext4 sysfs hiding
callback is removed. Optional old per-app unmount is unavailable.

## Verification result

The authoritative full build completed on 2026-11-04 with all seven patches
applied before configuration, from an empty
`/home/xiaoluo/umi-ksu-stage2/build-final` output directory. It used Android
Clang 22.0.2 r596125 (build 15071444; LLVM source
`de03d430485c884861198b25459851f429cbdbad`) and LLD 22.0.2. The command and
environment are captured in `final-clean-build.log`; pinned compiler hashes
are in `tools/umi-toolchain.lock.json`.

The full `Image modules dtbs` invocation exited 0 with no compiler warnings or
errors. Final verification reports an AArch64 ELF64 relocatable kernel,
zero unresolved strong symbols, and verified ThinLTO/CFI compiler flags.
Kernel release: `4.19.325-cip136-st20-perf-g72230f2635c1-dirty`.
Config SHA-256:
`cd083b1ff199fa679236ba82edd9ce9b270e2a1d39ce5379da5ce44b9e00889c`.

Generated output includes `vmlinux` (685,507,168 bytes; SHA-256
`61883b4ff297f1c7568948f1125fe806022dc9cc4e548813331279d03963b939`),
arm64 `Image` (SHA-256
`b0c8a0aec72955154315ae85214f228083a332d68fafdad2b67b730727845dc2`),
3 base DTBs, 12 DTBOs, assembled `dtb.img` (1,424,944 bytes), `dtbo.img`
(5,705,728 bytes), and 3 loadable modules. DTBO has 12 validated entries
and fits the 32 MiB partition limit. Exact sizes and hashes are recorded in
`docs/validation/stage2/final-verification.json`, `final-artifacts.sha256`
and `final-dt-package-verification.json`, alongside ELF and symbol evidence.

Key config retains `CONFIG_LTO=y`, `CONFIG_THINLTO=y`, `CONFIG_CFI=y`,
`CONFIG_CFI_CLANG=y`, `CONFIG_CFI_CLANG_SHADOW=y`, `CONFIG_SECCOMP=y`,
`CONFIG_SECCOMP_FILTER=y`, `CONFIG_SECURITY_SELINUX=y`, and
`CONFIG_DEFAULT_SECURITY_SELINUX=y`. `CFI_PERMISSIVE`, SELinux disable and
bootparam options, and `KSU_DEBUG` are unset. See `final-key-config.txt` and
the complete `final.config` for the exact result.

This establishes compile and link integrity only. No device boot, root command,
AVC policy behavior, or runtime Seccomp/SELinux enforcement test was performed.
Seccomp filters remain active for su-originated commands; those commands may
be restricted. Matching userspace is not integrated (`embed_ksud.c` is an
empty stub), and no v3 manager ABI compatibility is claimed. Modern mount
namespace profiles and optional `path_umount` behavior are unavailable.
Do not treat these binaries as stable or flash-ready.

`docs/validation/stage2/README.md` indexes the complete logs, source audit,
patch replay, tests and generated evidence. The earlier successful six-patch
build is retained as history, not as the final acceptance result.

## Error-to-fix audit trail

All steps were full-tree Image/modules/dtbs invocations. The failed formal
attempts and continuations share build-v111; the final build uses a separate
new, empty build-final directory with all seven patches applied before make.
No GCC objects or objects from the Clang 22.0.0 diagnostic tree were reused.
An intermediate clean rebuild was deliberately stopped when the final su
enforcing change was added; its partial output is not the final result.

| Attempt | Actual error / reason | Fix commit | Regression evidence |
| --- | --- | --- | --- |
| v3.4.2 diagnostic | Missing modern file_operations members and REMAP_FILE_DEDUP; separate previous diagnostics also identify seccomp cache/header failures | 0e8573365 chooses official prctl-based candidate; 82c93c2f4 supplies replayable patches | v3.4.2-clang22-full-build.log; full formal candidate build |
| Formal attempt 1 | IS_ERR incorrectly receives integer crypto return | f55b25a96 | Seven injected signature/error cases; formal rebuild |
| Formal attempt 2 | Missing real declarations; int supplied for int pointer; raw syscall register address supplied to user-copy APIs; unwanted ext4 sysfs unregister action | ff1fec1e8 | Real headers, native user address APIs, actual parameter object; formal rebuild |
| Formal attempt 3 | fd, argv and read-count argument contracts in ksud hooks | 2785125d0 | Correct typed objects/pointer declaration and native compat address API; formal rebuild |
| Formal attempt 4 | Missing real avc_ss_reset declaration; raw SELinux ABI address fields | 5fb826929 | Include native avc_ss.h and retain actual two-argument function, full rebuild |
| SELinux su enforcement | Upstream automatically marks the su domain permissive | eca4a0cb3 | Final fresh full build; verifier rejects automatic permissive call |
| Reproducibility | Do not let a caller silently substitute a compiler with the same name | 113df8910 | SHA-256 lock checked before configuration |

All seven patches also replayed onto a fresh archive of the official v1.1.1
kernel sources and reproduced the seven modified working files byte-for-byte.
Effective KernelSU source passes git diff --check. Patch files themselves
contain unified-diff context prefixes and are not standalone C source.

## Upstream source references

- https://github.com/KernelSU-Next/KernelSU-Next/tree/4c706b5938665866ebe16944a481a7b91e3396af/kernel
- https://github.com/KernelSU-Next/KernelSU-Next/tree/8af3d4fec33be32fa5d3f8dae4f380fac45bf2cd/kernel
- https://github.com/KernelSU-Next/KernelSU-Next/tree/0d6bdc6364cbfc73517dcfdf7ab23b0ba8045553/kernel
- https://github.com/LineageOS/android_kernel_xiaomi_sm8250/blob/6b34d24765327d746074c8e53b5ad0d24a51acc7/kernel/seccomp.c
- https://github.com/LineageOS/android_kernel_xiaomi_sm8250/blob/6b34d24765327d746074c8e53b5ad0d24a51acc7/fs/namespace.c
- https://github.com/LineageOS/android_kernel_xiaomi_sm8250/blob/6b34d24765327d746074c8e53b5ad0d24a51acc7/arch/arm64/kernel/ptrace.c

## Stage 3 source/provenance changes

The historical build above predates patch 0008. New builds require committed
parent sources, a fresh output directory, exact whole-queue source proof and
pre/post source identity. tools/build-umi.sh now invokes linked verification
and creates provenance.json with upstream/custom/KSU SHAs, queue/toolchain
hashes and final Image SHA-256. See STAGE3-VALIDATION.md for new evidence.
Expected patch-induced -dirty is not hidden. Official matching v1.1.1 assets
are now pinned and verified offline; no device userland deployment occurred.

## Stage 4 regression build

The final fresh checkout at 1a8fe03c7a70e9d559a14aaebbc8acde615a4ea2 builds Image/modules/dtbs
with pinned Clang r596125/22.0.2, unchanged ThinLTO/CFI/Seccomp/SELinux, exit 0.
Image SHA-256: f2b60e45ca862ef001e9afcc78b8c7e6b568f65852feea36c6cbbf1a2946872d.
The native tree, including charging/touch/fingerprint/Wi-Fi drivers, matches
stage-3 HEAD exactly. See [stage 4](STAGE4-VALIDATION.md) for both raw build
consoles, source/queue/artifact hashes, the launcher's initial missing-exit
record, final direct exit capture and offline regressions. Two fresh builds
have different Image hashes; no byte-for-byte reproducibility claim is made.
Current direct-su architecture remains NO-GO for ordinary-app general Root
under retained App Seccomp. Compile success is not a policy or device result.
