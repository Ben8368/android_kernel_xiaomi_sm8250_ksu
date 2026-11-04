#!/usr/bin/env bash
# All checks run locally; never touches adb/fastboot or an Android device.
set -euo pipefail
root=$(cd "$(dirname "$0")/.." && pwd)
: "${KSU_ASSETS:?Set KSU_ASSETS to the pinned release download directory}"
python3 "$root/tools/prepare-ksu.py"
python3 "$root/tools/test-ksu-patch-replay.py"
python3 "$root/tools/test-ksu-source-proof.py"
python3 "$root/tools/test-ksu-signature-errors.py"
python3 "$root/tools/test-ksu-runtime-contract.py"
python3 "$root/tools/test-ksu-userland.py" --assets "$KSU_ASSETS"
python3 "$root/tools/test-umi-boot-format.py"
python3 - "$root" <<'PY'
import hashlib,json,pathlib,sys
root=pathlib.Path(sys.argv[1]);d=root/'docs/validation/stage3'
for item in json.loads((d/'sources.lock.json').read_text()):
 assert hashlib.sha256((d/'sources'/item['file']).read_bytes()).hexdigest()==item['sha256'],item['file']
print('PASS all pinned external source snapshots')
PY
set +e
python3 "$root/tools/check-ksu-readiness.py"
status=$?
set -e
[[ "$status" == 2 ]] || { echo 'Expected documented deployment blockers require re-audit'; exit 1; }
echo 'PASS readiness gate correctly reports BLOCKED (not permission to flash)'
