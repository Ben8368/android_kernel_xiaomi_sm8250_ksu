#!/usr/bin/env python3
"""Mutate copies of the actual completed build evidence; never edit artifacts."""
import json
import pathlib
import shutil
import tempfile
from ksu_audit import ROOT, digest
from ksu_readiness import current_inputs, verify_compile

original = ROOT / 'docs/validation/stage4'
inputs = current_inputs()
verify_compile(original, inputs)
print('PASS actual complete build evidence matches current kernel, queue and native inputs')


def reject(label, change):
    with tempfile.TemporaryDirectory(prefix='ksu-build-evidence-') as tmp:
        d = pathlib.Path(tmp)
        record = json.loads((original / 'build-result.json').read_text())
        for name in record['files']:
            p = d / name
            p.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(original / name, p)
        change(d)
        # Rehash the altered material: semantic validation must still reject it.
        record['files'] = {name: digest(d / name) for name in record['files']}
        (d / 'build-result.json').write_text(json.dumps(record))
        try:
            verify_compile(d, inputs)
        except (ValueError, KeyError, OSError):
            print('PASS rejects rehashed', label)
            return
        raise AssertionError('accepted ' + label)


def wrong_queue(d):
    p = json.loads((d / 'provenance.json').read_text())
    p['source']['patch_queue_sha256'] = '0' * 64
    (d / 'provenance.json').write_text(json.dumps(p))
    (d / 'source-before.json').write_text(json.dumps(p['source']))


def unsafe_config(d):
    p = json.loads((d / 'provenance.json').read_text())
    cfg = (d / 'build.config').read_text()
    if 'CONFIG_SECCOMP=y\n' not in cfg:
        raise AssertionError('original evidence lacks Seccomp')
    (d / 'build.config').write_text(cfg.replace('CONFIG_SECCOMP=y\n', '# CONFIG_SECCOMP is not set\n'))
    p['config_sha256'] = digest(d / 'build.config')
    (d / 'provenance.json').write_text(json.dumps(p))


def missing_module(d):
    m = json.loads((d / 'modules.sha256.json').read_text())
    m.pop(next(iter(m)))
    (d / 'modules.sha256.json').write_text(json.dumps(m))


reject('stale patch queue with matched pre/post source records', wrong_queue)
reject('disabled Seccomp despite updated config hash', unsafe_config)
reject('incomplete module inventory', missing_module)
reject('nonzero build exit', lambda d: (d / 'build.exit').write_text('1\n'))
reject('missing build completion marker', lambda d: (d / 'build-console.log').write_text((d / 'build-console.log').read_text().replace('SUCCESS ', 'INCOMPLETE ')))
print('SCOPE: archived build evidence only; no target policy/device claim')
