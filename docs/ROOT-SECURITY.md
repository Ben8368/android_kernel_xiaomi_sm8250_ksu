# Root 安全审计：第四阶段

基线：KernelSU Next v1.1.1 `0d6bdc6364cbfc73517dcfdf7ab23b0ba8045553`，补丁 0001…0010。**NO-GO：普通应用通用 Root 在现有直接执行架构与保留 App Seccomp 的约束下未实现。禁止把离线测试或编译通过称作可进入刷机测试。** 第三阶段记录保留为历史证据，由本文更新当前状态。

## 已完成的内存与发布规则（0009）

- 每条 app_profile 发布后不可变。写入先在锁外用 GFP_ATOMIC 分配新记录，短 `spin_lock_irqsave` 只串行化查找/RCU 发布/计数；没有锁内文件 I/O、GFP_KERNEL、用户复制或等待。1024 条总上限防无界表增长；满表和分配失败返回 false，保持原状态。拒绝不是授权成功。
- 读路径使用 RCU，返回调用方持有的副本。`ksu_get_root_profile(uid, out)` 同时检查当前记录的 allow_su 并复制自定义/默认 profile；最多三次 seqcount 重试，持续修改时拒绝。`escape_to_root` 不再持有内部指针，不会因 prune/free 使用已释放对象。
- 删除与替换都标记原记录 retired，`call_rcu` 在宽限期后释放。prune 在 RCU 中判断，随后持短写锁检查**同一个对象**是否已 retired，避免删除并发替换的新记录。predicate 的契约是不可睡眠、无副作用、不保存 package/data 指针；当前 predicate 仅比较调用方拥有的包列表。
- 普通 UID 只有一条记录，更换 package key 也替换旧记录，避免旧 bitmap/high-UID 数组与 profile 表分叉；旧两份缓存删除。`#`/`$` 默认项仅允许保留 UID 9999，不作为 UID Root grant。Shared UID 仍是同一个安全主体，不存在包级隔离承诺。
- 默认 profile 的初始值在初始化后不再写，覆盖值也使用不可变记录。列表导出及持久化通过 seqcount 检查有界副本；文件 I/O 在 RCU 外。写盘过程中有新修改则重排保存工作；加载工作在首次实时修改后不再导入旧记录，防覆盖撤销。
- Manager UID 使用 READ_ONCE/WRITE_ONCE；删除未验签的按 appId 动态提升为其他用户 Manager UID 的分支。Manager 证书常量、APK 验签和 GET/SET profile 的 manager-only 外层门禁保留。此改动没有解决全部身份生命周期问题。
- 收尾先关闭更新，再 cancel load/save work，释放记录后 rcu_barrier。契约要求调用方已停止 producers/hooks；目标是 built-in KSU，**不宣称 upstream 可卸载 LSM 路径安全**。

| 调用路径 | 可能上下文 | 本轮规则 |
|---|---|---|
| sucompat exec/stat/access/devpts | kprobe，禁止睡眠；不支持 NMI | 授权/副本读取为 RCU，不能加 mutex |
| prctl GET/SET profile | 本配置为 task_prctl LSM；其他接线可能是 kprobe | profile 输入复制在上游调用方；表的写入分配 GFP_ATOMIC，发布短 spinlock，不依赖可睡眠上下文 |
| ksu_uid_should_umount/task_fix_setuid | LSM/凭据路径 | 不返回内部指针，RCU 中无 I/O |
| throne tracker prune | inode_rename 路径；上游本身还做可睡眠 I/O | prune 的表操作不睡眠；**tracker 调用环境仍需单独修复/验证** |
| save/load worker | ordered workqueue，允许睡眠 | 先拷贝/退出 RCU，再文件 I/O；没有持写锁跨 I/O |
| unload/exit | 仅已停 producers 的进程上下文 | 允许 cancel_work_sync/rcu_barrier；不能从 probe 调用 |

Host 测试编译的是实际完整 allowlist.c，Linux API 由明确的 pthread/liburcu/文件适配层替换；没有复制一份授权算法。ASan/UBSan 与确定性 prune/replace 竞争、并发读写/保存、释放计数、撤销后新查询、旧加载、高 UID、多用户 UID、容量失败和非法参数均覆盖。**没有在目标内核运行 lockdep/KASAN/KCSAN；host RCU 无法模拟 IRQ/preempt/目标 CFI。**

## 撤销语义和未修复项

内存更新完成后，新开始的稳定授权快照读取最新 deny；与撤销重叠的请求可在线性化点获得之前的授权副本。撤销不会回收已提交给进程的 UID/caps/SELinux context 或它已经派生的后代，也没有 promise 终止全部旧会话。必须把“禁止新会话”和“回收已有 Root”分开验证。

**以下事项继续 BLOCKED，不能回答“allowlist 生命周期全部已修复”：**

1. UID/package/certificate：持久 ABI 只有 package+UID，没有安装代次/证书绑定；相同包名和 UID 重装/换签、共享 UID、多用户卸载尚不能充分识别。throne tracker 仍按异步包列表发现变化；Manager 缓存检查“UID 仍存在”不能排除 UID 被其他包重用，也不能替代每次授权的稳定身份。
2. Tracker 解析/上下文：上游 `track_throne` 在 rename 通知中进行等待/文件遍历，存在未初始化 fp、解析终止/缓存等需要独立重构的路径；本轮没有把局部 RCU 修复包装成整个包身份服务已安全。
3. 持久化：保存是私有一致快照，仍非原子替换/fsync 事务；写盘失败或掉电可能留下旧/部分状态。Manager 的更新 ACK 只代表内存接受，不能称撤销已持久落盘。不修改格式也没有内核内完整身份代次可恢复。
4. Root 转换：exec kprobe 中原有 prepare_creds/groups_alloc 等可睡眠分配、用户栈写入，以及 `setup_selinux` 对已发布 credential/security 的直接修改还需专门上下文和共享凭据审查。修好 profile 指针不会修好这些路径。未证明 kprobe 注册成功或无 CFI/atomic-sleep 告警。
5. LSM unload 与初始化：upstream 没有可靠的完整 LSM hook 移除；仅验证 built-in 编译。不能将 rcu_barrier 当作停止所有回调的证明。

## SELinux 与 Root 功能边界（0010）

25 条含 ALL 的 bootstrap 调用（含四条全 ioctl xperm）已删除；不再新增 MLS/网络/蓝牙豁免。只保留 22 项能由内核文件操作证明的 metadata/store 权限。root-only 运行时 policy 注入返回 EOPNOTSUPP，避免重新引入通配/permissive 并绕开 neverallow。外层认证未放宽。LOS userdebug/eng 自带 permissive su 的问题也被明确发现，显式 enforce su。

这会使缺少目标策略的 ksud/PTY/init/模块功能不可用。**这是收紧和隔离未审查功能，没有实现通用 Root；不以功能缩水宣称目标完成。** 还没有目标 ROM 完整 policy；编译/neverallow 和真正 Enforcing 行为仍 BLOCKED。矩阵、剩余较广的 DAC 能力及 adb_data_file 标签粒度见 [SELINUX-MATRIX.md](SELINUX-MATRIX.md)。

官方 root_shell 的 setgroups/setresgid 会被 App Seccomp TRAP。即使改写这两个调用，mount/chroot/reboot 等仍受限。Manager bootstrap 不代表普通 App；没有新增 IPC 特权服务或清除/绕过 Seccomp。候选和服务威胁模型见 [SECCOMP-FEASIBILITY.md](SECCOMP-FEASIBILITY.md)。

## 当前结论及新增风险

安全回归的 PASS 只证明所测约束没有回退。整体静态安全审查、目标 policy、精确 Boot 输入、真机启动和普通应用 Root 均不通过。`check-ksu-readiness.py` 分七项报告；缺证据为 BLOCKED，不能填 PASS JSON 升级真机状态。

本轮新增的可用性风险是 GFP_ATOMIC 分配失败/1024 条上限拒绝更新、密集写入导致快照拒绝、策略收紧导致已有功能失败；RCU/seqcount 改造仍需真实内核压力验证。没有新增无认证服务或放宽 Manager 身份验证；仍不能证明“没有新增安全风险”或“完全最小权限”。当前不适合人工真机 Root 验收。
