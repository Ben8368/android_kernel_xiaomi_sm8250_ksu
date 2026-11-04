# SELinux 权限需求与收紧矩阵

第四阶段源码收紧已完成，**目标 ROM 编译、neverallow、有效标签/域及功能验证仍 BLOCKED**。此补丁是 NO-GO 候选的安全收紧，不是可部署 Root 策略。

真实公开 LineageOS 24.0 `system/sepolicy` 固定为 `d61fd80832f558d52de026097d30d695634e8b0f`。`public/su.te` 定义 su 类型；`private/su.te` 在 userdebug/eng 中声明 `permissive su`，还有 MLS、网络、HAL 属性与 dontaudit。不能从全局 getenforce=Enforcing 推断该域也 enforcing。补丁 0010 显式调用 `ksu_enforce(db, "su")` 清除继承状态；仍须在目标编译后及启动后的策略中检查 su 和所有可选 profile 域。

## 全部通配及 xperm 清单

[机器清单](validation/stage4/selinux-inventory.json) 记录原 rules.c 的所有 allow/allowxperm 调用，包括运行时可变参数 dispatch。bootstrap 有 **25 条含 ALL 的调用，其中 4 条是所有 ioctl xperm**；运行时还有一处通用 allowxperm dispatch，不能与四条静态 xperm 混淆。

| 原规则（分组） | 问题 | 0010 处理 |
|---|---|---|
| ALL → ksu_file，所有 class/perm | 任意主体均可访问该标签 | 删除授权；仅保留类型定义，无 MLS 豁免 |
| su → ALL，所有 class/perm | 近似 allow-all Root | 删除，不通过列举所有类型来伪装最小权限 |
| su → ALL 的 blk_file/fifo_file/chr_file/file，全部 ioctl | 未限制设备及 ioctl 命令 | 四条全部删除，无新增 xperm |
| kernel → adb_data_file dir/file 全权限 | 持久化只需要有限文件操作 | 替换为下表有限权限 |
| kernel → shell_data_file file 全权限 | 可选模块挂载，超出可证需求 | 删除 |
| kernel → packages_list_file file/dir 全权限 | 读取包元数据不需要写权限 | 仅文件 open/read/getattr；删除旧 4.4 dir 兼容项 |
| kernel → system_data_file file/dir 全权限 | 大范围系统数据读写 | 只保留目录 search |
| init → adb_data_file file/dir 全权限 | 安装/启动所需操作尚未在目标 ROM 确认 | 删除，不猜测替代权限 |
| init → su 所有 class/perm | 无边界跨域权限 | 删除 |
| ALL → su process sigchld、fd use、fifo_file write/read/open/getattr | 过宽通信及 FD 访问主体 | 六条删除，等待具体通信矩阵 |
| kernel → ALL file read/write | 任意文件读写 | 两条删除 |
| ALL → su binder 全权限 | 任意 Binder 交互 | 删除 |
| su 的 mlstrustedsubject/netdomain/bluetoothdomain；ksu_file 的 mlstrustedobject | 属性可能隐含大量授权/豁免 | 删除 KernelSU 新增属性；不声称移除了 ROM 已有全部属性 |
| root-only handle_sepolicy 通用接口 | NULL 通配、xperm、permissive、属性操作绕过离线 neverallow 审查 | 返回 EOPNOTSUPP；外层 root/Manager 身份门禁保留 |

此外删除了来源未被本轮需求证明的有限 servicemanager/logd/hwservicemanager/system_server/zygote 通信规则。删除不等于证明所有这些操作永远不需要；恢复每一项之前须有目标标签、具体操作和 neverallow 审查。

## 保留的 22 项有限操作

| 主体 → 对象 : class | 权限 | 可由源码证明的需求 | 限制 |
|---|---|---|---|
| kernel → adb_data_file : dir | open/read/search/write/add_name | allowlist store 路径查找及创建文件；已有目录 | 无 remove_name、目录 create、mount |
| kernel → adb_data_file : file | open/read/write/create/getattr/setattr | allowlist 文件 open/read/write/O_TRUNC | 标签粒度仍覆盖整个 adb_data_file 类型，尚非专属存储标签 |
| kernel → apk_data_file : dir | open/read/search | throne tracker 遍历 `/data/app` | 证书/解析链另有问题，见 Root 审计 |
| kernel → apk_data_file : file | open/read/getattr | APK 验签读文件 | 不授予写或 execute |
| kernel → packages_list_file : file | open/read/getattr | 包列表读取 | 不授予写 |
| kernel → system_data_file : dir | search | 包列表路径父目录查找 | 不允许遍历读取目录内容 |
| kernel → kernel : capability | dac_override | 上游 kernel metadata 路径跨 DAC 读取的既有需求 | 能力本身较广；不宣称绝对最小权限，待目标对象专属化后复审 |

[reviewed-kernel-metadata.te](validation/stage4/reviewed-kernel-metadata.te) 仅是上述规则的可检查导出，并非完整 ROM policy。没有用 audit2allow；没有替换为全部设备/文件类型的枚举。

函数运行在内核中不代表其 SELinux 主体必然是 `kernel`。workqueue 与 rename/LSM 调用方可能具有不同 current credentials；还必须核实每条实际 I/O 的主体和有效对象标签。此表约束的是保留下来的有限授权集合，不证明这些授权足以让所有路径工作。

## 尚缺的 su/ksud 权限

| 能力 | 必须获得的真实材料 | 本轮决定 |
|---|---|---|
| ksud 安装、init 启动和域转换 | 同一 ROM init/ramdisk、文件标签、daemon 操作清单 | 不新增猜测规则，BLOCKED |
| shell exec、动态链接、proc、stdio/PTY | 系统/可执行文件/库/devpts 的有效标签及具体权限 | 没有功能性授权矩阵，BLOCKED |
| groups/caps、信号、服务通信 | 实际命令集合和双向 Binder/FD 主体 | BLOCKED |
| 模块、挂载、块设备/ioctl | 独立能力范围和特权服务架构 | 不在当前实现支持范围；不能称通用 Root |
| profile 自定义 SELinux 域 | 完整目标 policy，确认存在、enforcing 和授权边界 | BLOCKED |

完整目标材料必须包含平台、vendor、product、system_ext、映射/版本、构建 variant 和最终 policy。需要在真实 ROM 构建中加入经过审查的源策略，运行编译与 neverallow 检查，并检验最终二进制。运行时修改 policydb 不会自动执行源策略 neverallow；内核编译通过也不等于 policy 编译通过。

任意 Root shell 与完全最小权限在语义上存在冲突；如果未来接受任意系统管理能力，必须明确它可读写的资产和服务/内核攻击面，不能宣称“完全最小权限”。本轮没有交付这样的能力。
