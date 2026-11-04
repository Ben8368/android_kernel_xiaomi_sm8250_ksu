#!/usr/bin/env python3
"""Offline verification of pinned release bytes, APK v2 signature and daemon ELF.
Requires python3-cryptography. Never installs or executes Android binaries.
"""
import argparse, hashlib, io, json, pathlib, struct, zipfile
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
ROOT = pathlib.Path(__file__).resolve().parents[1]
def sha(b): return hashlib.sha256(b).hexdigest()
def require(ok, msg):
    if not ok: raise ValueError(msg)
def u32(b, p=0): return struct.unpack_from('<I', b, p)[0]
def lp(b):
    require(len(b)>=4, 'truncated length')
    n=u32(b); require(n<=len(b)-4, 'length outside buffer')
    return b[4:4+n], b[4+n:]
def seq(b):
    result=[]
    while b:
        item,b=lp(b); result.append(item)
    return result

def verify_apk(b, lock):
    # EOCD must be complete, single-disk, without ZIP64.
    eocd=b.rfind(b'PK\x05\x06', max(0,len(b)-65557))
    require(eocd>=0 and eocd+22+struct.unpack_from('<H',b,eocd+20)[0]==len(b), 'bad EOCD')
    require(b[eocd+4:eocd+8]==bytes(4), 'multi-disk ZIP unsupported')
    cd=u32(b,eocd+16); require(cd+u32(b,eocd+12)==eocd, 'bad central directory')
    require(b[cd-16:cd]==b'APK Sig Block 42', 'missing APK signing block')
    size=struct.unpack_from('<Q',b,cd-24)[0]; start=cd-size-8
    require(start>=0 and struct.unpack_from('<Q',b,start)[0]==size, 'bad signing block size')
    pairs={}; pos=start+8
    while pos<cd-24:
        n=struct.unpack_from('<Q',b,pos)[0]; pos+=8
        require(n>=4 and pos+n<=cd-24, 'bad signing pair')
        ident=u32(b,pos); require(ident not in pairs, 'duplicate signing ID')
        pairs[ident]=b[pos+4:pos+n];pos+=n
    require(pos==cd-24 and 0x7109871a in pairs, 'missing v2 block')
    require(not ({0xf05368c0,0x1b93ad61}&pairs.keys()), 'old kernel rejects v3/v3.1')
    signers,tail=lp(pairs[0x7109871a]); require(not tail,'signer tail')
    signers=seq(signers); require(len(signers)==1,'expected one signer')
    signed,rest=lp(signers[0]); signatures,rest=lp(rest); public,rest=lp(rest)
    require(not rest,'signer trailing data')
    digests,signed_rest=lp(signed); certs,signed_rest=lp(signed_rest)
    # Official lsposed-signed APK has four authenticated zero padding bytes.
    attrs,signed_rest=lp(signed_rest); require(signed_rest in (b'', bytes(4)),'unexpected signed-data trailing bytes')
    certs=seq(certs); require(len(certs)==1,'expected single release certificate')
    cert=certs[0]
    require(len(cert)==lock['certificate_size'] and sha(cert)==lock['certificate_sha256'],'release certificate mismatch')
    key=x509.load_der_x509_certificate(cert).public_key()
    require(key.public_bytes(serialization.Encoding.DER,serialization.PublicFormat.SubjectPublicKeyInfo)==public,'public key mismatch')
    digest_records={u32(x):lp(x[4:])[0] for x in seq(digests)}
    sig_records={u32(x):lp(x[4:])[0] for x in seq(signatures)}
    require(digest_records.keys()==sig_records.keys(),'digest/signature algorithm mismatch')
    alg=next((x for x in [0x0103,0x0101] if x in sig_records),None)
    require(alg is not None,'unsupported APK signature algorithm')
    pad=padding.PKCS1v15() if alg==0x0103 else padding.PSS(mgf=padding.MGF1(hashes.SHA256()),salt_length=32)
    key.verify(sig_records[alg],signed,pad,hashes.SHA256())
    fixed=bytearray(b[eocd:]);struct.pack_into('<I',fixed,16,start)
    chunks=[]
    for section in (b[:start], b[cd:eocd], bytes(fixed)):
        for offset in range(0,len(section),1024*1024):
            chunk=section[offset:offset+1024*1024]
            chunks.append(hashlib.sha256(b'\xa5'+struct.pack('<I',len(chunk))+chunk).digest())
    digest=hashlib.sha256(b'\x5a'+struct.pack('<I',len(chunks))+b''.join(chunks)).digest()
    require(digest==digest_records[alg],'APK content digest mismatch')
    with zipfile.ZipFile(io.BytesIO(b)) as z:
        require('META-INF/MANIFEST.MF' not in z.namelist(),'old kernel rejects v1 signature')
    return dict(certificate_sha256=sha(cert),certificate_size=len(cert),signing_ids=[hex(x) for x in pairs],algorithm=hex(alg),v2_signature_verified=True,content_digest_verified=True)

def elf(b):
    require(b[:6]==b'\x7fELF\x02\x01' and struct.unpack_from('<H',b,18)[0]==183,'expected AArch64 ELF64 LE')
    require(struct.unpack_from('<H',b,16)[0]==3,'expected PIE/ET_DYN daemon')
    off=struct.unpack_from('<Q',b,32)[0]; ents,n=struct.unpack_from('<HH',b,54)
    aligns=[];interp=None
    for i in range(n):
        entry=struct.unpack_from('<IIQQQQQQ',b,off+i*ents)
        if entry[0]==1: aligns.append(entry[7])
        if entry[0]==3: interp=b[entry[2]:entry[2]+entry[5]].rstrip(b'\0').decode()
    require(interp=='/system/bin/linker64','expected Android dynamic linker')
    return dict(machine='AArch64',type='PIE',interpreter=interp,load_alignments=aligns)

def manifest_values(b):
    require(b[:4]==b'\x03\x00\x08\x00','expected binary AndroidManifest')
    strings=[];values={};pos=8
    def len8(p):
        n=b[p];return (((n&0x7f)<<8)|b[p+1],p+2) if n&0x80 else (n,p+1)
    while pos<len(b):
        kind,head,size=struct.unpack_from('<HHI',b,pos)
        require(size>=head and pos+size<=len(b),'invalid AXML chunk')
        if kind==1:
            count,styles,flags,start,style_start=struct.unpack_from('<5I',b,pos+8)
            for i in range(count):
                p=pos+start+u32(b,pos+head+4*i)
                if flags&0x100:
                    _,p=len8(p);n,p=len8(p);s=b[p:p+n].decode('utf8')
                else:
                    n=struct.unpack_from('<H',b,p)[0];p+=2
                    if n&0x8000:n=((n&0x7fff)<<16)|struct.unpack_from('<H',b,p)[0];p+=2
                    s=b[p:p+2*n].decode('utf-16le')
                strings.append(s)
        if kind==0x102:
            name=strings[u32(b,pos+20)];start,ents,count=struct.unpack_from('<HHH',b,pos+24)
            if name in ['manifest','uses-sdk']:
                for i in range(count):
                    p=pos+16+start+ents*i;_,key,raw=struct.unpack_from('<3I',b,p);typ=b[p+15];data=u32(b,p+16)
                    values[strings[key]]=strings[data] if typ==3 else data
        pos+=size
    return {k:values[k] for k in ['package','versionCode','versionName','minSdkVersion','targetSdkVersion']}

def verify(directory):
    lock=json.loads((ROOT/'tools/ksu-userland.lock.json').read_text())
    results={}
    for item in lock['assets']:
        p=directory/item['name']; b=p.read_bytes()
        require(len(b)==item['size'] and sha(b)==item['sha256'],'asset mismatch: '+p.name)
        result=dict(sha256=sha(b),size=len(b),release_digest_matched=True)
        if p.suffix=='.apk':
            result.update(verify_apk(b,lock))
            with zipfile.ZipFile(io.BytesIO(b)) as z: manifest=manifest_values(z.read('AndroidManifest.xml'))
            require(manifest['package']=='com.rifsxd.ksunext' and manifest['versionCode']==12851 and manifest['versionName']=='v1.1.1','unexpected Manager identity/version')
            result['manifest']=manifest
        with zipfile.ZipFile(io.BytesIO(b)) as z:
            native={}
            for name,expected in item['executables'].items():
                data=z.read(name); require(sha(data)==expected,'daemon hash mismatch: '+name)
                native[name]=dict(sha256=sha(data),size=len(data),**elf(data))
            result['executables']=native
        results[p.name]=result
    return dict(source_commit=lock['commit'],version=lock['version'],version_code=12851,assets=results,scope='OFFLINE ONLY; no Android execution or device authentication')
if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--assets',type=pathlib.Path,required=True);ap.add_argument('--output',type=pathlib.Path)
    a=ap.parse_args();report=json.dumps(verify(a.assets),indent=2)+'\n'
    if a.output: a.output.write_text(report)
    print(report,end='')
