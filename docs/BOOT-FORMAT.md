# umi LineageOS Boot 格式取证与离线准备

取证日期：2026-11-04。**没有收到目标 ROM 的官方 Boot/target-files，未制作可交给手机的测试镜像。**

## 固定官方来源

- LineageOS/android_device_xiaomi_umi @ 8e115b1ed63caa3ee5c3d52df0a7bce7c27512cd：BoardConfig.mk、device.mk。
- LineageOS/android_device_xiaomi_sm8250-common @ b84fe80a52e7407c53119d2dd6507285da8090d4：BoardConfigCommon.mk、kona.mk、rootdir/etc/fstab.qcom。
- LineageOS/android_system_tools_mkbootimg @ 808ecd09666ffe0ff5800f02af693abce56eb395（官方 lineage-23.0 分支中可获取的工具修订，**不是声称找到 lineage-24.0 工具分支**）。用于标准 v2 格式独立 fixture 验证，未来实际 ROM 必须按其 manifest 锁定自己的工具。
- 快照及各文件 SHA-256：docs/validation/stage3/sources.lock.json。其来源为官方 GitHub API 固定 commit；不随默认分支漂移。

## 源码支持的格式结论

| 项目 | 当前确认的非 VAB umi 候选 |
|---|---|
| Boot Header | v2，pagesize 4096，base 0 |
| Kernel | raw ARM64 Image；BOARD_KERNEL_IMAGE_NAME=Image |
| DTB | BOARD_INCLUDE_DTB_IN_BOOTIMG=true，在 header-v2 独立 DTB section；不是把 DTB 任意附到 Image 后 |
| DTB 合集 | 第二阶段按 Lineage BoardConfigKernel.mk 规则组合 kona、kona-v2、kona-v2.1，当前 dtb.img 与 Image 同次构建 |
| Ramdisk | 来自**目标同一次完整 ROM 构建** Boot 内的 init ramdisk；kernel 仓库不提供 |
| DTBO | 独立 dtbo 分区，BOARD_KERNEL_SEPARATED_DTBO=true；不可拿任意机型 overlay 替换 |
| Boot/recovery 分区 | 各 134217728 bytes（128 MiB），非 VAB 有独立 recovery |
| DTBO 分区 | 33554432 bytes（32 MiB） |
| AVB | BOARD_AVB_ENABLE=true；上游 vbmeta 生成参数含 --flags 3；fstab 对 system/vendor 等仍指定 avb 链 |

公共配置有 PRODUCT_VIRTUAL_AB_OTA=true→header v3、TARGET_IS_VAB=true→不同 boot/vendor_boot 和恢复布局分支。umi 已取到的 device.mk 未启用该分支，不能推广成任意 ROM 都是 v2。还需目标 ROM 的完整 product/vendor 配置及实际镜像核验；离线工具遇到 v3/v4 一律拒绝。

BOARD_INCLUDE_RECOVERY_DTBO=true 描述 recovery 构建需要 DTBO，不表示可把 recovery ramdisk 当正常 Boot ramdisk。不得从 GKI release 抽取 android12 boot、从其他日期 ROM 拿 ramdisk、从 MIUI 拿 DTBO 拼接当前 Image。

AVB footer/descriptor、vbmeta chain、rollback index、安全补丁日期、Boot OS version、cmdline/offsets 必须保留目标构建语义。改 kernel 会改变 hash descriptor，旧 AVB 签名不能沿用。上游 --flags 3 只是取证事实，不是本项目要求用户修改 vbmeta 或关闭验证；不得自动生成/刷入 bypass vbmeta。解锁状态及该 ROM 允许的测试路径由未来人工确认，不能随意重新上锁。

## 已实现与未实现

只实现 tools/inspect-umi-boot.py 只读格式门禁，不提供打包/刷写入口：

- 检查 Android magic、header-v2 size=1660、page size、各 payload 界限、ARM64 Image magic、ramdisk 编码、DTB header/范围与拼接、AOSP SHA-1 Boot ID、AVB footer 范围和不明尾数据。
- --target-files 要求一个 ZIP 同时包含 boot/dtbo/vbmeta/recovery 和 META/misc_info.txt，并检查 umi/Android 17/LineageOS 24.0 属性。**单 ZIP 只证明输入源单元，不证明可信发行或真实源码关系。** 仍要求人工核对官方来源和 manifest；工具显式 packaging_ready=false。
- AVB footer 存在仅代表范围检查，报告始终 avb_signature_verified=false，不假装完成签名/信任校验。
- 合成测试使用固定官方 mkbootimg 创建临时 v2 fixture，与独立 parser 对照，再验证 8 种错误输入被拒绝。fixture 用合成 kernel/ramdisk/DTB，只证明格式门禁，不是可启动 Boot。临时文件测试结束即删除。

未来在获得并核验目标同次 ROM 产物后，才能增加保留原始参数/ramdisk 的离线 packer，要求 AOSP unpack→pack→unpack 对照、payload hash、DTBO 表与 umi 对应关系、partition size、avbtool info/verify 与 ROM trust/rollback 策略审查。当前没有满足这些前置条件，因此**不能声称已经构建格式正确且适配目标 ROM 的测试 Boot 镜像**。

## 离线运行


tools/inspect-umi-boot.py 可用 python3 执行：

```bash
python3 tools/test-umi-boot-format.py
python3 tools/inspect-umi-boot.py --image /absolute/path/to/official-same-rom/boot.img
python3 tools/inspect-umi-boot.py --target-files /absolute/path/to/exact-umi-target_files.zip
```

本轮未执行后两条，因为没有真实 ROM 输入。不输出 fastboot/adb 写入或 reboot 命令。
