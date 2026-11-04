# Xiaomi SM8250 kernel — experimental KernelSU Next integration

**DRAFT / NOT BUILDABLE / DO NOT FLASH.** This branch is an unfinished experiment for Xiaomi Mi 10 (`umi`), Linux 4.19.325 and LineageOS 24.0. It is not a released kernel. No boot image is provided. Root integration changes the device security model; a bad kernel can cause boot failure or data loss. Keep a tested recovery plan and backups.

`lineage-24.0` is the fork's upstream-tracking default branch. At inspection, both it and the official LineageOS branch were at `6b34d24765327d746074c8e53b5ad0d24a51acc7`. This experimental branch adds KernelSU Next v3.4.2 as a pinned submodule (`4c706b5938665866ebe16944a481a7b91e3396af`), driver wiring and `umi` configuration. Integration has **not** compiled successfully and has not been tested on a device. Official source: https://github.com/KernelSU-Next/KernelSU-Next .

Initialize using `git submodule update --init --recursive`. Run `tools/check-umi-config.sh` for an exploratory configuration check only; see [build notes](docs/BUILD.md). This does not replace the actual LineageOS Clang/LTO build or prove root functionality. No CI, scheduled synchronization or release workflow is implemented yet; see [maintenance](docs/MAINTENANCE.md).

Not verified: kernel link, DTB/DTBO, ROM build, boot, USB PD/PPS, fingerprint, touch, audio, networking, SELinux, manager authentication and root authorization. Do not flash any output from these experiments.
