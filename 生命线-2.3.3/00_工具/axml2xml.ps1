<#
.SYNOPSIS
  axml2xml.ps1 — 把 Android 二进制 XML (AXML) 解码成可读 XML。

.DESCRIPTION
  纯 PowerShell 实现，不依赖 apktool/aapt。处理字符串池(UTF-8/UTF-16)、
  START_ELEMENT / END_ELEMENT / CDATA 三类 chunk，并把 android 命名空间
  属性写成 android:xxx 前缀。用于还原 AndroidManifest.xml 与 res/xml/*.xml。

.EXAMPLE
  pwsh -File axml2xml.ps1 -Path ..\02_解包\AndroidManifest.xml -Out ..\03_反编译\清单\AndroidManifest.xml
#>
param(
  [Parameter(Mandatory = $true)][string]$Path,
  [string]$Out
)

$ErrorActionPreference = 'Stop'
if (-not (Test-Path -LiteralPath $Path)) { throw "文件不存在: $Path" }
$b = [IO.File]::ReadAllBytes((Resolve-Path -LiteralPath $Path))

function Get-U16([int]$o) { [BitConverter]::ToUInt16($b, $o) }
function Get-U32([int]$o) { [BitConverter]::ToUInt32($b, $o) }

$type = Get-U16 0
if ($type -ne 0x0003) { throw ("不是 AXML (RES_XML_TYPE): type=0x{0:X4} file={1}" -f $type, $Path) }

# ---------- 字符串池 ----------
$poolOff = Get-U16 2
if ((Get-U16 $poolOff) -ne 0x0001) { throw ("字符串池缺失 @0x{0:X}" -f $poolOff) }
$strCount = Get-U32 ($poolOff + 8)
$strFlags = Get-U32 ($poolOff + 16)
$strStart = Get-U32 ($poolOff + 20)
$strBase = $poolOff + $strStart
$isUtf8 = ($strFlags -band 0x100) -ne 0

$strOffsets = New-Object 'uint32[]' $strCount
for ($i = 0; $i -lt $strCount; $i++) { $strOffsets[$i] = Get-U32 ($poolOff + 28 + 4 * $i) }

function Read-Str([long]$idx) {
  if ($idx -lt 0 -or $idx -ge $strCount) { return $null }
  $p = [int]($strBase + $strOffsets[$idx])
  if ($isUtf8) {
    $n1 = $b[$p]; $p++
    if ($n1 -band 0x80) { $len = (($n1 -band 0x7F) -shl 8) -bor $b[$p]; $p++ } else { $len = $n1 }
    $n2 = $b[$p]; $p++
    if ($n2 -band 0x80) { $blen = (($n2 -band 0x7F) -shl 8) -bor $b[$p]; $p++ } else { $blen = $n2 }
    return [Text.Encoding]::UTF8.GetString($b, $p, $blen)
  }
  $len = [BitConverter]::ToUInt16($b, $p); $p += 2
  return [Text.Encoding]::Unicode.GetString($b, $p, $len * 2)
}

function Esc([string]$s) {
  if ($null -eq $s) { return '' }
  return $s.Replace('&', '&amp;').Replace('<', '&lt;').Replace('>', '&gt;').Replace('"', '&quot;')
}

function Fmt-Value([int]$dataType, [uint32]$data) {
  switch ($dataType) {
    0x00 { return 'null' }
    0x01 { return ('@0x{0:X8}' -f $data) }
    0x02 { return ('?0x{0:X8}' -f $data) }
    0x03 { return (Read-Str ([long]$data)) }
    0x04 { return ([BitConverter]::ToSingle([BitConverter]::GetBytes([uint32]$data), 0)).ToString('R') }
    0x05 {
      # TYPE_DIMENSION: 24 位尾数 <<8，低 4 位单位；radix 决定小数缩放
      $c = [uint32]$data
      $u = $c -band 0xF; $r = ($c -shr 4) -band 0x3
      $m = [double]($c -band 0xFFFFFF00)
      $v = $m / 256.0
      if ($r -eq 1) { $v = $m / 32768.0 } elseif ($r -eq 2) { $v = $m / 8388608.0 }
      $units = @('px', 'dp', 'sp', 'pt', 'in', 'mm')
      $un = if ($u -lt $units.Count) { $units[$u] } else { '?' }
      return ('{0:0.###}{1}' -f $v, $un)
    }
    0x06 { return ('frac(0x{0:X8})' -f $data) }
    # INT_DEC 是有符号 32 位：0xFFFFFFFF 必须按 -1 输出，不能直接 [int] 强转
    0x10 { return ([BitConverter]::ToInt32([BitConverter]::GetBytes([uint32]$data), 0)).ToString() }
    0x11 { return ('0x{0:X}' -f $data) }
    0x12 { if ($data -ne 0) { return 'true' } else { return 'false' } }
    0x1c { return ('#{0:X8}' -f $data) }
    default { return ('0x{0:X8}' -f $data) }
  }
}

# ---------- 逐 chunk 构建 XML ----------
$sb = [Text.StringBuilder]::new()
$indent = 0
$androidNs = 'http://schemas.android.com/apk/res/android'
$end = Get-U32 4
$pos = [int]($poolOff + (Get-U32 ($poolOff + 4)))

while ($pos -lt $end) {
  $ctype = Get-U16 $pos
  $chSize = Get-U32 ($pos + 4)
  if ($chSize -eq 0) { break }

  if ($ctype -eq 0x0102) {            # START_ELEMENT
    $nameIdx = Get-U32 ($pos + 20)
    $attrStart = Get-U16 ($pos + 24)
    $attrSize = Get-U16 ($pos + 26)
    $attrCount = Get-U16 ($pos + 28)
    $tag = Read-Str ([long]$nameIdx)
    $line = ('  ' * $indent) + "<$tag"
    for ($a = 0; $a -lt $attrCount; $a++) {
      $ao = $pos + 16 + $attrStart + $a * $attrSize
      $ans = Get-U32 $ao
      $an = Get-U32 ($ao + 4)
      $raw = Get-U32 ($ao + 8)
      $dt = $b[$ao + 15]
      $dd = Get-U32 ($ao + 16)
      $prefix = ''
      if ($ans -ne 0xFFFFFFFF) {
        $nsp = Read-Str ([long]$ans)
        if ($nsp -eq $androidNs) { $prefix = 'android:' }
      }
      # 注意：部分打包器把 rawValue 写成 0（指向空串）而不是 0xFFFFFFFF，
      # 因此以 typedValue 为准；仅当类型为 NULL 时才回退到 rawValue。
      $val = if ($dt -eq 0x00 -and $raw -ne 0xFFFFFFFF) { Read-Str ([long]$raw) } else { Fmt-Value $dt $dd }
      $line += ' ' + $prefix + (Read-Str ([long]$an)) + '="' + (Esc $val) + '"'
    }
    [void]$sb.AppendLine($line + '>')
    $indent++
  }
  elseif ($ctype -eq 0x0103) {        # END_ELEMENT
    $indent--
    if ($indent -lt 0) { $indent = 0 }
    $nameIdx = Get-U32 ($pos + 20)
    [void]$sb.AppendLine(('  ' * $indent) + '</' + (Read-Str ([long]$nameIdx)) + '>')
  }
  # 0x0104 CDATA / 0x0180 RESOURCE_MAP / 其他 chunk：跳过

  $pos += [int]$chSize
}

$xml = $sb.ToString().TrimEnd() + "`n"
# 把空元素折成自闭合 <tag .../>，便于阅读
$xml = [Text.RegularExpressions.Regex]::Replace(
  $xml,
  '(?m)^(?<pad>[ \t]*)<(?<name>[A-Za-z_][\w:.-]*)(?<attr>[^<>]*)>\r?\n[ \t]*</\k<name>>\r?$',
  '${pad}<${name}${attr}/>')
if (-not $Out) { $Out = [IO.Path]::ChangeExtension($Path, '.decoded.xml') }
[IO.File]::WriteAllText($Out, $xml, [Text.UTF8Encoding]::new($false))
Write-Output ("OK: {0} -> {1} ({2} bytes, {3} lines)" -f $Path, $Out, $xml.Length, ($xml -split "`n").Count)
