#!/usr/bin/env python3
"""Check linked umi kernel, security flags and actual artifact formats."""
import argparse,hashlib,json,os,pathlib,re,struct,subprocess
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--out',required=True,type=pathlib.Path)
parser.add_argument('--clang',required=True,type=pathlib.Path)
a=parser.parse_args();out=a.out.resolve();tool=a.clang.resolve();root=pathlib.Path(__file__).resolve().parents[1]
def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
config=(out/'.config').read_text()
required=['MACH_XIAOMI_UMI','KSU','KSU_KPROBES_HOOK','KSU_LSM_SECURITY_HOOKS','KPROBES','EXT4_FS','LTO','LTO_CLANG','THINLTO','CFI','CFI_CLANG','SECCOMP','SECCOMP_FILTER','SECURITY_SELINUX','STACKPROTECTOR_STRONG']
for key in required:assert 'CONFIG_'+key+'=y\n' in config,key
for key in ['CFI_PERMISSIVE','SECURITY_SELINUX_DISABLE','SECURITY_SELINUX_BOOTPARAM','KSU_DEBUG']:
 assert '# CONFIG_'+key+' is not set\n' in config,key
cmd=(out/'drivers/kernelsu/.core_hook.o.cmd').read_text().splitlines()[0]
for flag in ['-flto=thin','-fsanitize=cfi','-fsanitize-cfi-cross-dso']:
 assert flag in cmd,flag
vmlinux=out/'vmlinux'
with vmlinux.open('rb') as f:elf=f.read(64)
assert elf[:6]==b'\x7fELF\x02\x01','ELF64 little endian'
assert struct.unpack_from('<H',elf,18)[0]==183,'AArch64 ELF machine'
elf_type=struct.unpack_from('<H',elf,16)[0]
assert elf_type==2 or (elf_type==3 and 'CONFIG_RELOCATABLE=y\n' in config),'linked executable or relocatable kernel'
elf_description='ELF64 AArch64 '+('DYN (relocatable kernel)' if elf_type==3 else 'EXEC')
undef=subprocess.check_output([str(tool/'bin/llvm-nm'),'--undefined-only',str(vmlinux)],text=True)
assert not any(line.split()[0]=='U' for line in undef.splitlines() if line.split()),undef
symbols=(out/'vmlinux-symbols.txt').read_text()
for symbol in ['kernelsu_init','__cfi_check','__secure_computing']:
 assert symbol in symbols,symbol
boot=out/'arch/arm64/boot';image=boot/'Image'
with image.open('rb') as f:header=f.read(64)
assert header[56:60]==b'ARMd','arm64 Image header'
artifacts=[]
for p in [image,*sorted(boot.rglob('*.dtb')),*sorted(boot.rglob('*.dtbo')),*[p for p in (boot/'dtb.img',boot/'dtbo.img') if p.exists()]]:
 with p.open('rb') as f:header=f.read(64)
 if p.suffix in ['.dtb','.dtbo']:
  magic,total=struct.unpack_from('>II',header)
  assert magic==0xd00dfeed and total<=p.stat().st_size,(p,magic,total)
 artifacts.append(dict(path=str(p.relative_to(out)),size=p.stat().st_size,sha256=digest(p)))
assert any(x['path'].endswith('umi-sm8250-overlay.dtbo') for x in artifacts),'umi overlay'
assert any(x['path'].endswith('.dtb') for x in artifacts),'base DTB'
ksu=root/'KernelSU-Next'
changed=subprocess.check_output(['git','-C',str(ksu),'diff','--name-only'],text=True).splitlines()
protected=['kernel/seccomp.c','include/linux/seccomp.h','fs/namespace.c','include/linux/mount.h','security/selinux']
assert not subprocess.check_output(['git','-C',str(root),'diff','1708fc0888f13780183482dbeb31329202311889','--',*protected]),'protected native source changed'
build_heads=re.findall(r'^([0-9a-f]{40})$',(out/'build.log').read_text(),re.MULTILINE)
assert build_heads,'missing build-time commit identity'
result=dict(build_invocation_head=build_heads[-1],source_head_at_verification=subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip(),kernel_release=(out/'include/config/kernel.release').read_text().strip(),ksu_base=subprocess.check_output(['git','-C',str(ksu),'rev-parse','HEAD'],text=True).strip(),effective_ksu_sha256={p:digest(ksu/p) for p in changed},config_sha256=digest(out/'.config'),required_configs=required,cfi_flags_verified=True,elf=elf_description,unresolved_strong_symbols=0,vmlinux_size=vmlinux.stat().st_size,vmlinux_sha256=digest(vmlinux),dtb_count=sum(x['path'].endswith('.dtb') for x in artifacts),dtbo_count=sum(x['path'].endswith('.dtbo') for x in artifacts),dtbo_img_exists=(boot/'dtbo.img').exists(),module_count=len(list(out.rglob('*.ko'))),artifacts=artifacts,limitations=['No device boot or runtime security verification','Seccomp remains active for su; app root commands may be restricted','Modern namespace profile and optional old path_umount features unavailable','Upstream embed_ksud.c is an empty stub; matching userspace not integrated'])
(out/'verification.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in ['effective_ksu_sha256','artifacts','required_configs']},indent=2))
