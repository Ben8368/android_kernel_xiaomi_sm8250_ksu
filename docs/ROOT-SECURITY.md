# Root 权限链路与阻断项

审计基线：v1.1.1 + compat/kernelsu-next/0001…0008。**静态回归通过不等于安全审计全部通过。当前禁止进入刷机测试。**

## 授权到撤销

1. Manager 不是任意调用 CMD_BECOME_MANAGER 就取得身份。throne_tracker 扫描已安装 APK 证书、从系统 packages.list 关联 UID。认证的 Manager UID 可设置 app_profile；同 UID/shared UID 应用共享授权边界，不能声称包级隔离。
2. 用户在 Manager 修改授权，JNI setAppProfile→ksu.cc::set_app_profile→prctl CMD_SET_APP_PROFILE。内核先执行 from_root/from_manager 外层门禁，再在 GET/SET_APP_PROFILE 前执行 manager-only 门禁，copy_from_user 后更新 allowlist/bitmap。普通应用未获授权时不会凭 su 调用自动获得弹窗/临时授权；应在 Manager 明确授权测试 UID。
3. sucompat 的 arm64 __arm64_sys_execve kprobe 检查精确 /system/bin/su 和 ksu_is_allow_uid，改写到 /data/adb/ksud，escape_to_root 根据 profile 设置 UID/GID/groups/caps，再设置 SELinux context。Manager 的 debug su 是另一条 CMD_GRANT_ROOT→is_allow_su→escape_to_root→用户态 sh 路径。
4. Seccomp 始终保留；SELinux 不自动 permissive。Root profile 不等于完全可执行所有 syscall，namespace 模式与 per-app unmount 在该 4.19 候选不支持。
5. Manager 取消 allow_su 后更新授权缓存，保存 /data/adb/ksu/.allowlist，后续新的 su 入口应被拒绝。撤销**不会追溯回收**已有进程的 UID/caps/context 或子进程权限；必须人工结束已有 Root 会话再测试新调用，不可把 UI 撤销称为已有 Root 全部失效。
6. 卸载/包列表更新会触发 throne tracker、Manager invalidation 与 allowlist prune；UID 复用、多用户/工作资料跨用户 UID 改写、重装/证书变更都必须负向验证。当前 manager UID 缓存不是每次请求重新验 APK。

## 本轮确定修复（补丁 0008）

- get_allow_list 原来可把超过 128 个 profile 写入内核栈上的 array[128]。现在调用方传入 capacity，超容量返回失败和长度 0，不向用户复制部分授权列表。
- profile 要求恰好 ABI v2、非负 current_uid/root UID/GID、groups_count 为 0…32；key/domain 必须在固定数组内 NUL 结束，避免 strlen/strcmp 越界和负 UID bitmap 下标风险。
- 持久化文件拒绝错误格式号和短 record，先验证再打印或导入；新建文件 mode 0600（不假称改变已存在文件的 mode、实现原子写或抵御已获 Root 的篡改）。
- 把 CAP_DAC_READ_SEARCH 的**编号**改为 1ULL << CAP_DAC_READ_SEARCH 位掩码，避免定制 profile 临时添加错误 capability。
- Host harness 编译的是补丁后的真实函数，ASan/UBSan 覆盖非法输入和 0…200 个授权项；不声称测到了内核并发或 CFI 运行行为。

## 尚未解决，不能出具“安全验证通过”

### S1：SELinux Enforcing 但 su 权限仍近似全放行

规则仍含 ksu_allow(db, KERNEL_SU_DOMAIN, ALL, ALL, ALL)、对 su 的所有 ioctl xperm，以及 ALL→ksu_file 的全部权限。保持 enforcing 仅证明没有 automatic permissive，**不等于最小权限**。尤其不应在未检查实际对象标记之前认为 ksu_file 的访问安全。

下一步需拿到同一 ROM 的编译后 sepolicy，建立明确任务能力集合，并逐对象/类/权限列出规则。最小 Root smoke test 候选需要：init 到 su 的显式转换/执行与 daemon 的 adb_data_file 访问；su 对 shell/system 可执行文件的 read/open/getattr/map/execute/execute_no_trans；stdio FD/fifo/devpts；必要 proc 属性读取、信号和 groups/capability；确需 Binder 时再审 servicemanager/hwservicemanager/logd 的双向规则。**这些是待审需求，不是已验证可用策略，不添加 allow-all 或盲目 audit2allow。** 非必需模块挂载、任意设备节点/块设备/ioctl 不在首轮支持范围。

### S2：授权表并发/生命周期

ksu_set_app_profile、get/root-profile readers 与 ksu_prune_allowlist 的锁/RCU 使用不一致，返回内部 profile 指针可能与 prune/free 并发。现有 mutex 并不保护全部路径，且 kprobe 上下文不能简单加入可睡眠 mutex。需要统一读写同步、profile 快照及生命周期设计；本轮输入边界补丁**没有修复或验证该问题**。持久化写也非原子，失败/崩溃后授权恢复待测。

### S3：Kprobe、CFI、启动依赖

编译后有 __arm64_sys_execve、execveat、KSU handler 和 __cfi_check 符号，并不证明 register_kprobe 成功。运行时需检查每个注册返回值/tracefs kprobes list、nmissed/异常/CFI 告警。su 与 bootstrap 同时探测 execve；旧代码还在 probe 回调中进行凭据分配/策略操作，存在上下文与睡眠约束风险，需专门审核，不能凭编译通过排除。

目前只装配 execve kprobe，没有 execveat syscall probe。函数名称包含 execveat 不代表 syscall 被覆盖；本内核两个独立 syscall wrapper 都存在。fexecve/AT_EMPTY_PATH/32-bit compat 路径不宣称支持。

### S4：用户态和真实 ROM 缺口

官方普通 su 的 setgroups/setresgid 与保留 app Seccomp 已知冲突，见 KERNELSU-USERLAND.md；不通过禁用过滤器解决。Manager bootstrap 候选仍未执行。没有同一 ROM 的 boot/ramdisk/DTBO/vbmeta/recovery 或完整 target-files，无法确认 init 注入、policy 与 AVB。

## 自动化状态的含义

- test-ksu-runtime-contract.py：保护静态门禁、结构/编号、补丁源码一致性；实际 Manager C++ wrapper 在 host mock prctl 下检查 EINVAL/哨兵；不是 Android syscall。
- verify-ksu-userland.py：对官方下载资产进行真正的 host 密码学校验；不是设备 Manager 身份验证。
- check-ksu-readiness.py：以退出码 2 报告 BLOCKED。test-ksu-stage3.sh 最后一项 PASS 仅表示正确检测到阻断项，**并非总体安全通过**。
- 禁止全局 SELinux 关闭、自动 su permissive、清除 app Seccomp、CFI 弱化、跳过 Manager 验签。后续若不能满足约束，维持不支持。
