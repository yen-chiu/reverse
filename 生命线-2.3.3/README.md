# 生命线 (Lifeline) 2.3.3 — 逆向工程工作区

《生命线》Android 版（Big Fish Games 发行 / 3 Minute Games 开发）的静态逆向工程目录。
目标包：`com.threeminutegames.lifeline.google` v2.3.3 (versionCode 37)。

> 结论见 **`05_报告\生命线_逆向分析报告.md`**（16 节，含 34 条 REA Evidence ID 与复现步骤）。
> 包内容（res/assets/内嵌 Wear/语言矩阵）见 **`05_报告\包内容分析.md`**。
> 本 README 只负责「文件在哪、怎么重建、什么不能动」。

---

## 1. 目录约定

目录编号沿用同工作区 `异次元通讯-次元复苏-1.5.4\` 的既有约定，两个逆向工程结构一致、可互相参照。

| 目录 | 内容 | 是否可重生成 |
|---|---|---|
| `00_工具\` | 纯 PowerShell 工具链（无 apktool/jadx 依赖），见 §3 | 手写，勿覆盖 |
| `01_原始\` | 原始 APK，字节级不改动。**唯一真源** | ✗ 只读 |
| `02_解包\` | APK 完整解包树（532 个条目：dex、assets、res、META-INF、Manifest、arsc） | ✓ 可重解包 |
| `03_反编译\` | 派生：`清单\`（AXML→XML，含主清单/内嵌 Wear 清单/附属 xml）、`dex\`（dex 头部、关键串命中、类名/包名直方图）、`布局\`（19 个解码布局 + `标注\` 版） | ✓ `run_all.ps1` |
| `04_资源分析\` | 派生：`剧本统计.md/.json`、`字符串表_cn.md`、`语言矩阵.md`、`资源ID表.txt`、`包内容清单.md/.csv` | ✓ `run_all.ps1` |
| `05_报告\` | 交付报告 | 手写 |
| `99_临时\` | 草稿/一次性输出，**不纳入校验**、可随时清空 | — |
| `SHA256SUMS.txt` | 全项目文件哈希（排除自身与 99_临时） | ✓ `make_checksums.ps1` |

**规则**

1. `01_原始\` 只读：任何「改包/重签/试运行」都在 `99_临时\` 里做副本。
2. `02_解包\`、`03_反编译\`、`04_资源分析\` 都是可再生产物；要改结论就改工具再重跑，不要手改生成物。
3. 新增分析产物：数据类进 `04_资源分析\`，代码级（smali/反编译源码）进 `03_反编译\`，结论进 `05_报告\`。
4. 一次性脚本、试验性 dump 进 `99_临时\`；确认有价值后再提升到 `00_工具\` 或 `03_反编译\`。
5. 任何「字节一致」的声明都必须能由 `verify_hashes.ps1` 复算。

---

## 2. 包指纹

| 项 | 值 |
|---|---|
| 原始文件 | `01_原始\生命线-2.3.3.apk`（原名 `reverse\生命线.apk.1`，改名不改字节） |
| 大小 | 12,830,339 字节 |
| SHA-256 | `5607F43796ABC4709FE16B4E1C60FAEB6EBC843DD9DED637977DFBBC03A37824` |
| 结构 | 532 条目 / 无 native `.so` / `classes.dex` 8,119,568 + `classes2.dex` 140,652 |
| DEX 规模 | classes.dex：class_defs 6,919 / methods 57,486 / strings 53,400；classes2.dex：171 / 1,150 / 1,489 |
| 签名 | v1+v2+v3，同一证书 SHA-256 `37803c47397861e81ba0447b486a2bdf3e61202c01f178509f88c59b9b98237b`，无 rotation / 无 source stamp（未做密码学校验） |
| 共享收件区副本 | `..\原文件\生命线.apk`（同一 SHA-256，属于工作区级收件区，本目录不管理它） |

---

## 3. 工具链（`00_工具\`）

| 脚本 | 作用 | 备注 |
|---|---|---|
| `run_all.ps1` | 一键重建 `03_反编译` + `04_资源分析` | 幂等；只读 `02_解包` |
| `axml2xml.ps1` | AXML（Android 二进制 XML）→ 可读 XML | 处理字符串池 UTF-8/UTF-16、typedValue、空元素自闭合；**以 typedValue 为准**（部分打包器把 rawValue 写成 0 而不是 0xFFFFFFFF） |
| `dex_scan.ps1` | DEX 头部字段 + 24 个关键串命中 + 上下文片段 | Latin-1 整块扫描；用于证明「某功能有没有代码」 |
| `story_stats.ps1` | 剧本结构统计：段落/重名/token/choice 目标/悬空引用/变量 Top25/语言差分 | 输出 JSON + Markdown |
| `strings_table.ps1` | `assets/strings_<lang>.xml` → Markdown 对照表 | 该表是游戏自研文案表，不进 `resources.arsc` |
| `decode_layouts.ps1` | 批量解码自有 `res/layout*` → `03_反编译\布局\` | 只挑游戏用到的 9 种屏 |
| `annotate_ids.ps1` | 把 XML 里的 `@0x7Fxxxxxx` 换成 `@type/name` | 依赖 `资源ID表.txt`；输出到 `标注\` |
| `arsc_ids.ps1` | `resources.arsc` → `资源ID表.txt`（2096 个 ID） | 极简解析：类型块 headerSize / uint32 边界 / UTF-8+UTF-16 字符串池 |
| `dex_classes.ps1` | DEX `class_defs` 解析 → 类名清单 + 包名直方图 | 不依赖 baksmali/jadx |
| `language_matrix.ps1` | 9 个剧本 + 8 个文案表 → `语言矩阵.md` | 段落/choice/变量/文案键差分 |
| `content_inventory.ps1` | res/assets/raw/drawable/META-INF/Wear 条目清点 → `包内容清单.md/.csv` | 顺带解出内嵌 Wear 清单 |
| `make_checksums.ps1` | 生成 `SHA256SUMS.txt` | 排除自身与 `99_临时` |
| `verify_hashes.ps1` | 按 `SHA256SUMS.txt` 复算校验 | 退出码非 0 表示不一致 |

**运行环境**：Windows PowerShell 5.1 或 PowerShell 7；脚本均存为 **UTF-8 with BOM**（5.1 才能正确读中文注释）。
若执行策略受限，用 `powershell -ExecutionPolicy Bypass -File <脚本>` 或先在当前进程 `Set-ExecutionPolicy -Scope Process Bypass`。

```powershell
# 在新机器上从零重建
Set-ExecutionPolicy -Scope Process Bypass -Force
.\00_工具\run_all.ps1                  # 生成清单 XML / dex 扫描 / 剧本统计 / 文案表
.\00_工具\make_checksums.ps1 -Root .   # 重算全量哈希
.\00_工具\verify_hashes.ps1 -Root .    # 自检
```

---

## 4. 关键数据速查（详见报告）

- **剧本**：`StoryData_cn.txt` 832 段落（830 唯一）/ 684 个 `<<choice>>` / 154 个 `<<if>>` / 146 个 `<<set>>` / 65 组 `<<silently>>`；1,072 个 choice 目标、761 唯一、**0 悬空**。`StoryData_en.txt` 820 段落 / 685 choice。
- **语言差分**：**CN/ES/KO 独有 12 段**（其余 6 种语言没有），全部属于「Big Fish 营销邮件收集 + 年龄门槛」流程（`legalese`→`confirm_legal`→`age_verify`→`enter_email`→…→`send_email`→`email_successful`）；该流程依赖 `<<textinput>>`/`<<netcheck>>`/`<<sendemail>>` 三个 token，而这三个 token 在 `classes.dex` 中命中数为 **0** → 死流程。
- **注入 SDK**：`classes2.dex` 全是 `com.wh.authsdk`（实名/防沉迷）、`com.one.oaid`（设备标识）、`com.whgame.sdk`；清单无注册、主 dex 零引用 → 未接线的死代码，但随包分发，含明文 `http://auth-api.heibaige.com/apicenter/...`。
- **存档**：Gson 序列化的消息队列 → TinyDB `sequence-part1A/2A/3A`；Wear 数据层 `/playerData` + asset `sequence-asset`；无加密无校验。
- **通知节奏**：`(字数/120)*4` 秒/条，日语 ×3，快进 1 秒/条；章节悬念后追加 3600/86400/172800 秒三条催回提醒。

---

## 5. 已知未解（待后续）

1. `SplashActivity.onCreate` 里的 `t.r(this)`：目标类 `t` 在两个 dex 中都不存在（`Lt;` 0 命中），需 smali 级核对。
2. `StoryData` 的 11 个 `mRegex*` 字段赋值点未定位（无 `<clinit>`、无 setup 方法）。
3. `ViewServer` 是否监听本地 socket（本地攻击面）未展开。
4. `SplashTheme`/`AppTheme` 的 style bag 未展开（启动图是否由 `windowBackground` 提供仍是推断）；`res/` 479 个资源已完成审计，见 `05_报告\包内容分析.md`。
5. CN/ES/KO 邮件流程在 `parseWayPoint` 默认分支下的实际表现未逐行确认。
6. 证书主体（DN）未提取；签名真实性未做密码学校验。
7. 与官方渠道包（Play）的二进制 diff 未做——无法判定 `classes2.dex` 是发行方注入还是二次分发方注入。
8. `checkForHungState` 的循环内重置是死代码（已确认逻辑，但未做运行时验证）。

---

## 6. 相关

- 报告：`05_报告\生命线_逆向分析报告.md`
- 同工作区姊妹项目：`..\异次元通讯-次元复苏-1.5.4\`（Flutter/Dart + CSV 剧情，目录约定一致）
- REA 证据：报告 §15 的 34 条 `ev_...` 可直接用 `inspect_analysis_view` / `get_evidence_bundle` 取回
