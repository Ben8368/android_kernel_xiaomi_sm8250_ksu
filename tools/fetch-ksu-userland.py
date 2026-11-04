#!/usr/bin/env python3
"""Download only hash-pinned official v1.1.1 assets. No install/execute actions."""
import argparse, hashlib, json, pathlib, urllib.request
ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=pathlib.Path,required=True);a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
lock=json.loads((pathlib.Path(__file__).parent/'ksu-userland.lock.json').read_text())
for item in lock['assets']:
    p=a.out/item['name']
    data=p.read_bytes() if p.exists() else urllib.request.urlopen(item['url'],timeout=120).read()
    if len(data)!=item['size'] or hashlib.sha256(data).hexdigest()!=item['sha256']: raise SystemExit('asset hash mismatch: '+item['name'])
    if not p.exists():
        tmp=p.with_suffix(p.suffix+'.partial');tmp.write_bytes(data);tmp.replace(p)
    print('PASS',item['name'],item['sha256'])
