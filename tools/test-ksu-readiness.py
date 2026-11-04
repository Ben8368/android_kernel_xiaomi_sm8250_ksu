#!/usr/bin/env python3
"""Negative tests for evidence binding and independent readiness categories."""
import copy
import json
import pathlib
import tempfile
from ksu_audit import digest
from ksu_readiness import GATE_NAMES, REQUIRED_TESTS, assess, current_inputs, verify_offline, verify_files


def reject(call, label):
    try:
        call()
    except (ValueError, KeyError, OSError):
        print('PASS rejects', label)
        return
    raise AssertionError('accepted ' + label)


inputs = current_inputs()
with tempfile.TemporaryDirectory(prefix='ksu-readiness-negative-') as tmp:
    d = pathlib.Path(tmp)
    report = assess(d)
    assert set(report['gates']) == set(GATE_NAMES)
    assert all(g['status'] == 'BLOCKED' for g in report['gates'].values())
    assert report['status'] == 'BLOCKED' and not report['manual_device_test_ready']
    (d / 'validation-state.json').write_text(json.dumps({name: 'PASS' for name in GATE_NAMES}))
    assert assess(d)['status'] == 'BLOCKED'
    print('PASS missing evidence and unverified PASS booleans cannot promote any category')
    (d / 'fixture.log').write_text('synthetic record used only for validator negative tests\n')
    record = dict(inputs=inputs, source_commit='fixture', tests=[dict(
        id=name, exit_code=0, log='fixture.log', sha256=digest(d / 'fixture.log')) for name in sorted(REQUIRED_TESTS)])
    (d / 'offline-results.json').write_text(json.dumps(record))
    verify_offline(d, inputs)  # Checks record integrity, not independent attestation.
    report = assess(d)
    assert report['gates']['offline_compatibility']['status'] == 'PASS'
    assert report['gates']['compile']['status'] == 'BLOCKED'
    assert all(report['gates'][n]['status'] == 'BLOCKED' for n in GATE_NAMES[2:])
    assert not report['manual_device_test_ready']
    print('PASS host-result records cannot certify static security, ROM policy, Boot inputs or device results')
    wrong = copy.deepcopy(inputs)
    wrong['patch_queue_sha256'] = '0' * 64
    reject(lambda: verify_offline(d, wrong), 'stale/different source and patch fingerprint')
    saved = (d / 'fixture.log').read_bytes()
    (d / 'fixture.log').write_bytes(saved + b'altered\n')
    reject(lambda: verify_offline(d, inputs), 'tampered test log')
    (d / 'fixture.log').write_bytes(saved)
    bad = copy.deepcopy(record)
    bad['tests'][0]['exit_code'] = 1
    (d / 'offline-results.json').write_text(json.dumps(bad))
    reject(lambda: verify_offline(d, inputs), 'failed test presented as passed')
    bad = copy.deepcopy(record)
    bad['tests'].pop()
    (d / 'offline-results.json').write_text(json.dumps(bad))
    reject(lambda: verify_offline(d, inputs), 'missing required regression')
    bad = copy.deepcopy(record)
    bad['tests'].append(bad['tests'][0])
    (d / 'offline-results.json').write_text(json.dumps(bad))
    reject(lambda: verify_offline(d, inputs), 'duplicate test identities')
    reject(lambda: verify_files(d, {'../outside.log': '0' * 64}), 'evidence path traversal')
print('SCOPE: evidence validators only, no device success asserted')
