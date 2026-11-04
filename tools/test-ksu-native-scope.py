#!/usr/bin/env python3
"""Ensure all native drivers/configuration/build inputs stay at the stage-3 base."""
from ksu_readiness import current_inputs, native_tree

baseline = '7f9c153e61fd2c8e970a9c63a421500a274f8470'
inputs = current_inputs()
if native_tree(baseline) != inputs['native_tree_sha256']:
    raise AssertionError('native kernel/drivers/configs/build inputs changed')
print('PASS complete native tree and build input blobs match stage-3 HEAD: ' + baseline)
print('PASS charging/touch/fingerprint/Wi-Fi drivers and original LTO/ThinLTO/CFI/Seccomp/SELinux source/config inputs unchanged')
print('SCOPE: Git source equality; hardware operation still untested')
