<#
.SYNOPSIS
  dex_scan.ps1 — 读取 DEX 头部统计并用明文字符串命中定位关键逻辑。

.DESCRIPTION
  DEX 内部的字符串以长度前缀 + MUTF-8 存放，但类名/URL/资源键等在字节流中
  几乎都是连续可读 ASCII，因此用 Latin-1 整块解码后做子串统计即可得到
  「某功能有没有实现」的高置信度证据（0 命中同样有意义）。
  本脚本不做反编译，只做头部解析 + 关键串命中 + 上下文片段。

.EXAMPLE
  pwsh -File dex_scan.ps1 -Path ..\02_解包\classes.dex,..\02_解包\classes2.dex -Out ..\03_反编译\dex\dex_scan.txt
#>
param(
  [Parameter(Mandatory = $true)][string[]]$Path,
  [string]$Out
)

$ErrorActionPreference = 'Stop'
$enc = [Text.Encoding]::GetEncoding(28591)   # Latin-1，逐字节映射，便于保留偏移

$patterns = @(
  # 故事 DSL 里的"未实现 token"
  'sendemail', 'netcheck', 'textinput', 'canTextInput', 'mAllowFreeFormTextInput',
  # 注入的国产 SDK
  'authsdk', 'AuthSDK', 'heibaige', 'whgame', 'oaid', 'OAID',
  # 归因 / 崩溃上报
  'hastrk3', 'crashlytics', 'Crashlytics',
  # 计费 / 授权
  'BillingClient', 'com/android/vending/licensing', 'ILicensingService', 'LICENSE_CHECK_FAILED',
  # 调试与存档
  'ViewServer', 'sequence-part', 'inboxStyleNotifications', 'inBridgeContent',
  'group_taylor_communications', 'story_taylor_is_waiting_for_you'
)

$report = New-Object System.Collections.Generic.List[string]

function Read-U32([byte[]]$bb, [int]$o) { [BitConverter]::ToUInt32($bb, $o) }

foreach ($p in $Path) {
  $full = (Resolve-Path -LiteralPath $p).Path
  $bytes = [IO.File]::ReadAllBytes($full)
  $name = Split-Path $full -Leaf

  $magicRaw = $enc.GetString($bytes, 0, 8)
  $magic = ($magicRaw -replace "`0", '\0')
  $report.Add("================================================================")
  $report.Add("FILE        : $full")
  $report.Add("SIZE        : {0:N0} bytes" -f $bytes.Length)
  $report.Add("MAGIC       : $magic")
  if ($bytes.Length -ge 112) {
    $ck = Read-U32 $bytes 8
    $fs = Read-U32 $bytes 32
    $hs = Read-U32 $bytes 36
    $sn = Read-U32 $bytes 56
    $so = Read-U32 $bytes 60
    $tn = Read-U32 $bytes 64
    $pn = Read-U32 $bytes 72
    $fn = Read-U32 $bytes 80
    $mn = Read-U32 $bytes 88
    $cn = Read-U32 $bytes 96
    $report.Add(("CHECKSUM    : 0x{0:X8}" -f $ck))
    $report.Add(("FILE_SIZE   : {0}" -f $fs))
    $report.Add(("HEADER_SIZE : {0}" -f $hs))
    $report.Add(("STRINGS     : {0,8}  (off 0x{1:X8})" -f $sn, $so))
    $report.Add(("TYPES       : {0,8}" -f $tn))
    $report.Add(("PROTOS      : {0,8}" -f $pn))
    $report.Add(("FIELDS      : {0,8}" -f $fn))
    $report.Add(("METHODS     : {0,8}" -f $mn))
    $report.Add(("CLASS_DEFS  : {0,8}" -f $cn))
  }

  $s = $enc.GetString($bytes)
  $report.Add("")
  $report.Add("---- 关键字符串命中 ----")
  foreach ($pat in $patterns) {
    $ms = [regex]::Matches($s, [regex]::Escape($pat))
    $n = $ms.Count
    $line = "  {0,-36} {1,5}" -f $pat, $n
    if ($n -gt 0) {
      $ctx = @()
      foreach ($m in ($ms | Select-Object -First 2)) {
        $from = [Math]::Max(0, $m.Index - 48)
        $len = [Math]::Min(120, $s.Length - $from)
        $frag = $s.Substring($from, $len) -replace '[^\x20-\x7E]', '.'
        $ctx += ("@0x{0:X8}: {1}" -f $m.Index, $frag)
      }
      $line += "  | " + ($ctx -join "  ||  ")
    }
    $report.Add($line)
  }
  $report.Add("")
}

$text = ($report -join "`r`n") + "`r`n"
if ($Out) {
  [IO.File]::WriteAllText($Out, $text, [Text.UTF8Encoding]::new($false))
  Write-Output ("OK: {0} ({1} lines)" -f $Out, $report.Count)
} else {
  $text
}
