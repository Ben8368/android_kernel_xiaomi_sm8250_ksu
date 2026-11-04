#!/usr/bin/env python3
"""Compile/run extracted production callbacks with mock objects, not a kernel runtime test."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys

root = Path(__file__).resolve().parents[2]
out = Path(sys.argv[1]).resolve()
out.mkdir(parents=True, exist_ok=False)
sub = root / "KernelSU-Next/kernel"
def function(text, signature):
    start = text.index(signature)
    first = text.index("{", start)
    depth = 1
    end = first + 1
    while depth:
        depth += (text[end] == "{") - (text[end] == "}")
        end += 1
    return text[start:end]
wrapper = (sub / "infra/file_wrapper.c").read_text()
parts = [function(wrapper, signature) for signature in [
    "static struct file *ksu_unwrap_file(",
    "static ssize_t ksu_wrapper_copy_file_range(",
    "static int ksu_wrapper_clone_file_range(",
    "static int ksu_wrapper_dedupe_file_range("]]
source = r"""
#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stdint.h>
#include <sys/types.h>
#include <stdio.h>
typedef uint64_t u64;
struct file;
struct inode { void *i_sb; };
struct file_operations {
    int (*release)(struct inode *, struct file *);
    int (*clone_file_range)(struct file *, loff_t, struct file *, loff_t, u64);
    int (*dedupe_file_range)(struct file *, loff_t, struct file *, loff_t, u64);
    ssize_t (*copy_file_range)(struct file *, loff_t, struct file *, loff_t, size_t, unsigned int);
};
struct file { struct file_operations *f_op; void *private_data;
              struct inode *inode; struct { void *mnt; } f_path; int refs; };
struct ksu_file_wrapper { struct file *orig; struct file_operations ops; };
static int ksu_wrapper_release(struct inode *inode, struct file *file) { return 0; }
#define file_inode(fp) ((fp)->inode)
""" + "\n".join(parts) + r"""
static struct file *expected_src, *expected_dst;
static int calls, result;
static int checked(struct file *src, loff_t off, struct file *dst, loff_t pos, u64 len) {
    assert(src == expected_src && dst == expected_dst);
    assert(off == 123 && pos == 456 && len == 0x100000003ULL);
    calls++; return result;
}
static ssize_t copied(struct file *src, loff_t off, struct file *dst, loff_t pos, size_t len, unsigned int flags) {
    assert(flags == 0x37); return checked(src, off, dst, pos, len);
}
int main(void) {
    int sb1, sb2, m1, m2;
    struct inode in = { &sb1 }, inode_out = { &sb1 };
    struct file_operations src_ops = { .clone_file_range = checked };
    struct file_operations dst_ops = { .dedupe_file_range = checked, .copy_file_range = copied };
    struct file src = { .f_op = &src_ops, .inode = &in, .f_path.mnt = &m1, .refs = 4 };
    struct file dst = { .f_op = &dst_ops, .inode = &inode_out, .f_path.mnt = &m1, .refs = 6 };
    struct file_operations wrap_ops = { .release = ksu_wrapper_release };
    struct ksu_file_wrapper sdata = { .orig = &src }, ddata = { .orig = &dst };
    struct file sw = { .f_op = &wrap_ops, .private_data = &sdata };
    struct file dw = { .f_op = &wrap_ops, .private_data = &ddata };
    struct ksu_file_wrapper nested_data = { .orig = &sw };
    struct file nested = { .f_op = &wrap_ops, .private_data = &nested_data };
    struct file *sources[] = { &src, &sw, &nested }, *destinations[] = { &dst, &dw };
    expected_src = &src; expected_dst = &dst;
    for (unsigned int i = 0; i < 3; ++i) for (unsigned int j = 0; j < 2; ++j) {
        int results[] = { 0, -EIO, -EINVAL, 17 };
        for (unsigned int k = 0; k < 4; ++k) {
            result = results[k];
            assert(ksu_wrapper_clone_file_range(sources[i],123,destinations[j],456,0x100000003ULL) == result);
            assert(ksu_wrapper_dedupe_file_range(sources[i],123,destinations[j],456,0x100000003ULL) == result);
            assert(ksu_wrapper_copy_file_range(sources[i],123,destinations[j],456,0x100000003ULL,0x37) == result);
        }
    }
    int before = calls;
    src_ops.clone_file_range = NULL;
    assert(ksu_wrapper_clone_file_range(&sw,123,&dw,456,0x100000003ULL) == -EOPNOTSUPP);
    dst_ops.dedupe_file_range = NULL;
    assert(ksu_wrapper_dedupe_file_range(&sw,123,&dw,456,0x100000003ULL) == -EOPNOTSUPP);
    dst_ops.copy_file_range = NULL;
    assert(ksu_wrapper_copy_file_range(&sw,123,&dw,456,0x100000003ULL,0x37) == -EOPNOTSUPP);
    src_ops.clone_file_range = checked; inode_out.i_sb = &sb2;
    assert(ksu_wrapper_clone_file_range(&sw,123,&dw,456,0x100000003ULL) == -EXDEV);
    dst_ops.dedupe_file_range = checked; dst.f_path.mnt = &m2;
    assert(ksu_wrapper_dedupe_file_range(&sw,123,&dw,456,0x100000003ULL) == -EXDEV);
    assert(calls == before && src.refs == 4 && dst.refs == 6);
    puts("PASS: actual callback bodies; wrapped/unwrapped/nested src/dst, 64-bit lengths, flags, exact errors, no borrowed ref mutation");
}
"""
cache = (sub / "infra/seccomp_cache.c").read_text()
cache = "\n".join(l for l in cache.splitlines() if not l.startswith("#include"))
cache_source = r"""
#include <errno.h>
#include <assert.h>
#include <stdio.h>
#define KERNEL_VERSION(a,b,c) (((a)<<16)|((b)<<8)|(c))
#define LINUX_VERSION_CODE KERNEL_VERSION(4,19,325)
struct seccomp_filter;
""" + cache + r"""
int main(void) {
    struct seccomp_filter *unknown = (void *)1;
    assert(ksu_seccomp_allow_cache(unknown, 142) == -EOPNOTSUPP);
    assert(ksu_seccomp_clear_cache(unknown, -1) == -EOPNOTSUPP);
    assert(ksu_seccomp_allow_cache(NULL, 0) == -EOPNOTSUPP);
    assert(ksu_seccomp_clear_cache(NULL, 10000) == -EOPNOTSUPP);
    puts("PASS: 4.19 action cache always reports unsupported, including invalid pointers, without dereference");
}
"""
seccomp = function((root / "kernel/seccomp.c").read_text(), "void ksu_seccomp_disable_current(void)")
seccomp_source = r"""
#include <assert.h>
#include <stdio.h>
#include <stddef.h>
struct seccomp_filter { int refs; };
struct sighand { int siglock; };
struct task { struct { int mode; struct seccomp_filter *filter; } seccomp;
              struct sighand *sighand; int thread_flag; };
static struct task *current;
static int held;
#define TIF_SECCOMP 1
#define SECCOMP_MODE_DISABLED 0
#define spin_lock_irqsave(lock, flags) do { assert(!held); held=1; (flags)=7; } while (0)
#define spin_unlock_irqrestore(lock, flags) do { assert(held && (flags)==7); held=0; } while (0)
static void clear_thread_flag(int flag) { assert(held && flag==1); current->thread_flag=0; }
static void __put_seccomp_filter(struct seccomp_filter *f) { assert(!held); if(f) { assert(f->refs>0); f->refs--; } }
""" + seccomp + r"""
int main(void) {
    struct seccomp_filter f = { .refs=2 };
    struct sighand sh = {0};
    struct task root = { .seccomp={2,&f}, .sighand=&sh, .thread_flag=1 };
    struct task app = { .seccomp={2,&f}, .sighand=&sh, .thread_flag=1 };
    current=&root;
    ksu_seccomp_disable_current();
    assert(!root.seccomp.mode && !root.seccomp.filter && !root.thread_flag);
    assert(app.seccomp.mode==2 && app.seccomp.filter==&f && app.thread_flag==1 && f.refs==1);
    ksu_seccomp_disable_current(); assert(f.refs==1);
    puts("PASS: native helper body only detaches current, preserves mock peer filter and shared reference, releases outside siglock");
}
"""
for name, text in [("wrapper", source), ("cache", cache_source), ("seccomp", seccomp_source)]:
    c = out / (name + ".c"); c.write_text(text)
    exe = out / name
    command = ["/usr/bin/cc", "-std=gnu11", "-O1", "-g", "-fsanitize=address,undefined", str(c), "-o", str(exe)]
    print("COMPILE", json.dumps(command), flush=True)
    subprocess.run(command, check=True)
    subprocess.run([str(exe)], check=True)
    print(name, "source_sha256", hashlib.sha256(c.read_bytes()).hexdigest(), "binary_sha256", hashlib.sha256(exe.read_bytes()).hexdigest())
print("Host mock tests only: no claim of real FD lifetime, TSYNC race, fsnotify teardown, or device authorization validation.")
