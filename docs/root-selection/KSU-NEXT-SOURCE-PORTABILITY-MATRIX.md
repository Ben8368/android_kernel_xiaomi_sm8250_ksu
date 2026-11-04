# KernelSU Next v3.4.2 / dev 源码与 4.19.325 可移植性审查

审查日期：2026-11-04。对象为 KernelSU Next v1.1.1 `0d6bdc6364cbfc73517dcfdf7ab23b0ba8045553`、v3.4.2 `4c706b5938665866ebe16944a481a7b91e3396af` 和官方 dev `a6c81fa4a8b7341d0bc5c3e4507531459df871ae`。dev 相对 v3.4.2 有 100 个提交。目标内核证据来自 LineageOS 内核提交 `6b34d24765327d746074c8e53b5ad0d24a51acc7`；未运行构建或设备测试。

**结论：v3.4.2 确实修复多项 v1.1.1 内存安全、签名解析、凭据隔离和 UID 记账问题，但仍有授权生命周期及失败关闭阻断。dev 另外修复了真实缺陷，不能因目标 4.19 移植困难而忽略。两者均不可直接移植到 4.19.325；dev 不能整体回移植，v3.4.2 也不能以可编译替代安全验收。KSU 候选 BLOCKED。**

## 源码差异矩阵

| v1.1.1 已发现事项 | v3.4.2 | dev 相对 v3.4.2 | 目标安全结论 |
|---|---|---|---|
| APK SHA 错误码被 `IS_ERR` 判断、短读/长度边界不足 | **已修复**：整数错误码直接判断；精确读取、有界证书和嵌套签名块解析 | 核心解析器未见实质变化 | 修复证书摘要提取与容器解析；不是独立完整 APK 签名链验证。发行 Manager 与内核 pin 的证书/构建对应仍需验证 |
| allowlist 裸指针并发释放、UID bitmap 与 profile 分叉、负组数/列表边界 | **已显著修复**：RCU hash + kref、不可变替换、有界复制、版本化 profile、持久记录长度检查；groups_count 无符号 | 同一 RCU 结构，主要变化为减少锁内高频日志 | 仍有授权语义阻断：授权查询和 profile 查询分离；撤销重叠时失配可能回退默认 profile。profile 对 UID/GID 范围、未知 flags/caps 等仍有验证缺口 |
| Manager tracker 未初始化 fp/解析终止、卸载缓存缺陷 | **部分修复**：初始化/错误检查、互斥解析、package+UID 与可选 `KSU_MANAGER_PACKAGE` 校验、变化失效、task_work 延迟扫描 | **修复 fsnotify 生命周期**：`786f73e6218dc97bf5adc769aceb418531c894a1` 添加 `free_mark`，销毁 group 前 drain mark work | 仍阻断：Manager package pin 可选；未 pin 时只检查 appId 存在；appId 为 UID 模 100000；同名同 UID 不强制重验签；无安装代次/证书授权键；扫描失败可能保留缓存。v3.4.2 缺 mark free/drain，不能视为安全卸载 |
| exec kprobe 内执行可睡眠凭据变更/修改已发布 SELinux cred | **架构已替换**：syscall tracepoint 选路，改分派槽后在正常 syscall 分派中处理 exec；`prepare_creds` 上变更后 `commit_creds` | 核心路径相同 | 改善旧原子 kprobe 风险；仍需验证 syscall-table 分派、CFI、初始化失败回滚、32 位/execveat。非全系统调用兼容证明 |
| UID 改变不更新 user 记账 | **已修复**：`alloc_uid/free_uid`；仅 5.14+ 更新 ucounts | 未见回退 | 4.19 应使用 `user_struct` 分支；核实 user namespace、错误回滚和 commit_creds 记账 |
| Manager 可借 su session FD 调管理 ioctl | **已收紧**：逐 ioctl 权限表；su-session FD 只豁免 wrapper/disable escape，不含 grant/profile；exec 成功后安装 CLOEXEC FD | 同核心行为 | 需验证 FD 传递和调用者身份。UID 0 仍能管理，是完整 Root 的明确权限例外 |
| grant/revoke 在 irq-off/tasklist 锁内高频 printk，可能 watchdog | v3.4.2 仍存在 | **已修复**：`b462d4c1a0a096f7afd5d542fd0d6c944e07f171` 删除临界区逐线程日志 | 移植必须保留，虽不改变认证逻辑但关系稳定性 |
| file wrapper 原始 file 引用泄漏 | v3.4.2 有 | **已修复**：`c7e66ae0315857e96a0b547503630e278f4bec7e` reopen 后 `fput(orig_file)` | 需独立回移植并做引用生命周期测试 |
| SELinux AVC grant generation 固定/传零 | v3.4.2 旧语义 | **已修复**：`48501dadfbe627798b8da78a52cf029ec3e84e18` 追踪 latest_granting 并传至 AVC/status/netlink | 需映射 4.19 security server/AVC 世代语义；不能只换参数或复制新 struct |
| 撤销持久化/Manager 换签/UID 重用 | **未完整修复** | 未发现关闭上述风险的提交 | BLOCKED。保存使用 `O_TRUNC`、0644、忽略 profile 短写、非原子替换；load 逐条发布并忽略部分错误。ACK 不是 durable revoke。0644 影响需结合目标目录 DAC/SELinux 判断 |
| groups / SELinux profile 应用失败 | **未修复**：`setup_groups` / `setup_selinux` 为 void，失败后仍提交 creds | dev sucompat 重构未关闭该问题 | fail-closed 阻断：请求 profile 与实际身份可能不一致 |
| 授权查询与 profile 获取分离 | **仍有竞态疑点**：撤销后第二次查找失配可能回退默认 profile | 未见事务化修复 | 按重叠撤销线性化语义定向验证；不能断言任意应用已能提权，也不能解除 BLOCKED |

## Linux 4.19.325 可移植性矩阵

标记：**低**=原生 API 基本具备，需配置/编译验证；**中**=兼容层和语义测试；**高**=重构；**阻断**=不能宣称安全移植。

| 子系统 / 4.19 原生证据 | Next 需求 | 结论与必要工作 |
|---|---|---|
| RCU / mutex / kref / hash / kfree_rcu | allowlist 并发和生命周期 | **低**。保留现代 RCU 设计；不回退裸指针/旧 bitmap。验证配置、锁序、竞态 |
| execve/execveat syscall tracepoint 与 dispatcher | tracepoint 选路、替换 syscall nr | **高/阻断**。目标 arm64 `ptrace.c` 在 `trace_sys_enter` 前先 `secure_computing`；Seccomp 限制的 reboot 安装握手在 KSU 回调前已拒绝。Manager 预装 FD、授权 app execve/execveat 是独立可能路径，需分别证明；这不表示所有 su 都依赖 reboot。核对 SVC/compat、CFI、patch failure 原子回滚 |
| task_work | Next 用 `TWA_RESUME`；4.19 是 `task_work_add(task, work, bool notify)` | **中**。仅做明确 notify 映射，审查退出任务和失败处理。分配/排队失败时当前 observer inline scan 可能在 fsnotify/rename 锁上下文做睡眠工作 |
| fsnotify | Next `.handle_inode_event`；4.19 `.handle_event(group,inode,mask,data,type,name,cookie,iter)`；4.19 已有 `free_mark` 和 `fsnotify_wait_marks_destroyed()` | **高**。适配回调原型，保留 dev free_mark + drain；watch 初始化失败需返回失败。不得将 v3.4.2 当前释放实现视为安全 |
| Seccomp filter | Next 假定现代 filter/action cache/`filter_count`/`seccomp_filter_release`；4.19 为 usage/prev/prog，只有 `put_seccomp_filter(task)` | **高/阻断**。不可伪造 struct。put 只减引用，不等价于正确解除当前线程的 filter 链。要么在授权 Root worker 上按 4.19 引用语义实现并测试，要么保留 filter 并接受命令受限；检查线程共享 filter，不可全局关闭无关应用 Seccomp |
| ARM64 Seccomp bootstrap | setuid hook 缓存 reboot filter；目标 seccomp 先于 syscall tracepoint | **阻断**。no-op cache 仅过编译，不能让握手越过 seccomp。Manager 继承 FD、ksud 扫描 driver FD、su exec 分派需逐条验证；尚无完整 4.19 通路证据 |
| SELinux | Next 依赖 `selinux_state.policy/policy_mutex/struct selinux_policy` 等现代模型；4.19 是 `selinux_state.ss`、旧 policy_rwlock/security server，AVC reset 两参数 | **高/阻断**。不是字段别名；需重写 grant/AVC 更新、同步及 generation，使用目标 ROM policy 验证。dev 的 grant generation 修复不能因难移植被略过 |
| mount namespace | Next 无条件依赖 `uapi/linux/mount.h`、`path_mount/path_umount`；4.19 无等价 path API | **高**。决定禁用相关可选功能或按旧 `do_mount` 语义实现；禁止伪造 extern 或重新按路径查找来假装兼容 |
| file wrapper fops | Next 使用 `iopoll`、`remap_file_range`、`REMAP_FILE_DEDUP`；4.19 使用旧 clone/dedupe hooks | **中/高**。区分可弃用 op 与 TTY/open/read/write 主功能；保留 dev `fput` 修复并做 fd 引用测试 |
| CFI / `__nocfi` | 目标 clang 有局部 `__nocfi` 属性 | **中/配置相关**。每个函数指针原型、syscall wrapper、符号解析、文本写保护核实实际 config；局部豁免不等于关闭全局 CFI |
| UID accounting | 4.19 仍是 user_struct，无新版 ucounts | **低/中**。保留 `alloc_uid/free_uid` 旧分支；验证 namespace 和错误回滚 |
| 32-bit compat | Next hook manager 对 compat task 早退 | **中/高**。若 ROM 支持 32 位应用，验证原生 64 位 ksud 调用路径；不能宣称 direct compat syscall 已支持 |
| 发布 KMI | Next LKM 发布资产 KMI 起点 5.10 | **不适用**。不能据发布 LKM 认定支持 4.19；只能评估 in-tree 集成和本地维护负担 |

## Manager / ksud 版本与发布归属

v3.4.2 的 `uapi/supercall.h` 定义 UAPI 5、`uapi/app_profile.h` 定义 profile ABI 4；固定 dev 将 UAPI 提升为 6。`userspace/ksud/src/ksucalls.rs` 的 `ensure_uapi_version_matched()` 要求内核和 ksud UAPI **精确相等**，`init_event.rs` 在不匹配时跳过事件，模块路径也要求匹配。Manager JNI `manager/app/src/main/cpp/ksu.cc` 扫描已有 driver FD，`GET_INFO_LEGACY` 只作为版本探测回退并把 UAPI 标为 0，不是旧 prctl 授权通道。`userspace/ksud/src/su.rs` 的 root shell 基于内核已授予的 profile，只有显式请求 identity 时再调用 `set_identity()`；不应把它当 Magisk 式独立授权 daemon。

因此内核 v3.4.2 + dev ksud/Manager、或仅替换旧 v1.1.1 用户态，不能据“能启动”认定 ABI 相容。还须检查 ABI 结构大小、ioctl 编号、Manager 签名证书常量与实际 APK、嵌入到 APK 的 ksud 和独立 release ksud 是否一致。官方 release API 列出普通 `KernelSU_Next_v3.4.2_33355-release.apk`（16,682,167 bytes，SHA-256 `774a5511f7034a4930e881114e202319cbdc34c5aaaa5c7c6b6d2902364e4c58`）及 `ksud-aarch64-linux-android`（7,059,592 bytes，SHA-256 `2771a2ae989b522b5d70f3288ad5a2f379488962d09c1fe11e13a745eba89362`）。**这里只核对了发布元数据，没有下载这些附件、验 APK 证书或证明 APK 内嵌 ksud 与独立发布件逐字节相同。发行二进制归属与证书 pin 对应继续 BLOCKED。**不选 spoofed Manager 附件作为正常候选。

## 对选型的影响

v3.4.2 不是“旧而能编译”的捷径：身份/撤销/profile 错误路径仍阻断，4.19 Seccomp/SELinux/挂载移植成本大。dev 是必须尊重的修复语义来源，尤其 fsnotify mark 生命周期、文件引用、临界区日志和 SELinux grant generation；但不适合整枝回移植，也未关闭 Manager/授权身份风险。

按减少长期内核补丁的目标，KSU 对 4.19.325 需高成本 API/安全语义维护。综合报告仍推荐官方 Magisk 作为下一步验证候选，而非部署结论。KSU v3.4.2/dev 均 **BLOCKED**。

## 证据边界

官方 API metadata、完整 tree 和 compare patch、原始归档哈希及目标 ROM 内核源码哈希清单位于 [KSU evidence](evidence/ksu-next/)；[4.19 原生 API 快照](evidence/ksu-next/native/)随文档保存。完整上游源码归档不复制到 PR；可按固定 SHA 从 [v1.1.1](https://github.com/KernelSU-Next/KernelSU-Next/tree/0d6bdc6364cbfc73517dcfdf7ab23b0ba8045553)、[v3.4.2](https://github.com/KernelSU-Next/KernelSU-Next/tree/4c706b5938665866ebe16944a481a7b91e3396af)、[dev 固定提交](https://github.com/KernelSU-Next/KernelSU-Next/tree/a6c81fa4a8b7341d0bc5c3e4507531459df871ae)复核。只读静态检查：未构建 KSU、运行 APK/ksud、连接/刷写设备或修改实验分支。重点路径：`kernel/manager/apk_sign.c`、`kernel/policy/allowlist.c`、`kernel/policy/app_profile.c`、`kernel/manager/throne_tracker.c`、`kernel/manager/pkg_observer.c`、`kernel/hook/syscall_hook_manager.c`、`kernel/hook/setuid_hook.c`、`kernel/selinux/`、`userspace/ksud/src/ksucalls.rs`、`userspace/ksud/src/su.rs`。
