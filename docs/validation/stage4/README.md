# Stage 4 evidence (offline only)

Build: build-console.log + build.exit (actual subprocess return code),
provenance.json/source-before.json, build.config, linked-verification.json,
build-contract.json, modules.sha256.json, artifacts.sha256 and DT packaging.
build-result.json binds these inspectable materials by SHA-256. The final
Image/vmlinux/modules/DT bytes remain in the native WSL output directory;
check-ksu-readiness.py --build-dir rehashes them separately.

first-build-console.log/first-provenance.json and launcher-note.txt preserve
the initial build whose launcher did not capture an exit code. Do not infer
an exit value from its blank launcher file. repeat-build-comparison.json
records different Image hashes and identical config; no reproducibility claim.

offline-results.json records actual commands/exits/log hashes and the code,
native tree, KSU source, queue and source-snapshot fingerprint. Source and
patch changes or altered logs invalidate the corresponding PASS.
readiness-result.json distinguishes seven independent categories.

sources.lock.json verifies SHA-256 and upstream Git blob identities for the
fixed public LOS/Magisk reference files. Public branch policy is not the exact
ROM's full platform/vendor/product/system_ext policy. selinux-inventory.json
and reviewed-kernel-metadata.te are review materials, not target neverallow
or functional Root results. No device or real Boot image was produced.
