#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <errno.h>
typedef uint32_t u32;
typedef uint16_t u16;
#define GFP_KERNEL 0
#define GFP_ATOMIC 0
#define CONFIG_64BIT 1
#define BITS_PER_LONG 64
#define BUG_ON(x) assert(!(x))
#define cond_resched() ((void)0)
static int fail_at = -1, calls, live;
static void *alloc(size_t n) { if (calls++ == fail_at) return NULL; void *p = calloc(1, n); if (p) live++; return p; }
static void kfree(const void *p) { if (p) { live--; free((void *)p); } }
static void *kzalloc(size_t n, int flags) { (void)flags; return alloc(n); }
static char *kstrdup(const char *s, int flags) { char *p; (void)flags; p = alloc(strlen(s)+1); if (p) strcpy(p,s); return p; }
static void *hashtab_node_cachep, *ebitmap_node_cachep;
static void *kmem_cache_zalloc(void *cache, int flags) { (void)flags; return alloc(cache == &hashtab_node_cachep ? sizeof(struct_hashtab_node_placeholder) : sizeof(struct_ebitmap_node_placeholder)); }
static void kmem_cache_free(void *cache, void *p) { (void)cache; kfree(p); }
static unsigned int find_first_bit(const unsigned long *p, unsigned int size) { unsigned int i; for (i=0; i<size; i++) if (p[i/64] & (1UL << (i%64))) return i; return size; }
/* NATIVE_DEFINITIONS */
/* NATIVE_FUNCTIONS */
struct type_datum { u32 value; };
struct class_datum { u32 value; };
struct symtab { struct hashtab *table; };
struct policydb { struct symtab p_types, p_classes; struct ebitmap filename_trans_ttypes; struct hashtab *filename_trans; };
#define symtab_search(s, name) hashtab_search((s)->table, name)
#include "filename_trans_compat.h"

static u32 strhash(struct hashtab *h, const void *v) { const unsigned char *s=v; u32 n=0; while (*s) n=n*33+*s++; return n & (h->size-1); }
static int strcmp_key(struct hashtab *h, const void *a, const void *b) { (void)h; return strcmp(a,b); }
static unsigned long partial_name_hash(unsigned char c, unsigned long h) { return (h + (c << 4) + (c >> 4)) * 11; }
/* NATIVE_FILENAME_HASH */
static struct hashtab *table(u32 (*hash)(struct hashtab *,const void *), int (*cmp)(struct hashtab *,const void *,const void *)) { struct hashtab *h=calloc(1,sizeof(*h)); h->size=16; h->htable=calloc(h->size,sizeof(*h->htable)); h->hash_value=hash; h->keycmp=cmp; return h; }
static void cleanup(struct hashtab *h, bool owned) { unsigned i; for(i=0;i<h->size;i++) { struct hashtab_node *n=h->htable[i]; while(n) { struct hashtab_node *next=n->next; if(owned) { struct filename_trans *k=n->key; kfree(k->name); kfree(k); kfree(n->datum); } kfree(n); n=next; } } free(h->htable); free(h); }
static void reset_fail(int n) { calls=0; fail_at=n; }
int main(void) {
    struct policydb db={0}; struct type_datum src={1}, src2={2}, tgt={500}, def={3}, other={4}; struct class_datum cls={7};
    struct filename_trans key={1,500,7,"file"}; struct filename_trans_datum *v; int i, baseline;
    hashtab_node_cachep=&hashtab_node_cachep; ebitmap_node_cachep=&ebitmap_node_cachep;
    db.p_types.table=table(strhash,strcmp_key); db.p_classes.table=table(strhash,strcmp_key); db.filename_trans=table(filenametr_hash,filenametr_cmp);
    assert(!hashtab_insert(db.p_types.table,"src",&src)); assert(!hashtab_insert(db.p_types.table,"src2",&src2)); assert(!hashtab_insert(db.p_types.table,"tgt",&tgt)); assert(!hashtab_insert(db.p_types.table,"def",&def)); assert(!hashtab_insert(db.p_types.table,"other",&other)); assert(!hashtab_insert(db.p_classes.table,"file",&cls));
    baseline=live;
    assert(!add_filename_trans(&db,"missing","tgt","file","def","file"));
    assert(!add_filename_trans(&db,"src","missing","file","def","file"));
    assert(!add_filename_trans(&db,"src","tgt","missing","def","file"));
    assert(!add_filename_trans(&db,"src","tgt","file","missing","file"));
    assert(live==baseline && db.filename_trans->nel==0);
    /* Fail key, name, datum, bitmap node and native hash node allocations. */
    for(i=0;i<5;i++) { reset_fail(i); assert(!add_filename_trans(&db,"src","tgt","file","def","file")); assert(db.filename_trans->nel==0); assert(!ebitmap_get_bit(&db.filename_trans_ttypes,500)); assert(live==baseline); }
    reset_fail(-1); db.filename_trans->nel=HASHTAB_MAX_NODES;
    assert(!add_filename_trans(&db,"src","tgt","file","def","file"));
    assert(!ebitmap_get_bit(&db.filename_trans_ttypes,500) && live==baseline);
    db.filename_trans->nel=0;
    reset_fail(-1); assert(add_filename_trans(&db,"src","tgt","file","def","file"));
    v=hashtab_search(db.filename_trans,&key); assert(v && v->otype==3); assert(ebitmap_get_bit(&db.filename_trans_ttypes,500));
    baseline=live; reset_fail(0); assert(add_filename_trans(&db,"src","tgt","file","def","file")); assert(live==baseline);
    assert(!add_filename_trans(&db,"src","tgt","file","other","file")); assert(v->otype==3 && live==baseline);
    assert(!ebitmap_set_bit(&db.filename_trans_ttypes,500,0)); baseline=live;
    reset_fail(0); assert(!add_filename_trans(&db,"src","tgt","file","def","file"));
    assert(!ebitmap_get_bit(&db.filename_trans_ttypes,500) && v->otype==3 && live==baseline);
    reset_fail(-1); assert(add_filename_trans(&db,"src","tgt","file","def","file")); baseline=live;
    reset_fail(3); assert(!add_filename_trans(&db,"src2","tgt","file","other","file")); assert(ebitmap_get_bit(&db.filename_trans_ttypes,500) && live==baseline);
    reset_fail(-1); assert(add_filename_trans(&db,"src2","tgt","file","other","file")); key.stype=2; v=hashtab_search(db.filename_trans,&key); assert(v && v->otype==4 && db.filename_trans->nel==2);
    cleanup(db.filename_trans,true); ebitmap_destroy(&db.filename_trans_ttypes); cleanup(db.p_types.table,false); cleanup(db.p_classes.table,false); assert(live==0);
    puts("PASS: filename transitions, conflicts, source separation, allocation and rollback"); return 0;
}
