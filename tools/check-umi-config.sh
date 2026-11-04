#!/usr/bin/env bash
# Exploratory GCC Kconfig check only; not a production kernel build.
set -euo pipefail
root=$(cd "$(dirname "$0")/.." && pwd)
out=${OUT_DIR:-$(mktemp -d)}
mkdir -p "$out"
cd "$root"
ARCH=arm64 scripts/kconfig/merge_config.sh -m -O "$out" \
 arch/arm64/configs/vendor/kona-perf_defconfig \
 arch/arm64/configs/vendor/debugfs.config \
 arch/arm64/configs/vendor/xiaomi/sm8250-common.config \
 arch/arm64/configs/vendor/xiaomi/umi.config
make O="$out" ARCH=arm64 CROSS_COMPILE="${CROSS_COMPILE:-aarch64-linux-gnu-}" olddefconfig
for symbol in KPROBES KSU EXT4_FS OVERLAY_FS SECURITY_SELINUX; do
 grep -qx "CONFIG_${symbol}=y" "$out/.config" || { echo "Missing CONFIG_${symbol}=y" >&2; exit 1; }
done
echo "Exploratory configuration passed: $out/.config (not a Clang/LTO build)"
