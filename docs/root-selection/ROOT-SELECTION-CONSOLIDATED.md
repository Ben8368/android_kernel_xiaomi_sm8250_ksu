# umi Root 方案总报告

日期：2026-11-04。目标：Xiaomi Mi 10（umi）、LineageOS 24.0、Android 17、Linux 4.19.325。综合依据：本目录 [实际选型报告](ROOT-PRACTICAL-SELECTION.md)、仓库原始 [架构决定](../ROOT-ARCHITECTURE-DECISION.md) / [APatch 可行性](../APATCH-FEASIBILITY.md) / [安全审计](../ROOT-SECURITY.md)，以及 [KSU Next v3.4.2 与 dev 源码及移植矩阵](KSU-NEXT-SOURCE-PORTABILITY-MATRIX.md)。

**最终结论：推荐官方 Magisk 作为首选验证路线，但并未批准部署；当前总体状态 BLOCKED。** 现有 Magisk 审查中，授权缓存、UID/Manager 身份生命周期、撤销持久性、发行二进制与认证修复归属及目标策略仍有未闭环项。APatch 有已知认证问题且发行修复归属不明。KSU v3.4.2 仍有授权失败路径和身份生命周期阻断；dev 修复了真实缺陷，但对 4.19 的 Seccomp/SELinux/接口移植量明显违背避免长期大规模内核补丁的目标。若无法排除未经授权提权，结论必须保持 BLOCKED，不以设备暂缺或版本更新为理由降级。

没有任何候选获得 GO。当前实际使用应维持未 Root 的原生 LineageOS。这个推荐是“优先验证 Magisk”的相对排序，不等于安全认证或硬件完整性证明绕过承诺。

## 安全验收边界

- 普通 Android 应用默认拒绝，只有用户事前明确授权的应用可按授权执行 Root 任务。未授权应用不得获得 Root、Manager 身份或写授权状态的管理权限。
- 必须验证调用主体的内核 UID/PID、Manager 认证、应用签名/安装身份、shared UID、多用户、isolated UID、UID 重用、并发授权与撤销。包名或 UI 提示不能单独作为身份凭证。
- 已授权 Root 任务可拥有必要且明确记录的能力、Seccomp 或 SELinux 例外。例外应局限于专用 Root worker/可信管理组件；不得无关应用全局关闭 Seccomp、SELinux、CFI、neverallow 等安全措施，也不得伪造检测结果。
- 撤销至少要求撤销确认后的新会话拒绝，并证明状态已持久化。撤销不等于杀死已 Root 的既有进程、回收其派生子进程或撤销已完成的系统修改；这些需分开记录和处理。
- 完整 UID 0 是高信任能力，授权应用可能修改系统和授权存储或转授权限。若产品要求“应用可完整 Root，但绝不能影响授权管理/其他应用”，三方案都不满足，需另建受限特权服务；本次按用户明确授权完整 Root 的权限例外评估。

## 推荐与方案比较

| 方案 | 使用模式与优势 | 关键未决风险 | 4.19 / OTA 维护成本 | 决定 |
|---|---|---|---|---|
| **官方 Magisk** | 用户态 su daemon 和授权 worker，最符合普通应用实际 Root 工作流；不必在本地长期维护 KSU 内核 API 补丁。以无模块、Zygisk 默认关闭开始，减少额外组件 | 已审查 v31.1 存在约 3 秒 SuInfo 授权缓存，数据库撤销没有同步失效；Manager UID/包身份与重用生命周期未闭环；写库失败/持久化 ACK 需测；发行 APK/daemon 的签名证书 pin、构建开关与修复归属未完全验证；policy 对 zygote/system_server 的 execmem 等公共影响需目标 ROM 审查 | **相对最低**：每个目标 ROM 仍重新取 boot/AVB/策略/恢复材料，检查新附件并做 OTA/撤销回归；不意味着无需维护 ramdisk/daemon | **第一验证候选，BLOCKED** |
| APatch / KernelPatch | 无 LOS 内核源码大补丁，通过 kernel patch 框架实现 Root；提供 Manager 与 su | 已知管理命令认证/tag 路径问题：旧 tag 认证比较曾未核完整密钥长度，后续 key/授权修复不能确认进入 release kpimg；Manager 陈旧 UID、标签命令门禁/持久化需实测；release binary 与精确源码/修复提交归属不清 | **中到高**：无需 LOS 源码 cherry-pick，但每次目标内核/boot 变化均需重新确认符号、偏移、Hook、CFI、启动和发布归属。4.19 可运行线索不是当前 LOS24.0/4.19.325 证据 | **不推荐作为 Magisk 被阻断后的自动替代，BLOCKED** |
| KSU Next v3.4.2 | 内核 allowlist + Manager/ksud，KernelSU 风格应用 Root | 相比 v1.1.1 已改 RCU/kref、APK parser、凭据流程、UID 记账，但 Manager identity、授权/profile 竞态、持久撤销和 profile 失败后继续提交 creds 仍阻断 | **高**：4.19 没有现代 Seccomp filter API、mount API 和 SELinux policy 数据模型；fsnotify/task_work/文件操作/CFI 均需适配并持续跟踪 | **不采用** |
| KSU Next official dev | 吸收 v3.4.2 之后的源码修复：fsnotify mark 释放、临界区日志、file ref 和 SELinux grant generation 等 | 上述核心 Manager/授权生命周期问题未被比较到的提交关闭；不能用“dev 更新”推断安全闭环 | **最高**：100 commits ahead；把修复逐项语义回移植到 4.19 需要维护 fork，不应整体搬运现代 SELinux/Seccomp 接口 | **研究参考，不是可刷版本；BLOCKED** |

因此不因 v3.4.2 能编译而优先旧版；也不因 dev 对 4.19 编译不通过而忽略它的安全修复。理想的研究基线是理解并单独保留 dev 修复语义，但目前没有获准或安全闭环后的 KSU 移植方案。

## KSU 源码结论摘要

v1.1.1 的多项问题在 v3.4.2 **确有修复**：APK SHA 错误码检查及解析边界；授权表从裸指针/分叉缓存改为 RCU hash + kref；exec 提权转到 syscall 分派路径并在新 cred 上修改；UID/user 记账；session FD 的 ioctl 权限边界；Manager tracker 的部分解析与包 UID 绑定改进。

仍未关闭的事项：Manager pin 可选且缓存只使用 appId/package+UID 的不完整身份；跨用户 UID 取模与 UID 重用、重装换签的身份代次问题；授权和 profile 分开查询、撤销时竞态及默认 profile 回退疑点；groups/SELinux profile 配置失败仍可能 commit creds；保存文件非原子、0644、忽略 profile 短写、load 部分导入；新撤销 ACK 不是落盘证据。

官方 dev 相对 v3.4.2 的明确修复包括：`786f73e6…` 修 fsnotify mark free/drain；`c7e66ae0…` 平衡 wrapper file 引用；`b462d4c1…` 移除原子临界区逐线程日志；`48501dad…` 传递 SELinux grant generation。它们应作为不可忽略的修复要求；但 dev 仍不是安全完成版。v3.4.2 内核/ksud 使用 UAPI 5、profile ABI 4，dev 的内核/ksud UAPI 已变为 6；`ksud` 对 UAPI 精确匹配，Manager 的 legacy GET_INFO 只是探测回退。发行 APK/内嵌 ksud 与固定源码/内核证书 pin 的映射尚未验证，不能混用旧版用户态来规避兼容问题。

## 目标兼容性证据与未知项

现有目标树内核原生源码锁定在 LineageOS commit `6b34d24765327d746074c8e53b5ad0d24a51acc7`。证据显示 4.19 seccomp 结构为 `usage/prev/prog` 并提供 `put_seccomp_filter()`；无 Next 当前依赖的 filter_count/seccomp_filter_release/action cache 语义。ARM64 secure_computing 早于 syscall tracepoint，影响 reboot 握手，但不能据此误称所有 su 执行路径都不可用：Manager 继承 FD、ksud driver-FD 扫描、已授权 su exec 分派是分离路径，尚未在目标完成端到端验证。SELinux 是旧 security server 模型，Next 现代 `selinux_policy/policy_mutex` 接口不能直接套用。`path_mount/path_umount` 不存在；fsnotify 使用旧 handler 原型但存在 `free_mark` 和 mark drain API；task_work 使用 bool notify。target clang 有局部 `__nocfi` 属性，但不能代表所有 CFI/间接调用/动态文本修改安全。

目标设备能否启动、是否支持某一实际镜像方案、应用 ABI、实际 SELinux policy/neverallow、Seccomp 路径、AVB 链、槽位、bootloader 解锁、恢复可达性、硬件与 OTA 均未知。此前设备配置只表明非 VAB 配置候选有 header v2、页大小 4096、独立 DTB section 等，配置含 VAB 条件分支；它不能替代对用户手中 ROM 文件的解析。Android 17 的组件版本声明不能代替 umi 上实际授权链测试。

## 必须取得的精确 ROM 文件

不得臆造 ROM 日期或文件名。先只读设备记录完整 fingerprint/build ID/incremental、SPL、内核版本、bootloader 状态和活动槽位，再取得与**同一当前安装版本**逐项对应的文件；OTA 演练还需下一目标构建另一套文件与溯源。

| 材料 | 精确要求 |
|---|---|
| 完整 LineageOS ROM 包 | umi / LOS 24.0，精确匹配当前 fingerprint、build ID 和增量版本；提供官方/维护者来源、包大小、SHA-256、签名校验方式/可信公钥。若非官方构建，记录构建者及签名身份 |
| 同次构建启动/恢复镜像 | 原始 `boot.img`、`recovery.img`、`dtbo.img`、`vbmeta.img`；存在时加 `vbmeta_system.img`、`vbmeta_vendor.img`、`vendor_boot.img`、`init_boot.img` 及真实启动链成员。只有分区确实存在才纳入，不因 Android 17 推定 init_boot 存在 |
| target-files ZIP（优先） | `IMAGES/` 实际镜像；`META/misc_info.txt`、`ab_partitions.txt`、`dynamic_partitions_info.txt`（若存在）、分区映射、OTA keys；相关分区 build.prop、fstab/rc、策略。普通 OTA ZIP 不自动等价 target-files |
| 完整 SELinux 输入 | 同构建 system/vendor/product/system_ext/odm CIL、mapping、contexts、precompiled/runtime policy（若有），以及可复现实际加载策略的文件 |
| 源码/内核构建来源 | repo manifest 全部 revision、device/common/kernel/vendor 仓库修订、实际 `.config`、编译器/链接器版本、原始 Image/DTB 哈希、内核 release、SPL；用于验证 CFI、Seccomp、AVB 与实际内核一致 |
| OTA 数据 | OTA metadata、payload.bin/payload_properties 或对应更新脚本、addon.d/backuptool 组件与执行时序；标识 full/incremental 的源/目标版本及槽位行为 |
| 恢复资料 | 精确匹配的固件需求、可信恢复包/官方流程、bootloader/recovery 实际可达性、userdata 加密/解密和数据备份方案。不要提供或索取私钥、设备密钥/账号口令 |

不完整 target-files 可先做部分只读分析，但缺失策略、布局、签名来源、恢复路径任一关键证据，状态继续 BLOCKED。只接受从可信来源取回的原始文件，不拿其他日期、MIUI 或其他机型镜像替代。

## OTA 后维护成本

三个方案都不能假定旧启动组件与新 system/vendor 兼容，也不应假设 OTA 自动保留 Root。

- **Magisk：相对最低**。每个 ROM 版本检查原始 boot/AVB/ramdisk 和 patch 流程、匹配官方 APK/daemon、权限策略、授权撤销和完整性；测试 OTA 前后的启动与恢复。禁用不需要的模块/Zygisk，审计 addon.d/backuptool 是否自动修改新 boot。源报告中的 Magisk OTA 文档对 A/B 和 A-only 路径有区分，不能从通用文档推断 umi 的实际槽位/自动保留支持。
- **APatch：中到高**。每次新 kernel/image 重新匹配注入点/符号偏移、Hook/CFI、启动可靠性和 kpimg/Manager 的确切来源及修复提交，回归授权与恢复。
- **KSU：高**。每次 LOS 上游合并要重新应用并审查大量接口和安全补丁、更新现代/4.19 条件代码、内核完整构建、真实 policy/CFI 运行时测试、Manager/ksud ABI 对齐、目标设备授权和 OTA 回归。盲目 cherry-pick dev 或长期挂大补丁均不可接受。

第一次 OTA 目标应是先验证纯净 ROM 正常升级和恢复；只有连续两版完整演练成功后，才讨论 Root 自动保留。每版保存更新前后的原始启动材料与哈希，重新测试默认拒绝、已授权成功、撤销后新请求拒绝、重启后状态以及无关 app 安全边界。

## 分阶段离线与人工验证

以下是未来门禁，不是已执行结果；用户本轮仅授权只读研究和文档。没有生成镜像、安装 APK、刷机或更改 KSU 分支。

| 阶段 | 工作 | 通过/停止条件 |
|---|---|---|
| 0. 只读源码复核（已完成） | 固定三版源码、dev compare patch、目标内核 API，完成本文和矩阵 | 源码结论有固定 commit；不声称目标编译或设备 PASS |
| 1. 精确 ROM 与发布材料 | 获取上述 ROM/target-files/策略/恢复材料；只读解析镜像布局、AVB、boot header、ramdisk、DTB、槽位；检查 APK/daemon/Manager 签名和源码归属 | 任一文件版本不匹配、签名链不明或恢复路径不可行即 STOP；解析器通过不等于可刷 |
| 2. 离线安全阻断审查 | Magisk：SuInfo 缓存撤销、UID/Manager 代次、IPC peer identity/FD/PID、DB 错误持久化、policy 公共影响、发行件 pin。APatch：完整 tag/key 授权、Manager 生命周期、release 来源。KSU：profile 原子授权、fail-closed、撤销事务、dev 安全修复映射与 4.19 API 设计 | 任意未授权身份可写管理状态、获得新 Root，或二进制修复归属不明，保持 BLOCKED；先要求实现/发行者提供可审计修复和新固定版本，再独立复核 |
| 3. 隔离人工安全测试（另行授权后） | 可先在 disposable 测试环境/备用设备验证 Manager、协议和 UID 生命周期；真实产品只在有恢复能力的目标设备执行 | 真实调用 UID/PID、签名、SELinux domain、Seccomp 状态、返回码和持久状态均记录；不模拟/篡改检测结果 |
| 4. 目标设备最小 Root 验证（另行授权后） | 无模块/Zygisk 基线。先确认原生启动与恢复，再测未授权拒绝、事前批准后实际只读 Root 任务、撤销和重启后拒绝 | 未授权 app 在 direct su/伪造请求/session FD/Manager 操作全部拒绝；已授权任务成功；撤销确认后新请求失败且重启保持。并发中已开始会话按线性化点单独记录 |
| 5. 生命周期、日常功能与 OTA | 卸载/同包重装/换签/UID 重用/shared UID/多用户/isolated UID；存储满/写失败/掉电/重启；目标应用工作流；硬件功能和下一 ROM OTA/恢复演练 | 每种故障均无授权扩大；完整 Root 既有会话与新请求区分；USB/蜂窝/Wi-Fi/蓝牙/相机/睡眠/热控/PD-PPS 等目标功能正常；OTA 后重新验证安全门禁 |
| 6. 决策 | 汇总固定 ROM/Root/Manager/daemon 哈希、来源、测试日志、权限例外清单、OTA 和恢复记录 | 所有安全 BLOCKED 关闭才可单独讨论 GO；Root 检测全绿、编译成功或能启动均不是安全验收 |

**失败恢复纪律**：任何未来刷写前必须先验证 bootloader/recovery 可达并保存当前已安装版本对应原始镜像。Root 不工作但可启动时停止功能扩展，使用匹配 ROM 的官方恢复组件/卸载路径；bootloop 时只恢复当前安装版本真实受影响分区，先判活动槽位及 rollback 状态。OTA 失败不代表旧 system/vendor 仍完整；禁止盲切槽、混刷旧 boot、随意改 vbmeta/锁 bootloader。若发生未授权 Root，隔离敏感用途并保全日志，恢复可信原生状态；仅删除 grant 或重刷 boot 不证明已消除完整 Root 的持久修改。不得承诺 EDL 可用或数据必不丢失。

## 最终决定

1. 验证投入排序：**官方 Magisk > APatch > KSU**；这是以使用成熟 daemon 工作流、降低内核长期维护为目标的相对排序，不是信任背书。
2. 当前状态：**全部 BLOCKED，不安装、不刷写、不生成镜像**。维持原生 LineageOS。优先收集精确 ROM 文件并关闭 Magisk 已知安全与发行归属项。
3. KSU 后续只允许只读研究。v3.4.2 和 dev 的源码对照及 4.19 兼容差异见配套矩阵；不得为得到 GO 跳过新修复或把不兼容直接删掉。
4. 已知认证缺陷和 release artifact 对源码/修复提交的归属问题是硬阻断项。只要存在无法排除的未经授权提权风险，报告维持 BLOCKED。

## 研究范围与来源记录

既有 Magisk/APatch 报告及其源码快照、release metadata、目标 LineageOS 配置和历史 ROM 证据见 [前序报告](ROOT-PRACTICAL-SELECTION.md)和 [evidence](evidence/)。本轮 KSU 固定提交、官方 compare/release metadata、归档哈希和本地内核 API 快照见 [KSU evidence](evidence/ksu-next/)；原始完整源码归档只保留哈希记录，不在 PR 中复制上游整仓。本报告未复用“编译通过=安全”的判定。审查时实验仓库 `HEAD` 为 `7ed4c8426759601636d108679b6df3e60c1db94f`，工作区 clean；本 PR 文档提交不改动其内核实验内容。
