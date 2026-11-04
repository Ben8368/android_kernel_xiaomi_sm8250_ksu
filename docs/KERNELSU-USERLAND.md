# KernelSU Next v1.1.1 用户态审计（2026-11-04）

## 结论与支持边界

**官方完整用户态配套存在；匹配旧协议的来源已固定且下载验签通过。不是 Android 17 运行兼容通过。**

- 官方仓库：https://github.com/KernelSU-Next/KernelSU-Next
- 官方 tag：v1.1.1；commit：0d6bdc6364cbfc73517dcfdf7ab23b0ba8045553。
- 官方 release：https://github.com/KernelSU-Next/KernelSU-Next/releases/tag/v1.1.1 （2025-09-21）。
- 非 spoofed Manager：KernelSU_Next_v1.1.1_12851-release.apk；包名 com.rifsxd.ksunext；签名内 Manifest versionCode=12851、versionName=v1.1.1、minSdk=26、targetSdk=36。
- APK SHA-256：988dae93c17b5477b8b97952cc5bca6809a386bbbba55940ce45aecc90cacb80。
- 官方源与版本对应关系通过 tag、Release 元数据、Manifest、源码 ABI 和 Cargo.lock 交叉核对；**尚无独立可复现构建/供应链证明表明 release 字节可从该 commit 逐字节复现**。
- 不采用 v3.x/latest Manager，不重签、不修改 APK、不改内核期望证书、不启用 KSU_DEBUG。

完整资产 URL、GitHub asset id、文件大小和哈希在 tools/ksu-userland.lock.json。

| arm64 配套 | SHA-256 |
|---|---|
| APK 内 lib/arm64-v8a/libksud_magic.so | 59e2fdcbc2de760f7d92aaf73adb4c37881b836e21a6866ba019e603dd711e31 |
| APK 内 lib/arm64-v8a/libksud_overlayfs.so | ee2ffc95b569b667dd7abba2f49ee4c5fb906c6652df0ded74af66df17db2d09 |
| 官方 ksud_magic-aarch64-linux-android.zip | aa095727822d1e11b46853a489c9fe52da02c267508b0ca505c7ca46d786fb96 |
| 上述 ZIP 内 aarch64-linux-android/release/ksud | 188a467039e32bac20bc1ceea0b5541c4c5c71afd5f2ddcf2e0d2fedd49fbef9 |
| 官方 ksud_overlayfs-aarch64-linux-android.zip | 702313ff36932f834399ff8d96f45f6dfbebcde33fb47371f3fd015c5cc63065 |
| 上述 ZIP 内 aarch64-linux-android/release/ksud | 6220f7da643f44ea78e67bce7efc3ac5678c8d345c7b3c27773e8b3714c33dca |

APK 内 daemon 和独立 ZIP daemon **不是相同字节**（大小相差 8 字节）；不把它们混用同一哈希，不据此推定差异成因。首次部署只选同一官方 APK 自带组件。magic/overlayfs 是同版本的两种挂载实现，不在本阶段验证模块挂载；不安装 SUSFS/隐藏组件。官方 APK 自身携带其他上游组件不代表本项目启用它们。

## embed_ksud.c 为什么为空

固定 tag 的 kernel/embed_ksud.c 本身是“CI 会重生成”的零长度 stub。对该 tag 整个 kernel 的检索显示，ksud_size 和 ksud 数组没有消费者；仅由 Makefile 链接进内核。kernel/ksud.c 是启动事件/RC 注入驱动，**不是嵌入可执行 daemon 的提取器**。因此填充数组并不能修复用户态安装。

真正来源为 userspace/ksud_magic 和 userspace/ksud_overlayfs；官方 .github/workflows/ksud.yml 编译 Rust，build-manager.yml 把产物放入 APK jniLibs。两者 Cargo.lock 使用官方 KernelSU-Next/rustix 固定 commit 4a53fbc7cb7a07cabe87125cc21dbc27db316259，通信实现在 src/process/prctl.rs（已保存哈希快照）。

实际启动链路：

1. 包管理器安装官方签名 APK，kernel/throne_tracker.c 扫描 /data/app 的 base.apk 并关联 packages.list UID；成功验签后记录 Manager UID。
2. Manager 使用自己 nativeLibraryDir 下 libksud_magic.so 的 debug su 请求 CMD_GRANT_ROOT；不是依赖预先存在的 /system/bin/su。
3. Manager 的 install 调用所选 daemon 的 install --magiskboot，utils.rs::install 将 /proc/self/exe 复制到 /data/adb/ksud 并设置 adb_data_file 标签、准备资产。**这一路径未在设备执行，Manager fallback 到普通 sh 不应误判为成功。**
4. 内核在 init 读取 /system/etc/init/atrace.rc 的旧式 read hook 中附加 RC，安排 /data/adb/ksud post-fs-data、services、boot-completed。首次安装前路径不存在，不能假定启动时 daemon 可用。post-fs-data 事件负责加载持久化授权表；还存在 first app_process 的旧版回退。
5. 普通获授权应用 execve('/system/bin/su') 被改写为 /data/adb/ksud，然后进入 Rust root_shell。

**实际标准 su 必须有可执行 /data/adb/ksud。内核链接成功、空 stub、仅安装 APK 均不等于部署完成。** Manager 的 install 只在以后人工确认的测试中操作；本轮未调用。不要调用上游 uninstall：它还原 Boot 并主动重启，超出本阶段权限。

## Kernel/Manager/ksud 协议

- 传输为 prctl(option=0xDEADBEEF, command, arg3, arg4, arg5)。built-in 配置通过 LSM task_prctl 回调进入 ksu_handle_prctl，非现代 ioctl/reboot ABI。
- 写操作使用 arg5 指向的 u32=0xDEADBEEF 作为成功哨兵；读取版本把 12851 和 flags 写入 arg3/arg4。LSM 回调返回 -ENOSYS 继续 native prctl，最终 syscall 可能返回 EINVAL；上游 wrapper 检查输出而非单看返回码。
- CMD_GRANT_ROOT=0、BECOME_MANAGER=1、GET_VERSION=2；3/4 是保留常量，不是当前授权实现；GET_ALLOW_LIST=5、REPORT_EVENT=7、SET_SEPOLICY=8、GET/SET_APP_PROFILE=10/11、UID 查询=12/13、IS/ENABLE_SU=14/15、GET_MANAGER_UID=16、HOOK_MODE=0xC0DEAD1A。
- app_profile.version=2。host LP64 对照：sizeof(app_profile)=776、sizeof(root_profile)=240，current_uid/allow_su/rp_config 偏移 260/264/272，root capabilities 偏移 144。此为 host 结构布局与源代码契约检查，**不是 Android Binder/arm32/真机传输测试**。
- 版本号仅是构建编号，不是未来版本兼容承诺。v3 Manager 的新 API/结构绝不能仅因名称相同就使用。

## Manager 签名认证

kernel/apk_sign.c 检查 APK v2 signing block 的证书长度与 SHA-256，要求恰好一个 v2 block，拒绝 v1 MANIFEST.MF 和 v3/v3.1；不是任意自签名 APK。默认证书 998 bytes / SHA-256 79e590113c4c4c0c222978e413a5faa801666957b1212a328e46c00c69821bf7。内核不是完整 APK RSA/content verifier：安装完整性依赖 Android PackageManager；本项目不把证书指纹扫描描述为完整密码学验证。

本轮离线工具对真实官方 APK 额外验证了 RSA PKCS#1 SHA-256 签名、APK v2 分块内容摘要、证书、公钥匹配、签名内 Manifest，以及 daemon ELF。官方 lsposed 签名块 signed-data 有 4 个**被签名保护的**零填充字节，工具仅允许空尾或这 4 个零，不跳过签名验证。负向测试覆盖内容篡改、错误证书、截断。

## Android 17 风险（明确区分已知与待验证）

1. **已知：标准应用 su 与保留 app Seccomp 不兼容。** 官方 su.rs::set_identity 无条件调用 set_thread_groups 和 set_thread_res_gid；固定 LineageOS 24.0 bionic 的 APP blocklist 包含 setgroups、setresgid。过滤器在 syscall 入口先于 Root hook 执行、跨 exec/fork 继承；UID=0 并不解除它。可能收到 SIGSYS 或错误，.ok() 不能捕获进程被杀。**把官方 daemon 的普通应用 su 标为不支持，不清除过滤器。**
2. prctl 在已取证的 bionic 基础列表中且不在 APP/COMMON blocklist，源级看可进入；应用可叠加自有 filter，仍能阻止 magic prctl。真实 ROM 生成 BPF/额外 vendor 过滤器未取到，不能承诺可达。
3. Manager 的 debug su 走单独 prctl→exec sh 路径，没有标准 root_shell 的 set_identity，但 libsu/命令/后续安装仍可能触发禁止 syscall；只是候选入口，未验证。
4. mount/umount、改时钟、reboot、chroot、模块装卸等在 app blocklist；其他命令也需按全部 syscall、SELinux、capabilities、namespace 综合检查。不能简单宣称 id 可运行，因为 daemon 在执行 id 前就可能失败。
5. APK targetSdk=36，不是 Android 17 的运行保证；安装限制、包路径/签名格式、旧 atrace.rc read 注入/modern init mmap/open 行为、JNI/linker、启动事件时序都需要目标 ROM 证据。原生程序 PT_LOAD alignment=4096，符合本内核 4 KiB 候选；不宣称能跑 16 KiB 内核。
6. 32-bit compat exec/probe 未覆盖验证；本轮只支持源级分析 arm64 execve。execveat/fexecve 虚拟 su 不支持，不能通过权限绕过补齐。

后续安全方向是：基于固定源码设计不执行冗余身份 syscall 的受限 daemon、显式最小权限策略并完成独立审核；若需要自编 daemon，必须独立锁定来源/工具链/哈希，不能重签 Manager 或伪装为原官方字节。本轮没有交付该新 daemon。
