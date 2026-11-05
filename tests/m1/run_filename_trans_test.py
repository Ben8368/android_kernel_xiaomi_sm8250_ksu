#!/usr/bin/env python3
"""Exercise the production helper with structures and functions from this kernel."""
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]
ss = root / "security/selinux/ss"

def block(text, marker):
    start = text.index(marker)
    opening = text.index("{", start)
    depth = 0
    for pos in range(opening, len(text)):
        if text[pos] == "{":
            depth += 1
        elif text[pos] == "}":
            depth -= 1
            if not depth:
                return text[start:pos + 1]
    raise ValueError(marker)

policy = (ss / "policydb.h").read_text()
policy_c = (ss / "policydb.c").read_text()
bitmap_h = (ss / "ebitmap.h").read_text()
bitmap_c = (ss / "ebitmap.c").read_text()
hash_h = (ss / "hashtab.h").read_text()
hash_c = (ss / "hashtab.c").read_text()
definitions = bitmap_h[bitmap_h.index("#ifdef CONFIG_64BIT"):bitmap_h.index("#define ebitmap_length")]
definitions += bitmap_h[bitmap_h.index("#define EBITMAP_NODE_INDEX"):bitmap_h.index("#define ebitmap_for_each_positive_bit")]
definitions += "\n" + block(policy, "struct filename_trans {") + ";\n"
definitions += block(policy, "struct filename_trans_datum {") + ";\n"
definitions += hash_h[hash_h.index("#define HASHTAB_MAX_NODES"):hash_h.index("struct hashtab_info")]
functions = "\n".join(block(text, marker) for text, marker in [
    (hash_c, "int hashtab_insert("), (hash_c, "void *hashtab_search("),
    (bitmap_c, "int ebitmap_get_bit("), (bitmap_c, "int ebitmap_set_bit("),
    (bitmap_c, "void ebitmap_destroy(")])
test = (root / "tests/m1/filename_trans_test.c").read_text()
allocator = next(line for line in test.splitlines() if line.startswith("static void *kmem_cache_zalloc"))
test = test.replace(allocator + "\n", "")
allocator = allocator.replace("struct_hashtab_node_placeholder", "struct hashtab_node").replace("struct_ebitmap_node_placeholder", "struct ebitmap_node")
test = test.replace("/* NATIVE_DEFINITIONS */", definitions + "\n" + allocator)
test = test.replace("/* NATIVE_FUNCTIONS */", functions)
test = test.replace("/* NATIVE_FILENAME_HASH */", block(policy_c, "static u32 filenametr_hash(") + "\n" + block(policy_c, "static int filenametr_cmp("))
with tempfile.TemporaryDirectory() as tmp:
    source = Path(tmp) / "fixture.c"
    binary = Path(tmp) / "fixture"
    source.write_text(test)
    subprocess.run(["/usr/bin/gcc", "-std=gnu11", "-g", "-O1", "-Wall", "-Wextra", "-Werror", "-Wno-unused-parameter",
                    "-fsanitize=address,undefined", "-fno-omit-frame-pointer",
                    "-I", str(root / "KernelSU-Next/kernel/selinux"), str(source), "-o", str(binary)], check=True)
    subprocess.run([str(binary)], check=True)
