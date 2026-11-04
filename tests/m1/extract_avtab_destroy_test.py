#!/usr/bin/env python3
"""Compile and run the exact avtab_destroy() body from the target kernel."""
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]
source = (root / "security/selinux/ss/avtab.c").read_text()
marker = "void avtab_destroy(struct avtab *h)"
start = source.index(marker)
open_brace = source.index("{", start)
depth = 0
end = None
for pos in range(open_brace, len(source)):
    if source[pos] == "{":
        depth += 1
    elif source[pos] == "}":
        depth -= 1
        if depth == 0:
            end = pos + 1
            break
assert end is not None
destroy = source[start:end]
harness = r'''
#include <assert.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdlib.h>
#define AVTAB_XPERMS 0x0700
struct avtab_extended_perms { uint8_t specified, driver; uint32_t perms[8]; };
struct avtab_key { uint16_t specified; };
struct avtab_datum { union { uint32_t data; struct avtab_extended_perms *xperms; } u; };
struct avtab_node { struct avtab_key key; struct avtab_datum datum; struct avtab_node *next; };
struct flex_array { struct avtab_node **buckets; unsigned int slots; };
struct avtab { struct flex_array *htable; uint32_t nel, nslot, mask; };
static int node_frees, xperms_frees, array_frees;
static struct avtab_node *flex_array_get_ptr(struct flex_array *fa, unsigned int i) { return i < fa->slots ? fa->buckets[i] : NULL; }
static void flex_array_free(struct flex_array *fa) { array_frees++; free(fa->buckets); free(fa); }
static void kmem_cache_free(void *cache, void *ptr) { if (cache == (void *)1) xperms_frees++; else node_frees++; free(ptr); }
static void *avtab_node_cachep = (void *)2;
static void *avtab_xperms_cachep = (void *)1;
''' + destroy + r'''
int main(void) {
    struct avtab *table = calloc(1, sizeof(*table));
    struct flex_array *fa = calloc(1, sizeof(*fa));
    struct avtab_node *plain = calloc(1, sizeof(*plain));
    struct avtab_node *xpnode = calloc(1, sizeof(*xpnode));
    table->htable = fa; table->nslot = 2; fa->slots = 2;
    fa->buckets = calloc(2, sizeof(*fa->buckets));
    plain->next = xpnode; xpnode->key.specified = AVTAB_XPERMS;
    xpnode->datum.u.xperms = calloc(1, sizeof(*xpnode->datum.u.xperms));
    fa->buckets[0] = plain;
    avtab_destroy(table);
    assert(node_frees == 2 && xperms_frees == 1 && array_frees == 1);
    assert(table->htable == NULL && table->nslot == 0 && table->mask == 0);
    avtab_destroy(table);
    assert(node_frees == 2 && xperms_frees == 1 && array_frees == 1);
    free(table);
    return 0;
}
'''
with tempfile.TemporaryDirectory() as tmp:
    binary = Path(tmp) / "avtab_destroy_test"
    subprocess.run(["cc", "-std=gnu11", "-Wall", "-Wextra", "-Werror", "-Wno-sign-compare", "-x", "c", "-o", str(binary), "-"], input=harness, text=True, check=True)
    subprocess.run([str(binary)], check=True)
print("PASS: extracted Linux 4.19 avtab_destroy frees nodes/xperms once and tolerates repeat destroy")
