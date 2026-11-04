#include <assert.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <errno.h>

#define GFP_KERNEL 0
#define ARRAY_SIZE(a) (sizeof(a) / sizeof((a)[0]))
#define TEST_BUCKETS 8
struct flex_array { struct avtab_node *items[TEST_BUCKETS]; unsigned int count; };
struct avtab_key { uint16_t source_type, target_type, target_class, specified; };
struct avtab_datum { union { uint32_t data; struct avtab_extended_perms *xperms; } u; };
struct avtab_extended_perms { uint8_t specified, driver; struct { uint32_t p[8]; } perms; };
struct avtab_node { struct avtab_key key; struct avtab_datum datum; struct avtab_node *next; };
struct avtab { struct flex_array *htable; uint32_t nel, nslot, mask; };
static bool fail_next_put;
static void *flex_array_get_ptr(struct flex_array *fa, unsigned int i) { return i < fa->count ? fa->items[i] : NULL; }
static int flex_array_put_ptr(struct flex_array *fa, unsigned int i, struct avtab_node *node, int flags) { (void)flags; if (i >= fa->count || fail_next_put) { fail_next_put = false; return -ENOMEM; } fa->items[i] = node; return 0; }
#include "../../KernelSU-Next/kernel/selinux/avtab_compat.h"

int main(void)
{
    struct flex_array src_array = { .count = TEST_BUCKETS };
    struct flex_array dst_array = { .count = 1 };
    struct avtab src = { .htable = &src_array, .nel = 3, .nslot = TEST_BUCKETS };
    struct avtab dst = { .htable = &dst_array, .nslot = 1 };
    struct avtab_node a = {0}, b = {0}, c = {0}, absent = {0}, *it;
    unsigned int seen = 0;

    assert(ksu_avtab_bucket(&src, 0) == NULL);
    assert(ksu_avtab_bucket(&src, TEST_BUCKETS) == NULL);
    assert(ksu_avtab_set_bucket(&src, TEST_BUCKETS, &a) == -EINVAL);
    assert(ksu_avtab_set_bucket(&src, 2, &a) == 0);
    assert(ksu_avtab_bucket(&src, 2) == &a);
    assert(ksu_avtab_set_bucket(&src, 2, NULL) == 0);

    a.next = &b; b.next = &c; c.next = NULL;
    assert(ksu_avtab_set_bucket(&src, 3, &a) == 0);
    ksu_avtab_for_each(src, it) { seen++; }
    assert(seen == 3);

    fail_next_put = true;
    assert(!ksu_avtab_move_node(&src, &dst, &a));
    assert(ksu_avtab_bucket(&src, 3) == &a && src.nel == 3);
    assert(ksu_avtab_bucket(&dst, 0) == NULL);

    assert(ksu_avtab_move_node(&src, &dst, &b));
    assert(ksu_avtab_bucket(&src, 3) == &a && a.next == &c);
    assert(ksu_avtab_bucket(&dst, 0) == &b && b.next == NULL);
    assert(src.nel == 2 && dst.nel == 1);
    assert(!ksu_avtab_move_node(&src, &dst, &b));
    assert(!ksu_avtab_move_node(&src, &dst, &absent));

    assert(ksu_avtab_set_bucket(&dst, 0, NULL) == 0);
    dst.nel = 0;
    assert(ksu_avtab_move_node(&src, &dst, &a));
    assert(ksu_avtab_bucket(&src, 3) == &c && c.next == NULL);
    assert(ksu_avtab_bucket(&dst, 0) == &a && a.next == NULL);
    assert(src.nel == 1 && dst.nel == 1);

    {
        struct avtab_extended_perms xp = {0};
        xp.perms.p[0] = 1U;
        xp.perms.p[7] = 1U << 31;
        assert(xp.perms.p[0] == 1U && xp.perms.p[7] == (1U << 31));
    }
    puts("PASS: flex_array buckets, traversal, atomic detach, failure, duplicate removal, xperms bounds");
    return 0;
}
