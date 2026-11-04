# Official build source snapshots (2026-11-04)

GitHub files are from the lineage-24.0 branch at the commits in revisions.json.
The source manifest's AOSP remote uses android-17.0.0_r1. Its Clang prebuilt
repository resolves to 29182889399818f97baa65ea238c80e8117981eb.

Toolchain selection follows vendor/lineage/build/envsetup.sh, which exports
LLVM_AOSP_PREBUILTS_VERSION from tools/get_clang_version.py. That script reads
vars/aosp_target_release (cp2a), then the vendor release flag before the AOSP
flag. The vendor cp2a flag selects clang-r596125. config/BoardConfigKernel.mk
uses that exported value in the absence of a device override. The umi and
sm8250-common BoardConfig files have no compiler override. Soong's default
clang-r584948 is consequently not the toolchain for this release.

Proprietary vendor BoardConfig was not available in this standalone checkout;
no unseen override in a complete vendor tree is claimed to have been checked.
This is an explicit reproducible standalone kernel build using the public
LineageOS device/release configuration, not a complete LineageOS ROM build.

Sources:
- https://github.com/LineageOS/android/tree/e4b71068f6ee045ff30e4865a8d82f4047eb78ea
- https://github.com/LineageOS/android_vendor_lineage/tree/528681ef98b8dee25ff9d8ca76cd9e2c4f4ba4ec
- https://github.com/LineageOS/android_device_xiaomi_sm8250-common/tree/b84fe80a52e7407c53119d2dd6507285da8090d4
- https://github.com/LineageOS/android_device_xiaomi_umi/tree/8e115b1ed63caa3ee5c3d52df0a7bce7c27512cd
- https://android.googlesource.com/platform/prebuilts/clang/host/linux-x86/+/29182889399818f97baa65ea238c80e8117981eb/clang-r596125/

DT image generation additionally uses the unmodified AOSP mkdtboimg.py from
platform/system/libufdt at 60546233f51d5eaceb9ca8837d1192539ccea1a1, resolved
from the same android-17.0.0_r1 tag. Its source URL and SHA-256 are in
tools/third_party/mkdtboimg.source.json. The wrapper validates all DTBO input
bytes after packing and checks the 4096-byte zero padding from the official
tool separately from the header total_size.
