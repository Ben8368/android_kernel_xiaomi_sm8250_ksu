#!/usr/bin/env python3
"""Source provenance helpers. Expected patch dirtiness is proven, never hidden."""
import hashlib, io, pathlib, subprocess, tarfile, tempfile
ROOT=pathlib.Path(__file__).resolve().parents[1]
BASE='0d6bdc6364cbfc73517dcfdf7ab23b0ba8045553'
UPSTREAM='6b34d24765327d746074c8e53b5ad0d24a51acc7'
def git(path,*args): return subprocess.check_output(['git','-C',str(path),*args],text=True).strip()
def digest(path):
    h=hashlib.sha256()
    with pathlib.Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''): h.update(b)
    return h.hexdigest()
def prove_sources(require_clean=True):
    ksu=ROOT/'KernelSU-Next'
    if git(ksu,'rev-parse','HEAD')!=BASE: raise ValueError('unexpected KSU base')
    if git(ksu,'diff','--cached','--name-only'): raise ValueError('staged submodule edits')
    status=git(ROOT,'status','--porcelain','--untracked-files=all','--ignore-submodules=all')
    if require_clean and status: raise ValueError('uncommitted parent source: '+status)
    patches=sorted((ROOT/'compat/kernelsu-next').glob('*.patch'))
    queue=hashlib.sha256(); entries=[]
    for p in patches:
        queue.update(p.name.encode()+b'\0'+p.read_bytes())
        entries.append(dict(name=p.name,sha256=digest(p)))
    archive=subprocess.check_output(['git','-C',str(ksu),'archive','HEAD','kernel'])
    names=git(ksu,'ls-tree','-r','--name-only','HEAD','kernel').splitlines()
    with tempfile.TemporaryDirectory(prefix='ksu-proof-') as tmp:
        temp=pathlib.Path(tmp)
        with tarfile.open(fileobj=io.BytesIO(archive)) as t: t.extractall(temp,filter='data')
        subprocess.run(['git','init','-q',str(temp)],check=True)
        for p in patches: subprocess.run(['git','-C',str(temp),'apply',str(p)],check=True)
        for name in names:
            if (temp/name).read_bytes()!=(ksu/name).read_bytes(): raise ValueError('unexplained source: '+name)
        actual={str(p.relative_to(ksu)) for p in (ksu/'kernel').rglob('*') if p.is_file()}
        if actual!=set(names): raise ValueError('extra or missing files in KSU kernel: '+str(actual^set(names)))
    outside=[n for n in git(ksu,'diff','--name-only').splitlines() if not n.startswith('kernel/')]
    if outside or git(ksu,'ls-files','--others','--exclude-standard'): raise ValueError('unexplained submodule edits')
    return dict(lineage_upstream_sha=UPSTREAM,custom_branch_sha=git(ROOT,'rev-parse','HEAD'),custom_tree=git(ROOT,'rev-parse','HEAD^{tree}'),ksu_official_base_sha=BASE,patch_queue_sha256=queue.hexdigest(),patch_queue_hash_format='sorted filename UTF-8 + NUL + raw patch bytes, concatenated',patches=entries,effective_ksu_kernel_sha256={name:digest(ksu/name) for name in names},parent_status=status,expected_patch_dirty=bool(git(ksu,'diff','--name-only')),unexplained_dirty=False)
