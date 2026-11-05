# M1 Round 5: Linux 4.19 filename transitions

The new helper uses the target `struct filename_trans` key (including source
type) and the target three-argument `hashtab_insert`. `services.c` checks the
target type value directly in `filename_trans_ttypes`, not value minus one.
An identical key and output is idempotent; the same key and a different output
is rejected without changing the datum. Different source types are separate
keys. A successful insertion transfers the key, name and datum to policydb;
on failure the helper frees only its own allocations. A bit newly set before
insertion is cleared on insert failure; the target's clear operation does not
allocate. This assumes serialized access to an isolated, mutable policydb.
No active policy publication or transaction safety is provided here.

## Verification

- `python3 tests/m1/run_filename_trans_test.py`: exit 0 under GCC 13.3 with
  `-fsanitize=address,undefined`, no sanitizer findings. The fixture extracts
  the target filename and bitmap structures, native hashtab insert/search,
  bitmap get/set/destroy, and policydb filename hash/comparison bodies. Kernel
  allocation, symbol tables, surrounding policydb and name-hash primitive are
  host shims; it is not a complete kernel policydb test. It covers new and
  existing entries, conflict, distinct source, missing symbols, every new
  allocation failure, bitmap failure, hash allocation and maximum-table
  failures, rollback with and without a pre-existing bitmap bit, duplicate
  bitmap repair failure, and tracked frees. No running policy is touched.
- First test attempt used the Android clang and exited 1 because its host
  ASan runtime is absent; the successful test uses `/usr/bin/gcc`.
- Requested top-level `make ... -j4 Image modules dtbs`: exit 2; first error
  is `rules.c:54` missing `selinux_state.policy_mutex`. Log and recorder:
  `out/m1-round2/m1-round5-build.{log,json,exit}`. The build ran before the
  version guard was narrowed from 5.9 to 5.7; both select the same helper on
  this 4.19 kernel.
- `python3 tests/m1/compile_sepolicy_from_kbuild.py`: exit 1, rerunning the
  exact compiler command printed by the previous Kbuild `V=1` log, with the
  configured output directory and toolchain. No filename transition errors;
  the first remaining errors are `sepolicy.c:712` missing
  `policydb.type_val_to_struct` and `:729` flex_array/ebitmap mismatch. This
  is not a successful object build. Log: `out/m1-round2/m1-round5-sepolicy-compile.log`.
- Clean official v3.4.2 archive plus complete queue: exit 0, 440 regular files
  byte-compared to the live patched submodule, including new files. Manifest
  SHA-256 `8774b962888a11647e3ba65d5db26e2aeb420cbd33f9ba81c755d73ef458e81b`.
- Queue SHA-256: `74b35bcc7c1b03cb7428da1d39d74cd23d718b31d60ed72367de799b3235f98b`.

Full M1 remains PARTIAL. Type index/attribute maps, policy publication, locks,
SID/AVC generation, Seccomp and mount helpers are outside this slice.
