# Android 逆向工程（reverse）

两个 Android 游戏的静态逆向工程工作区，**纯静态分析，不运行目标 APK**。
所有字节级结论都能用目录内的工具链重新算出来。

> ⚠️ 仅供个人学习与研究。APK 与游戏素材版权归原厂商（3 Minute Games / Big Fish Games / 异次元通讯作者）所有，请勿再分发或商用。

---

## 项目

| 项目 | 包 | 版本 | 体积 | 入口 |
|---|---|---|---|---|
| `生命线-2.3.3\` | `com.threeminutegames.lifeline.google`（Big Fish 发行 / 3 Minute Games 开发） | 2.3.3 (37) | 34 MB | [README](生命线-2.3.3/README.md) ｜ [代码/逻辑报告](生命线-2.3.3/05_报告/生命线_逆向分析报告.md) ｜ [包内容分析](生命线-2.3.3/05_报告/包内容分析.md) |
| `异次元通讯-次元复苏-1.5.4\` | Flutter/Dart 应用 | 1.5.4 | 108 MB | 见该目录 `00_工具\` / `03_反编译\` / `04_资源分析\` |

`原文件\` 是工作区收件区，存放两份原始 APK（与各项目 `01_原始\` 同哈希）。

### 《生命线》看点

- **通知即叙事**：剧情是一条条定时消息，`AlarmManager` + 自定义通知布局；阅读节奏 = `(字数/120)*4` 秒/条，日语 ×3。
- **CN/ES/KO 三语独有 12 段**「Big Fish 营销邮件 + 年龄门槛」流程，但 `<<textinput>>`/`<<netcheck>>`/`<<sendemail>>` 在 `classes.dex` 中**零实现** → 死流程。
- `classes2.dex` 是**未接线**的国产实名/防沉迷 + OAID SDK（`com.wh.authsdk` / `com.one.oaid`，明文 `http://auth-api.heibaige.com/...`），清单未注册、主 dex 零引用。
- 发行层残留：BFG 模板的评分/内购指向不存在的包、`launch_test` 测试段落、调试按钮与 `fast`/`rew` 文案。

### 《异次元通讯》看点

- Flutter 应用：`libapp.so`（Dart AOT）+ `libflutter.so`，剧情在 `assets/flutter_assets/assets/story/*.csv`。
- 产物：`03_反编译\dart_strings_*.txt`、`dex\*.txt`（类/方法/字段/字符串）、`04_资源分析\story_schema.txt` 与 `剧情CSV\`。

---

## 目录约定（两个项目一致）

| 目录 | 内容 | 可重生成 |
|---|---|---|
| `00_工具\` | 解码/统计脚本（生命线为纯 PowerShell；异次元为 Python） | 手写，勿覆盖 |
| `01_原始\` | 原始 APK，字节级不改动，**唯一真源** | ✗ 只读 |
| `02_解包\` | APK 完整解包树 | ✓ |
| `03_反编译\` | 清单、布局、DEX 统计、Dart 字符串等派生结果 | ✓ |
| `04_资源分析\` | 剧本统计、语言矩阵、资源 ID 表、内容清单等 | ✓ |
| `05_报告\` | 中文结论报告 | 手写 |
| `99_临时\` | 一次性输出，不纳入校验 | — |
| `SHA256SUMS.txt` | 全项目文件哈希（生命线项目内） | ✓ |

---

## 复现（生命线项目）

本机环境：Windows PowerShell 5.1（无 `gh`/`apktool`/`jadx` 依赖）。

```powershell
Set-ExecutionPolicy -Scope Process Bypass -Force
cd 生命线-2.3.3
.\00_工具\run_all.ps1          # 10 步：清单/布局/arsc/DEX/剧本/语言矩阵/内容清单
.\00_工具\verify_hashes.ps1    # 613 个文件哈希校验
```

> 所有 `.ps1` 必须存为 **UTF-8 with BOM**：PowerShell 5.1 会把无 BOM 的 UTF-8 当 ANSI 读，中文路径会变成 `02_瑙ｅ寘`。

工具链：`axml2xml`（AXML→XML）、`arsc_ids`（resources.arsc→2096 个 ID）、`decode_layouts` / `annotate_ids`（布局解码 + `@type/name` 标注）、`dex_scan` / `dex_classes`（DEX 头/串/类名）、`story_stats` / `language_matrix` / `content_inventory`（剧本、语言、包内容）。

---

## 免责声明

本项目仅用于安全研究与逆向工程学习：不包含破解、去广告、内购绕过或可运行的修改版；不提供任何规避授权/DRM 的方法。请支持正版。
