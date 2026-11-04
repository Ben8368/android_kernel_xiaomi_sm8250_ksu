#!/usr/bin/env python3
"""Synthetic AOSP mkbootimg fixture tests. Temporary images are NOT device images."""
import gzip, importlib.util, json, pathlib, shutil, struct, subprocess, tempfile
ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('boot',ROOT/'tools/inspect-umi-boot.py');boot=importlib.util.module_from_spec(spec);spec.loader.exec_module(boot)
SOURCES=ROOT/'docs/validation/stage3/sources'
def reject(b,name):
    try:boot.inspect(b)
    except (ValueError,struct.error):print('PASS reject',name);return
    raise AssertionError('accepted '+name)
with tempfile.TemporaryDirectory(prefix='umi-synthetic-') as d:
    t=pathlib.Path(d);(t/'gki').mkdir()
    shutil.copy(SOURCES/'mkbootimg.py',t/'mkbootimg.py');shutil.copy(SOURCES/'generate_gki_certificate.py',t/'gki/generate_gki_certificate.py')
    kernel=bytearray(4096);kernel[56:60]=b'ARMd';(t/'Image').write_bytes(kernel)
    (t/'ramdisk').write_bytes(gzip.compress(b'070701'+b'0'*104+b'TRAILER!!!\0'))
    fdt=struct.pack('>10I',0xd00dfeed,72,56,72,40,17,16,0,0,16)+bytes(16)+struct.pack('>4I',1,0,2,9)
    (t/'dtb').write_bytes(fdt)
    subprocess.run(['python3',str(t/'mkbootimg.py'),'--header_version','2','--pagesize','4096','--base','0','--kernel',str(t/'Image'),'--ramdisk',str(t/'ramdisk'),'--dtb',str(t/'dtb'),'--cmdline','androidboot.hardware=qcom','-o',str(t/'fixture.img')],check=True)
    b=(t/'fixture.img').read_bytes();r=boot.inspect(b);assert r['sections']['dtb']['trees'][0]['size']==72
    print('PASS independent AOSP mkbootimg header-v2 synthetic fixture, section ranges and SHA-1 ID')
    reject(b[:1659],'short header');reject(b[:-4096],'truncated DTB');reject(b[:40]+struct.pack('<I',3)+b[44:],'v3 header')
    x=bytearray(b);x[36:40]=struct.pack('<I',2048);reject(x,'wrong page size')
    x=bytearray(b);x[4096+56]=0;reject(x,'bad ARM64 magic')
    x=bytearray(b);x[576]=0;reject(x,'wrong AOSP boot ID')
    reject(b+b'NOT_AN_AVB_FOOTER','unknown trailer')
    x=bytearray(b);x[1648:1652]=struct.pack('<I',0);reject(x,'missing DTB')
    print('SCOPE: temporary synthetic fixture deleted; no matching ROM boot image was built')
