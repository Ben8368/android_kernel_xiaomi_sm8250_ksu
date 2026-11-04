#!/usr/bin/env python3
"""Fetch pinned AOSP Clang for LineageOS 24.0 cp2a umi.
Individual tools are verified against upstream Git blob IDs.
"""
import urllib.request,pathlib,concurrent.futures,base64,json,tarfile,io,hashlib,os,time,threading,argparse
rev='29182889399818f97baa65ea238c80e8117981eb';name='clang-r596125'
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--destination',required=True,type=pathlib.Path)
root=parser.parse_args().destination.resolve()
root.mkdir(parents=True,exist_ok=True)
base='https://android.googlesource.com/platform/prebuilts/clang/host/linux-x86/'
urlbase=f'{base}+/{rev}/{name}/'
records=[]
def request(u):
 for i in range(4):
  try:return urllib.request.urlopen(u,timeout=100).read()
  except Exception as e:
   print('retry',i,u,str(e),flush=True)
   if i==3:raise
   time.sleep(2)
def tree(rel):return json.loads(request(urlbase+(rel+'/' if rel else '')+'?format=JSON')[4:])['entries']
entries={e['name']:e for e in tree('bin')}
libs={e['name']:e for e in tree('lib')}
locks={}
lock_guard=threading.Lock()
def get(rel,e=None):
 with lock_guard: lock=locks.setdefault(rel,threading.RLock())
 with lock: return get_locked(rel,e)
def get_locked(rel,e=None):
 if e is None:
  parent,name=rel.rsplit('/',1) if '/' in rel else ('',rel)
  if parent=='bin': e=entries[name]
  elif parent=='lib': e=libs[name]
  else: e=next(x for x in tree(parent) if x['name']==name)
 p=root/rel
 if p.exists() and not p.is_symlink():b=p.read_bytes()
 elif p.is_symlink():b=os.readlink(p).encode()
 else:b=None
 def blob(b):return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
 if b is None or (e and blob(b)!=e['id']):b=base64.b64decode(request(urlbase+rel+'?format=TEXT'))
 if e and blob(b)!=e['id']:raise RuntimeError(('Git blob mismatch',rel))
 p.parent.mkdir(parents=True,exist_ok=True)
 if e and e['mode']==40960:
  if p.is_symlink() or p.exists():p.unlink()
  p.symlink_to(b.decode())
  target=str((p.parent/b.decode()).relative_to(root));get(target)
 else:
  p.write_bytes(b)
  if rel.startswith('bin/'):p.chmod(0o755)
 records.append(dict(path=rel,blob=blob(b),sha256=hashlib.sha256(b).hexdigest()))
 print('verified',rel,len(b),flush=True)
need=['clang','clang++','clang-real','clang++-real','ld.lld','lld','llvm-ar','llvm-nm','llvm-objcopy','llvm-objdump','llvm-readelf','llvm-readobj','llvm-size','llvm-strip','llvm-ranlib','llvm-strings']
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:list(ex.map(lambda n:get('bin/'+n,entries[n]),need))
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:list(ex.map(lambda n:get('lib/'+n,libs[n]),['libxml2.so.16']))
get('AndroidVersion.txt');get('clang_source_info.md')
version=(root/'AndroidVersion.txt').read_text().split('.')[0]
u=f'{base}+archive/{rev}/{name}/lib/clang/{version}/include.tar.gz'
b=request(u)
with tarfile.open(fileobj=io.BytesIO(b)) as t:t.extractall(root/f'lib/clang/{version}/include',filter='data')
(root/'verified-files.json').write_text(json.dumps(dict(revision=rev,toolchain=name,files=records),indent=2)+'\n')
print('READY',flush=True)
