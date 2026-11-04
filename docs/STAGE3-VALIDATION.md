# 第三阶段离线验证记录

日期：2026-11-04。工作分支 lineage-24.0-ksu；起始 HEAD 1528d4d5178cc308ba5226e3d72d83a408eeba55。PR #1 保持 Draft，默认 lineage-24.0 不变。

## 可执行入口

WSL Ubuntu 24.04 / Python 3、gcc/g++、python3-cryptography：

```bash
python3 tools/fetch-ksu-userland.py --out /absolute/path/to/assets
KSU_ASSETS=/absolute/path/to/assets bash tools/test-ksu-stage3.sh
# 阻断项报告：退出码 2 是明确 BLOCKED，不是就绪。
python3 tools/check-ksu-readiness.py
```

测试执行日志已保存在 docs/validation/stage3/；实际结果以日志为准。host mock/ASan/fixture 不应描述为设备 Root。

## 干净 checkout 和 -dirty

父仓库源码必须已提交，KSU gitlink 仍指向官方 0d6bdc…，不创建无法访问的子模块提交。tools/prepare-ksu.py 在临时干净 archive 预演完整队列，仅接受官方未修改源码或完整最终源码；不重置/覆盖未知修改。

ksu_audit.py 对**每个** KSU kernel 文件比较官方基线加队列的结果，同时拒绝未解释的子模块 tracked/untracked 修改。补丁间重叠会使逐 patch reverse-check 不可靠；因此 prepare 改用完整树证明，保证重复调用。

应用已审补丁会使父仓库 git describe/setlocalversion 出现 -dirty，这是事实且保留；不设置 LOCALVERSION 假装干净。构建 provenance.json 同时记录 expected_patch_dirty=true 和 unexplained_dirty=false；若父仓库有未提交源码，构建失败。队列摘要定义为按文件名排序逐个 SHA-256 更新 filename UTF-8 + NUL + patch 原始字节；锁定每个 patch 自己的哈希，避免“同名补丁但内容不同”。

每次构建从新输出目录开始（拒绝已有 vmlinux），保存 source-before.json，编译后重新证明源码未变、验证 linked vmlinux/CFI/security config，再生成 provenance.json，包含：

- LineageOS 上游 SHA 6b34d24765327d746074c8e53b5ad0d24a51acc7。
- 实际构建定制分支 SHA/parent tree，KSU 官方基础 SHA。
- 队列摘要/各 patch 和所有有效 KSU 源码 hash。
- Clang 实际版本和 clang-real SHA-256、工具链锁文件 hash。
- .config、vmlinux 和最终 Image SHA-256、带真实 -dirty 的 kernel.release。

验证最终 vmlinux 中 kernelsu_init、ksu_handle_prctl、ksu_task_prctl、escape_to_root、ksu_set_app_profile、ksu_handle_execve_sucompat、ksu_ksud_init、native execve/execveat 和 __cfi_check，检查 AArch64 ELF/未解析强符号和实际编译 CFI flags。**符号存在不能证明 hook 注册成功或目标设备可用。**

干净重建命令（示例路径由操作者替换）：

```bash
git clone --branch lineage-24.0-ksu https://github.com/Ben8368/android_kernel_xiaomi_sm8250_ksu.git clean-kernel
cd clean-kernel
git submodule update --init --recursive
CLANG_DIR=/absolute/path/to/clang-r596125 OUT_DIR=/absolute/path/to/new-output JOBS=8 bash tools/build-umi.sh
```

不承诺跨主机 byte-for-byte 可复现（绝对路径/宿主构建工具也可能影响）；本轮目标是证明干净提交、完整补丁与最终字节可追踪。第二阶段 build-final 的历史证据不得冒充补丁 0008 的新构建结果。

## 状态边界

| 验收类别 | 判定方式 |
|---|---|
| 编译验证 | 第三阶段干净 checkout 完整 Image/modules/dtbs/ThinLTO/CFI/最终链接通过，exit 0；见 build-console.log/provenance.json |
| 用户态协议 | 固定 tag 的常量、LP64 ABI 与真实 Manager wrapper 的 host mock；官方资产密码学校验；不含设备调用 |
| 静态安全回归 | 身份门禁、Seccomp/CFI/Enforcing 不回退、边界测试；不等于整体安全通过 |
| 安全审计 | BLOCKED：wildcard SELinux、allowlist 并发、官方 su 与 app Seccomp 冲突 |
| 真机启动 | 未验证 |
| 真机 Root | 未验证；官方普通 su 在保持目标 app Seccomp 下不支持 |
| 测试 Boot | 仅合成格式 fixture 通过，无适配真实目标 ROM 的镜像 |

用户态详情见 KERNELSU-USERLAND.md，Root 风险见 ROOT-SECURITY.md，Boot 输入门禁见 BOOT-FORMAT.md，未来人工流程见 DEVICE-TEST-PLAN.md。

## 本轮实际执行结果

- 构建 commit：bd877bc5bed63a2a182b43e320cd2a606850ce81。WSL 中从 Git 对象库重新 clone（不复制已修改 working tree），子模块另行 checkout 官方 SHA，初始 git status 为空；完整队列首次应用及重复调用均成功。
- 构建时间：2026-11-04 04:31:25–04:39:35 UTC（上海 12:31:25–12:39:35）；exit=0。不是 Android ROM 构建。
- 实际 release：4.19.325-cip136-st20-perf-gbd877bc5bed6-dirty。记录证明 expected_patch_dirty=true、unexplained_dirty=false；没有抹去 -dirty。
- Clang：Android r596125 / 22.0.2；Image SHA-256：3deece0ccb0754151b0ff44b1aa949f6293f94e24295d6f7ca5851fd871fbbba。
- vmlinux SHA-256：4a5366b43146ea020c33c868df0360d5e0dd7fe31889d07e3aa1bc1cda3bb382；0 未解析强符号，3 个 DTB / 12 个 DTBO / 3 个模块。
- 队列 SHA-256：19a3ea41b2fd7e20a025a57564cdfaf5e080cebf94a5ef6397a239431ae89c1e。
- 最终离线 suite 在 f99a8405eb0e89ec200630c02ec2e945c00452cc 执行，exit=0，80 条 PASS 输出；其中含“正确报告 BLOCKED”，不应解读为 80 项真机功能通过。边界 harness 内实际覆盖 201 种列表长度，ASan/UBSan 通过。
- 输入污染负向测试：未解释 tracked 修改、extra kernel 文件、staged 子模块修改、未提交父仓库源码均被拒绝，全部只在临时 clone 中执行。
- APK 资产：Release hash、v2 RSA 签名/内容摘要/证书/Manifest 通过，4 个 arm64 daemon ELF 检查通过；内容篡改/错误证书/截断均拒绝。
- Boot：独立官方 mkbootimg 的合成 header-v2 fixture 通过，8 种坏输入拒绝；真实 ROM 镜像未提供，未构建真实测试 Boot。
- 编译参数后验检查：真实 apk_sign.o 命令仍使用官方证书 998 bytes/锁定指纹，同时有 ThinLTO/CFI 参数，实际 linked KSU 权限路径符号存在；见 build-contract.json 和 ksu-compile-commands.txt。

构建后 f99a8405e 只改了额外测试、只读 Boot inspector 的说明/错误文本与 Boot 文档；最终记录提交只增证据/文档及独立的编译产物审计工具。build-input-delta.txt 证明内核、补丁队列及构建输入与 bd877bc5b 没有差异。**provenance 中保留真正构建 SHA，不把后来的文档 HEAD 冒充已构建。**

完整产物保留于 WSL /home/xiaoluo/umi-ksu-stage3/build-clean；官方资产在 /home/xiaoluo/umi-ksu-stage3/assets；干净重建源码在 /home/xiaoluo/umi-ksu-stage3/clean-checkout。用户维护分支工作区为 /home/xiaoluo/umi-ksu-work-20261104。Windows C:\android_kernel_xiaomi_sm8250_ksu 原本为无效 HEAD/未完成 checkout，现恢复成文档/工具 sparse checkout；内核树有 Windows 保留文件名和大小写冲突，**不要在 Windows sparse 目录编译，完整验证使用 WSL 原生目录**。

追加核验入口：

```bash
python3 tools/verify-ksu-build-contract.py --out /home/xiaoluo/umi-ksu-stage3/build-clean
```
