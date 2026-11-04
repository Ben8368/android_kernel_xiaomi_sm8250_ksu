# Xiaomi Mi 10 umi 人工测试计划（未执行）

**当前门禁：BLOCKED，不具备进入刷机/人工真机 Root 验证的条件。** 本文件是未来人工计划；本轮没有连接手机、刷写、重启、安装 APK、修改分区或改变设备授权。

## 进入测试前必须满足

1. 解决 ROOT-SECURITY.md 中 SELinux wildcard 授权、allowlist 同步/生命周期以及官方普通 su 的 Seccomp 冲突；无法安全兼容的功能维持不支持。完成非设备验证和独立审查。
2. 取得精确 LineageOS 24.0 umi ROM 的官方来源/发行哈希、构建 fingerprint/日期/安全补丁级别、repo manifest（含 kernel/device/vendor revision）、同次 boot/dtbo/vbmeta/recovery/target-files。核对运行 ROM 与所有 payload 一致，不仅“都是 24.0”。
3. 通过 BOOT-FORMAT.md 真实镜像门禁、离线打包往返、AVB/分区/ramdisk/hash 校验，保存最终测试镜像清单和命令记录。
4. 用户**另行明确确认实际刷机操作**。在此之前任何脚本均不得自动调用刷写/重启；确认不能由本轮请求代替。
5. 准备该设备/ROM 的原始 Boot、原始 DTBO、vbmeta 和 Recovery 的只读备份及 SHA-256；重要用户数据外部备份，验证可以读取恢复；确认电量、数据线、USB 驱动、bootloader 状态和可用恢复环境。准备与该机固件/ROM 一致的官方恢复包，不把其他 ROM 文件充当恢复手段。
6. 人工确认实体按键可进入 bootloader/recovery、电脑可识别设备、存在不依赖本次 Root 的恢复路径。未验证则停止。先保存原配置和基准日志，避免首次失败时才寻找原始镜像。

## 分阶段验收表

每一步记录 PASS / FAIL / 未验证、时间、操作者、ROM fingerprint、内核 commit/patch hash、Image/Boot/DTBO/APK/daemon SHA-256 和日志位置。失败立即停止升级下一阶段，不运行修复安全机制的快捷命令。

| 项目 | 操作与证据 | 通过要求 | 当前状态 |
|---|---|---|---|
| 原始系统基准 | 记录 boot、recovery、SELinux、Seccomp、功能状态和充电曲线 | 原 ROM 所有目标功能正常，恢复手段可用 | 未验证 |
| 正常启动 | 人工执行另行确认的最小测试，记录启动动画、解锁、uptime、dmesg/logcat/pstore | 可稳定启动，无 panic/CFI/SELinux 启动循环 | 未验证 |
| Kprobe | 检查 su/bootstrap execve、read、input 等注册返回值与可读的 tracefs 记录 | 注册成功，无错误/异常 missed 或上下文告警 | 未验证 |
| Manager | 安装固定官方非 spoofed APK；确认 package/version/cert/hash 与锁文件；记录 UI 截图与 UID | 检测 built-in KernelSU 12851/Kprobes；认证失败必须拒绝 | 未验证 |
| Bootstrap | 仅在前置安全修复后人工测试 Manager debug su/install | 有日志证明成功 uid/context/退出码、daemon path/mode/label/hash 正确，无 fallback sh 假成功 | 未验证 |
| Root 请求/授权 | 干净普通测试 UID 初始拒绝；在 Manager 明确授权；新会话执行受限 id/上下文只读命令 | 授权前拒绝，授权后仅允许已审能力，不意外给予其他 UID Root | 未验证（官方普通 su 当前不支持） |
| 撤销 | 结束原 Root 会话，取消授权，再创建新会话；重启后的持久化另行确认 | 新 Root 请求被拒；不误称已存在 Root 凭据被收回 | 未验证 |
| 负向身份 | 普通 app 直接 prctl、非 Manager 改 profile、isolated UID、重装/UID 复用、多用户 | 无越权；错误签名 APK 只做隔离离线/专门受控测试，不替换有效认证 | 未验证 |
| Seccomp | 对比 app→候选 root shell 的 /proc/self/status Seccomp/Seccomp_filters/NoNewPrivs，结合受控 syscall 探针 | 过滤器不减少；预期禁止 syscall 失败，不用清除过滤器修复 | 未验证 |
| SELinux | getenforce、进程 context、su 域 policy permissive map、AVC 与明确策略对照 | 全局 Enforcing，su 不 permissive；无 wildcard 掩盖缺失权限 | 未验证 |
| USB PD/PPS | 同一充电器/线缆、相近电量/温度、原 ROM 对照；记录电压/电流/温度/协商与插拔 | PD/PPS、温控与充电稳定，无异常发热/掉充 | 未验证 |
| Wi-Fi | 2.4/5GHz、休眠唤醒、漫游/热点按原 ROM 能力对比 | 连接稳定、吞吐与待机正常 | 未验证 |
| 指纹 | 解锁/录入/重启首次解锁后恢复 | 功能与原 ROM 一致 | 未验证 |
| 触摸 | 多点/边缘、亮灭屏、充电中操作 | 无失灵/鬼触 | 未验证 |
| 音频 | 扬声器/麦克风/听筒/通话/蓝牙与 USB 音频按原支持范围测试 | 无路由或录放音回归 | 未验证 |
| Recovery | 在有恢复条件且另行确认重启后人工进入 Recovery | 可进入、可使用必要恢复功能 | 未验证 |

Root 功能测试不执行系统写入、reboot、模块加载、任意 mount 或硬件设备 ioctl 作为第一步。execveat/fexecve、32-bit compat、模块 unmount/namespace profile 属于未支持/未验证，不以切换 permissive 或清除 Seccomp 补齐。

## 失败后的恢复流程

- 停止重复启动/追加刷写，记录现象、时间、Boot 哈希和最后操作；能读取时收集 pstore/ramoops、recovery 日志。不要在失败机上临时启用安全绕过。
- 由操作者使用已经验证的实体按键路径进入 bootloader 或独立 Recovery；恢复**该机同 ROM 的原始 Boot**。如果另行批准过其他分区改动，严格按事前清单恢复原始对应镜像；本轮工具不执行这些操作。
- 原始 Recovery 也不能进入或设备无法识别时，停止，转向事先验证的官方恢复手段/人工维修流程；不猜分区、不擦除 userdata、不改 vbmeta、不尝试重新锁定 bootloader。
- 恢复原 ROM 正常启动后再次核对重要数据、原始安全状态、充电/网络等功能。失败日志保留为审计证据，不能把恢复后成功当新内核通过。

## 状态字段定义

“编译验证通过”“用户态协议验证通过（注明静态/host）”“静态安全回归检查通过”“安全审计通过”“真机启动验证通过”“真机 Root 验证通过”分别独立记录。当前前两类只存在离线/历史构建证据；安全审计仍有阻断项，真机两项均未验证。
