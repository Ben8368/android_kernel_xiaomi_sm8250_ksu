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

测试执行日志将保存在 docs/validation/stage3/；实际结果以日志为准。host mock/ASan/fixture 不应描述为设备 Root。

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
| 编译验证 | 历史第二阶段通过；第三阶段新补丁需单独新构建并保存 provenance |
| 用户态协议 | 固定 tag 的常量、LP64 ABI 与真实 Manager wrapper 的 host mock；官方资产密码学校验；不含设备调用 |
| 静态安全回归 | 身份门禁、Seccomp/CFI/Enforcing 不回退、边界测试；不等于整体安全通过 |
| 安全审计 | BLOCKED：wildcard SELinux、allowlist 并发、官方 su 与 app Seccomp 冲突 |
| 真机启动 | 未验证 |
| 真机 Root | 未验证；官方普通 su 在保持目标 app Seccomp 下不支持 |
| 测试 Boot | 仅合成格式 fixture 通过，无适配真实目标 ROM 的镜像 |

用户态详情见 KERNELSU-USERLAND.md，Root 风险见 ROOT-SECURITY.md，Boot 输入门禁见 BOOT-FORMAT.md，未来人工流程见 DEVICE-TEST-PLAN.md。
