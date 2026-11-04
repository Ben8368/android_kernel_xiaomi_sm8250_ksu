# Seccomp 与通用应用 Root 可行性（第四阶段）

结论：**NO-GO，针对当前 v1.1.1 直接 su 架构与既定约束。** 经用户授权的普通应用通用 Root 尚未实现。停止在这条架构上继续叠加“跳过几个调用”的兼容补丁；这不是所有特权服务架构的不可行性证明。

## 事实与执行时序

2026-11-04 重新读取 LineageOS `lineage-24.0`：bionic 为 `ff3bb041547924ac1a7504e4b3bd3ea18169ca2f`；frameworks/base 为 `1f46fb30f571cf79cd79ee041b4ff192e95240af`。固定源码、上游 Git blob 和 SHA-256 见 [sources.lock.json](validation/stage4/sources.lock.json)。这些是公开分支源码，**没有目标手机精确 ROM 构建的生成策略或二进制**。

1. Zygote `SpecializeCommon` 在安装 App filter 前设置附加组和 `setresgid`，安装后再执行仍被允许的 `setresuid`。普通 App 继承已经安装的 filter。
2. bionic 使用真实 `gensyscalls.py` parser 和 `genseccomp.py::merge_names`：`SYSCALLS − (COMMON+APP blocklist) + (COMMON+APP allowlist)`。arm64 和 arm 均排除 setgroups/setresgid 对应 syscall，也排除 mount/umount2/chroot/reboot 等；prctl/setresuid 保留。不能依据旧 Android 文档或 AppZygote 的不同策略反推普通 App。
3. v1.1.1 的 `sucompat.c` 在 native `__arm64_sys_execve` probe 中识别 `/system/bin/su`，检查 UID 授权，再改写为 `/data/adb/ksud` 并调用 `escape_to_root`。凭据转换在 ksud 被执行前发生；0009 把 profile 改为调用方副本并再次检查授权。
4. UID/GID/groups/caps 的内核赋值不等于执行用户态 setgroups syscall，因此能先完成凭据转换。但过滤器没有被移除；execve、fork/clone 和后续 shell 的 exec 不清除它。这里的 filter 检查 syscall 号/参数，没有“变成 UID 0 就自动豁免”的路径。Linux 4.19 的 [Seccomp 继承说明](https://www.kernel.org/doc/html/v4.19/userspace-api/seccomp_filter.html) 与本树 `kernel/fork.c`/`kernel/seccomp.c` 相符。
5. ksud `root_shell` 的 pre_exec 无条件调用 `set_identity`，其中依次调用 set_thread_groups/set_thread_res_gid/set_thread_res_uid。前两者被 App 策略拦截。bionic 终止路径使用 `SECCOMP_RET_TRAP`，产生 SIGSYS；Rust `.ok()` 仅丢弃正常 Result，不能让被 TRAP 的进程继续。是否有额外信号处理或附加过滤器，仍须检查目标二进制和真机。
6. Manager 的 `debug su`/bootstrap 使用 `prctl CMD_GRANT_ROOT → grant_root → sh`，不走上述 `set_identity`。它仍继承 Manager 的 App filter，也仍需证书认证和内核门禁。它不是普通应用通用 Root，也没有真机成功证据。

`test-ksu-seccomp-policy.py` 执行固定源码 parser/合并，并给一次性 host 子进程增加一个更严格的测试 filter，验证 exec 前后 SIGSYS。没有修改 Android BPF/策略、内核安全判断或宿主父进程过滤器。该 fixture 不能替代 Android 17 真机或生成策略测试。

## 候选方案及边界

| 方案 | 能力与安全边界 | 决定 |
|---|---|---|
| 官方直接 su，保留 App filter | 凭据已转换，但 ksud 重复设置身份即触发阻断 | 不可用 |
| 用户态仅在身份完全相同时省略重复调用 | 可能使部分 shell 命令启动；必须逐字段验证实际 UID/GID/groups/caps，不可忽略失败 | 没有实现；mount/chroot/reboot 等仍阻断，不满足通用目标 |
| Manager prctl bootstrap | 认证 Manager 自身的受限执行路径，仍继承 filter | 未验证；不能替代普通应用 |
| 新的受控特权服务 | App 保留 filter，命令由另一、具有自己受审策略的 init 后代执行 | 原理可行，缺少可直接采用的受审实现；BLOCKED |
| 清除 filter、Hook 跳过安全检查、放宽 BPF | 破坏既定约束 | 禁止；未实现 |

任意应用还可自行追加过滤器，所以“App Root”不能承诺在该应用原进程内执行任意 syscall。服务方案把受审工作交给不同执行主体，必须明确告知授权范围，不能伪称原进程不再受限制。

## 独立服务的威胁模型（设计审查，非实现）

资产：Root 命令执行权、Manager 身份、授权/撤销数据库、包签名绑定、会话 FD、目标 ROM Enforcing 与系统服务完整性。攻击者包括未授权 App、共享 UID 的其他包、UID/PID 被复用后的进程、伪造请求者字段、转交 socket/FD 的进程，以及已撤销但持有旧会话的调用者。获准任意 Root 的恶意程序本就能危害整个系统；不能用 SELinux Enforcing 宣称能约束所有已获 Root 行为。

| 边界 | 必须满足的要求 | 本轮状态 |
|---|---|---|
| 服务启动 | init 启动、可信文件所有者/标签/完整性；服务采用独立明确的 Seccomp/SELinux 策略，不继承 App filter，也不清除任何现有 filter | 未实现 |
| 调用者身份 | 内核提供的 peer credentials/SELinux peer label；稳定进程引用防 PID 复用；不可相信请求中的 UID/package/PID | 未实现 |
| 包身份 | 完整 userId+appId、安装代次、包签名和共享 UID 语义；安装/卸载/签名变化立即失效并重新授权 | 当前 KSU ABI 不提供完整绑定 |
| 用户授权 | 使用已验签 Manager 的原生认证链；逐次检查当前 grant 和请求目标；Manager IPC 回复不能由普通包伪造 | 未实现 |
| 执行权限 | 明确任意 Root shell 或有限 API；按 profile 设置身份/caps/domain/namespace；禁止环境、工作目录、加载路径和动态库注入服务自身 | 未实现 |
| 会话与 FD | 请求大小/数量上限、超时和资源配额；限定 stdin/out/err、PTY 和 SCM_RIGHTS；防继承服务内部 FD、跨应用转交令牌和 confused deputy | 未实现 |
| 撤销 | 有代次的授权快照；撤销与新会话创建有确定先后关系；定义终止旧会话及其后代的规则 | 未实现 |
| 崩溃与重启 | 原子持久化/fsync/故障测试；不得恢复已经撤销的旧 grant；失败默认拒绝 | 未实现 |
| 证据 | IPC 模糊测试、并发授权/撤销、UID/PID/FD 复用攻击、目标策略编译/neverallow、真机负向测试和独立审查 | 缺失 |

公开服务架构参考是 [Magisk 的 su daemon](https://github.com/topjohnwu/Magisk/blob/33bfff7ce750c27f157ddb4580e36bf842d6d95b/native/src/core/su/daemon.rs)，固定的 daemon/connect/db 源码已保存。它有请求凭据、Manager/数据库决策等机制，但仅阅读三个文件不足以完成安全审查；还必须锁定启动、socket、构建 feature、Manager、数据库和 SELinux 路径。特别是源码存在 `not(feature = "su-check-db")` 的 allow 分支，不能不审构建配置就复制为可信服务。**本轮没有引入或启动该服务，也未断言它在此 ROM 已通过验证。**

替代路线是另立完整用户态/ROM 集成项目，选择成熟的认证服务架构并完成上表验证，或正式缩小为明确列出的受限任务 API。后者需要用户改变目标；本轮不把它当作通用 Root 已完成。
