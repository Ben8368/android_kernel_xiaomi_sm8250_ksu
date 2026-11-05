#!/usr/bin/env python3
"""Test the production readers against extracted target flex_array bodies."""
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]
source = (root / "lib/flex_array.c").read_text()

def block(marker):
    start = source.index(marker)
    opening = source.index("{", start)
    depth = 0
    for pos in range(opening, len(source)):
        if source[pos] == "{":
            depth += 1
        elif source[pos] == "}":
            depth -= 1
            if not depth:
                return source[start:pos + 1]
    raise ValueError(marker)

functions = "\n".join(block(x) for x in (
    "static inline int elements_fit_in_base(",
    "static int fa_element_to_part_nr(",
    "static unsigned int index_inside_part(",
    "void *flex_array_get(", "void *flex_array_get_ptr("))
fixture = r'''
#include <assert.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
typedef uint32_t u32;
#define PAGE_SIZE 4096
#define FLEX_ARRAY_PART_SIZE PAGE_SIZE
struct reciprocal_value { unsigned int divisor; };
struct flex_array_part { char elements[PAGE_SIZE]; };
struct flex_array {
    union {
        struct { int element_size, total_nr_elements, elems_per_part;
                 struct reciprocal_value reciprocal_elems;
                 struct flex_array_part *parts[]; };
        char padding[PAGE_SIZE];
    };
};
#define FLEX_ARRAY_BASE_BYTES_LEFT (PAGE_SIZE - __builtin_offsetof(struct flex_array, parts))
static unsigned int reciprocal_divide(unsigned int n, struct reciprocal_value r) { return n / r.divisor; }
struct type_datum { int marker; };
struct ebitmap { void *node; u32 highbit; };
#define SYM_TYPES 0
struct policydb {
    struct { u32 nprim; } p_types;
    struct flex_array *type_val_to_struct_array, *type_attr_map_array;
    struct flex_array *sym_val_to_name[1];
};
/* NATIVE */
#include "type_index_compat.h"
static struct flex_array *new_array(int size, int count) {
    struct flex_array *a = calloc(1, sizeof(*a));
    assert(a);
    a->element_size = size; a->total_nr_elements = count;
    a->elems_per_part = PAGE_SIZE / size;
    a->reciprocal_elems.divisor = a->elems_per_part;
    return a;
}
int main(void) {
    struct policydb db = {0};
    struct type_datum a = {1}, z = {2}, *v;
    char *name = "last";
    struct ebitmap map = { (void *)(uintptr_t)42, 7 };
    struct flex_array *types = new_array(sizeof(v), 700);
    struct flex_array *names = new_array(sizeof(name), 700);
    struct flex_array *maps = new_array(sizeof(map), 700);
    db.p_types.nprim = 700;
    db.type_val_to_struct_array = types; db.type_attr_map_array = maps;
    db.sym_val_to_name[0] = names;
    types->parts[0] = calloc(1, PAGE_SIZE); types->parts[1] = calloc(1, PAGE_SIZE);
    names->parts[1] = calloc(1, PAGE_SIZE); maps->parts[2] = calloc(1, PAGE_SIZE);
    assert(types->parts[0] && types->parts[1] && names->parts[1] && maps->parts[2]);
    v = &a; memcpy(types->parts[0]->elements, &v, sizeof(v));
    v = &z; memcpy(types->parts[1]->elements + (699 - 512) * sizeof(v), &v, sizeof(v));
    memcpy(names->parts[1]->elements + (699 - 512) * sizeof(name), &name, sizeof(name));
    memcpy(maps->parts[2]->elements + (699 - 512) * sizeof(map), &map, sizeof(map));
    assert(ksu_type_value_get(&db, 1) == &a);
    assert(ksu_type_value_get(&db, 700) == &z);
    assert(!ksu_type_value_get(&db, 0) && !ksu_type_value_get(&db, 701));
    assert(!ksu_type_index_get(NULL, 0) && !ksu_type_index_get(&db, 700));
    assert(!ksu_type_index_get(&db, 1));
    assert(!ksu_type_name_index_get(&db, 0));
    assert(ksu_type_name_index_get(&db, 699) == name);
    assert(!ksu_type_attr_index_get(&db, 0));
    assert(ksu_type_attr_index_get(&db, 699)->highbit == 7);
    assert(!ksu_type_attr_index_get(&db, 700));
    types->total_nr_elements = 699;
    assert(!ksu_type_index_get(&db, 699));
    types->total_nr_elements = 700;
    free(types->parts[0]); free(types->parts[1]); free(names->parts[1]); free(maps->parts[2]);
    free(types); free(names); free(maps);
    puts("PASS: native flex_array reads and bounds");
    return 0;
}
'''.replace("/* NATIVE */", functions)

with tempfile.TemporaryDirectory() as tmp:
    c = Path(tmp) / "test.c"
    exe = Path(tmp) / "test"
    c.write_text(fixture)
    subprocess.run(["/usr/bin/gcc", "-std=gnu11", "-g", "-O1", "-Wall", "-Wextra",
                    "-Wno-sign-compare", "-fsanitize=address,undefined", "-fno-omit-frame-pointer",
                    "-I", str(root / "KernelSU-Next/kernel/selinux"), str(c), "-o", str(exe)], check=True)
    subprocess.run([str(exe)], check=True)

# Compile the production write entry points with a minimal isolated database.
policy_source = (root / "KernelSU-Next/kernel/selinux/sepolicy.c").read_text()
source = policy_source
write_functions = "\n".join(block(x) for x in (
    "static bool add_type(struct policydb *db, const char *type_name, bool attr)\n{",
    "static bool add_typeattribute_raw(struct policydb *db, struct type_datum *type,\n                                  struct type_datum *attr)\n{",
    "static bool add_typeattribute(struct policydb *db, const char *type,\n                              const char *attr)\n{",
    "bool ksu_type(struct policydb *db, const char *name, const char *attr)\n{",
    "bool ksu_attribute(struct policydb *db, const char *name)\n{"))
write_fixture = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#define LINUX_VERSION_CODE 419
#define KERNEL_VERSION(a,b,c) 500
#define pr_warn(...) ((void)0)
#define pr_err(...) ((void)0)
#define pr_info(...) ((void)0)
struct type_datum { int value; bool attribute; };
struct symtab { unsigned nprim; struct type_datum *type, *attr; };
struct policydb { struct symtab p_types; unsigned sentinel[8]; };
static struct type_datum *symtab_search(struct symtab *s, const char *name) {
    if (!strcmp(name, "type")) return s->type;
    if (!strcmp(name, "attr")) return s->attr;
    return NULL;
}
/* PRODUCTION */
int main(void) {
    struct type_datum type = {1, false}, attr = {2, true};
    struct policydb db = { .p_types = {2, &type, &attr}, .sentinel = {17, 22} };
    struct policydb before = db;
    assert(ksu_attribute(&db, "attr"));
    assert(!ksu_attribute(&db, "new"));
    assert(!ksu_type(&db, "new", "attr"));
    assert(!ksu_type(&db, "type", "attr"));
    assert(!add_typeattribute(&db, "missing", "attr"));
    assert(!add_typeattribute(&db, "type", "missing"));
    assert(!memcmp(&before, &db, sizeof(db)));
    assert(type.value == 1 && !type.attribute && attr.value == 2 && attr.attribute);
    puts("PASS: blocked writes leave isolated fixture unchanged");
    return 0;
}
'''.replace("/* PRODUCTION */", write_functions)
with tempfile.TemporaryDirectory() as tmp:
    c = Path(tmp) / "write.c"
    exe = Path(tmp) / "write"
    c.write_text(write_fixture)
    subprocess.run(["/usr/bin/gcc", "-std=gnu11", "-g", "-O1", "-Wall", "-Wextra",
                    "-Wno-unused-parameter", "-fsanitize=address,undefined",
                    "-fno-omit-frame-pointer", str(c), "-o", str(exe)], check=True)
    subprocess.run([str(exe)], check=True)
