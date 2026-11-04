#!/usr/bin/env python3
"""Host-only ABI, input-boundary and static regression tests. NOT device Root."""
import argparse, json, pathlib, re, subprocess, tempfile
from ksu_audit import ROOT, BASE, UPSTREAM, git, prove_sources
ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--allow-uncommitted',action='store_true');a=ap.parse_args()
ksu=ROOT/'KernelSU-Next'
def text(p): return (ksu/p).read_text()
def check(ok,msg):
    if not ok: raise AssertionError(msg)
    print('PASS',msg)
def function(source,name):
    m=re.search(r'(?m)^(?:static )?(?:inline )?(?:bool|int|void) '+name+r'\([^;]*?\)\s*{',source)
    if not m: raise ValueError('function not found '+name)
    start=m.start();pos=m.end();level=1
    while level:
        if source[pos]=='{':level+=1
        if source[pos]=='}':level-=1
        pos+=1
    return source[start:pos]
proof=prove_sources(not a.allow_uncommitted)
check(proof['unexplained_dirty'] is False,'all KSU kernel files equal clean upstream + exact patch queue')
header=text('kernel/ksu.h'); native=text('manager/app/src/main/cpp/ksu.cc')
km={k:int(v,0) for k,v in re.findall(r'^#define (KERNEL_SU_OPTION|CMD_\w+) (0x[0-9A-Fa-f]+|[0-9]+)$',header,re.M)}
nm={k:int(v,0) for k,v in re.findall(r'^#define (KERNEL_SU_OPTION|CMD_\w+) (0x[0-9A-Fa-f]+|[0-9]+)$',native,re.M)}
alias={'CMD_GET_SU_LIST':'CMD_GET_ALLOW_LIST','CMD_IS_UID_GRANTED_ROOT':'CMD_UID_GRANTED_ROOT','CMD_IS_UID_SHOULD_UMOUNT':'CMD_UID_SHOULD_UMOUNT'}
for k,v in nm.items():check(km[alias.get(k,k)]==v,'Manager command '+k)
rust=(ROOT/'docs/validation/stage3/sources/rustix-prctl.rs').read_text()
for k,v in re.findall(r'^const (KERNEL_SU_OPTION|CMD_\w+): u(?:32|64) = (0x[0-9A-Fa-f_]+|[0-9]+);',rust,re.M):check(km[k]==int(v.replace('_',''),0),'ksud rustix command '+k)
check('KSU_VERSION := 12851' in text('kernel/Makefile'),'kernel release version code 12851')
for h in [header,text('manager/app/src/main/cpp/ksu.h')]:check('#define KSU_APP_PROFILE_VER 2' in h,'profile ABI v2')
core=text('kernel/core_hook.c');su=text('kernel/sucompat.c');allow=text('kernel/allowlist.c');rules=text('kernel/selinux/rules.c')
prctl=function(core,'ksu_handle_prctl');escape=function(core,'escape_to_root')
check(prctl.index('if (!from_manager)')<prctl.index('if (arg2 == CMD_SET_APP_PROFILE)'),'profile mutation after manager-only gate')
check('if (!from_root)' in prctl[prctl.index('if (arg2 == CMD_SET_SEPOLICY)'):prctl.index('if (arg2 == CMD_CHECK_SAFEMODE)')],'policy mutation root-only')
check('if (is_allow_su())' in prctl and 'ksu_is_allow_uid(current_uid().val)' in function(su,'ksu_handle_execve_sucompat'),'both root-entry paths require authorization')
check('commit_creds(cred)' in escape and 'setup_selinux(profile->selinux_domain)' in escape,'credential and SELinux transition remain explicit')
check(not any(x in core for x in ['disable_seccomp(', 'seccomp.mode = 0','seccomp.filter = NULL','clear_thread_flag(TIF_SECCOMP)']),'no caller seccomp removal')
check('ksu_permissive(db, KERNEL_SU_DOMAIN)' not in rules,'no automatic su permissive rule')
check('EXPECTED_MANAGER_HASH' in text('kernel/apk_sign.c') and 'is_manager_apk(dirpath)' in text('kernel/throne_tracker.c'),'certificate-based manager discovery retained')
check('init_kprobe(SYS_EXECVE_SYMBOL, execve_handler_pre)' in su and '__arm64_sys_execve' in text('kernel/arch.h'),'native arm64 execve probe wiring exists (registration NOT tested)')
check('SYS_EXECVEAT_SYMBOL' not in su,'execveat-only virtual su explicitly unsupported by this queue')
check(not git(ROOT,'diff',UPSTREAM,'--','kernel/seccomp.c','include/linux/seccomp.h','security/selinux','fs/namespace.c','include/linux/mount.h'),'native seccomp/SELinux/VFS sources unchanged from LineageOS')
structs=header[header.index('struct root_profile {'):header.index('bool ksu_queue_work')]
constants='\n'.join(x for x in header.splitlines() if re.match(r'#define KSU_(APP_PROFILE_VER|MAX_PACKAGE_NAME|MAX_GROUPS|SELINUX_DOMAIN) ',x))
pre='#include <stdint.h>\n#include <stdbool.h>\n#include <stddef.h>\n#include <stdio.h>\n#include <string.h>\n#include <assert.h>\ntypedef uint32_t u32; typedef uint64_t u64;\n'+constants+'\n'+structs
with tempfile.TemporaryDirectory(prefix='ksu-contract-') as temp:
    tmp=pathlib.Path(temp)
    # Compile the actual two declarations separately, comparing host LP64 layout.
    layout='int main(){printf("%zu %zu %zu %zu %zu %zu\\n",sizeof(struct app_profile),sizeof(struct root_profile),offsetof(struct app_profile,current_uid),offsetof(struct app_profile,allow_su),offsetof(struct app_profile,rp_config),offsetof(struct root_profile,capabilities));}'
    (tmp/'kernel.c').write_text(pre+layout)
    (tmp/'manager.cc').write_text('#include <stdint.h>\n#include <stddef.h>\n#include <stdio.h>\n#include <sys/types.h>\n#include "'+str(ksu/'manager/app/src/main/cpp/ksu.h')+'"\n'+layout)
    layouts=[]
    for src,compiler in [('kernel.c','gcc'),('manager.cc','g++')]:
        exe=tmp/(src+'.exe');subprocess.run([compiler,str(tmp/src),'-o',str(exe)],check=True);layouts.append(subprocess.check_output([str(exe)],text=True).strip())
    check(layouts[0]==layouts[1],'LP64 profile sizeof/offset match: '+layouts[0])
    harness=pre+'''
#define pr_info(...) ((void)0)
struct list_head { struct list_head *next; };
struct perm_data {struct list_head list; struct app_profile profile;};
static struct list_head allow_list;
#define list_for_each(pos,head) for(pos=(head)->next; pos!=(head); pos=pos->next)
#define list_entry(pos,type,member) ((type*)((char*)(pos)-offsetof(type,member)))
'''+function(allow,'profile_valid')+'\n'+function(allow,'ksu_get_allow_list')+'''
int main(void) {
 struct app_profile p={.version=2,.current_uid=10001,.allow_su=true};
 strcpy(p.key,"test.app"); strcpy(p.rp_config.profile.selinux_domain,"u:r:su:s0");
 assert(profile_valid(&p)); p.version=3;assert(!profile_valid(&p));p.version=2;
 p.current_uid=-1;assert(!profile_valid(&p));p.current_uid=10001;
 p.rp_config.profile.groups_count=-1;assert(!profile_valid(&p));
 p.rp_config.profile.groups_count=33;assert(!profile_valid(&p));p.rp_config.profile.groups_count=0;
 memset(p.key,'x',sizeof(p.key));assert(!profile_valid(&p));strcpy(p.key,"test.app");
 memset(p.rp_config.profile.selinux_domain,'x',64);assert(!profile_valid(&p));
 struct perm_data nodes[200]; int buf[130],len;
 for(int count=0;count<=200;count++) {
  for(int i=0;i<130;i++)buf[i]=0x12345678;
  allow_list.next=count?&nodes[0].list:&allow_list;
  for(int i=0;i<count;i++){nodes[i].profile.allow_su=true;nodes[i].profile.current_uid=i;nodes[i].list.next=i+1<count?&nodes[i+1].list:&allow_list;}
  len=-1;bool ok=ksu_get_allow_list(buf+1,&len,128,true);
  assert(ok==(count<=128));assert(len==(count<=128?count:0));
  assert(buf[0]==0x12345678 && buf[129]==0x12345678);
 }
 puts("PASS extracted profile validation and 201 allowlist capacity cases (ASan/UBSan)");
}
'''
    (tmp/'bounds.c').write_text(harness)
    subprocess.run(['gcc','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer',str(tmp/'bounds.c'),'-o',str(tmp/'bounds')],check=True)
    subprocess.run([str(tmp/'bounds')],check=True)
    # Execute upstream Manager native wrapper with a deliberately mocked prctl.
    mock='''
#define prctl mock_prctl
#include "'''+str(ksu/'manager/app/src/main/cpp/ksu.cc')+'''"
#include <stdarg.h>
#include <assert.h>
#include <errno.h>
static bool authorized=true;
extern "C" int mock_prctl(int option, ...) noexcept {
 va_list ap;va_start(ap,option);int cmd=va_arg(ap,int);void*a=va_arg(ap,void*);void*b=va_arg(ap,void*);uint32_t*r=va_arg(ap,uint32_t*);va_end(ap);
 assert((uint32_t)option==0xdeadbeef);
 if(authorized){if(cmd==2){*(int*)a=12851;*(int*)b=0;}else{*r=0xdeadbeef;}}
 errno=EINVAL;return -1;
}
int main(){assert(get_version()==12851);app_profile p={};assert(set_app_profile(&p));authorized=false;assert(!set_app_profile(&p));puts("PASS actual Manager wrapper accepts output sentinel despite prctl EINVAL; mock denial rejected");}
'''
    (tmp/'mock.cc').write_text(mock);subprocess.run(['g++',str(tmp/'mock.cc'),'-o',str(tmp/'mock')],check=True);subprocess.run([str(tmp/'mock')],check=True)
block=(ROOT/'docs/validation/stage3/sources/bionic-SECCOMP_BLOCKLIST_APP.TXT').read_text()
common=(ROOT/'docs/validation/stage3/sources/bionic-SECCOMP_BLOCKLIST_COMMON.TXT').read_text()
check('prctl(' in (ROOT/'docs/validation/stage3/sources/bionic-SYSCALLS.TXT').read_text() and not re.search(r'^prctl\(',block+'\n'+common,re.M),'pinned bionic source permits prctl syscall number; extra app filters still possible')
check('set_thread_groups(' in text('userspace/ksud_magic/src/su.rs') and 'setgroups(int,' in block and 'setresgid(' in block,'detect known official ordinary-su vs preserved app Seccomp incompatibility')
print('SCOPE: static checks and host mocks only; no Android prctl, device boot or Root validation')
