#!/usr/bin/env bash
# Apply an audited patch queue to the immutable upstream submodule.
set -euo pipefail
root=$(cd "$(dirname "$0")/.." && pwd)
ksu="$root/KernelSU-Next"
expected=0d6bdc6364cbfc73517dcfdf7ab23b0ba8045553
[[ $(git -C "$ksu" rev-parse HEAD) == "$expected" ]] || { echo 'Unexpected KernelSU revision; initialize the pinned submodule first' >&2; exit 1; }
for patch in "$root"/compat/kernelsu-next/*.patch; do
 if git -C "$ksu" apply --reverse --check "$patch" 2>/dev/null; then
  printf 'Already applied: %s\n' "$patch"
 else
  git -C "$ksu" apply --check "$patch"
  git -C "$ksu" apply "$patch"
 fi
done
