# APatch / KernelPatch 对 umi LineageOS 24.0 的可行性评估

日期：2026-11-04（Asia/Shanghai）。目标：Xiaomi Mi 10 / umi、Snapdragon 865、ARM64、Linux 4.19.325、LineageOS 24.0 / Android 17，保留 USB PD/PPS 等设备功能。

**唯一推荐：维持 Root NO-GO，继续维护无 Root 的原生 LineageOS 内核；本阶段不以 APatch 替换 KSU，也不创建可启动实验分支。** APatch 减少内核源码合并工作的优势成立，但其所审源码主动改变 Seccomp、SELinux 和 CFI 边界，不能满足严格安全模式。常规 Root 模式也不能直接验收：Manager 身份失效、授权持久化、发布二进制源码归属和目标设备运行证据仍有缺口。

这不是断言 APatch 不能在任何小米 10 上运行；它是对本项目安全约束和证据的决定。允许记录在案的 Root 权限扩张，不等于允许旧身份继续成为 Manager、授予其他 UID 未经用户批准的权限，或把未知风险写成通过。

## 1. 范围、基线与证据等级

- 本地研究分支：`lineage-24.0-ksu`，HEAD `45b868c5ae518543f691f9fcf4e8eb0cedf0cdce`。
- 本地纯净分支：`lineage-24.0`，`6b34d24765327d746074c8e53b5ad0d24a51acc7`。这是本轮读取的本地 ref，不声称代表远端今后的最新状态。
- 沿用 [ROOT-SECURITY.md](ROOT-SECURITY.md)、[SECCOMP-FEASIBILITY.md](SECCOMP-FEASIBILITY.md)、[SELINUX-MATRIX.md](SELINUX-MATRIX.md) 的安全门槛。[第四阶段结果](validation/stage4/readiness-result.json) 仍为 `NO-GO`、`manual_device_test_ready=false`；既有 KSU 编译通过不是 Root 功能验收。
- 开始时已有未跟踪文件 `docs/ROOT-ARCHITECTURE-DECISION.md`；本轮只读参考并保留原样，不把它算作本轮产出。
- 本轮只新增本文。第三方源码、release API 元数据及只用于 ZIP/哈希检查的官方 APK 存于仓库外临时目录；未执行上游安装器、补丁工具或二进制，未构建内核/Boot，未连接或刷写设备，未改补丁、分支 ref、默认分支或 PR #1，未提交或推送。

证据分为：**S：固定提交的静态源码**；**A：发布附件的读取/哈希事实**；**R：第三方自报真机记录**；**T：本目标独立验证**。S/A/R 均不能替代 T。本文没有 T 级 APatch 启动、普通应用授权/拒绝/撤销、硬件或 OTA 证据。未验证项记为未知/BLOCKED，明确违约项记为不符合。

## 2. 确切版本与发布物归属

2026-11-04 读取官方 GitHub releases/latest API，并解析 Git tag 对应的 commit；`target_commitish=main/master` 不是固定 SHA。源码基线如下：

| 对象 | 版本 / ref | 固定 Commit SHA | 用途 |
|---|---|---|---|
| APatch | 最新非预发布 release `11282`，发布于 2026-10-15；当时 main 同提交 | `e8e4651c16fb5075882a25813c8732285fdb3505` | Manager、apd、安装脚本、依赖与构建配置 [AP-REL] [AP-BUILD] |
| KernelPatch | release tag `0.13.9`，发布于 2026-09-24 | `b51197aaba8f2272dd8a3e30c85698a29aa928c9` | 可复核的标签源码；**不能直接等同 APK 内的 kpimg** [KP-REL] |
| KernelPatch | main，源码 version 仍为 `0.13.9` | `d4c88d6672687456b299e4b5153c24dc979d789b` | 排查标签后的认证、CFI、符号和 Hook 变化 [KP-MAIN] |
| KernelPatch 认证修复 | 2026-09-26，精确密钥长度 | `0961c53457c7ad6c47924fbe87e7f93abb999de0` | 标签后修复 [KP-KEYFIX] |
| KernelPatch 安全修复 | 2026-10-04，命令权限/密钥处理等 | `53c43f3ce650e94a46523f7ad17b30ce2bf0e3c9` | 标签后修复 [KP-AUTHFIX] |
| APatch 的 policy 依赖 | Cargo.toml 固定 rev | `51ff1161e23a343971e3db764056ec6ee7c8cc2e` | AndroidPatch/ap_policy，实际 `magisk_rules()` [AP-DEPS] [AP-POLICY] |
| Magisk | 最新非预发布 release `v31.1`，API 发布日期 2026-10-25 | `0972f67d97f9b6302b67c5171283330c74114b4a` | 比较 daemon、授权、策略、Android 17、Boot/OTA；changelog 自记日期为 10-24 [M-REL] [M-CHANGES] |

### 2.1 APK 与 KernelPatch 附件存在版本名无法表达的差异

下载官方 `APatch_11282_e8e4651_HEAD-release-signed.apk`，只用 ZIP 读取与 SHA-256 检查，APK 共 6,716,426 bytes；整包哈希与 release API 的 digest 相符。内部两个核心文件也分别匹配**本轮 API 返回的当前** KernelPatch `0.13.9` 同名发布附件 digest：[AP-REL] [KP-REL]

| 对象 | SHA-256 |
|---|---|
| APatch 11282 APK | `d6bf0dbcab95fb9a3aa111c35efd945267bcce3a41377c3297c3c1a9eab421a5` |
| APK `assets/kpimg`，296,336 bytes | `eb2e3d16fe69410150efcf6f9425baf8cad9ac0c39f051fc8b40ce57c7143adb` |
| APK `lib/arm64-v8a/libkptools.so`，248,016 bytes | `63a8656a79b74baadcf0ce57a7e89a8c8a94beb35b25df58aec0bcf1d066bc5b` |
| APK `lib/arm64-v8a/libapd.so` | `f6004da5032ea5f35f6c4e49e9f24054b3fa33fc0204ac45936eeec22a2d3fc8` |

但 `0.13.9` Git 标签提交时间为 09-24，当前两个核心附件的 API `created_at` 为 10-10 13:20 UTC 左右；kpimg 内能读取到编译字符串 `13:19:33 Oct 10 2026`（字符串未注明时区）。发布工作流允许 `allowUpdates: true`、`replacesArtifacts: true`，并按 version 字段上传同名 release。[KP-CI]

因此：**匹配当前附件哈希证明取得的是当前发布内容，不能证明它由 `b51197a…` 构建。** 不能将 09-26/10-04 的修复武断地判为 APK 已包含或未包含，也不能把当前 main 的修复全部算进 APK。编译日期接近某次 commit 也不是构建溯源证明。本轮没有重现构建、完整反汇编或验证 APK 签名证书，未建立每个发布二进制到源码、工具链和构建选项的完整映射。

后文涉及缺陷时明确标注适用源码；发布物归属未知本身是验收阻断项，而不是恶意软件判定。后续至少需要不可变附件哈希、构建 run 对应 SHA/参数和可复核产物关系。

## 3. Root 实现：四个组件不能混为一谈

| 层次 | 实际职责和执行链 | 关键边界 |
|---|---|---|
| Boot / 内核镜像修补 | Manager 的 `boot_patch.sh` 调用 kptools 解包 boot、取 kernel、注入 kpimg、重打包；kpimg 在内核早期执行，再装各类 Hook [AP-PATCH] [KP-PATCH] | 不需要将 KSU 补丁合入 LOS 源码，**但修改了内核二进制及启动信任链**，不是只安装 APK |
| 内核提权 | SuperCall 或 sucompat 路径 → `commit_su` → `commit_common_su`/`commit_kernel_su`；修改 UID/GID/capabilities、组和可选安全上下文。`task_su` 还能改指定任务 [KP-ACC] [KP-SU] [KP-SC] | 普通 App 的授权后提权发生在内核，通常仍是该 App 的执行祖先链 |
| 用户态 apd | sucompat 把执行路径转给 `/data/adb/apd`，其 `root_shell()` 明确假设内核已提权；另有 init 阶段执行的 post-fs-data/services、模块、policy、UID 配置同步 [AP-CLI] [AP-SHELL] [AP-EVENT] | 名称含 daemon 不代表 su 请求通过独立、保留 App filter 的认证服务执行；本版 su 路径是直接执行 |
| Manager / 授权 | Manager 用 JNI/SuperCall 管理 UID allowlist/profile、配置持久化；内核识别可信 Manager UID，也可接受 SuperKey [AP-JNI] [AP-GRANT] [KP-USERD] [KP-SC] | 包名、证书摘要、当前 UID、密钥、普通 Root grant 是不同凭据和权限级别，必须分别审查 |

APatch `apd/src/cli.rs` 发现 argv[0] 以 su/kp 结尾就进入 `root_shell()`；后者仍会设置 groups/GID/UID 并 exec shell。它并没有把普通 su 改造成 Magisk 的 daemon-fork 模型。内核 `handle_before_execve()` 先检查 allowlist/Manager，再提权并改写到 apd；不存在“仅靠 apd 名称就天然不继承 Seccomp”的结论。[AP-CLI] [AP-SHELL] [KP-SU]

KernelPatch 本身可不安装 APatch 的 APM 层，但 SuperCall、凭据转换、SELinux/CFI Hook 仍属于内核核心；只用 KernelPatch 不会自动满足严格模式。KPM 是额外可装的内核代码，不是获得基础 Root 必需条件；不装 KPM 也不能消除核心边界变化。

Boot 磁盘 ramdisk 的修补与运行时 init 接管也要分开：APatch 主安装链修补 kernel；KernelPatch `userd.c::before_openat()` 在 init 读取原 rc 时生成带附加动作的替代 rc，并重定向本次打开，建立 apd 的启动事件。故“无需修改 LOS 内核源码”不代表“不会改变 init 行为”。[AP-PATCH] [KP-USERD]

## 4. 严格安全模式：三项独立 NO-GO

### 4.1 Seccomp：确实关闭目标任务的有效检查

标签和本次 main 的 `kernel/patch/common/accctl.c` 均可见：[KP-ACC] [KP-ACC-MAIN]

- `commit_common_su()` 清除当前任务 `thread_info.flags` 中 `_TIF_SECCOMP`；随后将其 `seccomp.mode` 写为 `SECCOMP_MODE_DISABLED`。
- `task_su()` 对指定任务做同类操作。
- `seccomp_filter_release(task)` 在这些位置是注释，不能描述成已安全释放或清空 filter 指针；**即使旧 filter 指针仍在，清线程标志/关闭 mode 也已破坏执行边界**。
- 写 mode 的判断用的是 `comm_offset > 0`，不是 `seccomp_offset` 的有效性检查；偏移解析失败如何安全拒绝，还需单独证明，不能仅凭 kallsyms 开启推定可靠。

这不是修改全局 `CONFIG_SECCOMP`，也不是 Linux 合法的“Root 自动不受 App filter 限制”。它直接从内核更改已经安装在任务上的过滤状态。Root 转换本来无需执行用户态 setuid syscall；真正冲突在其后的 shell/syscall。APatch 通过放开已提权任务来绕过既有 KSU 路线的阻断，因而**解决功能障碍的方式违反本项目严格条件**。[本树 Seccomp 分析](SECCOMP-FEASIBILITY.md)

`commit_su()` 在配置了 all-allow SID 且目标 UID 为 0 时还有 `commit_kernel_su()` 分支，后者本身不包含上述清除语句；这不等于完整 APatch 可保证所有 App filter 不变，也不使另两项违约消失。本文没有声称每一种 profile 都执行同一分支。删除这几行会留下直接执行模型与 Android App 策略的不兼容，本轮不修改它们，也不将删检查当作解决办法。

### 4.2 SELinux：保持全局 Enforcing 仍可绕过拒绝和审计

`bypass_selinux()` Hook `avc_denied` 和 `slow_avc_audit`。替代函数对 `all_allow_sid` 或 task extension 中 `sel_allow/priv_sel_allow` 标记的任务直接放行：设置 `avd->allowed=0xffffffff`，`auditallow/auditdeny=0`，返回成功；审计路径也可直接返回。`commit_common_su()` 会设置相关标记，`taskob.c` 将标记传给符合条件的后代。[KP-ACC] [KP-ACC-MAIN] [KP-TASK]

这是有条件的内核权限检查豁免，不是所有任务的全局 permissive；但足以违背“不绕过 SELinux”。保留 `u:r:untrusted_app:s0` 等上下文并不能证明该任务仍被同样强制限制。官方 FAQ 也描述通过 Hook 绕过 SELinux，但 FAQ 的叙述不能代替具体分支审查。[官方 FAQ](https://apatch.dev/faq.html)

另有独立的策略变化：APatch 11282 `on_post_data_fs()` 无条件调用 policy 依赖的 `magisk_rules()` 并写 `/sys/fs/selinux/load`，随后重新设置 apd profile。实际固定依赖 `51ff1161…` 创建 `magisk` 域、广泛 allow/xperm，并调用 `permissive([magisk])`。因此完整 APatch 不只是保持上下文的内核 Hook，也包含用户态 policy 注入和特权域 permissive。[AP-EVENT] [AP-DEPS] [AP-POLICY]

还发现可选 `selinux_hide`：Manager 此开关默认 false，开启后以控制文件触发 Hook；标签实现含向 App 提供替代 SELinux status/查询视图的逻辑，main 又修改了 clean-policy 查询实现。Manager 源码对低于 5.10 或非 GKI 提示额外风险。**它影响安全状态的可观察性，不能用于安全验收，不能以查询结果替代真实拒绝测试。** 关闭这个可选功能也不会关闭前述核心绕过或 permissive policy。[AP-HIDE] [KP-HIDE] [KP-HIDE-MAIN]

### 4.3 CFI：不是关闭配置，但确实扩大豁免区域

标签 `secpass.c::should_cfi_pass()` 对 KP text、Hook 区域和 KPM ROX 区域返回 true。`replace__cfi_slowpath()` 对这些目标直接返回，不执行原类型检查；`replace_report_cfi_failure()` 将这些失败降为 WARN。main 还加入 `cfi_handler` Hook，在目标属于同类区域时跳过故障指令。初始化 `before_rest_init()` 调用 `bypass_kcfi()`，不是只在用户安装 KPM 时才发生。[KP-CFI] [KP-CFI-MAIN] [KP-INIT]

应称为**对补丁代码区域的 CFI 豁免/降低**，不应夸大为整个内核全部 CFI 已关闭；也不能反过来因为其余区域保留检查就称“没有降低 CFI”。KP 独立编译、动态 Hook/代码加载与原内核 ThinLTO 的类型约束不是同一验证链。[KP-MAKE] [KP-CI]

本树 `kernel/cfi.c` 确实含旧式 Clang CFI 的 `__cfi_slowpath`、shadow 和失败处理，且已有构建记录保留 ThinLTO/CFI。不能采信第三方源码注释中“<=5.4 无 CFI”的概括，更不能拿别的设备 kCFI 启动成功证明本树 Clang 22 CFI 通过。[LOS-CFI] [BUILD.md](BUILD.md)

**严格模式结论：NO-GO，Seccomp/SELinux/CFI 各有足够的源码依据。** 当前没有发现官方提供同时保留这三项有效约束、又已实现本目标通用 Root 的现成受审模式；这不是要求现在维护一个安全分支去删兼容检查。

## 5. 常规 Root 模式的认证与新增攻击面

### 5.1 SuperKey 与 Manager 认证的实际关系

官方文档仍主要描述 SuperKey；本版 APatch Manager `resolveSuperKey()` 默认尝试字符串 `su` 作为签名/UID 授权路径的调用参数，并在需要时回退旧密钥。补丁脚本把 `su` 当作不设置自定义密钥的模式；自定义密钥是另一条认证入口。**不能将参数 `su` 说成所有 App 均可用的默认后门密码，也不能说本版所有管理操作都必须持有用户输入密钥。** [AP-KEY] [AP-PATCH]

KernelPatch `before()` 区分：已验证 SuperKey、可信 Manager UID、普通 su allowlisted UID。前两者为 `is_authed`，普通 grant 仅为受信调用者而非管理员。`__NR_supercall=45` 是对既有 syscall 槽的 Hook/复用（arm64 原为 truncate），不是给原内核正式增加一个带独立系统 ABI 的新 syscall 号码。它仍受到达 Hook 前的 syscall/Seccomp 入口次序约束。[KP-SC] [KP-ABI] [LOS-PTRACE]

`userd.c` 包含可信包名及证书 DER 的 SHA-256 摘要、APK signing block 解析、packages.list UID 关联和 Manager UID 缓存；还自动提权可信 Manager 执行的特定路径。这里比较证书摘要不等于内核完整验证 APK 全内容签名，完整信任链还依赖 Android 安装验证及受保护的包路径/元数据。自签 APK、证书轮换、签名方案（标签要求 v2-only，排斥 v1/v3 混用）、多用户和升级必须逐组合验证。[KP-USERD]

SuperKey 是高于普通 Root grant 的管理凭据，能触及 KPM、密钥和系统控制接口；泄漏 Boot 中的相关信息、Manager 私有存储或命令参数会扩大控制面。官方明确警告强密钥和第三方预修补镜像风险。[官方安全说明](https://apatch.dev/warn.html) 强密钥不能修复 UID 生命周期或命令分派缺陷。

### 5.2 固定源码中发现的阻断项

| 发现 | 适用证据和实际含义 | 当前处置 |
|---|---|---|
| 标签缺少管理命令的前置门禁 | `b51197a…::supercall()` 在检查 `!is_authed` 前就处理 SU_TASK、GRANT/REVOKE_UID、KSTORAGE_WRITE、CONTROL_FEATURE、PANIC 等；外层普通 allowlisted UID 可以进入。普通 Root grant 不等于用户授权它改其他 grant/管理状态 [KP-SC] | 标签源码不接受；不宣称完全无授权 App 可无条件进入，也不宣称当前 APK 已证实含此问题 |
| 标签密钥比较不核对完整长度 | `auth_superkey()` 只比较配置密钥长度范围内字节；`0961c53…` 改为精确长度校验。`53c43f3…` 又限制非管理员命令、修复用户指针处理并增加密钥擦除 [KP-PREDATA] [KP-KEYFIX] [KP-AUTHFIX] | 修复已存在于 main；当前 APK 与这些提交的归属尚未建立，不能据版本字符串保证已修复 |
| Manager 缓存失效时保留旧 UID | 标签与 `d4c88d6…` 的 refresh 在找不到有效 Manager/读取出错时直接返回，不把已有 `trusted_manager_uid` 清为 invalid；后续只比较当前 UID。卸载/换包、UID 重用的 fail-closed 行为没有保证 [KP-USERD] [KP-USERD-MAIN] | 属于静态可见生命周期风险；未做目标利用复现，但在常规模式也必须 BLOCKED |
| grant 与安装身份绑定不足 | 内核 `su_profile` 只有 uid/to_uid/scontext；apd CSV 为 pkg/exclude/allow/uid/to_uid/sctx，无签名/安装代次。同步按包名存在性及 UID 修正；错误时可能保留旧配置/既有 grant。shared UID 仍是同一安全主体 [KP-ABI] [AP-PACKAGE] [AP-REFRESH] | 没有证明重装/换签/多用户卸载后旧授权及时失效；不能称精确包级授权 |
| 默认 shell grant | `su_compat_init()` 直接加入 UID 2000 和 0；apd 刷新跳过这两个 critical UID 的撤销 [KP-SU] [AP-REFRESH] | 经 ADB shell 获得 Root 是新增信任边界，不能写成每个主体都先经 Manager 手动同意 |
| 任务/凭据内存与 Hook 失败路径 | `task_su()` 标有 RCU todo，直接改已有目标 cred/real_cred；动态偏移推断、目标退出、共享凭据、分配失败和部分 Hook 安装失败需要专审 [KP-ACC] [KP-STRUCT] | 不将源码阅读冒充并发安全证明；本轮不修复、不运行压力测试 |
| Manager 扫描处于 rename Hook 上下文 | 标签/main 仍有 rename 触发同步 APK/包列表扫描；公开 PR #326 提出移出锁内 I/O，PR #327 修两阶段目录扫描 [KP-USERD] [KP-USERD-MAIN] | 已有相关真机挂死报告；PR 存在且自报测试通过不等于已合入所用发布物 |

`53c43f3…` 的新 `kpscauth.h` 限制普通 grant 可用命令，并限制其只查询自己 profile；这是实质修复，应予记录。但其没有解决以上所有身份/撤销问题；其提交说明与实际实现不一致时，以代码为准，例如默认构建仍保留经过管理认证的明文密钥读取，只有 `KP_HIDE_SUPERKEY` 才禁用。[KP-AUTHFIX] [KP-SC-MAIN]

APatch `boot_patch.sh` 在自定义密钥模式仍使用 `-S` 参数，并在工具调用周围使用 `set -x`；不能因为 KP 新增了更安全的 fd 输入就宣称 Manager 已使用它。argv、补丁日志、导出 bugreport 的密钥暴露范围仍需审查，日志不得带入真实 SuperKey。[AP-PATCH] [KP-AUTHFIX]

撤销 grant 也不会自动撤销已提交凭据、继承的 SELinux 豁免、已运行 Root shell 及其后代，更无法回收既成系统修改。必须明确“禁止新会话”和“收回已有会话”的承诺；目前缺乏本目标并发撤销和重启持久化验证。

### 5.3 新增高权限攻击面清单

内核新增 SuperCall/用户指针处理、sucompat 路径改写、目标 PID 提权、内核存储、APK/CSV/路径解析、task extension 生命周期、指令重定位/动态内核代码、CFI/SELinux Hook；用户态新增 Manager JNI、root shell 参数/PTY/namespace、policy 解析、启动脚本、模块/Lua/WebUI 和在线模块下载信任链。KPM 等于任意内核代码授权，APM 脚本也可任意 Root；二者都要视为高信任组件。[KP-SC] [KP-SU] [KP-USERD] [KP-MODULE] [AP-SHELL] [AP-EVENT]

常规 Root 可以接受经批准的任意 Root shell，但不能因此免审授权前入口、把普通 grant 当管理凭据，或接受旧 Manager UID 的控制权。本轮既未发现足够材料证明不存在未经授权提权，也未证明所有上述风险在交付二进制中可控；**常规模式当前仍 NO-GO/BLOCKED，不等于未来原则上不可研究。**

## 6. Linux 4.19.325 / Android 17 兼容性矩阵

| 项目 | 已确认的证据 | 本目标状态 |
|---|---|---|
| ARM64 / 4.19 版本范围 | APatch README/安装文档列 ARM64、3.18–6.12；KernelPatch README 范围表述为理论支持，与 APatch 口径并不完全相同 | 满足声明的基本架构/版本前提；不是启动 PASS |
| kallsyms | 用户给定 KALLSYMS/ALL=y；纯净树 kona-perf_defconfig 显式 ALL=y。kptools 解析镜像内压缩符号，区分地址/相对偏移等格式 [KP-KALL] | 必要条件满足；精确目标 Image 的表定位/地址校验未知 |
| 符号与布局解析 | 工具匹配后缀符号，避开 `.cfi_jt` 等；启动、AVC、CFI、copy_process 等符号被写入配置；运行时推断 task/cred 偏移，main 新增 BTF 辅助 [KP-SYMBOL] [KP-PATCH] [KP-STRUCT] | ThinLTO 内联、重命名、裁剪和编译器更新会改变可用符号/函数入口；未在本 Image 核验 |
| 指令 Hook | `hook_prepare()` 备份入口指令、生成跳板、重定位被覆盖指令、跳回；`hook_install()` 修改原文本，syscall 可用表/dispatcher Hook [KP-HOOK] [KP-SYSCALL] | ARM64/PAC/BTI 处理存在不等于本树每个入口正确；SMP、缓存一致性、部分失败、恢复未知 |
| CFI / ThinLTO | 本树旧式 Clang CFI 确实存在；KP 有区域豁免。KP 的 GCC 构建不等于与 LOS Clang 22 CFI 类型体系完成匹配 | 严格模式不符合；常规模式运行兼容性未知，不能关 CFI 来填 PASS |
| Seccomp / syscall 45 | 本树 secure_computing 在 trace_sys_enter 前；SuperCall 复用 syscall，普通 su 的被禁 syscall 由内核清状态实现放行 | 严格模式不符合；双 ABI、附加 filter、错误密钥/未授权负向行为未知 |
| SELinux / Android 17 policy | AVC Hook、magisk 域 permissive、live policy 修改、可选隐藏；Manager compileSdk=37、targetSdk=36、minSdk=26 [AP-BUILD] | SDK 配置不是 Android 17 真机认证；策略格式、init 和包管理兼容性未知 |
| SuperKey / Manager | 存在密钥、签名摘要及 UID 路径；版本升级改变认证模型，标签后有修复 | 基本实现存在；二进制修复归属、UID 生命周期和完整负向测试 BLOCKED |
| Boot / kernel 格式 | [BOOT-FORMAT.md](BOOT-FORMAT.md) 的非 VAB 候选为 header v2、page 4096、raw Image、独立 DTB section、128 MiB boot；KP bootimg.c 有解包/压缩/重打包实现 [KP-BOOT] | 缺目标 ROM 同次 boot/target-files；头部、DTB、分区余量和 AVB/签名未核验 |
| 模块 / GKI LKM | APatch 下载表及 KP release 的 LKM 资产从 android12-5.10 等 KMI 起，没有本设备 4.19 KMI 成品 [AP-ASSETS] [KP-REL] | 不能把 GKI `.ko` / Jailbreak 模式移用于本非 GKI 4.19；本文评估二进制 Boot 修补链 |
| USB PD/PPS、热管理、相机等 | 未改本树驱动；不存在本目标 APatch 硬件回归日志 | **未知**，不能用驱动源码未变推导充电不受影响 |
| OTA / 恢复 | 官方 APatch 更新文档明确 OTA 保留功能仍不稳定；目标实际分区/更新流程尚无证据 | BLOCKED |

镜像方面，APatch 文档明确其标准链修补 `boot.img`，不可根据 Android 17 就改选 init_boot。现有公共 umi 配置含 VAB/非 VAB 条件分支，必须以目标完整 product 配置和原始镜像为准。源码支持 v2 或识别压缩格式，只是 parser 代码存在；重打包成功也不能证明可启动。改 kernel 会改变 Boot 摘要/验证关系，不自动关闭 AVB，不生成 bypass vbmeta，不复用旧日期的修补 Boot。[官方安装说明](https://apatch.dev/install.html) [KP-BOOT] [BOOT-FORMAT.md](BOOT-FORMAT.md)

### 6.1 找到的真实设备记录及其局限

| 记录 | 实际覆盖 | 可以/不可以证明什么 |
|---|---|---|
| [KernelPatch #151](https://github.com/bmax121/KernelPatch/issues/151)，2024-12-16 | 小米 10 umi、4.19.318-perf+、LOS 21 / Android 14、APatch 10763、KP 0.10.7；带崩溃分析/日志 | 证明存在此机型历史运行与失败报告；不是当前版本安全缺陷复现，也不是 4.19.325/Android 17 通过 |
| [KernelPatch PR #326](https://github.com/bmax121/KernelPatch/pull/326)，2026-10-07 | 作者自报 Mi 10 4.19.157、无 kCFI；旧 packages.xml fallback 加 main 冷缓存重命名挂死，补丁后 10/10 重命名、20/20 安装通过；另测 Pixel kCFI | 有具体局部硬件测试；未给出本目标 ROM、原生 Clang CFI/PD/PPS 证据，未合入的 PR 不能视为发布版修复 |
| [KernelPatch PR #327](https://github.com/bmax121/KernelPatch/pull/327) | `/data/app` 迭代中嵌套 lookup 的两阶段修复，自报重点涉及新内核 | 说明包扫描上下文风险真实存在；不能据其他设备/版本实验推定本设备通过 |
| [APatch #1138](https://github.com/bmax121/APatch/issues/1138)，2025-07-22 | Redmi K40 alioth、4.19.325 RealKing、LOS 21、APatch 11107 / KP 0.12.0；WebUI 失败 | 同补丁号的另一自定义内核有运行报告；非 umi、非 CFI/Android 17 全面验收 |
| [APatch #1579](https://github.com/bmax121/APatch/issues/1579)，2026-08-29 | 另一设备 4.14 + CFI，修补成功而不开机；作者自己未证实 CFI 因果关系 | 提醒旧内核 CFI backport 不能按版本号排除；不能据此宣称 umi 一定以同原因失败 |
| [APatch #1677](https://github.com/bmax121/APatch/issues/1677)，2026-10-30 | Samsung A53、LOS 24.0、5.10、APatch 11282，用户报告解锁后反复重启，KP 版本/日志缺失 | 低强度 Android 17 负向报告，不足以归因，也不能泛化全部 LOS 24.0 |

检索覆盖官方 APatch/KernelPatch 仓库、文档和 issue/PR 中 umi/Mi 10、4.19.325、CFI、Android 17/LineageOS 24.0 组合。**未找到同时满足本目标精确版本、CFI 有效保留、授权负向测试与 PD/PPS 回归的通过材料**；检索无结果不是不存在任何私人成功案例的证明。

## 7. 与 Magisk 的维护、授权和 OTA 比较

以下以官方 APatch 11282 源码/当前附件与 Magisk v31.1 源码比较，都是候选分析，不是本机安装验收。

| 维度 | APatch / KernelPatch | Magisk v31.1 |
|---|---|---|
| LOS 内核源码维护 | 通常不用集成源码补丁；每个新 Boot 再做符号/指令/布局/安全 Hook 验证 | 通常无需集成 KSU/Hook 源码；以 init/ramdisk/daemon 为主要集成面 |
| Root 执行模型 | 内核先提权；App 的 su 后代直接进入 apd/shell，有清 Seccomp/AVC 豁免 | su 客户端通过 Unix socket 请求 daemon；daemon fork worker 执行命令，App 自身 filter 不因此被清除 [M-DAEMON] |
| 认证 / 用户授权 | 可信 Manager UID/证书摘要及可选 SuperKey；UI 预授予 UID，内核 allowlist 执行；生命周期问题见第 5 节 | peer credentials、SO_PEERSEC/客户端校验、Manager 和数据库；31.1 改为 Superuser 页**事前授权**，已移除请求时交互弹窗，不能套用旧教程 [M-SOCKET] [M-DAEMON] [M-DB] [M-CHANGES] |
| 构建安全选项 | 发布文件可按版本名覆盖，须固定二进制/源码映射 | `core/Cargo.toml` 默认启用 check-signature/check-client/su-check-db；无 su-check-db 有放行分支，不能使用任意裁剪构建 [M-FEATURES] [M-DAEMON] |
| Seccomp | 主路径明确更改目标任务状态；不满足严格模式 | 检查的 core/init/su 链未见 APatch 式移除 App filter；worker 是另一执行主体。不是对全仓所有可选模块的无绕过证明 |
| SELinux | AVC 拒绝/审计豁免 + policy magisk permissive，可选查询隐藏 | 默认 rules 同样将 magisk 域 permissive 并给广泛权限，严格模式仍不符合 [M-POLICY] |
| CFI / 内核修改面 | 增加二进制 Hook、动态代码及区域豁免 | 不需要同类通用内核 Hook；安装脚本仍有特定平台 kernel 二进制 patch 分支，实际 umi kernel 是否改变需比较，不能保证所有安装路径绝不碰 kernel [M-PATCH] |
| Android 17 | compileSdk 37 仅为构建信息；目标未知，存在其他设备正/负向局部记录 | v31.0 changelog 已明确 Zygisk Android 17/API 37 支持；不等于 umi Root、充电和 OTA 全面通过 [M-CHANGES] |
| 授权撤销 | 内核 grant 和 CSV/监听器有多处状态；不能自动回收旧 Root | 数据库 + SuInfo 缓存，需测撤销与缓存刷新；不能声称有完整安装代次/即时旧会话回收保证 [M-DAEMON] [M-DB] |
| 长期成本（定性判断） | 比维护本地 KSU 补丁队列少源码冲突，**多承担二进制适配和安全 Hook 回归** | 采用官方发行、接受其权限边界时，预计总体维护责任较低；自建 enforcing 策略 fork 会显著增加成本 |
| 当前采用结论 | 严格 NO-GO；常规也因生命周期、溯源与目标证据 BLOCKED | 严格 NO-GO；常规模式相对更成熟的维护参照，仍未获本目标验收，不自动改用 |

Magisk 的 daemon 模型适合把特权工作交给独立主体，能避开直接 su 继承 App filter 的结构性障碍；这项优势不等于满足本项目所有安全条件。其 v31.1 默认 `magisk` 域 permissive 已足以阻止严格模式采用，当前没有批准修改需求或迁移。

### 7.1 OTA 成本与上游变化的影响

APatch [官方更新说明](https://apatch.dev/update.html) 的保留 Root 流程使用 inactive slot，并明确提示不稳定；Magisk [固定版 OTA 指南][M-OTA] 只针对 A/B 流程，精确步骤仅在 Pixel 测过。**非 VAB 不等价于所有分区都 A-only，反过来也不能假定 umi 当前 ROM 有可用 inactive boot 槽。** 现有源码候选的独立 recovery/布局，不能代替实际 slot/update_engine/backuptool 证据。

Magisk 另有 `addon.d.sh` 的 A-only/backuptool 及 A/B 分支；APatch 安装脚本也有 slot/寻找 boot 的逻辑。代码存在不证明目标 recovery 能解密 /data、找到二进制、按正确时序恢复 Root，也不证明 OTA 保留脚本符合当前 LOS 验证链。[M-ADDON] [AP-UTIL]

| LOS 上游变化 | 影响的 APatch 组件 / 复核点 |
|---|---|
| 内核安全回移植、Clang/LTO/CFI 更新 | kptools kallsyms/symbol 查找、启动挂接点、跳板重定位、syscall dispatcher、CFI Hook；同为 4.19.325 也可能生成不同指令 |
| task/cred/LSM/SELinux 内部变化 | 运行时偏移推断、task extension、凭据修改、avc_denied/slow_avc_audit 参数和内联、policy 备份/查询隐藏 |
| boot header、Image 压缩、DTB/DTBO、分区/AVB 更新 | kptools unpack/repack、Image 增长与页对齐、boot 分区容量、原始备份与签名/摘要/rollback；不能只重用旧镜像 |
| init rc、挂载/加密、启动阶段变化 | userd rc 重定向、apd post-fs-data/services/boot-completed、SELinux 标签、模块挂载时序 |
| PackageManager 文件格式、APK 安装布局、签名方案或多用户模型变化 | Manager 包发现/证书解析/UID 失效、apd UID listener 和 CSV 同步、重装/换签授权 |
| Android App Seccomp 或 ABI 变化 | SuperCall 到达性、sucompat 的 native/compat 路径、执行 syscall 行为；不能补丁跳过新限制来宣称保持安全 |
| OTA、recovery、addon.d/backuptool 变化 | Root 是否被覆盖、恢复脚本能否读取 /data、slot 目标和失败回滚；APatch 和 Magisk 都要重验 |
| 电源/USB/热管理、vendor/DTBO 或服务权限变化 | 独立核验 PD/PPS 协商、充电温度/限流、USB 角色切换、休眠、关机充电等，Root 模块默认不应介入 |

因此“无需直接修改 LOS 内核源码维护”答案为**可以作为安装架构，但不是零维护**。每次 OTA 必须把新 ROM 配套原始 Boot/完整策略/manifest、APatch APK、kpimg/kptools/apd 和可选模块视为一组版本化输入；不能只更新 Manager，不能用已修改过的 KSU/Magisk Boot 混装测试。不改变驱动源码降低了直接修改驱动的风险，但全局 Hook、policy、模块或启动失败仍可能影响设备功能。

## 8. 两种目标下的决策与重新评估条件

| 目标 | 当前结论 | 原因 |
|---|---|---|
| 严格：不清 Seccomp、不绕 SELinux、不降 CFI | **NO-GO** | 固定标签及 main 的核心实现主动改变三者；完整 APatch 还将 magisk 域 permissive。配置 y/getenforce 输出无法推翻源码 |
| 常规：允许明确审查的 Root 边界变化，禁止未经授权提权/隐藏风险 | **当前 NO-GO / BLOCKED** | 尚未证明交付物包含必要修复；Manager UID 失效、grant 安装身份、撤销/持久化及包扫描上下文仍需修复/证明；目标运行、硬件与 OTA 证据缺失 |

下列是未来重新评估的门槛，不是本轮启动实验的授权或第二条推荐路线：

1. 先明确产品是否真的改为常规 Root，并列明任务级 Seccomp 关闭、SELinux 豁免/特权域 permissive、CFI 区域豁免、默认 ADB shell Root 和模块任意代码权限。不接受伪造安全状态作为验收手段；SELinux hide 保持关闭且验证实际状态。
2. 获得可证明源码归属的 KP/apd/Manager 发布组合，核对认证修复，解决 Manager 身份失效和授权生命周期问题；重新审查未授权命令、错误密钥、换包/换签、UID/PID 复用、shared UID、多用户、撤销竞争、掉电/重启持久化、包扫描锁上下文。
3. 取得精确 umi 24.0 ROM 的可信同次 target-files、原始 Boot、DTBO、vbmeta、recovery、完整 policy、manifest 及恢复材料；先做只读格式/符号/指令审查，缺失项保持 BLOCKED。
4. 只有另行批准后才考虑从纯净 `lineage-24.0` 建独立 `codex/apatch-umi-evaluation` 分支或独立产物研究库；不继承 KSU 提权改动，不混装两套 Root，不并入默认分支。Boot 型方案主要应保存输入锁、审计和验证，不应制造不必要的内核源码 fork。
5. 以后获准的设备阶段须包括双 ABI 普通 App 授权/拒绝/撤销、错误认证和旧身份负向测试、实际 Seccomp/SELinux/CFI 行为、安装更新冷缓存压力、连续启动/休眠与恢复、PD/PPS/USB/温度/关机充电等全硬件回归及至少一次真实 OTA/恢复。测试期间不通过关闭检查掩盖失败。本轮未执行任何此类工作。

严格模式只有出现能保持全部有效边界的新架构及相应证据才重新审议；“删掉清 Seccomp/Hook 代码后能编译”仍不能作为新架构通过。

### 验收问题的明确答复

| 问题 | 答复 |
|---|---|
| APatch 是否比目前 KSU 更值得继续？ | **在现有安全门槛下，不值得转为实施路线。** 免源码合并有价值，但没有解决严格模式，新增二进制 Hook/身份/溯源审查负担；不据“能 Root”覆盖安全失败 |
| 是否满足严格安全模式？ | **不满足，NO-GO** |
| 在哪里改变安全边界？ | 清 `_TIF_SECCOMP`/关任务 mode；AVC 拒绝与审计豁免、magisk 域 permissive；KP/Hook/KPM 区域 CFI 豁免；增加 SuperCall/Manager/SuperKey、默认 shell grant、模块控制面，另有可选安全查询隐藏 |
| 能否不直接改 LOS 内核源码维护？ | **可以采用原始 Boot 二进制修补模型**，仍修改 kernel/启动行为并承担每次镜像适配、安全及硬件验证 |
| 上游更新影响什么？ | kptools/kpimg 的符号、布局、Hook/CFI/SELinux；userd init/Manager 解析；apd/policy/模块；Boot/AVB/分区及 OTA 恢复链，详见第 7 节 |
| 是否值得现在创建独立实验分支？ | **现在不创建、不推荐进入可启动实验。** 先满足溯源和认证审查门槛；未来如另行批准常规模式，只可隔离研究，不能升级严格模式 NO-GO |

完成本评估不代表可刷写、发布或安全不可检测。**APatch、Magisk、KSU 均不能保证应用无法检测到 Root**，本文不把隐蔽性作为安全性或兼容性证据。最终唯一推荐保持：原生 LOS 内核独立维护，Root NO-GO。

## 9. 固定源码引用

以下链接固定到本轮实际读取的 Git 对象；issue/PR、文档和 release API 是调查当日的动态证据，状态及附件可能继续变化。上述哈希是本次记录的边界。

[AP-REL]: https://github.com/bmax121/APatch/releases/tag/11282
[KP-REL]: https://github.com/bmax121/KernelPatch/releases/tag/0.13.9
[M-REL]: https://github.com/topjohnwu/Magisk/releases/tag/v31.1
[AP-BUILD]: https://github.com/bmax121/APatch/blob/e8e4651c16fb5075882a25813c8732285fdb3505/build.gradle.kts
[AP-ASSETS]: https://github.com/bmax121/APatch/blob/e8e4651c16fb5075882a25813c8732285fdb3505/app/build.gradle.kts
[AP-DEPS]: https://github.com/bmax121/APatch/blob/e8e4651c16fb5075882a25813c8732285fdb3505/apd/Cargo.toml
[AP-POLICY]: https://github.com/AndroidPatch/ap_policy/blob/51ff1161e23a343971e3db764056ec6ee7c8cc2e/crates/policy/src/rules.rs
[AP-PATCH]: https://github.com/bmax121/APatch/blob/e8e4651c16fb5075882a25813c8732285fdb3505/app/src/main/assets/boot_patch.sh
[AP-CLI]: https://github.com/bmax121/APatch/blob/e8e4651c16fb5075882a25813c8732285fdb3505/apd/src/cli.rs
[AP-SHELL]: https://github.com/bmax121/APatch/blob/e8e4651c16fb5075882a25813c8732285fdb3505/apd/src/apd.rs
[AP-EVENT]: https://github.com/bmax121/APatch/blob/e8e4651c16fb5075882a25813c8732285fdb3505/apd/src/event.rs
[AP-JNI]: https://github.com/bmax121/APatch/blob/e8e4651c16fb5075882a25813c8732285fdb3505/app/src/main/cpp/apjni.cpp
[AP-GRANT]: https://github.com/bmax121/APatch/blob/e8e4651c16fb5075882a25813c8732285fdb3505/app/src/main/java/me/bmax/apatch/ui/viewmodel/SuperUserViewModel.kt
[AP-KEY]: https://github.com/bmax121/APatch/blob/e8e4651c16fb5075882a25813c8732285fdb3505/app/src/main/java/me/bmax/apatch/APatchApp.kt
[AP-HIDE]: https://github.com/bmax121/APatch/blob/e8e4651c16fb5075882a25813c8732285fdb3505/app/src/main/java/me/bmax/apatch/ui/screen/Settings.kt
[AP-PACKAGE]: https://github.com/bmax121/APatch/blob/e8e4651c16fb5075882a25813c8732285fdb3505/apd/src/package.rs
[AP-REFRESH]: https://github.com/bmax121/APatch/blob/e8e4651c16fb5075882a25813c8732285fdb3505/apd/src/supercall.rs
[AP-UTIL]: https://github.com/bmax121/APatch/blob/e8e4651c16fb5075882a25813c8732285fdb3505/app/src/main/assets/util_functions.sh
[KP-MAIN]: https://github.com/bmax121/KernelPatch/tree/d4c88d6672687456b299e4b5153c24dc979d789b
[KP-KEYFIX]: https://github.com/bmax121/KernelPatch/commit/0961c53457c7ad6c47924fbe87e7f93abb999de0
[KP-AUTHFIX]: https://github.com/bmax121/KernelPatch/commit/53c43f3ce650e94a46523f7ad17b30ce2bf0e3c9
[KP-CI]: https://github.com/bmax121/KernelPatch/blob/b51197aaba8f2272dd8a3e30c85698a29aa928c9/.github/workflows/build.yml
[KP-PATCH]: https://github.com/bmax121/KernelPatch/blob/b51197aaba8f2272dd8a3e30c85698a29aa928c9/tools/patch.c
[KP-BOOT]: https://github.com/bmax121/KernelPatch/blob/b51197aaba8f2272dd8a3e30c85698a29aa928c9/tools/bootimg.c
[KP-KALL]: https://github.com/bmax121/KernelPatch/blob/b51197aaba8f2272dd8a3e30c85698a29aa928c9/tools/kallsym.c
[KP-SYMBOL]: https://github.com/bmax121/KernelPatch/blob/b51197aaba8f2272dd8a3e30c85698a29aa928c9/tools/symbol.c
[KP-STRUCT]: https://github.com/bmax121/KernelPatch/blob/b51197aaba8f2272dd8a3e30c85698a29aa928c9/kernel/patch/ksyms/task_cred.c
[KP-ACC]: https://github.com/bmax121/KernelPatch/blob/b51197aaba8f2272dd8a3e30c85698a29aa928c9/kernel/patch/common/accctl.c
[KP-ACC-MAIN]: https://github.com/bmax121/KernelPatch/blob/d4c88d6672687456b299e4b5153c24dc979d789b/kernel/patch/common/accctl.c
[KP-CFI]: https://github.com/bmax121/KernelPatch/blob/b51197aaba8f2272dd8a3e30c85698a29aa928c9/kernel/patch/common/secpass.c
[KP-CFI-MAIN]: https://github.com/bmax121/KernelPatch/blob/d4c88d6672687456b299e4b5153c24dc979d789b/kernel/patch/common/secpass.c
[KP-INIT]: https://github.com/bmax121/KernelPatch/blob/b51197aaba8f2272dd8a3e30c85698a29aa928c9/kernel/patch/patch.c
[KP-MAKE]: https://github.com/bmax121/KernelPatch/blob/b51197aaba8f2272dd8a3e30c85698a29aa928c9/kernel/Makefile
[KP-SC]: https://github.com/bmax121/KernelPatch/blob/b51197aaba8f2272dd8a3e30c85698a29aa928c9/kernel/patch/common/supercall.c
[KP-SC-MAIN]: https://github.com/bmax121/KernelPatch/blob/d4c88d6672687456b299e4b5153c24dc979d789b/kernel/patch/common/supercall.c
[KP-SU]: https://github.com/bmax121/KernelPatch/blob/b51197aaba8f2272dd8a3e30c85698a29aa928c9/kernel/patch/common/sucompat.c
[KP-ABI]: https://github.com/bmax121/KernelPatch/blob/b51197aaba8f2272dd8a3e30c85698a29aa928c9/kernel/patch/include/uapi/scdefs.h
[KP-USERD]: https://github.com/bmax121/KernelPatch/blob/b51197aaba8f2272dd8a3e30c85698a29aa928c9/kernel/patch/android/userd.c
[KP-USERD-MAIN]: https://github.com/bmax121/KernelPatch/blob/d4c88d6672687456b299e4b5153c24dc979d789b/kernel/patch/android/userd.c
[KP-TASK]: https://github.com/bmax121/KernelPatch/blob/b51197aaba8f2272dd8a3e30c85698a29aa928c9/kernel/patch/common/taskob.c
[KP-PREDATA]: https://github.com/bmax121/KernelPatch/blob/b51197aaba8f2272dd8a3e30c85698a29aa928c9/kernel/base/predata.c
[KP-HIDE]: https://github.com/bmax121/KernelPatch/blob/b51197aaba8f2272dd8a3e30c85698a29aa928c9/kernel/patch/common/selinux_hide.c
[KP-HIDE-MAIN]: https://github.com/bmax121/KernelPatch/blob/d4c88d6672687456b299e4b5153c24dc979d789b/kernel/patch/common/selinux_hide.c
[KP-HOOK]: https://github.com/bmax121/KernelPatch/blob/b51197aaba8f2272dd8a3e30c85698a29aa928c9/kernel/base/hook.c
[KP-SYSCALL]: https://github.com/bmax121/KernelPatch/blob/b51197aaba8f2272dd8a3e30c85698a29aa928c9/kernel/patch/common/syscall.c
[KP-MODULE]: https://github.com/bmax121/KernelPatch/blob/b51197aaba8f2272dd8a3e30c85698a29aa928c9/kernel/patch/module/module.c
[LOS-CFI]: https://github.com/Ben8368/android_kernel_xiaomi_sm8250_ksu/blob/6b34d24765327d746074c8e53b5ad0d24a51acc7/kernel/cfi.c
[LOS-PTRACE]: https://github.com/Ben8368/android_kernel_xiaomi_sm8250_ksu/blob/6b34d24765327d746074c8e53b5ad0d24a51acc7/arch/arm64/kernel/ptrace.c
[M-DAEMON]: https://github.com/topjohnwu/Magisk/blob/0972f67d97f9b6302b67c5171283330c74114b4a/native/src/core/su/daemon.rs
[M-SOCKET]: https://github.com/topjohnwu/Magisk/blob/0972f67d97f9b6302b67c5171283330c74114b4a/native/src/core/daemon.rs
[M-DB]: https://github.com/topjohnwu/Magisk/blob/0972f67d97f9b6302b67c5171283330c74114b4a/native/src/core/su/db.rs
[M-FEATURES]: https://github.com/topjohnwu/Magisk/blob/0972f67d97f9b6302b67c5171283330c74114b4a/native/src/core/Cargo.toml
[M-POLICY]: https://github.com/topjohnwu/Magisk/blob/0972f67d97f9b6302b67c5171283330c74114b4a/native/src/sepolicy/rules.rs
[M-PATCH]: https://github.com/topjohnwu/Magisk/blob/0972f67d97f9b6302b67c5171283330c74114b4a/scripts/boot_patch.sh
[M-OTA]: https://github.com/topjohnwu/Magisk/blob/0972f67d97f9b6302b67c5171283330c74114b4a/docs/ota.md
[M-ADDON]: https://github.com/topjohnwu/Magisk/blob/0972f67d97f9b6302b67c5171283330c74114b4a/scripts/addon.d.sh
[M-CHANGES]: https://github.com/topjohnwu/Magisk/blob/0972f67d97f9b6302b67c5171283330c74114b4a/docs/changes.md

可复核元数据入口：[APatch latest release API](https://api.github.com/repos/bmax121/APatch/releases/latest)、[KernelPatch latest release API](https://api.github.com/repos/bmax121/KernelPatch/releases/latest)、[Magisk latest release API](https://api.github.com/repos/topjohnwu/Magisk/releases/latest)。这些入口会漂移；复核时同时比较本文 tag、commit、附件大小、created_at 和 SHA-256，不仅比较版本号。
