#!/usr/bin/env bash
# Complete-tree validation avoids false reverse-check failures for overlapping patches.
set -euo pipefail
root=$(cd "$(dirname "$0")/.." && pwd)
exec python3 "$root/tools/prepare-ksu.py"
