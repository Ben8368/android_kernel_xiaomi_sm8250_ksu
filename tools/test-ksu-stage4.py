#!/usr/bin/env python3
"""Run existing and new host regressions and retain inspectable bound results.

Write outputs outside the checkout during execution so the existing clean-source
checks remain meaningful. Copy results into docs/validation/stage4 afterwards.
"""
import argparse
import json
import os
import pathlib
import subprocess
import sys
from ksu_audit import ROOT, digest, git
from ksu_readiness import current_inputs

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--out', required=True, type=pathlib.Path)
parser.add_argument('--assets', default=os.environ.get('KSU_ASSETS'))
args = parser.parse_args()
out = args.out.resolve()
if out.is_relative_to(ROOT.resolve()):
    raise SystemExit('Use an external result directory during the clean-source suite')
if not args.assets:
    raise SystemExit('Set --assets or KSU_ASSETS to the pinned release directory')
out.mkdir(parents=True, exist_ok=True)
before = current_inputs()
tests = [
    ('stage3-suite', ['bash', 'tools/test-ksu-stage3.sh']),
    ('allowlist-concurrency', [sys.executable, 'tools/test-ksu-allowlist-concurrency.py']),
    ('seccomp-policy', [sys.executable, 'tools/test-ksu-seccomp-policy.py']),
    ('selinux-surface', [sys.executable, 'tools/test-ksu-selinux-surface.py']),
    ('readiness-negative', [sys.executable, 'tools/test-ksu-readiness.py']),
    ('protected-native-tree', [sys.executable, 'tools/test-ksu-native-scope.py']),
    ('build-evidence-negative', [sys.executable, 'tools/test-ksu-build-evidence.py']),
]
env = dict(os.environ, KSU_ASSETS=str(pathlib.Path(args.assets).resolve()))
results = []
for name, command in tests:
    path = out / (name + '.log')
    with path.open('wb') as log:
        result = subprocess.run(command, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
    results.append(dict(id=name, command=command, exit_code=result.returncode, log=path.name, sha256=digest(path)))
    print(('PASS' if result.returncode == 0 else 'FAIL'), name, 'exit=' + str(result.returncode), flush=True)
if current_inputs() != before:
    raise SystemExit('Inputs changed during the offline suite; results cannot be certified')
record = dict(source_commit=git(ROOT, 'rev-parse', 'HEAD'), inputs=before, tests=results,
              scope='host/offline only; expected BLOCKED in stage3 suite is not readiness')
(out / 'offline-results.json').write_text(json.dumps(record, indent=2) + '\n')
raise SystemExit(0 if all(r['exit_code'] == 0 for r in results) else 1)
