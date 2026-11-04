#!/usr/bin/env python3
"""Exercise the actual patched certificate-check function with injected errors."""
import pathlib, subprocess, tempfile
root=pathlib.Path(__file__).resolve().parents[1]
source=(root/'KernelSU-Next/kernel/apk_sign.c').read_text()
function=source[source.index('static bool check_block('):source.index('struct zip_entry_header')]
harness=r'''
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
typedef uint32_t u32;
typedef long long loff_t;
struct file { int dummy; };
#define SHA256_DIGEST_SIZE 32
#define pr_info(...) ((void)0)
static int reads, sha_calls, sha_result, read_result, cert_size;
static long ksu_kernel_read_compat(struct file *fp, void *p, unsigned int n, loff_t *pos)
{
 (void)fp; ++reads;
 if(reads<=6) { *(u32*)p=cert_size; *pos+=n; return n; }
 if(read_result!=0) return read_result;
 memset(p,'c',n); *pos+=n; return n;
}
static int ksu_sha256(const unsigned char *p, unsigned int n, unsigned char *out)
{ (void)p;(void)n;++sha_calls;memset(out,0,32);return sha_result; }
static void bin2hex(char *out,const void *p,unsigned int n)
{ (void)p;memset(out,'0',2*n); }
'''
tests=r'''
int main(void)
{
 struct file fp;
 const char *good="0000000000000000000000000000000000000000000000000000000000000000";
 struct {const char *name;int hash_error,read_error,size;bool valid,accept;int hashes; } cases[]={
 {"valid signature",0,0,4,true,true,1},
 {"wrong signature",0,0,4,false,false,1},
 {"crypto ENOMEM",-ENOMEM,0,4,true,false,1},
 {"crypto EINVAL",-EINVAL,0,4,true,false,1},
 {"short certificate read",0,3,4,true,false,0},
 {"certificate read EIO",0,-EIO,4,true,false,0},
 {"oversized certificate",0,0,1025,true,false,0},
 };
 for(unsigned i=0;i<sizeof(cases)/sizeof(cases[0]);++i){
  reads=sha_calls=0;sha_result=cases[i].hash_error;read_result=cases[i].read_error;cert_size=cases[i].size;
  u32 size=0,offset=0;loff_t pos=0;
  bool ok=check_block(&fp,&size,&pos,&offset,cert_size,cases[i].valid?good:"bad hash");
  if(ok!=cases[i].accept||sha_calls!=cases[i].hashes){fprintf(stderr,"FAIL %s\n",cases[i].name);return 1;}
  printf("PASS %s\n",cases[i].name);
 }
 return 0;
}
'''
with tempfile.TemporaryDirectory(prefix='ksu-signature-') as tmp:
 path=pathlib.Path(tmp);(path/'test.c').write_text(harness+function+tests)
 subprocess.run(['cc','-std=gnu11','-Werror=int-conversion','-Werror=implicit-function-declaration',str(path/'test.c'),'-o',str(path/'test')],check=True)
 subprocess.run([str(path/'test')],check=True)
