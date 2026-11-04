#!/usr/bin/env python3
"""Read-only umi non-VAB header-v2 format gate. Never packs, flashes or reboots.
A passing format inspection does not prove AVB trust, ROM matching or bootability.
"""
import argparse, hashlib, json, pathlib, struct, zipfile

def require(ok,msg):
    if not ok: raise ValueError(msg)
def align(n,a): return (n+a-1)//a*a
def dtbs(data):
    pos=0;result=[]
    while pos<len(data):
        if not any(data[pos:]):break
        require(len(data)-pos>=40,'truncated FDT header')
        magic,size,st,strings,res,ver,last,cpu,szstr,szst=struct.unpack_from('>10I',data,pos)
        require(magic==0xd00dfeed and 40<=size<=len(data)-pos,'invalid DTB size/magic')
        require(ver>=17 and last<=17 and res%8==0,'unsupported DTB header')
        require(st+szst<=size and strings+szstr<=size and res+16<=size,'DTB offsets out of range')
        result.append(dict(offset=pos,size=size,sha256=hashlib.sha256(data[pos:pos+size]).hexdigest()))
        pos+=size
        # Lineage DTB packaging pads each concatenated tree to eight bytes.
        if pos<len(data) and data[pos:pos+4]!=b'\xd0\x0d\xfe\xed':
            end=align(pos,8);require(not any(data[pos:end]),'nonzero DTB alignment padding');pos=end
    require(bool(result),'empty DTB section');return result

def inspect(b):
    require(len(b)>=1660 and b[:8]==b'ANDROID!','not Android boot image')
    require(len(b)<=134217728,'exceeds non-VAB umi boot partition')
    fields=struct.unpack_from('<10I',b,8)
    kernel_size,kaddr,ramdisk_size,raddr,second_size,saddr,tags,page,version,os_version=fields
    require(version==2,'only confirmed non-VAB header v2 supported; v3/VAB needs separate target evidence')
    require(page==4096 and struct.unpack_from('<I',b,1644)[0]==1660,'bad page/header size')
    recovery_size=struct.unpack_from('<I',b,1632)[0];recovery_offset=struct.unpack_from('<Q',b,1636)[0]
    dtb_size=struct.unpack_from('<I',b,1648)[0]
    require(kernel_size>=64 and ramdisk_size>0 and dtb_size>0,'missing kernel, ramdisk or DTB')
    require(second_size==0,'unexpected second-stage payload for confirmed umi layout')
    pos=page;sections={};payload=[]
    for name,size in [('kernel',kernel_size),('ramdisk',ramdisk_size),('second',second_size),('recovery_dtbo',recovery_size),('dtb',dtb_size)]:
        require(pos+size<=len(b),'truncated '+name)
        if name=='recovery_dtbo':require(recovery_offset==(pos if size else 0),'recovery DTBO offset mismatch')
        data=b[pos:pos+size];payload.append(data)
        sections[name]=dict(offset=pos,size=size,sha256=hashlib.sha256(data).hexdigest())
        if name=='kernel':require(data[56:60]==b'ARMd','expected raw ARM64 Image, not Image.gz or Image-dtb')
        if name=='ramdisk':require(data.startswith((b'\x1f\x8b',b'\x02\x21\x4c\x18',b'\x04\x22\x4d\x18',b'070701',b'070702')),'unknown ramdisk encoding')
        if name=='dtb':sections[name]['trees']=dtbs(data)
        pos=align(pos+size,page)
    require(pos<=len(b),'truncated payload alignment')
    h=hashlib.sha1()
    for data in payload:h.update(data);h.update(struct.pack('<I',len(data)))
    require(b[576:608]==h.digest()+bytes(12),'AOSP boot ID checksum mismatch')
    footer=len(b)>=64 and b[-64:-60]==b'AVBf'
    if footer:
        major,minor,original,vbmeta_off,vbmeta_size=struct.unpack_from('>IIQQQ',b,len(b)-60)
        require(original>=pos and original<=vbmeta_off and vbmeta_off+vbmeta_size<=len(b)-64,'AVB footer range invalid')
        require(b[vbmeta_off:vbmeta_off+4]==b'AVB0','missing vbmeta header')
    else:require(not any(b[pos:]),'unrecognized nonzero trailer; AVB/legacy signature requires explicit audit')
    cmd=(b[64:576].split(b'\0',1)[0]+b[608:1632].split(b'\0',1)[0]).decode('utf8')
    return dict(format='Android boot header v2',pagesize=page,os_version_field=os_version,cmdline=cmd,sections=sections,avb_footer_present=footer,avb_signature_verified=False,sha256=hashlib.sha256(b).hexdigest(),scope='FORMAT ONLY; not approval to flash')

def inspect_target_files(path):
    # One ZIP is the source unit: no accepting loose ramdisk/DTBO from another ROM.
    with zipfile.ZipFile(path) as z:
        names=set(z.namelist())
        required={'IMAGES/boot.img','IMAGES/dtbo.img','IMAGES/vbmeta.img','IMAGES/recovery.img','META/misc_info.txt'}
        require(required<=names,'missing same-build images/metadata in target-files')
        report=inspect(z.read('IMAGES/boot.img'))
        props='\n'.join(z.read(n).decode(errors='replace') for n in ['SYSTEM/build.prop','SYSTEM/system/build.prop','SYSTEM_EXT/build.prop','PRODUCT/build.prop'] if n in names)
        require(any(x in props.splitlines() for x in ['ro.product.device=umi','ro.product.system.device=umi','ro.product.product.device=umi']),'target-files not identified as umi')
        require('ro.build.version.release=17' in props.splitlines(),'target-files is not Android 17')
        require(any(x.startswith('ro.lineage.version=24.0-') for x in props.splitlines()),'target-files not LineageOS 24.0')
        d=z.read('IMAGES/dtbo.img');require(len(d)>=32 and struct.unpack_from('>I',d)[0]==0xd7b7ab1e,'invalid DTBO image magic')
        require(len(d)<=33554432,'DTBO exceeds partition')
        report['same_archive_images']={n:hashlib.sha256(z.read(n)).hexdigest() for n in sorted(required)}
        report['build_properties']=[x for x in props.splitlines() if x.startswith(('ro.build.fingerprint=','ro.lineage.version=','ro.build.version.security_patch='))]
        report['rom_kernel_revision_verified']=False
        report['packaging_ready']=False
        report['remaining_gate']='Verify exact ROM kernel/device/vendor manifest and AVB policy before adding a packer'
        return report
if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);group=ap.add_mutually_exclusive_group(required=True);group.add_argument('--image',type=pathlib.Path);group.add_argument('--target-files',type=pathlib.Path)
    a=ap.parse_args();print(json.dumps(inspect(a.image.read_bytes()) if a.image else inspect_target_files(a.target_files),indent=2))
