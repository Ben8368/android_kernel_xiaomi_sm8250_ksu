# M1 Round 6: type index read groundwork, writes BLOCKED

This is a partial slice, not an implementation of type creation or attribute
updates. For Linux 4.19, new type creation and all type-attribute associations
return false before mutation. Duplicate type creation retains the old
idempotent result. `ksu_type` therefore also fails to add the association for
an existing type. The isolated policydb and caller serialization requirements
are not enforced by the current caller and active policy operations are unsafe.

The new zero-based readers use `flex_array_get_ptr` for pointer elements and
`flex_array_get` for in-place bitmaps. They check both `nprim` and flex-array
capacity, and the value helper rejects zero before converting a one-based type
value. They are groundwork and are not yet used by production call sites.
No flex-array growth or ebitmap ownership transfer is implemented.

## Verification

- `out/m1-round2/m1-round6-type-final.{log,json,exit}`: exit 0. GCC
  ASan/UBSan exercised the production readers and 4.19 blocked write entry
  points. The reader fixture extracts five functions from the target
  `lib/flex_array.c`; the layout, allocation, reciprocal division and policydb
  are host shims. It tests first/last, missing part, zero and out-of-range
  values, a shortened backing array, and frees its allocations. The write
  fixture uses extracted production functions but a shimmed symbol lookup and
  minimal policydb; it checks bytewise unchanged state after blocked operations.
  It does not test a real hashtable, expansion, ebitmap nodes, role/constraint
  mutation, allocation or insert failure, or full policydb destruction.
- `out/m1-round2/m1-round6-filename.{log,json,exit}`: exit 0; previous filename
  compatibility fixture passes with GCC ASan/UBSan.
- `out/m1-round2/m1-round6-sepolicy.{log,json,exit}`: exit 1. The exact prior
  Kbuild compiler command reports first `sepolicy.c:949` incomplete
  `struct selinux_policy`; earlier type-index diagnostics do not appear.
- `out/m1-round2/m1-round6-build.{log,json,exit}`: exit 2, first error is
  `rules.c:54` missing `selinux_state.policy_mutex`. This was not a Hangup.
- `out/m1-round2/m1-round6-replay.{log,json,exit}`: exit 0; official v3.4.2
  clean archive plus queue compared equal to 441 live submodule files. Manifest
  SHA-256 `8a1024adf43ad86cf801f6a9a2b86b00ef1de97b23f5c760dfac8eceff8d60b9`.
- Patch SHA-256
  `c92d79a079d6c3cb8b5a5db141b0bce34afb6ec431b87bc213fa16912a3fc6a6`.

Build and test recordings preceding patch regeneration refer to the previous
patch hash; they compiled/tested the same live source later verified by replay.
Full logs and exit records are retained in untracked `out/`.

Remaining work: prepare all three expanded indexes and deep-copy bitmap nodes,
stage role and constraint bitmap changes, check each allocation/put/insert,
commit and clean up atomically under an enforceable isolation contract, and
exercise failure injection and policydb destruction. Active-policy publication,
locking, authorization and permission safety remain separate unresolved risks.
