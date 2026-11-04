#!/usr/bin/env python3
"""Report seven independent evidence gates; exit 2 for unresolved blockers."""
import argparse
import json
from ksu_audit import ROOT
from ksu_readiness import assess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--evidence-dir', default=ROOT / 'docs/validation/stage4')
parser.add_argument('--build-dir', help='Also rehash the actual Image/vmlinux/modules/DT artifacts')
args = parser.parse_args()
report = assess(args.evidence_dir, args.build_dir)
print(json.dumps(report, indent=2))
raise SystemExit(2 if report['status'] == 'BLOCKED' else 0)
