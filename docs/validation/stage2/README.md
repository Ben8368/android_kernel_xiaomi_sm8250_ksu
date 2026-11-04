# Stage two evidence index

The authoritative final result is final-verification.json and the corresponding
final-clean-build.log, produced in a new empty output directory build-final.
The recorded build invocation commit and effective KernelSU file hashes identify
the compiled code; later documentation-only commits do not retroactively change
that identity. See docs/BUILD.md for restrictions and the error-to-fix table.

- final-clean-build.log: complete final build stdout/stderr, with commands,
  compiler identity, config generation, all target compilation/link steps.
- final-verification.json / final-link-verification.log: independent ELF,
  undefined-symbol, CFI, security config and actual artifact validation.
- final.config / final-key-config.txt: exact final config and key settings.
- final-artifacts.sha256 / final-dt-package-verification.json / final-dtbo-dump.txt:
  actual generated files and DT image entry validation.
- final-symbol-evidence.txt: linked KSU, CFI, seccomp and SELinux symbols.
- final-effective-ksu.diff: exact local submodule changes from official v1.1.1.
- patch-replay-test.log: clean application of all seven patches and byte match.
- signature-error-tests.log: extracted certificate check with injected failures.
- build-input-files.json / tools/umi-toolchain.lock.json: inputs and tool hashes.
- source-security-audit.txt: unchanged native security source and candidate limits.
- sources/: official source snapshots and immutable-source hash checks.
- v3.4.2-clang22-full-build.log: diagnostic with generic Soong default Clang
  r584948; not the actual cp2a formal compiler selection.
- v1.1.1-formal-attempt1..4.log: formal Clang errors that led to patches 3..6.
- formal-complete-build.log and formal-success-invocation.log: first successful
  link using patches 1..6. This predates the final su-enforcing patch and must
  not be substituted for the final seven-patch result.
- first-link-verification.log / dt-package-first.log: that earlier result.

No binary is asserted to be stable, bootable or authorized for flashing. The
original full outputs stay in WSL /home/xiaoluo/umi-ksu-stage2; generated kernel
binaries are not committed to Git. PR #1 remains an unmerged draft.
