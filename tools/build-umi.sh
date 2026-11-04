#!/usr/bin/env bash
# Standalone kernel verification using the LineageOS umi config fragments.
set -euo pipefail
root=$(cd "$(dirname "$0")/.." && pwd)
: "${CLANG_DIR:?Set CLANG_DIR to the pinned AOSP clang-r596125 directory}"
"$root/tools/prepare-ksu.sh"
CLANG_DIR=$(realpath "$CLANG_DIR")
out=$(realpath -m "${OUT_DIR:-$root/out/umi-clang}")
[[ "$out" != "$root" ]] || { echo 'Use a separate output directory' >&2; exit 1; }
export PATH="$CLANG_DIR/bin:$PATH"
export LC_ALL=C
export KBUILD_BUILD_USER=ksu-validation KBUILD_BUILD_HOST=wsl-ubuntu
export KBUILD_BUILD_TIMESTAMP='2026-11-04 00:00:00 UTC'
export KBUILD_BUILD_VERSION=1
mkdir -p "$out"
exec > >(tee -a "$out/build.log") 2>&1
printf 'START %s\n' "$(date -u +%FT%TZ)"
git -C "$root" rev-parse HEAD
git -C "$root" submodule status
clang --version
ld.lld --version
sha256sum "$CLANG_DIR/bin/clang" "$CLANG_DIR/bin/clang-real" "$CLANG_DIR/bin/ld.lld"
args=(-C "$root" O="$out" ARCH=arm64 LLVM=1 LLVM_IAS=1
      CLANG_TRIPLE=aarch64-linux-gnu- CROSS_COMPILE=aarch64-linux-gnu-
      CROSS_COMPILE_ARM32=arm-linux-gnueabi-)
run_make() { printf 'COMMAND:'; printf ' %q' make "${args[@]}" "$@"; printf '\n'; make "${args[@]}" "$@"; }
run_make vendor/kona-perf_defconfig
ARCH=arm64 "$root/scripts/kconfig/merge_config.sh" -m -O "$out" "$out/.config" \
 "$root/arch/arm64/configs/vendor/debugfs.config" \
 "$root/arch/arm64/configs/vendor/xiaomi/sm8250-common.config" \
 "$root/arch/arm64/configs/vendor/xiaomi/umi.config"
run_make olddefconfig
for symbol in MACH_XIAOMI_UMI KPROBES KSU LTO_CLANG CFI_CLANG SECCOMP SECCOMP_FILTER SECURITY_SELINUX; do
 grep -qx "CONFIG_$symbol=y" "$out/.config" || { echo "Required CONFIG_$symbol=y missing" >&2; exit 1; }
done
cp "$out/.config" "$out/config.before-build"
run_make -j"${JOBS:-6}" Image modules dtbs
if grep -RqE '^dtbo\.img[[:space:]]*:' "$root/arch/arm64" --include=Makefile; then
 run_make -j"${JOBS:-6}" dtbo.img
fi
cmp "$out/config.before-build" "$out/.config"
find "$out/arch/arm64/boot" -type f \( -name Image -o -name '*.dtb' -o -name '*.dtbo' -o -name dtbo.img \) -print0 | sort -z | xargs -0 -r sha256sum > "$out/artifacts.sha256"
test -s "$out/vmlinux" && test -s "$out/System.map" && test -s "$out/arch/arm64/boot/Image"
llvm-readelf -h "$out/vmlinux" > "$out/vmlinux-elf.txt"
llvm-nm "$out/vmlinux" > "$out/vmlinux-symbols.txt"
printf 'SUCCESS %s\n' "$(date -u +%FT%TZ)"
