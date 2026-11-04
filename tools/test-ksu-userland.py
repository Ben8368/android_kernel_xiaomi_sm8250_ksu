#!/usr/bin/env python3
"""Offline cryptographic tamper rejection; requires the pinned APK download."""
import argparse, importlib.util, json, pathlib
ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('userland',ROOT/'tools/verify-ksu-userland.py');v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)
ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--assets',required=True,type=pathlib.Path);a=ap.parse_args()
report=v.verify(a.assets);lock=json.loads((ROOT/'tools/ksu-userland.lock.json').read_text())
print('PASS all release hashes, APK v2 RSA signature/content digest, manifest and four AArch64 daemons')
b=(a.assets/'KernelSU_Next_v1.1.1_12851-release.apk').read_bytes()
def reject(data,expected,name):
    try:v.verify_apk(data,expected)
    except Exception:print('PASS reject',name);return
    raise AssertionError('accepted '+name)
x=bytearray(b);x[100]^=1;reject(x,lock,'APK payload tampering')
bad=dict(lock,certificate_sha256='0'*64);reject(b,bad,'wrong signing certificate')
reject(b[:-1],lock,'truncated APK')
print('SCOPE: offline cryptography only, no Android install or kernel authentication')
