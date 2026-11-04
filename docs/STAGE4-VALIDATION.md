# 第四阶段：安全收紧与架构可行性

日期：2026-11-04（Asia/Shanghai）。起点 `7f9c153e61fd2c8e970a9c63a421500a274f8470`，工作分支 `lineage-24.0-ksu`。PR #1 保持 Draft；默认分支、驱动和原生安全配置不变。

结论：**NO-GO，针对当前 v1.1.1 直接 su 架构在保留 App Seccomp 下实现普通应用通用 Root 的目标。** 局部内存修复和策略收紧有价值，但不解除整体阻断；不再在该执行链上添加跳过 syscall 的兼容补丁。独立受控服务是另一个需要完整威胁模型、实现和认证审查的项目，本轮没有引入服务。

## 改动范围

| 项目 | 当前状态 | 可检查材料 |
|---|---|---|
| Seccomp 原因与候选 | 官方 su 不兼容；仅受限命令不足以完成通用目标 | SECCOMP-FEASIBILITY.md、seccomp-policy.log、固定源码及 Git blob |
| allowlist 内存并发/生命周期 | 不可变 RCU 记录、调用方快照、统一发布/回收；host 并发测试通过 | 0009、allowlist-concurrency.log |
| UID/Manager 身份与完整撤销生命周期 | **未全部修复，BLOCKED** | ROOT-SECURITY.md：包/证书代次、Tracker、持久化、已有会话边界 |
| SELinux 通配/xperm | 删除 25 条含 ALL bootstrap 调用，含四条全 ioctl xperm；保留 22 个有限 kernel metadata/store 权限 | 0010、SELINUX-MATRIX.md、selinux-inventory.json、reviewed-kernel-metadata.te |
| SELinux 有效状态/neverallow | 公共 LOS debug policy 含 permissive su，补丁显式 enforce；完整目标 ROM 验证 **BLOCKED** | 固定 su.te、selinux-surface.log；没有虚构 policy 编译结果 |
| 就绪门禁 | 独立七项；日志/源码/补丁绑定；未知仍 BLOCKED | check-ksu-readiness.py、ksu_readiness.py、readiness-negative.log |
| 真机启动/Root | **未测试** | 没有 adb/fastboot/刷写/重启或 Boot 发布 |

新增可用性限制：1024 条 profile 上限、GFP_ATOMIC 失败返回拒绝、密集写入可能使稳定快照拒绝；runtime policy mutation 返回 EOPNOTSUPP，未配置目标 policy 的 init/PTY/模块行为可能失败。没有把这些限制称为通用 Root 成功，也不宣称整体最小权限或无新增风险。

## 回归入口

在原生 WSL Linux checkout 中，先配置 gcc/g++、pkg-config、liburcu-dev 和既有 cryptography 依赖；不在 Windows sparse checkout 构建。

```bash
python3 tools/prepare-ksu.py
python3 tools/test-ksu-stage4.py --assets /absolute/path/to/pinned-assets --out /absolute/path/outside-checkout
python3 tools/check-ksu-readiness.py
# 另行重新校验本地完整产物字节：
python3 tools/check-ksu-readiness.py --build-dir /absolute/path/to/build
# 退出码 2 表示 BLOCKED；不是测试故障，也不是刷机许可。
```

suite 保留原第三阶段补丁重放、源污染拒绝、签名错误、协议/ABI/边界、官方 APK 密码学、独立合成 Boot 格式测试，再添加 liburcu 并发、LOS Seccomp parser/继承、SELinux 表面和就绪负向测试。日志输出在 checkout 外生成，避免“干净源码”检查被测试自身污染；之后才归档。

校验材料的 checksum 是本地可检查证据绑定，不是独立审计方签名。填入 PASS boolean 不能使静态审查、目标策略、Boot 输入或真机状态通过；host 结果仅能证明对应离线测试。源码/补丁/工具/快照变更或日志篡改会令对应 gate BLOCKED。

## 真实构建和离线结果

完整构建使用全新 WSL checkout 和全新输出目录，源码提交 `1a8fe03c7a70e9d559a14aaebbc8acde615a4ea2`，完整补丁队列首次重放并经 pre/post 整树证明。最终构建进程由 Python subprocess 直接捕获 **exit=0**；2026-11-04 05:32:41–05:40:49 UTC（上海 13:32:41–13:40:49）。

- Android Clang r596125 / 22.0.2，工具链逐文件锁校验通过；原 LTO/ThinLTO/CFI/Seccomp/SELinux 配置未改，`.config` SHA-256 `cd083b1ff199fa679236ba82edd9ce9b270e2a1d39ce5379da5ce44b9e00889c`。
- Image/modules/dtbs、最终 AArch64 链接和 CFI 编译参数通过；3 个模块、3 个 DTB、12 个 DTBO；没有未解析强符号。
- Image SHA-256：`f2b60e45ca862ef001e9afcc78b8c7e6b568f65852feea36c6cbbf1a2946872d`。
- vmlinux SHA-256：`494f0eb87804685afc0fefa32e5687c62b221842ebb83ae6e314d0f0852b7a5c`。
- 补丁队列 SHA-256：`b714e84b3ea4bb27e49845d95bcc553469757f6903d69239b05ad825ef75da40`；每个补丁和每个有效 KSU kernel 文件的 hash 在 provenance.json/source-before.json。
- release：`4.19.325-cip136-st20-perf-g1a8fe03c7a70-dirty`。保留事实上的 `-dirty`，expected_patch_dirty=true / unexplained_dirty=false；没有隐藏补丁工作树。
- 真正编译的 Manager 证书和 CFI flags 已再次检查，见 build-contract.json；没有改签 Manager 或替换官方资产。

首轮同源码构建也到 SUCCESS，但 shell 启动器的退出码变量未正确保存，未把空文件当作 exit=0。最终从新 checkout 重建并直接捕获退出码；首轮原始日志/provenance 和 launcher-note.txt 一并保存。两次 `.config` 相同、Image hash 不同，源码绝对目录也不同；没有完成差异归因，**不承诺按字节可复现**，比较见 repeat-build-comparison.json。验收采用上述最终产物。

后续提交只改离线验证工具/文档/证据，不把它们的 SHA 冒充已构建 SHA。门禁比较当前全部有效 KSU hash、补丁队列和原生树/构建输入 blob；与构建输入不一致就 BLOCKED。

完整产物目录：`/home/xiaoluo/umi-ksu-stage4/build-final`；干净源码：`/home/xiaoluo/umi-ksu-stage4/build-final-source`；维护源码：`/home/xiaoluo/umi-ksu-stage4/source`。官方资产仍在 `/home/xiaoluo/umi-ksu-stage3/assets`。

完整 suite 的真实提交、各命令退出码、日志哈希和输入 fingerprint 由 offline-results.json 记录。最终七类结果由 readiness-result.json 记录；日志中“正确报告 BLOCKED”的 PASS 不能解释为 Root 安全通过。

## 阻止人工真机测试的条件

1. 当前普通应用 Root 路径不符合目标；尚无受审独立服务。Manager 能检测内核不代表通过。
2. Manager/UID/package/certificate 生命周期、持久撤销和 credential hook 上下文问题未全部解决；没有目标内核 lockdep/KASAN/KCSAN/CFI 运行证据。
3. 未提供精确 ROM 的完整 policy 和所有分区策略输入，不能做目标编译/neverallow/有效 enforcing 域验证。
4. 未提供精确 ROM Boot/ramdisk/DTBO/vbmeta/recovery/target-files、AVB 和已验证恢复材料；没有构建测试 Boot。
5. 无真机 kprobe 注册、启动、充电、触摸、指纹、Wi-Fi、授权/未授权/撤销 Root 的日志。

完整软件阻断解除、Boot 输入匹配和人工操作授权是不同条件；本轮不自动刷机、不发布 Boot、不合并默认分支、不 force push。

## 最终套件与就绪状态

完整 suite 在 `41229786ab624210a9465773a7ebfab3bab0b9eb` 的已提交父仓库上运行，7/7 组退出码均为 0。具体命令、输入指纹和日志 hash 见 offline-results.json；PASS 输出行数为 `{"stage3-suite": 82, "allowlist-concurrency": 4, "seccomp-policy": 4, "selinux-surface": 2, "readiness-negative": 8, "protected-native-tree": 2, "build-evidence-negative": 6}`，这些行包含正确拒绝坏输入和正确识别 BLOCKED，不能等同于设备功能数量。

最终门禁在实际产物重新计算 SHA-256 后：编译 PASS、离线兼容 PASS；整体静态安全、目标 ROM policy、精确 Boot 输入、真机启动、真机 Root 均 BLOCKED；manual_device_test_ready=false / NO-GO。readiness-result.json 和全部原始日志在 docs/validation/stage4。

最后的证据提交只补文档/日志/摘要，不改内核、补丁、工具或测试输入；门禁的当前代码/快照 fingerprint 仍须匹配 suite。
