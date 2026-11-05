# KernelSU Next compatibility patch queue

Base: official KernelSU-Next v3.4.2 commit
`4c706b5938665866ebe16944a481a7b91e3396af`.

The parent repository tracks that exact commit as the `KernelSU-Next`
submodule. Kernel-internal compatibility changes stay in this queue and are
not committed into the upstream submodule history.

Start with a freshly initialized official submodule (do not checkout over local edits).
From the kernel repository root, replay with:

```sh
test "$(git -C KernelSU-Next rev-parse HEAD)" = 4c706b5938665866ebe16944a481a7b91e3396af
git -C KernelSU-Next apply --unidiff-zero --check ../patches/kernelsu-next/0001-linux-4.19-compat.patch
git -C KernelSU-Next apply --unidiff-zero ../patches/kernelsu-next/0001-linux-4.19-compat.patch
```

The queue is compile compatibility work in progress. The Linux 4.19 filename
transition helper is tested on isolated fixtures, not on an active policy.
It does not claim a working Seccomp reboot handshake or a complete SELinux
policy adapter; publication and transaction safety remain blocked.

For a non-destructive, clean-source replay test without changing the live
submodule, use `python3 tests/m1/replay.py /absolute/new/empty-test-directory`.
It refuses an existing destination and compares every archived regular file.

Use `python3 tests/m1/run.py --label unique-name -- COMMAND ...` to preserve
real child exit codes and provenance. All binary outputs and full build logs
stay in `out/` and are not committed.
