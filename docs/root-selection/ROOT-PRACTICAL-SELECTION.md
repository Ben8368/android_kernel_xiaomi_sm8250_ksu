# umi 实际使用目标下的 Root 方案重新选型

评估日期：2026-11-04（Asia/Shanghai）。目标由用户给定：Xiaomi Mi 10（umi）、LineageOS 24.0、Android 17、Linux 4.19.325。尚无该设备当前安装包、完整 build fingerprint 或真机证据。

**结论：最推荐的实现方向是官方 Magisk，采用最小功能配置；当前实际部署仍为 BLOCKED。** 这表示优先投入 Magisk 的材料收集与安全验证，不能理解成已经允许安装或刷写。未能排除撤销后继续提权、UID 重用继承权限的风险，因此本轮没有任何候选获得部署 GO。APatch 不作为替代落地方案，现有 KSU 保留研究状态，不继续扩大补丁队列。

本报告依据用户重新定义的安全要求重新决策，替代旧报告在“严格 Seccomp/特权域 Enforcing 要求下的候选排序”；旧报告的事实、历史测试结果和阻断项仍保留。没有修改旧文件或把旧 readiness 改写成 PASS。

**1. 范围与判定规则**

本轮开始的仓库为 `lineage-24.0-ksu`，HEAD `7ed4c8426759601636d108679b6df3e60c1db94f`，git status --short 无输出。旧两份报告评估时的 HEAD 为 45b868c…，不是本轮 HEAD。全部新增研究输出保存在仓库外；没有修改代码、补丁、分支引用、索引、子模块或已有文档，没有构建、制作可刷写镜像、执行 APK/上游安装脚本、安装 APK、连接手机、刷机、提交或推送。

证据级别：S=固定提交源码；A=实际附件字节/发布元数据；H=既有主机测试；T=目标 ROM/设备验证。S/A/H 不能替代 T。本轮对三个方案都没有 T 级功能/安全通过证据。BLOCKED 包含静态可见缺陷和阻止验收的重要未知，不等于宣布已经在该设备复现漏洞。

| 要求 | 本轮解释与验收边界 |
|---|---|
| 普通应用经明确授权使用 Root | 初始默认拒绝，授权主体必须可确定；应用通过官方 su/daemon 执行实际任务。Manager UI 显示已安装、ADB shell id=0、编译通过均不够 |
| 未授权应用不得获 Root/管理权限 | 检查真实调用 UID、Manager 身份、包签名/安装身份变化、共享 UID、多用户、isolated UID、授权撤销、持久化和并发；任何未解决认证问题均阻断 |
| 允许特权例外 | 可接受可信 daemon/Root worker 的广权限、独立 Seccomp 状态或 permissive 域；必须记录范围与必要性。不能据此对所有普通应用全局 permissive、清 filter 或关闭公共内核防护 |
| 减少暴露 | 尽量减少模块、注入和全局修改；“Root 授权拒绝”和“Root 痕迹不可见”分开验收，不承诺全部检测或硬件完整性证明通过 |
| 撤销 | 至少保证明确完成撤销之后的新请求不再获权，并有持久化证据；并发请求需规定线性化点。已有完整 Root 进程及既成修改不能靠删除授权表自动回收 |
| 低维护 | 使用官方发行及原生 LOS 内核，避免自建认证服务、长期内核 Hook 适配或自维护大规模策略 fork |

这里的任意完整 Root 是高信任授权：持有 UID 0、广 capabilities、permissive 域的程序可以改变系统状态，甚至调用以 root 为门禁的管理接口。不能承诺恶意的已授权 Root 程序无法转授能力或修改授权库。如果“应用可完整 Root、同时不能影响其他应用或任何管理状态”也是硬要求，三者均不满足，需要另立受限特权服务项目。本轮按用户明确授权完整 Root 的模型评估，并要求 UI/文档告知这一权限例外；未授权主体直接越权仍是绝对阻断项。[M-IPC][M-SU][M-POLICY]

**2. 选型比较与推荐理由**

| 项目 | 官方 Magisk | APatch / KernelPatch | 现有 KSU 研究方案 |
|---|---|---|---|
| 实际应用 Root 模型 | su 请求交给独立 daemon，授权后 fork worker；适合常见 Root 应用 | 内核先提权再进入 apd/shell；有 Seccomp、SELinux 例外 | Next v1.1.1 加本地兼容与安全补丁；保留 App Seccomp 的 direct-su 仍不满足通用 Root |
| LOS 内核源码维护 | 通常无需本地内核补丁；维护 init/镜像/daemon 兼容 | 通常无源码补丁，但注入和 Hook 内核二进制 | 内核接线、CFI、旧版 KSU、Manager/ksud ABI、多项本地补丁一起维护 |
| 未授权应用影响 | 没有模块/Zygisk 时改动面较少，但仍新增 IPC、policy、挂载和启动组件 | 内核 AVC/CFI/凭据 Hook 扩大公共攻击面；无法仅以“不装模块”消除 | 本地收紧改善局部边界，身份和凭据路径仍阻断 |
| 认证与撤销 | 有默认拒绝、内核 peer credentials 和 Manager 证书检查；缓存和 UID 生命周期仍阻断 | 标签管理命令门禁缺陷、Manager 陈旧 UID、授权持久化及发行归属问题阻断 | Manager/应用 UID 安装身份、撤销持久化、Hook 上下文仍阻断 |
| OTA 成本（定性） | 三者中最低：每版新 ROM 材料、镜像适配、授权/设备回归；保留 Root 路径待验证 | 中等：每个新内核二进制重验符号、偏移、Hook、CFI、启动和授权 | 最高：LOS 合并、安全回移植、补丁重放、完整构建及设备回归 |
| 当前决定 | **第一候选，部署 BLOCKED** | **不选，BLOCKED** | **不选，BLOCKED；不修改现有分支** |

推荐 Magisk 的核心原因是独立用户态执行模型和避免维护本地内核集成。这是基于架构和维护责任的判断，不是“流行所以安全”。新要求允许记录明确的 Root 权限例外后，旧报告因 magisk 域 permissive 而直接否决的理由不再单独成立；认证、撤销、发行来源和普通应用安全边界仍须过关。[M-SU][M-POLICY][P-ROOT-ARCHITECTURE-DECISION][P-APATCH-FEASIBILITY]

建议未来验证基线：官方 release APK、官方原始包名、无模块、Zygisk 关闭、不安装 LSPosed/第三方隐藏或完整性伪造组件、不修改检测程序返回值。优先仅授权可信 owner 用户应用，逐项审查系统 UID、shell 和多用户设置；共享 UID 必须视为整个主体，不能给 UI 中某一包的勾选虚假的包级隔离含义。此配置仍不能关闭下文安全阻断项。

**3. 本轮版本与发布物核对**

2026-11-04 重新读取官方 GitHub releases/latest API，并单独解析 tag commit。不能将 target_commitish 的分支名当构建 SHA。

| 对象 | 发行/固定提交 | 本轮事实 |
|---|---|---|
| Magisk | v31.1；0972f67d97f9b6302b67c5171283330c74114b4a | API 发布时间 2026-10-25；changelog 记 10-24，两者字段不同。master 为 33bfff7ce750c27f157ddb4580e36bf842d6d95b；本轮下载的 master su/daemon.rs 与 v31.1 字节相同 |
| APatch | 11282；e8e4651c16fb5075882a25813c8732285fdb3505 | API 发布时间 2026-10-15；官方 APK 哈希与旧报告相同 |
| KernelPatch | 0.13.9；b51197aaba8f2272dd8a3e30c85698a29aa928c9 | 标签发行日 2026-09-24；当前 kpimg-android / kptools-android 附件创建于 10-10；main 为 d4c88d6672687456b299e4b5153c24dc979d789b |
| 本地 KSU | Next v1.1.1；0d6bdc6364cbfc73517dcfdf7ab23b0ba8045553 + 本仓补丁 | 既有官方用户态锁文件和离线签名证据可保留；不代表目标设备身份生命周期或 Root 已通过 |

Magisk-v31.1.apk 本轮只读下载到仓库外临时目录，大小 10,679,283 bytes，SHA-256 为 `89cefac0a318afa39fb3880c45c87b036c05bc1ebf02a7a715b7f8d7c26ac6e7`，与 API digest 相同。没有安装/执行。该一致性证明下载字节与该发布附件一致，**不等于完成 APK 签名验证、内嵌 daemon TRUSTED_CERT 非空检查、安全 features 的发行二进制绑定或可复现构建**。这些明确保持 BLOCKED，未把未完成验证说成已发现恶意二进制。[A-MAGISK]

APatch 旧报告实测整包 SHA-256 为 d6bf0dbcab95fb9a3aa111c35efd945267bcce3a41377c3297c3c1a9eab421a5；kpimg 为 eb2e3d16fe69410150efcf6f9425baf8cad9ac0c39f051fc8b40ce57c7143adb；kptools 为 63a8656a79b74baadcf0ce57a7e89a8c8a94beb35b25df58aec0bcf1d066bc5b。本轮 API 仍返回相同摘要，未重新做 APatch 整包验证。标签后 09-26 的密钥长度修复 0961c534…、10-04 的管理命令修复 53c43f3c…不能仅凭 10-10 的构建时间字符串判定已在 kpimg 内。**发布二进制对应源码/修复集合无法确定本身就是阻断项。**[KP-KEYFIX][KP-AUTHFIX][P-APATCH-FEASIBILITY]

**4. Manager、UID、撤销与权限边界审查**

| ID | 发现与证据 | 性质/影响 | 解除阻断所需证据 |
|---|---|---|---|
| M-01 | v31.1 的 SuInfo is_fresh 为 3 秒，缓存命中 refresh 时间戳；get_su_info 先用缓存，再查询数据库。Manager 删除 policy 经 magisk --sqlite，SuEvents 只是 App 内 Flow；所查路径无缓存失效联动。master 同文件未变 [M-SU][M-GRANT][M-EVENT][M-POLICY-DAO][M-SQL][M-NATIVE-DB] | **静态可见撤销/过期语义缺陷，BLOCKED**。在同 UID 连续命中、未被其他 UID 替换缓存时，可延长旧 Allow；3 秒不是硬性撤销上限。Manager 命令是否碰巧驱逐缓存依运行状态，不能作为保证 | 官方修复/可信构建归属；撤销 ACK 与授权判定明确同步，持续请求与并发测试、过期授权测试。只等 3 秒、UI 变灰、单次低频成功均不够 |
| M-02 | policy 按 UID/到期时间查；UID_REMOVED 异步删；prune 按已安装 appId 存在性且跨用户收集。未见签名+安装代次的授权绑定 [M-DB][M-RECEIVER][M-MANAGER] | **UID 快速重用/重装/跨用户清理风险未排除，BLOCKED**；未在目标复现无授权 App 提权，不冒充已证实 exploit | 包移除、卸载重装、换签、UID 再分配、共享 UID、多用户删除、Manager 停止/卸载/通知延迟时，旧 grant 必须不可被新主体继承；要代码闭环和回归，不仅一次测试 |
| M-03 | Manager 找 APK、提取 v2 首个证书并对 TRUSTED_CERT；正常发行检查失败返回无 Manager。build.py 未有 keystore 时可生成空 TRUSTED_CERT；check_apk 的证书不匹配拒绝受 release/check-signature 条件影响 [M-MANAGER][M-BUILD][M-FEATURES] | 有认证设计，但**官方附件的完整认证配置尚未独立绑定，BLOCKED**。提取证书不是验证 APK 全内容签名；依赖 Android 安装验证及可信包路径 | 验证官方 APK 签名/可信证书连续性、原生 daemon 绑定同证书且非空、release 模式与三项 features；错误签名、恶意同名包、Manager 缺失/更新/卸载/UID 重用均 fail closed |
| M-04 | daemon 读内核 peer UID/PID、SO_PEERSEC，非 root/zygote 检查客户端 exe；SQLITE_CMD 等要求 UID 0。认证成功 worker 才执行请求 [M-IPC][M-SU] | 不是发现普遍免认证；仍有 PID/FD/namespace 生命周期、解析失败、目标 PID 和客户端身份竞争待验证。**安全验收 BLOCKED** | 原生协议负向测试、请求体 UID 不能冒充 peer、非 Manager/未授权 UID 不能写库、isolated UID/32 位调用等按 ROM 实际支持验证 |
| M-05 | MagiskDB.exec 写操作等待 Shell 结果，但这里未检查退出码；Grant UI 更新后发本地事件 [M-SQL][M-GRANT] | 写库失败却呈现撤销完成的风险待证；不能把 UI ACK 当持久事务，**BLOCKED** | DB I/O/满盘/失败注入，实际数据回读、daemon 与重启后的拒绝状态一致；失败必须明确显示，不恢复旧 Allow |
| A-01 | KP 标签 supercall 在 !is_authed 管理检查前分发 SU_TASK、GRANT/REVOKE、KSTORAGE_WRITE、CONTROL_FEATURE、PANIC 等；普通 allowlisted UID 能进入外层 [KP-AUTH-TAG] | **已知门禁缺陷，标签不可采用**。并非声称任意未授权 App 都能无条件进入；也不声称当前 APK 已证实含缺陷 | 使用包括 53c43f3c… 修复的可归属构建并验证命令矩阵；主线已有前置限制不等于发行归属已证明 |
| A-02 | KP 标签密钥比较未核对完整长度，0961c534… 修复；后续还有指针/密钥处理修复 [KP-KEYFIX][KP-AUTHFIX][P-APATCH-FEASIBILITY] | **已知认证缺陷 + 发布物修复归属未知，BLOCKED**；不夸大为无需知道密钥即可突破 | 精确二进制/构建 SHA 关系与负向密钥验证 |
| A-03 | KP 标签和当前 main refresh 失败直接返回，不清已有 trusted_manager_uid；is_trusted_manager_uid_android 仅比较 UID [KP-MANAGER-TAG][KP-MANAGER-MAIN] | **静态可见陈旧 Manager UID 风险，BLOCKED**，卸载/找不到有效 Manager/读取失败后若 UID 重用可误认证；未做目标利用复现 | 错误路径清除身份、安装身份稳定绑定、并发生命周期审查与目标测试；强 SuperKey 无法替代修复 |
| A-04 | APatch/KP grant 的 UID/profile 与 CSV 缺签名/安装代次闭环；内存/持久状态不同步风险；默认 UID 2000 grant；task_su 直接凭据操作及 rename Hook 扫描上下文风险 [P-APATCH-FEASIBILITY] | **常规 Root 模式也 BLOCKED**。默认 shell 是额外授权主体；不能算所有主体都经过 Manager 单独确认 | 明确 shell 政策、取消不需要的默认权限、身份/持久撤销和内核上下文问题逐项解决，不能仅修 M/SELinux 标准 |
| K-01 | 本地 KSU ABI、Manager UID 缓存与异步 tracker 未闭合包签名/安装代次；保存无原子替换/fsync 事务；exec probe/已发布 cred 修改上下文待审 [P-ROOT-SECURITY] | **BLOCKED**；RCU 修复、主机测试和编译通过不能消除此风险 | 独立身份/撤销/凭据修复与目标回归；成本不符合本次避免长期内核补丁目标 |

M-01 的源码推导例子：t=0 授权请求缓存 Allow；随后 DB 删除成功；若同 UID 新请求不断在前次命中后不足 3 秒到达，它们续期旧缓存，不重新查 DB。其他 UID 请求可能替换单项缓存，但攻击者不能受“期待其他请求发生”约束。示例是代码路径推演，不是执行了手机攻击测试。M-02 则是证据缺口与时序风险，不将“没有签名字段”单独等同于已经发现任意提权。

另外两类默认信任必须登记：Magisk 对已经是 UID 0 的调用者直接允许，对经认证的 Manager 在授权判定中静默允许；不是每一次管理动作都弹窗。daemon 还允许 ADB shell 请求删除模块（请求可以包含重启选项），属于恢复管理例外，不等于 shell 默认获得 su。未来测试应以受信任的 ADB 配对/物理访问为前提，确认普通 App 不能伪装 shell；APatch 默认 shell Root grant 与此并不相同。[M-SU][M-IPC][P-APATCH-FEASIBILITY]

对已授权完整 Root 的例外必须直说：Magisk 的管理 SQL 接口只检查 root，所以已获完整 Root 的 worker 可以达到管理能力；不是只有 Manager UI 才能更改权限。APatch 还区分 SuperKey/Manager 与普通 grant，因此 A-01 违反其命令层门禁，不能用“都是 Root”掩盖。两者都无法承诺把恶意完整 Root 当作普通隔离应用。[M-IPC][KP-AUTH-TAG][KP-AUTH-MAIN]

**5. 安全机制与痕迹的实际变化**

| 层次 | Magisk 候选的变化及接受条件 | APatch / KSU 对照 |
|---|---|---|
| Seccomp | App 的 su 客户端不直接清自身 filter，Root worker 来自 daemon；二者可以有不同过滤状态。需测原 App、拒绝 App、worker 的真实 syscall 行为，不能仅看 Seccomp 数值 | APatch 会对特定任务关闭 Seccomp；新要求不因此单独否决，但必须限定已授权主体及其必要后代。现有 KSU 没放开此边界，通用 Root 问题仍在 |
| SELinux | magisk 域 permissive、广 allow/caps/ioctl 是明确的特权例外；全局应保持 Enforcing，普通域不可变 permissive。攻击面还含对 magisk 文件、socket、Binder、FD 的跨域访问 [M-POLICY] | APatch 有 AVC 拒绝/审计豁免及 ap_policy；仅 getenforce=Enforcing 不证明相关任务受强制约束 |
| 普通应用/公共域 | **官方规则无条件加入 zygote→zygote execmem、system_server→system_server execmem 等。关闭 Zygisk 也不去掉这些 policy 语句。** 需用目标原策略计算实际新增权限、追踪继承及拒绝测试；不能说“未授权应用完全不变” [M-POLICY] | KP CFI 豁免按目标地址区域判定，属于公共内核防护变化，不能完全包装成单个 Root 任务例外 [KP-CFI] |
| CFI/内核 | Magisk 不需要 KSU 式内核源码集成；boot_patch.sh 仍包含平台 kernel hexpatch 分支。只有目标原始/候选 kernel 比较才能确认 umi 实际改动；不预先承诺 kernel 字节不变 [M-PATCH] | APatch 对 KP text/hook/KPM 区域豁免 CFI。现有 KSU 仅有编译级 CFI 证据，仍无运行证明 |
| 启动与验证链 | 增加 init/ramdisk/daemon 和数据目录；修改启动分区意味着不能继续声称与原 ROM 有相同完整性保证。禁止把属性/检测输出伪造成验收结果 | APatch 修改 kernel、init 行为；KSU 修改内核。同样存在修改启动信任链的事实 |
| 暴露与隐藏 | 官方 v31.1 已删除 Manager 隐藏/重打包；默认包可见性受 Android 规则限制，仍可能被允许查询的 App、文件/挂载/进程行为检测发现 [M-CHANGES] | 内核 Root 也不等于不可检测；APatch 策略查询隐藏不能作为安全功能通过证据 |

**P-01：Magisk 对公共域的额外 policy 权限、对未授权应用的影响尚未用目标策略验证，保持 BLOCKED。** 它不是全局关闭 SELinux，但也不只是新增一个 Root 域。若验证发现无关应用安全机制被关闭或产生无法合理限定的新增访问，官方基线不可采用。若必须长期自维护策略 fork 才满足要求，则重新选型为继续无 Root，不偷偷扩大项目范围。

减少痕迹的优先顺序：先无模块、关闭 Zygisk，避免对其他应用注入；确有需求时另评估官方 DenyList 的挂载清理。v31.1 源码有无 Zygisk 的 logcat 路径，不能武断说 DenyList 必须开 Zygisk；但 Android 17 上该路径的覆盖、进程启动竞争和重启行为仍未验证。[M-DENY] DenyList 不是 Root 授权表，也不是抗检测/硬件证明保证；被列入 DenyList 不代表其 su 权限已撤销，反之亦然。不引入伪造完整性证明、改检测返回值或全局安全状态显示的验收方法。

**6. 目标兼容性的证据与未知**

| 对象 | 已有证据 | 尚不能声称的结论 |
|---|---|---|
| umi Boot 格式 | 固定 LineageOS device/common 配置指向非 VAB 候选：header v2、4096 页、独立 DTB section、boot/recovery 各 128 MiB、dtbo 32 MiB。公共配置同时有 VAB 条件分支 [LOS-UMI][LOS-COMMON][P-BOOT-FORMAT] | 不能仅凭该配置断定用户 ROM 的实际槽位、header、ramdisk、AVB 或所有镜像布局 |
| Android 17 | Magisk v31.0 changelog 明确提到 Zygisk Android 17/API 37 支持；v31.1 是后续稳定版本 [M-CHANGES] | 这是组件支持声明，不是 umi/LOS 24.0/4.19.325 普通 Root、策略、OTA 全链通过 |
| Linux 4.19.325 | Magisk daemon 模型不需要本设备 GKI LKM；旧源码已有 namespace 等接口兼容路径。APatch 有旧 ARM64 内核路径；现有 KSU 有本树编译/链接证据 [P-ROOT-ARCHITECTURE-DECISION][P-APATCH-FEASIBILITY] | 同内核版本号不等于同 config/编译器/CFI/backport/二进制。不能用其他 4.19 设备替代 |
| 历史 APatch Mi 10 记录 | 旧报告引用 KernelPatch #151 的 umi/4.19.318/LOS21 故障记录、PR #326 作者的 Mi10/4.19.157 无 kCFI 局部测试 [P-APATCH-FEASIBILITY] | 仅沿用旧报告，不把 PR 自报或其他版本案例升级成当前目标通过证据 |
| 真机整体 | 目前无本目标 root/revoke/boot/硬件日志 | 三者的正常启动、解锁、加密、32 位兼容（若 ROM 支持）、相机、蜂窝/Wi-Fi/蓝牙、USB 数据、PD/PPS、温控、待机、恢复和 OTA 均未知 |

首选待核验目标是**同一次 ROM 的原始 boot.img**，因为已取证非 VAB 配置存在 boot ramdisk；仍须实际检查后决定。不要仅因 Android 17 就索要 init_boot.img 或选择 GKI 通用镜像；只有精确 ROM 真实存在 init_boot/vendor_boot 等分区时才加入输入。Magisk 官方文档还区分 boot ramdisk 与 recovery 安装方式，最终按实际镜像和设备布局确定。[M-INSTALL][P-BOOT-FORMAT]

**7. 必须取得的精确 ROM 文件与身份信息**

当前缺完整构建标识，不能编造 lineage-24.0-某日期-umi.zip 文件名，也不能用“最新 umi ROM”替代。至少收集当前已装版本，以及首次 OTA 演练的下一个目标版本两套独立材料：

| 输入 | 精确要求/用途 |
|---|---|
| 完整 ROM 安装包 | 与设备已安装 fingerprint/build ID/增量号匹配的 umi LOS24.0 完整安装 ZIP、发行页面/维护者来源、大小、SHA-256、可验证签名/公钥关系。若是非官方或自编译，记录真实构建者与签名链，不冒充 LOS 官方 |
| 原始启动/恢复镜像 | 同次构建 boot.img、recovery.img、dtbo.img、vbmeta.img；实际存在的 vbmeta_system/vbmeta_vendor 及其他链条成员；实际存在才要求 vendor_boot/init_boot。镜像均保持原字节，用于解析和恢复，不能混用 MIUI/其他日期/其他机型 |
| target-files ZIP（优先向 ROM 构建者获取） | IMAGES/ 下实际镜像，META/misc_info.txt、ab_partitions.txt（若存在）、dynamic_partitions_info.txt（若存在）、文件/分区映射、OTA keys；SYSTEM/VENDOR/PRODUCT/SYSTEM_EXT 的 build.prop、fstab/rc、策略材料。普通 OTA ZIP 不一定具备这些内容 |
| 完整 SELinux 策略 | 同次平台/vendor/product/system_ext/odm 的 CIL、mapping、contexts 与 precompiled policy（若有），以及运行时真实加载策略或足以重建它的输入。不能只拿内核 security/selinux 源码替代 |
| 构建与内核溯源 | repo manifest（全部 revisions）、device/common/kernel/vendor 修订、实际 .config、编译器版本、原始 Image/DTB 与哈希、内核 release、SPL；用于核实 CFI/Seccomp/AVB 与内核字节关系 |
| OTA 内容 | META-INF/com/android/metadata；若有 payload.bin/payload_properties.txt 或 update_engine 配置则一并保存；若为其他 OTA 格式保存对应更新脚本及 addon.d/backuptool。用于识别 full/incremental、源/目标版本、槽位和更新顺序 |
| 固件/恢复资料 | 精确匹配的 Xiaomi 固件要求、对应可信固件包和恢复说明；备份用户数据、加密/恢复可达性。设备唯一校准/身份数据不公开，不拿其他设备分区替换 |
| 后续人工只读设备清单 | fingerprint、build ID/incremental、SPL、uname/config（可读取时）、ro.boot.slot_suffix、实际分区名称和大小、bootloader 状态、ROM 用户 ABI、recovery 与数据解密能力；本轮未连接设备获取 |

如果 target-files 不公开，可以先通过完整 ROM 和只读提取做部分检查；缺 policy/manifest/布局的门禁继续 BLOCKED，不假设 OTA ZIP 自动等价 target-files。不要要求用户提供任何私有签名密钥、设备密钥或账号口令。

**8. OTA 之后的实际维护成本**

成本结论为相对判断，不承诺分钟数。三者都不能把旧版 patched boot 直接重刷到新版 ROM。

| 工作 | Magisk（推荐路线） | APatch | 现有 KSU |
|---|---|---|---|
| LOS 每次更新 | 保存新包/哈希/原始镜像与布局；核查 Magisk兼容变更；重新核验镜像差异、策略、身份和恢复资料 | 除左侧工作还需重验符号、指令/结构偏移、Hook、CFI/AVC 及 kpimg 构建归属 | 同步 LOS，重放补丁、编译整个内核/设备 DT、检查 ABI/CFI/接线，再做所有回归 |
| Root 保留 | 目标流程尚未验证；最保守基线是先接受 OTA 后无 Root，再按新版原始材料恢复 Root | 官方保留 Root 流程不能据旧文档当作本设备已稳定 | 通常需为每个新内核重新集成/构建与打包 |
| 安全修复 | 跟踪官方 release、认证代码及发布物；如果只有本地 fork 能解决，成本优势下降 | 同时跟踪 APatch、KernelPatch、policy 依赖与二进制附件 | 跟踪 LOS 内核及过时 KSU/ksud/Manager，已存在补丁债务 |
| 失效处理 | Root 丢失可接受；系统和恢复保持可用优先 | 二进制 Hook 失配可表现为启动/运行时故障 | 合并/编译问题外，还可能有设备运行回归 |

Magisk 的 ota.md 主要描述 A/B，注明精确流程只在 Pixel 验证；addon.d.sh 另有 A-only/backuptool 路径。不能从这两点推出 umi 已支持自动保留 Root，也不能把“非 VAB”直接当作所有分区都无 A/B。精确槽位、recovery 能否访问 /data、backuptool 和恢复脚本时序都要核实。[M-OTA][M-ADDON]

后续 OTA 推荐策略：首次先把“原生 ROM 更新与正常启动”作为独立成功条件；Root 自动保留只在两版 ROM 的完整演练通过后考虑。若已安装 addon.d 保留脚本，必须核实并控制其实际行为，不能在它仍会自动修改新 boot 时宣称“先更新为纯净系统”。每次更新保存 before/after 的原始镜像与授权状态，复测默认拒绝、批准、新会话撤销、重启持久化和未授权应用边界；更新 Magisk 版本时重新核验认证与附件，不沿用旧结果。

**9. 分阶段验证和失败恢复**

下列是后续计划，不是本轮执行结果；现有用户授权仅限研究和文档。任何实际安装、构建可刷镜像、刷写或设备测试都不在本轮执行范围。

| 阶段 | 工作及必须产出的证据 | 通过条件/停止点 |
|---|---|---|
| P0 已执行：只读研究 | 阅读历史报告、固定 29 份官方源码快照、官方 release/tag 元数据、Magisk 附件下载哈希、记录阻断项 | 文档交付完成；部署仍 BLOCKED。没有把代码推导写成真机 PASS |
| P1 离线材料与发行核验 | 获取第7节精确 ROM；核对签名/来源与版本；只读解析 boot/AVB/ramdisk/DT/槽位/容量；验证官方 APK 内容签名与 daemon 证书/构建 features、源码映射 | 缺任一关键身份或镜像材料则停止，输出缺失清单。现有 inspect-umi-boot.py 只支持既定 v2 门禁且不证明 AVB 签名正确，不能把 parser PASS 当可刷 |
| P2 安全阻断闭环 | M-01～05、P-01；候选若改换 APatch/KSU，同样关闭相应 A/K 项。使用真实认证/授权实现做失败注入、状态机与并发检查，验证精确发布件包含修复 | 未授权身份风险、撤销/持久化、公共策略、发行归属任一未闭环，保持 BLOCKED，不进入日用设备试刷 |
| P3 后续另行授权的隔离验证 | 首选模拟环境/测试设备验证 Manager、IPC、UID 生命周期；需要新版本修复时只选可归属构建。未来产生候选镜像前先确认恢复路径、分区和原始材料；不把当前研究输出当镜像生成授权 | 隔离验证成功只能支持目标设备测试准备，不替代 umi 验证；认证失败立即停止，不靠放宽检查补齐 |
| P4 后续人工目标设备最小测试 | 无模块/无 Zygisk 基线；先验证原生启动与恢复，再测授权边界；记录 UID/PID、包签名、上下文、真实返回码、Seccomp/策略、日志及输入哈希 | 默认拒绝、明确预授权后实际任务成功、撤销与重启后拒绝、未授权应用防护均通过；既有完整 Root 会话单独记录和清理 |
| P5 人工实际工作与 OTA/恢复演练 | 真实所需 Root 应用逐项授权，验证命令/权限；USB、PD/PPS、热控、网络/相机/睡眠等；当前→下一版 OTA；模拟 Root 丢失/启动失败的恢复演练 | 能正常完成目标工作，恢复可信原生状态；不以 Root 检测“全绿”验收。通过仅适用于这套 ROM/Root 版本组合 |
| P6 发布/日用决定 | 汇总所有安全、产物、硬件、OTA 证据与例外；列出版本/哈希、明确授权清单与恢复材料 | 只有相关 BLOCKED 全部解除才讨论 GO；测试一次通过不等于证明永无漏洞 |

人工测试必须覆盖以下独立用例，每项保存原始记录、预期和实测结果：

- **默认拒绝**：未授权 A、B 应用均不能 su；不能改授权库、设置、模块、启动脚本或冒充 Manager。常规 su 客户端与直接协议请求都测，拒绝不能只靠没有 su 命令。
- **明确授权**：v31.1 是 Superuser 页事前授权，已删除旧式请求时弹窗；A 未授权前应拒绝，授权后新会话执行真实只读任务，B 保持拒绝。[M-CHANGES][M-GRANT]
- **撤销与到期**：持续请求/并发、短连接/长连接、Manager 已有 Root shell/新建 shell、App 重启、daemon 重启、设备重启、I/O 失败及掉电恢复；验证撤销完成后的所有新请求拒绝。已有 worker/后代及其修改单列，不把“老会话仍在”混同“新请求继续获权”。
- **身份生命周期**：卸载被授权 App、复装同包、合法签名升级/签名轮换、不同签名重新安装、其他包获得复用 UID；Manager 卸载/更新失败/错误证书/缓存失效；共享 UID、次用户、工作资料与 isolated UID（ROM 支持时）。每次核对实际 UID，不只看包名。
- **安全边界**：全局 Enforcing、真实 permissive map、App/worker 域、AVC 和实际受限 syscall/跨应用访问的负向探针；比较原生与候选有效策略。只读观察 getenforce 或 /proc/status 数字不构成完整通过。
- **实际任务**：先 id/context/受控目录只读，再按真实 Root 应用需求验证必要的写入或挂载；有明确授权范围、回滚材料和后果记录。首先不做任意分区写入、危险 ioctl 或系统安全机制关闭。
- **痕迹/完整性**：记录第三方检测的真实结果与可见文件/挂载行为，允许“检测到 Root/完整性不通过”；不改属性伪造锁定状态，不修改检测返回值，不把隐藏测试替代权限测试。

失败恢复应在未来任何设备改动前准备并可执行：

| 失败 | 人工恢复原则 | 禁止的推断或动作 |
|---|---|---|
| 镜像/签名/布局不明 | 停止，保留原设备状态并补齐材料 | 不用同机型其他日期镜像拼接，不尝试通用 GKI 镜像 |
| Root 不工作但正常启动 | 停止后续模块/策略变更；恢复与当前系统匹配的原始启动组件，或按已验证卸载路径回到原生状态 | 不清 Seccomp/关全局 SELinux 作为快捷修复 |
| bootloop/无法解锁数据 | 使用已确认可达的 bootloader/recovery，恢复**当前已安装系统版本**匹配的原始受影响镜像；必要时按发行者流程重装匹配完整 ROM | 不保证 fastboot boot 可用；不盲切槽、不混刷旧 boot、不随意改 vbmeta/重锁 bootloader |
| OTA 后失败 | 先判定新系统实际落盘/活动槽与版本；有验证过的兼容槽位和 rollback 条件才回退；否则恢复新系统对应原始组件 | 旧 boot 备份不自动适配新版 system/vendor；增量 OTA 失败不意味着旧分区都还在 |
| 出现未经授权提权/疑似完整 Root 失控 | 隔离敏感用途，保存必要证据；回到可信原生系统并重新建立授权状态。必要时按恢复方案清理持久数据/完整重装，恢复前保全用户数据 | 不能认为删 grant、重启或只恢复 boot 一定能清除已获得完整 Root 的持久修改；不能带回未经审查的授权 DB/模块备份 |
| 恢复工具不可达 | 停止进一步写入，使用设备/ROM 有文档支持的恢复或维修流程 | 不承诺可用 EDL 授权、数据必不丢失或任意降级 |

**10. 当前可执行决定**

维持无 Root 的原生 LineageOS 作为当前实际使用状态；下一步只收集精确 ROM/策略/恢复材料及等待或核验官方 Magisk 的安全闭环证据。推荐方向已经从旧严格标准下的“所有路线不选”改为“官方 Magisk 第一候选”，但**任何候选的部署状态仍为 BLOCKED**。不以自行关闭认证、删除负向测试、把 Root 检测改为通过，或把已知问题降级为普通待办来得到 GO。

优先阻断顺序：M-01 撤销缓存、M-02/M-03 身份与发行认证、M-05 失败 ACK/持久化、M-04 IPC 生命周期、P-01 普通应用安全边界、精确 ROM 与恢复、目标实测/OTA。APatch 的 A-01～04 与归属问题不因 Magisk 被阻断就自动豁免；KSU 原门禁继续有效。

**证据索引与复核方式**

本目录 evidence/sources.lock.json 保存固定仓库、完整 SHA、源码路径、本地快照路径及 SHA-256；evidence/prior.lock.json 保存历史报告快照哈希；evidence/retrieval-log.json 保存官方 API 请求、取回时间和结果。API latest 只是本轮发现入口，复核以落盘元数据与固定 commit 为准。外部网页搜索工具本轮未返回可用内容，因此改用官方 GitHub API 和固定 raw 源码直接取证；有限 issue 搜索没有提供可关闭上述风险的修复证据，不能据无匹配结果声称不存在漏洞。

以下源码引用均为官方一手来源；本地历史报告引用则明确标注为沿用证据。未对任何项目做全量审计或穷尽漏洞检索。

- [M-SU] topjohnwu/Magisk @ 0972f67d97f9b6302b67c5171283330c74114b4a，native/src/core/su/daemon.rs；[本轮快照](evidence/sources/M-SU.rs.txt)。
- [M-DB] topjohnwu/Magisk @ 0972f67d97f9b6302b67c5171283330c74114b4a，native/src/core/su/db.rs；[本轮快照](evidence/sources/M-DB.rs.txt)。
- [M-IPC] topjohnwu/Magisk @ 0972f67d97f9b6302b67c5171283330c74114b4a，native/src/core/daemon.rs；[本轮快照](evidence/sources/M-IPC.rs.txt)。
- [M-MANAGER] topjohnwu/Magisk @ 0972f67d97f9b6302b67c5171283330c74114b4a，native/src/core/package.rs；[本轮快照](evidence/sources/M-MANAGER.rs.txt)。
- [M-POLICY] topjohnwu/Magisk @ 0972f67d97f9b6302b67c5171283330c74114b4a，native/src/sepolicy/rules.rs；[本轮快照](evidence/sources/M-POLICY.rs.txt)。
- [M-FEATURES] topjohnwu/Magisk @ 0972f67d97f9b6302b67c5171283330c74114b4a，native/src/core/Cargo.toml；[本轮快照](evidence/sources/M-FEATURES.toml.txt)。
- [M-RECEIVER] topjohnwu/Magisk @ 0972f67d97f9b6302b67c5171283330c74114b4a，app/core/src/main/java/com/topjohnwu/magisk/core/Receiver.kt；[本轮快照](evidence/sources/M-RECEIVER.kt.txt)。
- [M-GRANT] topjohnwu/Magisk @ 0972f67d97f9b6302b67c5171283330c74114b4a，app/apk/src/main/java/com/topjohnwu/magisk/ui/superuser/SuperuserGrantViewModel.kt；[本轮快照](evidence/sources/M-GRANT.kt.txt)。
- [M-EVENT] topjohnwu/Magisk @ 0972f67d97f9b6302b67c5171283330c74114b4a，app/core/src/main/java/com/topjohnwu/magisk/core/su/SuEvents.kt；[本轮快照](evidence/sources/M-EVENT.kt.txt)。
- [M-CHANGES] topjohnwu/Magisk @ 0972f67d97f9b6302b67c5171283330c74114b4a，docs/changes.md；[本轮快照](evidence/sources/M-CHANGES.md.txt)。
- [M-INSTALL] topjohnwu/Magisk @ 0972f67d97f9b6302b67c5171283330c74114b4a，docs/install.md；[本轮快照](evidence/sources/M-INSTALL.md.txt)。
- [M-OTA] topjohnwu/Magisk @ 0972f67d97f9b6302b67c5171283330c74114b4a，docs/ota.md；[本轮快照](evidence/sources/M-OTA.md.txt)。
- [M-ADDON] topjohnwu/Magisk @ 0972f67d97f9b6302b67c5171283330c74114b4a，scripts/addon.d.sh；[本轮快照](evidence/sources/M-ADDON.sh.txt)。
- [M-PATCH] topjohnwu/Magisk @ 0972f67d97f9b6302b67c5171283330c74114b4a，scripts/boot_patch.sh；[本轮快照](evidence/sources/M-PATCH.sh.txt)。
- [M-BUILD] topjohnwu/Magisk @ 0972f67d97f9b6302b67c5171283330c74114b4a，build.py；[本轮快照](evidence/sources/M-BUILD.py.txt)。
- [M-MASTER-SU] topjohnwu/Magisk @ 33bfff7ce750c27f157ddb4580e36bf842d6d95b，native/src/core/su/daemon.rs；[本轮快照](evidence/sources/M-MASTER-SU.rs.txt)。
- [KP-AUTH-TAG] bmax121/KernelPatch @ b51197aaba8f2272dd8a3e30c85698a29aa928c9，kernel/patch/common/supercall.c；[本轮快照](evidence/sources/KP-AUTH-TAG.c.txt)。
- [KP-AUTH-MAIN] bmax121/KernelPatch @ d4c88d6672687456b299e4b5153c24dc979d789b，kernel/patch/common/supercall.c；[本轮快照](evidence/sources/KP-AUTH-MAIN.c.txt)。
- [KP-MANAGER-TAG] bmax121/KernelPatch @ b51197aaba8f2272dd8a3e30c85698a29aa928c9，kernel/patch/android/userd.c；[本轮快照](evidence/sources/KP-MANAGER-TAG.c.txt)。
- [KP-MANAGER-MAIN] bmax121/KernelPatch @ d4c88d6672687456b299e4b5153c24dc979d789b，kernel/patch/android/userd.c；[本轮快照](evidence/sources/KP-MANAGER-MAIN.c.txt)。
- [KP-CFI] bmax121/KernelPatch @ b51197aaba8f2272dd8a3e30c85698a29aa928c9，kernel/patch/common/secpass.c；[本轮快照](evidence/sources/KP-CFI.c.txt)。
- [LOS-UMI] LineageOS/android_device_xiaomi_umi @ 8e115b1ed63caa3ee5c3d52df0a7bce7c27512cd，BoardConfig.mk；[本轮快照](evidence/sources/LOS-UMI.mk.txt)。
- [LOS-COMMON] LineageOS/android_device_xiaomi_sm8250-common @ b84fe80a52e7407c53119d2dd6507285da8090d4，BoardConfigCommon.mk；[本轮快照](evidence/sources/LOS-COMMON.mk.txt)。
- [M-POLICY-DAO] topjohnwu/Magisk @ 0972f67d97f9b6302b67c5171283330c74114b4a，app/core/src/main/java/com/topjohnwu/magisk/core/data/magiskdb/PolicyDao.kt；[本轮快照](evidence/sources/M-POLICY-DAO.kt.txt)。
- [M-SQL] topjohnwu/Magisk @ 0972f67d97f9b6302b67c5171283330c74114b4a，app/core/src/main/java/com/topjohnwu/magisk/core/data/magiskdb/MagiskDB.kt；[本轮快照](evidence/sources/M-SQL.kt.txt)。
- [M-NATIVE-DB] topjohnwu/Magisk @ 0972f67d97f9b6302b67c5171283330c74114b4a，native/src/core/db.rs；[本轮快照](evidence/sources/M-NATIVE-DB.rs.txt)。
- [M-DENY] topjohnwu/Magisk @ 0972f67d97f9b6302b67c5171283330c74114b4a，native/src/core/deny/utils.cpp；[本轮快照](evidence/sources/M-DENY.cpp.txt)。
- [KP-KEYFIX] bmax121/KernelPatch @ 0961c53457c7ad6c47924fbe87e7f93abb999de0，kernel/base/predata.c；[本轮快照](evidence/sources/KP-KEYFIX.c.txt)。
- [KP-AUTHFIX] bmax121/KernelPatch @ 53c43f3ce650e94a46523f7ad17b30ce2bf0e3c9，kernel/patch/common/supercall.c；[本轮快照](evidence/sources/KP-AUTHFIX.c.txt)。
- [P-ROOT-ARCHITECTURE-DECISION] docs/ROOT-ARCHITECTURE-DECISION.md；[既有证据快照](evidence/prior/docs__ROOT-ARCHITECTURE-DECISION.md)。
- [P-APATCH-FEASIBILITY] docs/APATCH-FEASIBILITY.md；[既有证据快照](evidence/prior/docs__APATCH-FEASIBILITY.md)。
- [P-ROOT-SECURITY] docs/ROOT-SECURITY.md；[既有证据快照](evidence/prior/docs__ROOT-SECURITY.md)。
- [P-BOOT-FORMAT] docs/BOOT-FORMAT.md；[既有证据快照](evidence/prior/docs__BOOT-FORMAT.md)。
- [P-SECCOMP-FEASIBILITY] docs/SECCOMP-FEASIBILITY.md；[既有证据快照](evidence/prior/docs__SECCOMP-FEASIBILITY.md)。
- [P-SELINUX-MATRIX] docs/SELINUX-MATRIX.md；[既有证据快照](evidence/prior/docs__SELINUX-MATRIX.md)。
- [P-DEVICE-TEST-PLAN] docs/DEVICE-TEST-PLAN.md；[既有证据快照](evidence/prior/docs__DEVICE-TEST-PLAN.md)。
- [P-MAINTENANCE] docs/MAINTENANCE.md；[既有证据快照](evidence/prior/docs__MAINTENANCE.md)。
- [P-readiness-result] docs/validation/stage4/readiness-result.json；[既有证据快照](evidence/prior/docs__validation__stage4__readiness-result.json)。
- [P-sources.lock] docs/validation/stage3/sources.lock.json；[既有证据快照](evidence/prior/docs__validation__stage3__sources.lock.json)。
- [P-ksu-userland.lock] tools/ksu-userland.lock.json；[既有证据快照](evidence/prior/tools__ksu-userland.lock.json)。
- [A-MAGISK] [Magisk 附件取证记录](evidence/magisk-artifact.json)、[发行元数据](evidence/magisk-release.json)。
- [A-APATCH] [APatch 发行元数据](evidence/apatch-release.json)、[KernelPatch 发行元数据](evidence/kernelpatch-release.json)。
