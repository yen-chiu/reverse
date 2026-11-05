<#
.SYNOPSIS
  run_all.ps1 — 从 02_解包 重新生成全部派生产物（清单/布局/arsc/DEX 统计/剧本/语言矩阵/内容清单）。

.DESCRIPTION
  可重复执行：不触碰 01_原始，只覆盖 03_反编译 与 04_资源分析 下的生成物。
  依赖 00_工具 下的兄弟脚本，全部为纯 PowerShell（无 apktool / jadx / baksmali 依赖）。
  顺序有依赖：arsc_ids → annotate_ids（标注要用 ID 表）；其余相互独立。

.EXAMPLE
  pwsh -ExecutionPolicy Bypass -File run_all.ps1
#>
param(
  [string]$Root = (Split-Path $PSScriptRoot -Parent)
)

$ErrorActionPreference = 'Stop'
$tools = $PSScriptRoot
$unpack = Join-Path $Root '02_解包'
$dec = Join-Path $Root '03_反编译'
$res = Join-Path $Root '04_资源分析'

if (-not (Test-Path -LiteralPath $unpack)) { throw "缺少 $unpack（先解包 APK）" }
New-Item -ItemType Directory -Force -Path (Join-Path $dec '清单'), (Join-Path $dec 'dex'), (Join-Path $dec '布局'), $res | Out-Null

Write-Host '== 1/10 二进制 XML -> 可读 XML =='
& (Join-Path $tools 'axml2xml.ps1') -Path (Join-Path $unpack 'AndroidManifest.xml') -Out (Join-Path $dec '清单\AndroidManifest.xml')
foreach ($x in (Get-ChildItem (Join-Path $unpack 'res\xml') -File -Filter *.xml)) {
  & (Join-Path $tools 'axml2xml.ps1') -Path $x.FullName -Out (Join-Path $dec ('清单\' + $x.Name))
}

Write-Host '== 2/10 布局解码（游戏自有 9 种屏）=='
& (Join-Path $tools 'decode_layouts.ps1') -Root $Root

Write-Host '== 3/10 resources.arsc -> 资源 ID 表 =='
& (Join-Path $tools 'arsc_ids.ps1') -Root $Root

Write-Host '== 4/10 布局/清单标注（@0x7F.. -> @type/name）=='
& (Join-Path $tools 'annotate_ids.ps1') -Root $Root

Write-Host '== 5/10 DEX 头部 + 关键串命中 =='
& (Join-Path $tools 'dex_scan.ps1') -Path @((Join-Path $unpack 'classes.dex'), (Join-Path $unpack 'classes2.dex')) -Out (Join-Path $dec 'dex\dex_scan.txt')

Write-Host '== 6/10 DEX 类名清单 + 包名直方图 =='
& (Join-Path $tools 'dex_classes.ps1') -Path @((Join-Path $unpack 'classes.dex'), (Join-Path $unpack 'classes2.dex')) -OutDir (Join-Path $dec 'dex')

Write-Host '== 7/10 剧本统计（cn / en / 差分）=='
& (Join-Path $tools 'story_stats.ps1') `
  -Path @((Join-Path $unpack 'assets\StoryData_cn.txt'), (Join-Path $unpack 'assets\StoryData_en.txt')) `
  -OutJson (Join-Path $res '剧本统计.json') `
  -OutMd (Join-Path $res '剧本统计.md') `
  -Compare (Join-Path $unpack 'assets\StoryData_en.txt')

Write-Host '== 8/10 文案表（cn，对照 en）=='
& (Join-Path $tools 'strings_table.ps1') -Path (Join-Path $unpack 'assets\strings_cn.xml') `
  -Out (Join-Path $res '字符串表_cn.md') -Compare (Join-Path $unpack 'assets\strings_en.xml')

Write-Host '== 9/10 语言矩阵（9 剧本 + 8 文案表）=='
& (Join-Path $tools 'language_matrix.ps1') -Root $Root

Write-Host '== 10/10 包内容清单（res/assets/raw/Wear/dex）=='
& (Join-Path $tools 'content_inventory.ps1') -Root $Root

Write-Host ''
Write-Host '全部派生分析已生成。产物：'
$outs = @(
  (Join-Path $dec '清单'),
  (Join-Path $dec '布局'),
  (Join-Path $dec 'dex\dex_scan.txt'),
  (Join-Path $dec 'dex\classes_classes.txt'),
  (Join-Path $dec 'dex\classes2_classes.txt'),
  (Join-Path $res '资源ID表.txt'),
  (Join-Path $res '剧本统计.json'),
  (Join-Path $res '剧本统计.md'),
  (Join-Path $res '字符串表_cn.md'),
  (Join-Path $res '语言矩阵.md'),
  (Join-Path $res '包内容清单.md'),
  (Join-Path $res '包内容清单.csv')
)
foreach ($o in $outs) { Write-Host ("  {0}" -f $o) }
