#!/usr/bin/env python3
"""Replay the queue onto official sources and compare effective working files."""
from pathlib import Path
import subprocess,tempfile,tarfile,io
root=Path(__file__).resolve().parents[1];ksu=root/'KernelSU-Next'
archive=subprocess.check_output(['git','-C',str(ksu),'archive','HEAD','kernel'])
with tempfile.TemporaryDirectory(prefix='ksu-patch-replay-') as tmp:
 tmp=Path(tmp)
 with tarfile.open(fileobj=io.BytesIO(archive)) as t:t.extractall(tmp,filter='data')
 subprocess.run(['git','init','-q',str(tmp)],check=True)
 for patch in sorted((root/'compat/kernelsu-next').glob('*.patch')):
  subprocess.run(['git','-C',str(tmp),'apply','--check',str(patch)],check=True)
  subprocess.run(['git','-C',str(tmp),'apply',str(patch)],check=True)
  print('PASS clean replay:',patch.name)
 changed=subprocess.check_output(['git','-C',str(ksu),'diff','--name-only'],text=True).splitlines()
 for rel in changed:assert (tmp/rel).read_bytes()==(ksu/rel).read_bytes(),rel
 print('PASS effective source matches clean replay:',len(changed),'files')
 subprocess.run(['git','-C',str(ksu),'diff','--check'],check=True)
 print('PASS effective source whitespace check')
