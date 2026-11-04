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

本节在最终归档时补齐实际构建 SHA、Image/队列 hash、完整命令/日志和 suite 提交。历史第三阶段 Image 不用于第四阶段验收。

## 阻止人工真机测试的条件

1. 当前普通应用 Root 路径不符合目标；尚无受审独立服务。Manager 能检测内核不代表通过。
2. Manager/UID/package/certificate 生命周期、持久撤销和 credential hook 上下文问题未全部解决；没有目标内核 lockdep/KASAN/KCSAN/CFI 运行证据。
3. 未提供精确 ROM 的完整 policy 和所有分区策略输入，不能做目标编译/neverallow/有效 enforcing 域验证。
4. 未提供精确 ROM Boot/ramdisk/DTBO/vbmeta/recovery/target-files、AVB 和已验证恢复材料；没有构建测试 Boot。
5. 无真机 kprobe 注册、启动、充电、触摸、指纹、Wi-Fi、授权/未授权/撤销 Root 的日志。

完整软件阻断解除、Boot 输入匹配和人工操作授权是不同条件；本轮不自动刷机、不发布 Boot、不合并默认分支、不 force push。
