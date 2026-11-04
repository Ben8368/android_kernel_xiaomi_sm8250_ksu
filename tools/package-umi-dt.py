#!/usr/bin/env python3
"""Assemble DT artifacts with LineageOS's public BoardConfig/kernel.mk rules."""
import argparse,hashlib,json,pathlib,struct,subprocess,sys
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--out',required=True,type=pathlib.Path)
a=parser.parse_args();out=a.out.resolve();root=pathlib.Path(__file__).resolve().parents[1]
tool=root/'tools/third_party/mkdtboimg.py';lock=json.loads(tool.with_suffix('.source.json').read_text())
assert hashlib.sha256(tool.read_bytes()).hexdigest()==lock['sha256'],'mkdtboimg source mismatch'
dts=out/'arch/arm64/boot/dts';dtbs=sorted(dts.rglob('*.dtb'));overlays=sorted(dts.rglob('*.dtbo'))
assert len(dtbs)==3 and len(overlays)==12,'unexpected device tree input set'
assert any(p.name=='umi-sm8250-overlay.dtbo' for p in overlays),'umi overlay missing'
boot=out/'arch/arm64/boot';dtb=boot/'dtb.img';dtbo=boot/'dtbo.img'
# Same sorted concatenation as kernel.mk when no BOARD_DTB_CFG is supplied.
dtb.write_bytes(b''.join(p.read_bytes() for p in dtbs))
command=[sys.executable,str(tool),'create',str(dtbo),'--page_size=4096',*[str(p) for p in overlays]]
print('COMMAND:',*command,flush=True);subprocess.run(command,check=True)
with dtbo.open('rb') as f:data=f.read()
magic,total,header_size,entry_size,count,entries_offset,page_size,version=struct.unpack_from('>8I',data)
assert magic==0xd7b7ab1e and total==len(data) and count==12 and page_size==4096
assert total<=33554432,'BOARD_DTBOIMG_PARTITION_SIZE exceeded'
for i,p in enumerate(overlays):
 size,offset,*_=struct.unpack_from('>8I',data,entries_offset+i*entry_size)
 assert data[offset:offset+size]==p.read_bytes(),p
subprocess.run([sys.executable,str(tool),'dump',str(dtbo)],check=True,stdout=(out/'dtbo-dump.txt').open('w'))
result=dict(rule='LineageOS 24.0 kernel.mk sorted DTBs and mkdtboimg create --page_size=4096',tool_source=lock,dtb_inputs=[str(p.relative_to(out)) for p in dtbs],dtbo_inputs=[str(p.relative_to(out)) for p in overlays],dtbo_header=dict(version=version,entry_count=count,page_size=page_size,total_size=total),artifacts=[dict(path=str(p.relative_to(out)),size=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in [dtb,dtbo]])
(out/'dt-package-verification.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
