#!/usr/bin/env python3
"""Execute patched allowlist.c with liburcu + pthreads + ASan/UBSan.

This tests real record/publication/snapshot code, with host kernel API adapters.
It does not emulate IRQ/preemption, Android identity, filesystem durability or
prove Linux RCU/lockdep/CFI correctness on the target kernel.
Requires gcc, pkg-config and liburcu-dev (Ubuntu).
"""
import pathlib, re, subprocess, tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
ksu = ROOT / 'KernelSU-Next'
header = (ksu / 'kernel/ksu.h').read_text()
constants = '\n'.join(line for line in header.splitlines()
                      if re.match(r'#define KSU_(APP_PROFILE_VER|MAX_PACKAGE_NAME|MAX_GROUPS|SELINUX_DOMAIN) ', line))
structs = header[header.index('struct root_profile {'):header.index('bool ksu_queue_work')]
source = (ksu / 'kernel/allowlist.c').read_text()
source = '\n'.join(line for line in source.splitlines() if not line.startswith('#include'))
shim = r'''
#define _GNU_SOURCE
#include <assert.h>
#include <stdatomic.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <stddef.h>
#include <string.h>
#include <pthread.h>
#include <sched.h>
#include <sys/types.h>
#include <fcntl.h>
#include <urcu.h>
#include <urcu/rculist.h>
typedef uint32_t u32; typedef uint64_t u64;
#define KERNEL_VERSION(a,b,c) (((a)<<16)|((b)<<8)|(c))
#define LINUX_VERSION_CODE KERNEL_VERSION(4,19,325)
#define container_of(ptr,type,member) ((type*)((char*)(ptr)-offsetof(type,member)))
#define list_head cds_list_head
#define LIST_HEAD(name) CDS_LIST_HEAD(name)
#define list_for_each_entry cds_list_for_each_entry
#define list_for_each_entry_safe cds_list_for_each_entry_safe
#define list_for_each_entry_rcu cds_list_for_each_entry_rcu
#define list_replace_rcu cds_list_replace_rcu
#define list_add_tail_rcu cds_list_add_tail_rcu
#define list_del_rcu cds_list_del_rcu
#define READ_ONCE(x) __atomic_load_n(&(x),__ATOMIC_SEQ_CST)
#define WRITE_ONCE(x,v) __atomic_store_n(&(x),(v),__ATOMIC_SEQ_CST)
#define unlikely(x) (x)
#define likely(x) (x)
#define pr_info(...) ((void)0)
#define pr_err(...) ((void)0)
typedef struct {u32 cap[2];} kernel_cap_t;
#define CAP_FULL_SET ((kernel_cap_t){{~0U,~0U}})
static _Thread_local int writer_depth;
#define DEFINE_SPINLOCK(name) pthread_spinlock_t name
#define spin_lock_irqsave(lock,flags) do{(flags)=0;pthread_spin_lock(lock);writer_depth++;}while(0)
#define spin_unlock_irqrestore(lock,flags) do{(void)(flags);writer_depth--;pthread_spin_unlock(lock);}while(0)
typedef _Atomic unsigned int seqcount_t;
#define SEQCNT_ZERO(name) 0
static void write_seqcount_begin(seqcount_t *s){assert(writer_depth);atomic_fetch_add(s,1);}
static void write_seqcount_end(seqcount_t *s){atomic_fetch_add(s,1);}
static unsigned read_seqcount_begin(seqcount_t *s){unsigned v;do{v=atomic_load(s);}while(v&1);return v;}
static bool read_seqcount_retry(seqcount_t *s,unsigned v){return atomic_load(s)!=v;}
#define GFP_ATOMIC 1
static _Atomic bool fail_alloc;
static _Atomic long allocated,freed;
static void *kmalloc(size_t n,int gfp){assert(!writer_depth);assert(gfp==GFP_ATOMIC);if(atomic_exchange(&fail_alloc,false))return NULL;void*p=malloc(n);if(p)atomic_fetch_add(&allocated,1);return p;}
static void kfree(void *p){if(p){atomic_fetch_add(&freed,1);free(p);}}
static void *vzalloc(size_t n){assert(!writer_depth && !rcu_read_ongoing());return calloc(1,n);}
#define vfree free
struct work_struct {int unused;};
#define INIT_WORK(w,f) ((void)(w))
static void cancel_work_sync(struct work_struct*w){(void)w;assert(!writer_depth && !rcu_read_ongoing());}
static _Atomic long queued;
static bool ksu_queue_work(struct work_struct*w){(void)w;atomic_fetch_add(&queued,1);return true;}
static uid_t manager_uid = (uid_t)-1;
#define ksu_get_manager_uid() READ_ONCE(manager_uid)
#define ksu_is_manager_uid_valid() (ksu_get_manager_uid()!=(uid_t)-1)
static bool is_ksu_domain(void){return false;}
/* File adapter: only worker operations allowed; per-thread records are checked. */
typedef long long loff_t_test;
#define loff_t loff_t_test
struct file {int unused;};
static _Thread_local struct file fp_stub;
static _Thread_local const unsigned char *load_data;
static _Thread_local size_t load_size;
static struct file *ksu_filp_open_compat(const char*p,int mode,int perm){(void)p;(void)mode;(void)perm;assert(!writer_depth && !rcu_read_ongoing());return &fp_stub;}
#define IS_ERR(p) false
#define PTR_ERR(p) 0L
static int filp_close(struct file*f,int x){(void)f;(void)x;assert(!writer_depth && !rcu_read_ongoing());return 0;}
static ssize_t ksu_kernel_write_compat(struct file*f,const void*p,size_t n,loff_t*off){(void)f;(void)p;assert(!writer_depth && !rcu_read_ongoing());*off+=n;return n;}
static ssize_t ksu_kernel_read_compat(struct file*f,void*p,size_t n,loff_t*off){(void)f;assert(!writer_depth && !rcu_read_ongoing());if((size_t)*off>=load_size)return 0;if(n>load_size-*off)n=load_size-*off;memcpy(p,load_data+*off,n);*off+=n;return n;}
bool ksu_set_app_profile(struct app_profile*,bool);
'''
# Forward-declare after actual ABI structs, so types have file scope.
shim = shim.replace('bool ksu_set_app_profile(struct app_profile*,bool);', '')
main = r'''
static struct app_profile make_profile(int uid, int marker, bool allow){
 struct app_profile p={.version=2,.current_uid=uid,.allow_su=allow};
 strcpy(p.key,"test.app");p.rp_config.profile.uid=marker;p.rp_config.profile.gid=marker;
 p.rp_config.profile.groups_count=2;p.rp_config.profile.groups[0]=marker;p.rp_config.profile.groups[1]=marker;
 p.rp_config.profile.capabilities.effective=marker;strcpy(p.rp_config.profile.selinux_domain,"u:r:su:s0");return p;
}
static bool drop_all(uid_t uid,char*pkg,void*data){(void)uid;(void)pkg;(void)data;return false;}
static _Atomic bool race_entered,race_leave;
static bool race_predicate(uid_t uid,char*pkg,void*data){
 (void)pkg;(void)data;if(uid!=10001)return true;
 atomic_store(&race_entered,true);while(!atomic_load(&race_leave)){} return false;
}
static void *race_prune(void*unused){(void)unused;rcu_register_thread();ksu_prune_allowlist(race_predicate,NULL);rcu_unregister_thread();return NULL;}
static void check_snapshot(struct root_profile *p){
 assert(p->uid==17 || p->uid==23 || p->uid==0);
 if(p->uid){assert(p->uid==p->gid);assert(p->groups_count==2);assert(p->groups[0]==p->uid);assert(p->groups[1]==p->uid);assert(p->capabilities.effective==(u64)p->uid);}
}
static void *writer(void *arg){
 rcu_register_thread();int marker=(intptr_t)arg;
 for(int i=0;i<20000;i++){struct app_profile p=make_profile(10001,marker,i%7!=0);assert(ksu_set_app_profile(&p,false));}
 rcu_unregister_thread();return NULL;
}
static void *reader(void *arg){
 (void)arg;rcu_register_thread();
 for(int i=0;i<40000;i++){
  struct root_profile out;if(ksu_get_root_profile(10001,&out))check_snapshot(&out);
  struct app_profile p={.current_uid=10001};if(ksu_get_app_profile(&p) && p.allow_su)check_snapshot(&p.rp_config.profile);
  (void)__ksu_is_allow_uid(10001);
  int ids[4],n;assert(!ksu_get_allow_list(ids,&n,-1,true) && n==0);
 }
 rcu_unregister_thread();return NULL;
}
static void *pruner(void *arg){(void)arg;rcu_register_thread();for(int i=0;i<10000;i++)ksu_prune_allowlist(drop_all,NULL);rcu_unregister_thread();return NULL;}
static void *saver(void *arg){(void)arg;rcu_register_thread();for(int i=0;i<100;i++)do_save_allow_list(NULL);rcu_unregister_thread();return NULL;}
int main(void){
 rcu_register_thread();pthread_spin_init(&allowlist_lock,PTHREAD_PROCESS_PRIVATE);ksu_allowlist_init();
 struct root_profile out;assert(!__ksu_is_allow_uid((uid_t)-1));assert(!ksu_get_root_profile((uid_t)-1,&out));
 struct app_profile p=make_profile(10001,17,true);atomic_store(&fail_alloc,true);assert(!ksu_set_app_profile(&p,false));assert(!__ksu_is_allow_uid(10001));
 /* Disk imports after a live revoke cannot restore the old grant. */
 assert(set_profile(&p,false,true));p.allow_su=false;assert(ksu_set_app_profile(&p,false));p.allow_su=true;assert(!set_profile(&p,false,true));assert(!__ksu_is_allow_uid(10001));
 assert(ksu_set_app_profile(&p,false));assert(ksu_get_root_profile(10001,&out));
 struct root_profile held=out;ksu_prune_allowlist(drop_all,NULL);rcu_barrier();assert(!ksu_get_root_profile(10001,&out));check_snapshot(&held);
 assert(ksu_set_app_profile(&p,false));p.current_uid=300001;assert(ksu_set_app_profile(&p,false));assert(__ksu_is_allow_uid(300001));
 p.allow_su=false;assert(ksu_set_app_profile(&p,false));assert(!__ksu_is_allow_uid(300001));
 p=make_profile(10001,23,true);strcpy(p.key,"replacement.package");assert(ksu_set_app_profile(&p,false));
 int ids[4],n;assert(ksu_get_allow_list(ids,&n,4,true) && n==1);assert(allowlist_count==2);
 pthread_t race;pthread_create(&race,NULL,race_prune,NULL);while(!atomic_load(&race_entered)){}
 p=make_profile(10001,17,true);assert(ksu_set_app_profile(&p,false));atomic_store(&race_leave,true);pthread_join(race,NULL);
 assert(ksu_get_root_profile(10001,&out) && out.uid==17);puts("PASS deterministic prune/replacement race preserves successor; held snapshot survives RCU free");
 pthread_t threads[8];pthread_create(&threads[0],NULL,writer,(void*)17);pthread_create(&threads[1],NULL,writer,(void*)23);
 for(int i=2;i<6;i++)pthread_create(&threads[i],NULL,reader,NULL);
 pthread_create(&threads[6],NULL,pruner,NULL);pthread_create(&threads[7],NULL,saver,NULL);
 for(int i=0;i<8;i++)pthread_join(threads[i],NULL);rcu_barrier();
 puts("PASS 8 threads: 40000 replacements, 160000 reader iterations, 10000 prunes, 100 persistence snapshots (liburcu / ASan / UBSan)");
 p=make_profile(10001,17,true);assert(ksu_set_app_profile(&p,false));p.allow_su=false;assert(ksu_set_app_profile(&p,true));
 assert(!__ksu_is_allow_uid(10001) && !ksu_get_root_profile(10001,&out));
 WRITE_ONCE(manager_uid,10001);assert(__ksu_is_allow_uid(10001));WRITE_ONCE(manager_uid,(uid_t)-1);assert(!__ksu_is_allow_uid(10001));
 p=make_profile(9999,17,true);strcpy(p.key,"#");assert(ksu_set_app_profile(&p,false));assert(!__ksu_is_allow_uid(9999));
 p.current_uid=10002;strcpy(p.key,"#");assert(!ksu_set_app_profile(&p,false));
 p=make_profile(10002,17,true);p.rp_config.profile.groups_count=-1;assert(!ksu_set_app_profile(&p,false));
 p.rp_config.profile.groups_count=33;assert(!ksu_set_app_profile(&p,false));p.rp_config.profile.groups_count=1;p.rp_config.profile.groups[0]=-1;assert(!ksu_set_app_profile(&p,false));
 ksu_prune_allowlist(drop_all,NULL);rcu_barrier();assert(allowlist_count==1); /* default survives */
 for(int i=0;i<1023;i++){p=make_profile(200000+i,17,true);assert(ksu_set_app_profile(&p,false));}
 p=make_profile(900001,17,true);assert(!ksu_set_app_profile(&p,false));assert(!__ksu_is_allow_uid(900001));
 p=make_profile(200000,23,false);assert(ksu_set_app_profile(&p,false));assert(allowlist_count==1024);assert(!__ksu_is_allow_uid(200000));
 assert(!ksu_get_allow_list(ids,&n,4,true) && n==0);assert(!ksu_get_allow_list(NULL,&n,-1,true));
 puts("PASS deny visibility, stale load refusal, high/multiuser UID, package replacement, invalid Manager sentinel, reserved defaults, negative groups and capacity rollback");
 ksu_allowlist_exit();assert(allocated==freed);assert(allowlist_count==0);assert(!ksu_set_app_profile(&p,false));
 puts("PASS quiesced shutdown drains callbacks; every allocated record freed exactly once; stopped table rejects writes");
 rcu_unregister_thread();return 0;
}
'''
with tempfile.TemporaryDirectory(prefix='ksu-rcu-test-') as tmp:
    tmp = pathlib.Path(tmp)
    c = tmp / 'allowlist.c'
    c.write_text(shim + constants + '\n' + structs + '\nbool ksu_set_app_profile(struct app_profile*,bool);\n' + source + main)
    flags = subprocess.check_output(['pkg-config', '--cflags', '--libs', 'liburcu'], text=True).split()
    exe = tmp / 'allowlist'
    subprocess.run(['gcc', '-std=gnu11', '-O1', '-g', '-pthread', '-fsanitize=address,undefined',
                    '-fno-omit-frame-pointer', str(c), '-o', str(exe), *flags], check=True)
    subprocess.run([str(exe)], check=True, timeout=120)
print('SCOPE: host adapters and userspace RCU; target lockdep/KASAN/KCSAN, package identity and crash persistence remain BLOCKED')
