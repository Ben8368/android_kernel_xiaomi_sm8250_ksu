#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
BASE=4c706b5938665866ebe16944a481a7b91e3396af
SUB="$ROOT/KernelSU-Next"
PATCH="$ROOT/patches/kernelsu-next/0001-linux-4.19-compat.patch"

test "$(git -C "$SUB" rev-parse HEAD)" = "$BASE"
git -C "$SUB" apply --reverse --check "$PATCH"
python3 "$ROOT/tests/m1/test_file_wrapper_contract.py" "$SUB/kernel/infra/file_wrapper.c"
grep -q 'return -EOPNOTSUPP;' "$SUB/kernel/infra/seccomp_cache.c"
grep -q 'void ksu_seccomp_disable_current(void)' "$ROOT/include/linux/seccomp.h"
grep -q '__put_seccomp_filter(filter);' "$ROOT/kernel/seccomp.c"
grep -q 'CONFIG_THINLTO=y' "$ROOT/out/m1-umi/.config"
grep -q 'CONFIG_CFI=y' "$ROOT/out/m1-umi/.config"
grep -q 'CONFIG_SECCOMP_FILTER=y' "$ROOT/out/m1-umi/.config"
grep -q 'CONFIG_SECURITY_SELINUX=y' "$ROOT/out/m1-umi/.config"
grep -q 'CONFIG_USB_PD=y' "$ROOT/out/m1-umi/.config"
grep -q 'CONFIG_KSU=y' "$ROOT/out/m1-umi/.config"
echo "PASS: pinned base, replay state, compatibility contracts, protected config"
