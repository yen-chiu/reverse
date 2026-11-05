# 生命线 2.3.3 · 改动版工作区

这是《生命线》（Lifeline, `com.threeminutegames.lifeline.google` v2.3.3 / 37）的**可改动副本**，
与只读的逆向分析工程 `..\生命线-2.3.3\` 完全隔离：分析用的证据、报告、校验和都不在这里被改动。

## 目录

```
生命线-2.3.3-改动\
├─ 00_工具\
│   ├─ repack.py       # 按原 APK 条目顺序/压缩方式重新打包（剥离旧签名、对齐 resources.arsc）
│   ├─ build.ps1       # 一键：repack → keytool 建密钥 → apksigner 签名 → verify
│   └─ lifeline-mod.keystore   # 首次构建时自动生成（自签名，仅本地使用）
├─ 01_原始\生命线-2.3.3.apk     # 原件，只读参照
├─ 02_工作区\                   # 532 个解包条目，改这里
├─ 03_产物\                     # 构建出的 APK
├─ README.md
└─ 修改记录.md
```

## 改什么、怎么改

| 想改的内容 | 位置 | 是否可直接改 |
|---|---|---|
| 剧情文本、分支、变量 | `02_工作区\assets\StoryData_cn.txt`（或 `_en/_de/...`） | ✅ 纯文本，UTF-8 |
| 界面文案、按钮、提示 | `02_工作区\assets\strings_cn.xml` 等 | ✅ 纯 XML（自研文案表，不进 arsc） |
| 字体 | `02_工作区\assets\fonts\*` | ✅ 替换同名文件即可 |
| 图片 | `02_工作区\res\*.png` | ✅ 同名同尺寸替换最稳 |
| 布局 / 清单 / arsc | `02_工作区\res\*.xml`、`AndroidManifest.xml`、`resources.arsc` | ❌ 二进制 AXML，需 apktool 反编译后再改 |
| 代码逻辑（dex） | `classes.dex`、`classes2.dex` | ❌ 需 baksmali/smali 或 apktool |

剧本语法速查（引擎解析规则）：`:: 段落名`、`<<set $var = 值>>`、`<<if 条件>>` / `<<elseif>>` / `<<else>>` / `<<endif>>`、
`<<silently>>…<<endsilently>>`、`<<choice [[选项文字|目标段落]]>>`、`[[延迟 30s|目标]]`（`m`=分钟）、`<<category 名字>>`。

**注意**：`StoryData_cn.txt` 每个语言一份，改剧情时只改你要玩的那个语言文件（默认随系统语言）。
`strings_*.xml` 里的 `story_*` 是通知/等待提示，改错会导致通知排版错乱。

## 构建

```powershell
cd C:\03_Github\reverse\生命线-2.3.3-改动
powershell -ExecutionPolicy Bypass -File .\00_工具\build.ps1
```

产物：`03_产物\生命线-2.3.3-mod.apk`（v1+v2+v3 签名，`apksigner verify` 通过）。

工具链（本机已具备）：
- JDK 21 `C:\01_SOFTWARE\12_Tool\Java\jdk-21.0.13+9`
- Android build-tools r34 `C:\03_Github\reverse\_tools\android-14\`（用到 `lib\apksigner.jar`、`zipalign.exe`、`aapt.exe`；`.gitignore` 已排除）
- Python 3.14（PATH 内 `python`）

### 已验证

- 原样重建：529 个游戏条目（原 532 减去 3 个旧签名文件）+ 3 个新签名文件，条目名集合与原件一致；
- `zipalign -c -v 4` → `Verification succesful`（resources.arsc 保持 STORED 且 4 字节对齐）；
- `aapt dump badging` → `com.threeminutegames.lifeline.google` / 37 / 2.3.3；
- `apksigner verify` → v1 / v2 / v3 全部 true；
- 端到端改动测试：改 `strings_cn.xml` 一处文案 → 重新打包 → 签名 → 校验 → 回读 APK 内文本，改动生效。

首版产物（未改内容）：`03_产物\生命线-2.3.3-mod.apk`，12,994,762 B，
SHA-256 `A30024AD422B371B7CC148ED4BE640C9700FE73C6C485893F4C2E9AE46E74CA5`。

## 安装

改动版用的自签名证书与原版不同，**不能覆盖安装**：

1. 卸载手机上已装的《生命线》（会清空存档）；
2. `adb install 03_产物\生命线-2.3.3-mod.apk`，或把 APK 拷到手机点击安装；
3. 若后续想保留存档，可在卸载前用 `adb backup`/第三方工具导出 `shared_prefs`。

本机当前没有 `adb`；需要时把 platform-tools 放进来即可（`_tools\platform-tools\`）。

## 版本号

构建脚本暂不改 `versionCode/versionName`（仍是 37 / 2.3.3，二进制清单，需 apktool 才能改）。
若要与原版并存，必须改包名——那属于 apktool 级别的改动，见 `修改记录.md`。

## 免责

仅用于个人学习与研究。原作版权归 3 Minute Games / Big Fish Games 所有；请勿分发改动版或用于商业用途。
