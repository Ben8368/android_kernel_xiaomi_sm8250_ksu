# 第五阶段：Root 架构决策

日期：2026-11-04（Asia/Shanghai）。项目：Ben8368/android_kernel_xiaomi_sm8250_ksu。评估基线：`lineage-24.0-ksu`，`45b868c5ae518543f691f9fcf4e8eb0cedf0cdce`。

**唯一推荐：维持 Root 项目 NO-GO，停止旧版 KSU 直接 su 路线的功能开发；原生 LineageOS 内核上游同步可独立推进。** 本轮没有找到在本目标上同时满足 Linux 4.19、保留所有应用 Seccomp、SELinux 有效 Enforcing、保留 CFI，并具有完整身份/撤销验证证据的成熟 Root 实现。没有推荐另写特权服务作为当前交付路线，也没有批准换用 Magisk。

Magisk 的独立 daemon 执行模型和现成用户态生态，在允许改变产品要求时具有较低的维护成本；但它不满足“内核原生 KSU”，且本次检查的官方默认 SELinux 策略将 `magisk` 域置为 permissive。在沿用第四阶段安全标准的条件下，不能把它直接列为 GO。目标 umi / LineageOS 24.0 的实际兼容性仍是**未知**。

## 1. 决策边界与证据等级

“通用 Root”在本文指：普通应用经可信 Manager 授权后，可以请求执行常见 Root 命令，包括需要 mount 等特权 syscall 的工作；不承诺让应用原进程摆脱自己的过滤器。必须区分应用内直接执行与向另一执行主体委托命令。

沿用 [ROOT-SECURITY.md](ROOT-SECURITY.md)、[SECCOMP-FEASIBILITY.md](SECCOMP-FEASIBILITY.md) 和 [SELINUX-MATRIX.md](SELINUX-MATRIX.md) 的标准：

- 不清除或放宽调用应用及其直接派生进程已有的 Seccomp，不改 syscall 检查次序，不改允许缓存以绕过策略。
- 不关闭 SELinux，不把 su/特权服务域设为 permissive；仅 `getenforce=Enforcing` 不足以证明相关域受到强制检查。不能用全通配 allow 取代有范围的策略审查。
- 不关闭 CFI，不把局部取消检查或未经验证的 hook 类型转换当作已经适配。
- 编译、主机 fixture、源码存在某个兼容分支，均不等于目标 ROM 真机已验证。缺少证据记为未知或 BLOCKED；明确违反约束的路径记为不符合。

本轮只读核查官方源码、发布元数据和已有证据，并新增本文。没有重新构建内核、运行 Android 服务、生成 Boot、刷机、操作 PR #1 或推送分支。第四阶段 [readiness-result.json](validation/stage4/readiness-result.json) 的 NO-GO 和 `manual_device_test_ready=false` 继续有效。

## 2. 本次核对的官方源码

以 GitHub 官方仓库的 Git 对象为准。2026-11-04 查询 release API 时，最新稳定发布分别为 KernelSU v3.3.1、KernelSU Next v3.4.2、Magisk v31.1；同时检查开发分支和 legacy 分支。版本名称只用于定位，结论来自下列固定提交中的函数、构建文件和策略。

| 来源 / ref | 固定提交 | 本轮检查重点 |
|---|---|---|
| [KernelSU v3.3.1](https://github.com/tiann/KernelSU/tree/0c0fdb960178fa12d80d6cbcfdcb6ad8be6a865d) | `0c0fdb960178fa12d80d6cbcfdcb6ad8be6a865d` | app_profile、setuid_hook、seccomp_cache、SELinux rules、Kbuild/Kconfig、LKM CI |
| [KernelSU main](https://github.com/tiann/KernelSU/tree/28db74f6f4692e97006ce9ebd8b19b9cc614b5b7) | `28db74f6f4692e97006ce9ebd8b19b9cc614b5b7` | 同上；确认开发分支未换成保留 App filter 的独立执行服务 |
| [KernelSU v0.9.3](https://github.com/tiann/KernelSU/tree/825b14635fe1699cf815c375ce36eec6e6c79e08) | `825b14635fe1699cf815c375ce36eec6e6c79e08` | 历史非 GKI 候选的 core_hook/sucompat |
| [Next v3.4.2](https://github.com/KernelSU-Next/KernelSU-Next/tree/4c706b5938665866ebe16944a481a7b91e3396af) | `4c706b5938665866ebe16944a481a7b91e3396af` | 提权、通信、过滤器缓存、VFS、SELinux、构建 |
| [Next dev](https://github.com/KernelSU-Next/KernelSU-Next/tree/a6c81fa4a8b7341d0bc5c3e4507531459df871ae) | `a6c81fa4a8b7341d0bc5c3e4507531459df871ae` | 当前提权与 Seccomp 路径 |
| [Next v3.4.0-legacy](https://github.com/KernelSU-Next/KernelSU-Next/tree/8af3d4fec33be32fa5d3f8dae4f380fac45bf2cd) | `8af3d4fec33be32fa5d3f8dae4f380fac45bf2cd` | 低于 5.10 的实际处理、兼容层、hook 选择 |
| [Next legacy 分支](https://github.com/KernelSU-Next/KernelSU-Next/tree/b933b1f728116a456fbebf27b6a8772a640cdf23) | `b933b1f728116a456fbebf27b6a8772a640cdf23` | 确认 legacy 当前代码仍移除过滤器 |
| [Next v1.1.1](https://github.com/KernelSU-Next/KernelSU-Next/tree/0d6bdc6364cbfc73517dcfdf7ab23b0ba8045553) | `0d6bdc6364cbfc73517dcfdf7ab23b0ba8045553` | core_hook、sucompat、ksud_magic/ksud_overlayfs 的 su.rs；对照本仓库补丁 |
| [Magisk v31.1](https://github.com/topjohnwu/Magisk/tree/0972f67d97f9b6302b67c5171283330c74114b4a) | `0972f67d97f9b6302b67c5171283330c74114b4a` | init 启动、daemon/socket、su、Manager、授权库、构建 features、SELinux、Boot/OTA |
| [Magisk master](https://github.com/topjohnwu/Magisk/tree/33bfff7ce750c27f157ddb4580e36bf842d6d95b) | `33bfff7ce750c27f157ddb4580e36bf842d6d95b` | 与第四阶段固定来源对照；上述执行模型和 permissive 规则仍在 |

这些源码副本位于仓库外，仅用于读取，没有执行上游 setup、Makefile、安装器或二进制。固定提交与路径可以用 `git show <commit>:<path>` 复核；不依赖可漂移的分支链接。对当前 main/dev 的检查用于排除已检查路径中的现成替代实现，不是对所有未来版本或第三方 fork 的穷尽证明。

本树为 Windows sparse checkout；原生内核文件通过 `git show HEAD:<path>` 读取，没有扩展 sparse checkout 或初始化子模块。目标 ROM 公共源码沿用第三、四阶段固定快照及 hash，见 [stage3 sources.lock.json](validation/stage3/sources.lock.json) 和 [stage4 sources.lock.json](validation/stage4/sources.lock.json)。它们不是目标设备完整 build manifest 或出厂二进制。

## 3. 官方 KSU / Next 路线结论

### 3.1 当前上游：提权仍依赖移除 Seccomp

KernelSU v3.3.1 的 [`kernel/policy/app_profile.c`](https://github.com/tiann/KernelSU/blob/0c0fdb960178fa12d80d6cbcfdcb6ad8be6a865d/kernel/policy/app_profile.c#L80) 中，`escape_with_root_profile()` 提交 root credentials 后调用 `disable_seccomp()`；后者清除 Seccomp 线程工作标志，将 `current->seccomp.mode` 归零并将 filter 置空。main 同名文件也保留此行为。Next v3.4.2 的 [同一路径](https://github.com/KernelSU-Next/KernelSU-Next/blob/4c706b5938665866ebe16944a481a7b91e3396af/kernel/policy/app_profile.c#L80) 及 dev 同样如此。官方路径本身就不符合本项目约束，不必先尝试移植才能作出否决。

当前通信还有另一个独立问题：[`setuid_hook.c`](https://github.com/KernelSU-Next/KernelSU-Next/blob/4c706b5938665866ebe16944a481a7b91e3396af/kernel/hook/setuid_hook.c) 对 Manager/允许 su 的 UID 操作 reboot 的允许缓存；[`seccomp_cache.c`](https://github.com/KernelSU-Next/KernelSU-Next/blob/4c706b5938665866ebe16944a481a7b91e3396af/kernel/infra/seccomp_cache.c) 私自描述带 `action_cache` 的 filter 布局。本树 `kernel/seccomp.c` 的 filter 是 usage/log/prev/prog，没有该缓存；`arch/arm64/kernel/ptrace.c` 先 `secure_computing()`，再 `trace_sys_enter()`。不能靠增加宏、伪造结构体或跳过缓存操作宣称通信兼容。VFS 的 `path_mount` 等移植问题及 v3.4.2 失败构建已记录于 [BUILD.md](BUILD.md)，本轮没有重跑。

SELinux 也不能仅凭上游介绍判定合规：KernelSU v3.3.1 的 [`rules.c`](https://github.com/tiann/KernelSU/blob/0c0fdb960178fa12d80d6cbcfdcb6ad8be6a865d/kernel/selinux/rules.c#L88) 调用 `ksu_permissive(db, KERNEL_SU_DOMAIN)` 并包含广泛 allow。它不是本仓库第四阶段已经收紧的策略；升级不能把这些规则无审查带回。

KSU 的 [LKM CI](https://github.com/tiann/KernelSU/blob/0c0fdb960178fa12d80d6cbcfdcb6ad8be6a865d/.github/workflows/build-lkm.yml) 包含从 android12-5.10 起的构建组合，不能用它证明 umi 4.19 + Clang 22 CFI 的运行兼容性。当前版本在此目标上的完整 CFI/hook/启动验证：**未知**。没有推断“它一定必须关闭 CFI”；已经确认的 Seccomp 违约足以排除当前方案。

### 3.2 官方 legacy：有旧内核代码，仍不满足安全条件

v3.4.0-legacy 的 [`setuid_hook.c`](https://github.com/KernelSU-Next/KernelSU-Next/blob/8af3d4fec33be32fa5d3f8dae4f380fac45bf2cd/kernel/hook/setuid_hook.c) 在低于 5.10 的分支，为 Manager 和已授权 UID 调用 `disable_seccomp`。其 [`app_profile.c`](https://github.com/KernelSU-Next/KernelSU-Next/blob/8af3d4fec33be32fa5d3f8dae4f380fac45bf2cd/kernel/policy/app_profile.c#L84) 有旧内核的 `put_seccomp_filter(current)` 路径，并仍将 mode/filter 清空。当前 legacy `b933b1f…` 的 [对应文件](https://github.com/KernelSU-Next/KernelSU-Next/blob/b933b1f728116a456fbebf27b6a8772a640cdf23/kernel/hook/setuid_hook.c#L30) 仍保留低于 5.10 的清除行为。

legacy 的 [`Kconfig`](https://github.com/KernelSU-Next/KernelSU-Next/blob/b933b1f728116a456fbebf27b6a8772a640cdf23/kernel/Kconfig#L57) 明示 tracepoint+kretprobe 模式不应在低于 5.10 使用，另提供要求 >=4.17 的 syscall table 模式。这说明存在旧内核适配工作，不说明该模式在本树、现有 CFI、目标 ROM 上经过验证，也不改变其清除 Seccomp 的事实。**官方 legacy 路线不能接受。**

### 3.3 历史版和现有 v1.1.1：不能继续修补成通用方案

KernelSU v0.9.3 的 [`core_hook.c`](https://github.com/tiann/KernelSU/blob/825b14635fe1699cf815c375ce36eec6e6c79e08/kernel/core_hook.c#L109) 在提权中清除 Seccomp；Next v1.1.1 的 [`core_hook.c`](https://github.com/KernelSU-Next/KernelSU-Next/blob/0d6bdc6364cbfc73517dcfdf7ab23b0ba8045553/kernel/core_hook.c#L119) 也如此。回退旧版不能获得符合要求的官方实现。

本仓库 0002 刻意删除清除 filter 的行为，0009/0010 等收紧授权和策略。既有正式构建证明这套固定队列可以在本树保留 CFI 编译链接，**没有证明通用 Root 成功**。`execve → escape_to_root → ksud root_shell` 仍在 App 后代上运行，fork/exec 不清除 filter。v1.1.1 的 [`ksud_magic/src/su.rs`](https://github.com/KernelSU-Next/KernelSU-Next/blob/0d6bdc6364cbfc73517dcfdf7ab23b0ba8045553/userspace/ksud_magic/src/su.rs#L49) 和 overlayfs 对应实现重复执行 groups/GID/UID syscall，第四阶段的 LOS App 策略分析已确认前两项受阻。

跳过重复身份设置最多改变部分命令的表现，不能让 mount/chroot/reboot 等被拒绝的 syscall 合法执行；Manager bootstrap 也不代表普通 App。不能再通过修改这些局部路径延续开发。详见既有 [Seccomp 原因与测试边界](SECCOMP-FEASIBILITY.md)。

**综合回答：没有找到满足全部约束、并在该目标上已验证的官方 Linux 4.19 KSU 路线。** 这不是说 Linux 4.19 不能运行任何 Root；它是对本项目的安全条件、执行模型和证据要求的结论。

## 4. 经认证的独立特权服务：范围与安全设计

### 4.1 执行主体必须改变

可审查的模型应当是：App 及其 su 客户端保留原 filter；客户端通过受控 IPC 请求服务；由可信 init 启动的另一个执行主体认证、授权并派生工作进程。工作进程继承服务一侧的策略，而非 App 的过滤器。仅将现有 ksud 改名或放到后台，并不会改变祖先链。由已提权的 App fork 出“daemon”仍继承 App filter。

服务及工作进程必须有自己明确、可验证的 Seccomp/SELinux 策略；不能先在应用中清除 filter 再声称“应用保持 Seccomp”。服务可以自然从 init 获得必要启动权限；如采用 KSU bootstrap，只能让已认证启动主体取得最小启动能力，不能开放任意包提权。内核强制检查和 Manager 身份边界仍须独立审查。

这是待评审架构要求，**没有现成实现获准采用，也没有在本轮实现或启动**。任意 Root shell 的获准使用者本身具有极大破坏能力；服务认证能防止未授权调用，不能承诺约束一个已获得任意 Root 的恶意程序。

### 4.2 必须覆盖的边界

| 项目 | 必须落实的行为 | 现有组件可复用与缺口 |
|---|---|---|
| 调用者身份 | 从 Binder 调用身份或 Unix socket 内核凭据/peer label 获取实际 UID、进程和域；拒绝请求体自报 package/UID/PID 作为凭据；对断连、继承/转交 socket、跨进程代发定义语义 | 可用 Linux/Android IPC 原语；`SO_PEERCRED` 是连接时身份，不自动证明每条消息的当前发送主体，更不能代表包签名 |
| Manager 授权 | Manager 签名/可信安装链、完整 Android 用户身份、授权目标和范围均绑定；仅可信控制面可改 grant；普通应用不能伪造弹窗回复；认证失败、超时和服务不可用默认拒绝 | 旧 KSU APK 认证和 profile 可作参考，但现有 Manager/ABI 不能直接充当新服务的认证协议 |
| 包、UID 复用 | 完整 userId+appId、包集合、签名和安装代次；卸载/重装、签名变化、用户删除等立即使授权失效；共享 UID 按共同安全主体处理，不能承诺包级隔离 | 旧 profile 的 package+UID 不足；需要与可信 PackageManager 信息及安装事件建立一致性，不能只靠周期扫描 |
| PID 复用 | 在认证、命名空间/cwd/FD 获取和会话建立之间维持同一进程身份；不信任可被复用的数字 PID 或可重放 token | 本树有 pidfd 回移植，但 peer PID 到 pidfd 的取得仍有竞争；不能以读 starttime 后再 open 的检查代替原子身份绑定 |
| IPC / FD | 有版本的有界协议、请求大小/并发/超时/配额；区分控制面与执行面；FD 类型验证、CLOEXEC、只传必要 stdio/PTY；限制 SCM_RIGHTS、目标 namespace、路径及环境输入影响 | 需要新客户端和服务实现、协议模糊测试；不把 Unix socket 文件权限当作完整鉴权 |
| SELinux 域 | 服务与 worker 使用独立、有效 enforcing 的域及可审查 file/socket 标签和转换；显式定义需要的 capabilities、Binder/PTY/mount 权限 | 需要目标平台/vendor/product/system_ext 完整策略、编译及 neverallow 验证；不能借用 public debug su permissive 或全通配规则 |
| Seccomp | App filter 字节和有效行为不变；服务与 worker 按其实际任务制定、安装并验证自身策略；原进程仍不能执行被拦截 syscall | 现有 direct-su 不能提供这个边界；用户任意附加 filter 也可能禁止客户端 IPC，此时只能正常失败，不能保证所有 App 都能连接 |
| 授权状态 | 唯一授权权威、带代次的快照；创建 worker 与撤销有明确线性化点；跨内核/用户态不能存在两份互相覆盖的 grant | 若保留 KSU 为授权权威，需要服务可认证的新 ABI 和失效通知；若服务拥有数据库，Manager 及持久化协议必须随之改造 |
| 撤销 | 立即拒绝新任务并处理排队/待确认任务；定义已运行会话及后代的终止规则，取消继承 FD/token；重启不能恢复已撤销 grant | “拒绝以后请求”与“收回已授予 Root”不同；杀主 PID/进程组不足以保证回收全部后代或既成系统修改 |
| 生命周期 | init 启动次序、data 解密、失败重启、升级、崩溃恢复、原子落盘/fsync、worker 收割和孤儿处理；失败默认拒绝 | 新 init/ROM 集成和故障恢复项目，不能依赖 Manager 常驻；每次更新都需要一致性测试 |
| 审计日志 | 记录实际身份/授权代次、策略与服务版本、请求范围、允许/拒绝原因、会话起止、退出/撤销结果；日志访问控制、轮转和敏感参数脱敏 | 需要服务端记录及可查阅入口；默认关闭的通知或普通 App 日志不能代替审计。对已获完全 Root 的人不能保证本机日志不可篡改 |

关于 PID 能力，本轮实际读取本树 [`kernel/pid.c`](https://github.com/Ben8368/android_kernel_xiaomi_sm8250_ksu/blob/45b868c5ae518543f691f9fcf4e8eb0cedf0cdce/kernel/pid.c#L560) 的 `SYSCALL_DEFINE2(pidfd_open)`、`kernel/signal.c` 的 `pidfd_send_signal`，以及原生/compat syscall 表。不能写成“4.19 一律没有 pidfd”。但这些接口存在不等于 App 策略允许调用，也不自动消除连接认证到打开 PID 的时间窗口；所需的原子绑定、namespace FD 和整组回收语义尚未验证。若现有接口无法实现承诺，才有另行审查小范围内核/系统 broker 接口的理由，本轮没有设计补丁。

### 4.3 工作量判断

**这是新的用户态安全项目及 ROM 集成工程，不是小规模兼容改造。** 至少涉及 su 客户端、独立 daemon/worker、Manager 控制面、授权数据库及安装身份追踪、IPC/FD 协议、init 启动、SELinux/Seccomp 策略、撤销/生命周期管理、日志与升级恢复。保留 KSU 作为授权根还会新增稳定 ABI、服务身份认证和内核/用户态状态同步责任。

代码少并不能免除这些组件的长期维护。复用 Magisk 的部分 daemon 源码仍须处理其构建 features、Manager、数据库、启动链和策略依赖；不能复制几个 Rust 文件就称为成熟服务。没有实现规格、完整审查或真机证据，不给出伪精确工期；按工程范围应作为独立项目立项。本项目不推荐为保住 KSU 名称而承担该工程。

## 5. Magisk 替代方案

### 5.1 有实际源码支撑的优势与限制

以 v31.1 为主，master 作对照：

| 边界 | 实际源码事实 | 可以得出的结论 |
|---|---|---|
| 启动与执行主体 | [`rootdir.rs`](https://github.com/topjohnwu/Magisk/blob/0972f67d97f9b6302b67c5171283330c74114b4a/native/src/init/rootdir.rs#L13) 向 init rc 注入 UID 0、`u:r:magisk:s0` 的启动事件；[`daemon.rs`](https://github.com/topjohnwu/Magisk/blob/0972f67d97f9b6302b67c5171283330c74114b4a/native/src/core/daemon.rs#L448) 仅允许 root 在适当路径创建 daemon；[`su/daemon.rs`](https://github.com/topjohnwu/Magisk/blob/0972f67d97f9b6302b67c5171283330c74114b4a/native/src/core/su/daemon.rs#L117) 由 daemon fork 授权后的 worker | Root 命令不必由 App 自己提权后执行；客户端 filter 不会经 socket 转移给 worker。目标启动链的实际 filter 仍需运行验证 |
| IPC 身份 | daemon 读取 `peer_cred()`、SO_PEERSEC，并按非 root/非 zygote 客户端的 executable dev/inode 做检查；数据库控制请求要求 root | 有内核凭据和分层请求门禁，不信任请求体 UID 来决定 grant；不能据此宣称所有 PID/FD 复用竞争已解决 |
| Manager / 构建 | [`package.rs`](https://github.com/topjohnwu/Magisk/blob/0972f67d97f9b6302b67c5171283330c74114b4a/native/src/core/package.rs#L210) 检查 Manager APK 证书字节与 TRUSTED_CERT、跟踪文件变化并解析 Manager UID；[`Cargo.toml`](https://github.com/topjohnwu/Magisk/blob/0972f67d97f9b6302b67c5171283330c74114b4a/native/src/core/Cargo.toml#L10) 默认启用 check-signature/check-client/su-check-db；[`build.py`](https://github.com/topjohnwu/Magisk/blob/0972f67d97f9b6302b67c5171283330c74114b4a/build.py#L234) 的 Rust 构建不去掉默认 features | 第四阶段提到的无 su-check-db 即 allow 分支仍存在，但默认构建有检查；不能把调试构建或任意自编译件当作发行安全配置。本轮没有完成官方 APK/daemon 字节和可信证书的独立绑定 |
| 授权与 UID 生命周期 | [`su/db.rs`](https://github.com/topjohnwu/Magisk/blob/0972f67d97f9b6302b67c5171283330c74114b4a/native/src/core/su/db.rs#L45) 按 UID/到期时间查询，默认 Deny；Manager 的 [`SuperuserGrantViewModel.kt`](https://github.com/topjohnwu/Magisk/blob/0972f67d97f9b6302b67c5171283330c74114b4a/app/apk/src/main/java/com/topjohnwu/magisk/ui/superuser/SuperuserGrantViewModel.kt#L142) 管理 UID grant；[`Receiver.kt`](https://github.com/topjohnwu/Magisk/blob/0972f67d97f9b6302b67c5171283330c74114b4a/app/core/src/main/java/com/topjohnwu/magisk/core/Receiver.kt#L47) 在 UID_REMOVED 时异步删除，daemon 也有 prune | 是现成的用户授权实现；没有在授权记录中看到本项目所需的包签名+安装代次绑定。异步清理不等于证明 UID 快速复用无窗口 |
| 撤销与会话 | `su/daemon.rs` 缓存命中时刷新时间戳；worker fork 后 waitpid 返回结果；未见撤销遍历并终止会话后代的实现 | 不能承诺严格即时撤销或“最多 3 秒”生效，连续命中可延长缓存；本轮未见 DB 修改联动该缓存失效。已有 Root 的回收也未获保证 |
| 日志 | [`su/connect.rs`](https://github.com/topjohnwu/Magisk/blob/0972f67d97f9b6302b67c5171283330c74114b4a/native/src/core/su/connect.rs) 按 settings.log/notify 向 Manager 通知身份、命令和策略 | 有现成日志/通知路径；可以关闭、通知可能失败，不等于强制、持久且不可篡改的安全审计 |
| FD / namespace | [`su.cpp`](https://github.com/topjohnwu/Magisk/blob/0972f67d97f9b6302b67c5171283330c74114b4a/native/src/core/su/su.cpp#L331) 接收 stdio/PTY、选择 namespace、读取调用方 cwd/environ 后执行；[`utils.cpp`](https://github.com/topjohnwu/Magisk/blob/0972f67d97f9b6302b67c5171283330c74114b4a/native/src/core/utils.cpp#L160) 的 namespace 切换在 pidfd 方法失败时回退 `/proc/<pid>/ns/mnt` | 包含实际旧接口回退，不能简单说必须新内核；回退中的 PID/路径/生命周期性质仍需审计和目标验证 |

这是对已有服务实现的架构检查，**不是完成了 Magisk 全量安全审计，也不是发现上述边界全部通过本项目验收**。特别是 v31.1 的用户授权应按该版本 UI/数据库路径理解，不能套用旧教程假定每次 su 都有同步弹窗。

### 5.2 SELinux 与 CFI：不能直接通过

v31.1 [`sepolicy/rules.rs`](https://github.com/topjohnwu/Magisk/blob/0972f67d97f9b6302b67c5171283330c74114b4a/native/src/sepolicy/rules.rs#L51) 的 `magisk_rules()` 创建 `magisk` 域，加入广泛 allow、全范围 ioctl xperm，并调用 `permissive([proc])`。[`init/selinux.rs`](https://github.com/topjohnwu/Magisk/blob/0972f67d97f9b6302b67c5171283330c74114b4a/native/src/init/selinux.rs#L72) 实际调用这套规则；它不是无人调用的示例。master 中也保留这些行为。

所以即便全局 SELinux 仍报告 Enforcing，该特权域也不满足本项目沿用的强制检查标准。简单删掉 permissive 一行不等于解决问题：广泛 allow 仍在，启动/命令/模块所需权限与目标 ROM 的策略约束仍未验证。若自行改造，必须承认承担用户态/策略 fork 的维护成本，不能把它计为“原版成熟实现可直接满足”。本轮不提出关闭 SELinux 的替代方案。

Magisk 用户态架构不要求为 KSU hooks 修改本内核源码，因而可减少 CFI 适配责任；但 [`boot_patch.sh`](https://github.com/topjohnwu/Magisk/blob/0972f67d97f9b6302b67c5171283330c74114b4a/scripts/boot_patch.sh#L210) 仍包含某些平台的 kernel 二进制补丁，不能笼统保证安装器绝不改变 kernel payload。对实际 umi 输入必须核查解包前后 kernel hash、CFI 配置及运行状态；目前**未知**，没有运行安装器或做任何补丁。

### 5.3 小米 10、目标 LineageOS 与 Boot

官方 LineageOS Wiki 的固定 [`umi.yml`](https://github.com/LineageOS/lineage_wiki/blob/620b81d1660b9e37ebbc99ae3b24cf56caac2a9e/_data/devices/umi.yml) 将 Mi 10 / umi 对应到 Linux 4.19 和独立 recovery；`current_branch=23.2`，版本列表为 21、22.1、22.2、23.0、23.2。**这不是 LineageOS 24.0 已正式支持或已在这台手机安装成功的证据**，也不能外推为 24.0 永远不会发布。项目的目标仍是 24.0 / Android 17，现阶段只有公开研究源码和内核构建证据。

已固定的设备配置：[`umi BoardConfig.mk`](https://github.com/LineageOS/android_device_xiaomi_umi/blob/8e115b1ed63caa3ee5c3d52df0a7bce7c27512cd/BoardConfig.mk) 与 [`sm8250-common BoardConfigCommon.mk`](https://github.com/LineageOS/android_device_xiaomi_sm8250-common/blob/b84fe80a52e7407c53119d2dd6507285da8090d4/BoardConfigCommon.mk)。当前非 VAB 候选为 header v2、4096 pagesize、raw Image、独立 DTB section、boot/recovery 各 128 MiB、独立 dtbo，并启用 AVB。公共配置还包含 VAB/header v3/vendor_boot 分支；不能仅按“米 10”或 Android 版本猜测实际布局。完整取证见 [BOOT-FORMAT.md](BOOT-FORMAT.md)。

Magisk 的 [`bootimg.cpp`](https://github.com/topjohnwu/Magisk/blob/0972f67d97f9b6302b67c5171283330c74114b4a/native/src/boot/bootimg.cpp#L253) 有 header v2 parser，`boot_patch.sh` 有 ramdisk 注入/repack 路径，说明存在对应格式实现；不代表目标 ROM 的精确 Boot 已通过测试。需要同次 ROM 的 boot/ramdisk/DTBO/vbmeta/recovery、完整 manifest、产品/vendor 配置、解锁/AVB/rollback 状态和恢复材料。它们目前缺失，因此具体应该修补 boot、recovery 或其他承载 ramdisk 的镜像，以及最终能否启动，均须核实；不能因为 Android 17 就认定存在 init_boot。

未来若获准迁移，应在匹配 ROM 的原生、无 KSU 内核输入上单独评估，避免同时安装两套提权/策略修改系统；这不是要求现在删除 KSU 实验历史。Magisk 版本升级也要核查实际 release binary、Manager 证书、输入/输出与恢复链。它是 boot/init/用户态方案，**明确不满足“内核原生 KSU”原始要求**。

### 5.4 OTA 更新影响

Magisk v31.1 的官方 [`docs/ota.md`](https://github.com/topjohnwu/Magisk/blob/0972f67d97f9b6302b67c5171283330c74114b4a/docs/ota.md) 将所述 OTA 流程限定于 A/B，且说明精确流程只在 Pixel 测过。不能把“安装到未使用槽位”直接应用于本项目非 VAB umi 候选。

[`addon.d.sh`](https://github.com/topjohnwu/Magisk/blob/0972f67d97f9b6302b67c5171283330c74114b4a/scripts/addon.d.sh) 另有 A-only/backuptool 与 A/B 分支，会检查 data、寻找目标镜像并重新安装；这证明有保留 Root 的代码，**不证明目标 LineageOS 24.0 的 recovery、解密、addon.d/backuptool 和 OTA 签名/校验链已经配合成功**。两类流程应分开评估。

OTA 替换 boot 等相关分区时，Root 可能丢失；保留脚本或人工重新处理新版本镜像又可能因布局、权限、解密、签名及模块变化失败。每次 OTA 都应以新版本配套镜像重新核查，保留未修改的原版及恢复材料，不能沿用旧日期的 patched Boot。更改 boot 会改变摘要/AVB 关系；是否允许、如何处理必须依据目标 ROM 的实际验证链，不自动禁用验证或生成 bypass vbmeta。OTA 后 Root 保留和回滚在此设备上均为**未知**。

## 6. 三种方案比较

以下为本项目维护责任的定性估计，不是已完成实现的测量结果。

| 维度 | A：继续官方 KSU / Next 直接 su | B：KSU + 自建经认证独立服务 | C：采用官方 Magisk |
|---|---|---|---|
| 代码改动范围 | 老版队列维护或新版 VFS/SELinux/hook/通信回移植；保留 filter 后执行模型仍阻断 | 新 su 客户端、daemon/worker、Manager/数据库、IPC、init、策略、撤销/审计；可能另有小范围 ABI | 原生内核通常无需 KSU 集成；需 Boot/init 集成、输入检查、升级/恢复；满足严格策略时将额外承担 fork |
| 安全风险 | 内核攻击面、凭据/RCU/生命周期、旧版安全修复欠账；官方清 filter/permissive 与约束冲突 | 新增长期 root 服务和 IPC 攻击面，身份混淆/复用、状态分叉、FD/namespace/撤销竞争；缺独立审查 | 成熟 daemon 降低自研认证负担，但特权策略宽、magisk 域 permissive；缓存撤销与安装代次证据不足 |
| 长期上游同步成本 | 高：LOS 4.19 与 KSU 快速变化的 hook/VFS/策略双线同步 | 最高：内核/ABI、LOS 平台、独立服务与 Manager 多线同步 | 不改原生内核时较低；仍跟进 Magisk 和 ROM Boot/策略变化。自行收紧策略后明显增加 |
| 用户态维护成本 | 已经存在 Manager/ksud ABI、打包/证书/旧版本补丁责任，并非纯内核工作 | 最高：新增安全产品的协议、存储、安装身份、UI、升级和故障恢复全生命周期 | 使用官方发行时相对最低；自行 fork、模块、Zygisk 会增加责任，不纳入低成本基线 |
| 实际验证难度 | 已有 CFI 编译证据，但通用 Root 架构阻断；升级还需重新验证全部内核接线 | 最高：协议模糊测试、UID/PID/FD 攻击、并发撤销、策略、崩溃/升级、设备功能和外部审查 | 少做内核 hook 验证，但仍需目标 Boot、双 ABI App、授权/拒绝/撤销、Enforcing 域、CFI、OTA/恢复验证 |
| 是否内核原生 KSU | 是 | 内核授权 + 用户态执行的混合架构，需重新确认产品定义 | 否 |
| 是否已有本目标完整通过证据 | 否 | 否；尚无获准实现 | 否；目标 ROM/Boot/真机未知 |
| 当前决定 | NO-GO，停止局部修补 | NO-GO，不立项实施 | 不满足原始要求与严格 SELinux 标准，当前 NO-GO |

Magisk 是**改变要求后的较低维护成本候选**，不是当前的第二个推荐结论。没有找到满足全部要求的成熟方案时，唯一推荐必须是 NO-GO，不能为了给出 Root 成品而隐式放宽条件。

## 7. 后续工作边界与重新评估条件

原有 LineageOS 内核同步可以独立于 Root 推进：本地 `lineage-24.0` 与 `origin/lineage-24.0` 当前均指向 `6b34d24765327d746074c8e53b5ad0d24a51acc7`。这只是本地 refs 快照，不声称远端永远不变。本轮没有移动它们，也没有检查后自动合并上游。

未来按 [MAINTENANCE.md](MAINTENANCE.md) 的独立评审分支/PR 流程同步原生 LineageOS、安全修复和设备驱动，保留 Seccomp/SELinux/CFI，记录输入及硬件回归。KSU 分支和 PR #1 保留实验用途；不把 KSU 补丁或本决策文档自动带入默认分支，不强推、不 rebase 已发布历史。原生同步成功不代表 Root 就绪，Root NO-GO 也不应阻塞正常内核维护。本轮没有创建自动同步任务。

只有出现以下新证据才重新审议 Root，而非自动开始实现：

1. 官方提供可定位源码/构建配置的独立执行路线，能够保留 App filter、使实际特权域 Enforcing，并提供本树 CFI 与目标 ROM 的验证材料；或产品要求经用户明确修改。
2. 若考虑自建服务，先单独批准项目范围和安全设计，包括身份绑定、授权权威、撤销承诺及无法回收任意 Root 既成效果的边界，再决定是否实现；不能以本文为部署授权。
3. 取得精确可信的 umi 24.0 target-files/Boot/完整策略、manifest、版本对应官方用户态二进制及恢复材料。没有它们，Magisk 和新服务均不能把兼容性从未知提升为已验证。
4. 独立审查、离线安全验证及全部软件门禁通过之后，才讨论另行授权的设备测试。真机、刷写和发布是后续不同阶段，本轮均未执行。

## 8. 最终明确答复

| 问题 | 决策 |
|---|---|
| 继续 KernelSU 是否值得？ | **不值得继续当前通用 Root 功能开发。** 保留研究和修复证据；停止 direct-su 局部兼容补丁。不因换个官方版本就重新开工 |
| 是否存在已验证的 Linux 4.19 兼容路线？ | **本目标和全部约束下，没有找到。** 官方旧内核代码依赖清 filter 等不合条件的行为；现有队列仅证明编译/离线检查。Magisk 的精确目标兼容性未知 |
| 安全通用 Root 需要改哪些组件？ | 若坚持自建：独立执行服务、su IPC 客户端、Manager、授权/包身份及持久化、init、SELinux/Seccomp 策略、撤销/会话、日志/升级；保留 KSU 时另需认证 ABI。属于新用户态项目 |
| Magisk 是否维护成本更低？ | **采用官方发行且允许改变要求时，预计是。** 本轮不能采用：非内核 KSU、官方特权域 permissive、严格生命周期和目标 ROM/OTA 尚未验证；自行修策略会增加维护 |
| 原 LineageOS 内核上游同步能否独立推进？ | **可以。** 单独原生维护分支/PR，不合并 PR #1，不混入 Root 实验，不改变现有安全配置或重写历史 |

第五阶段以本架构决策完成评估；Root 的状态仍是 **NO-GO**，并未升级为可以刷写或发布。
