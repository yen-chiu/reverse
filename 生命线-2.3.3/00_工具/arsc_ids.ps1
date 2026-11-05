param(
  [string]$Root = (Split-Path $PSScriptRoot -Parent),
  [string]$Out
)
# Minimal resources.arsc reader: 0x7Fxxxxxx -> type/name (+ simple string value).
$ErrorActionPreference = 'Stop'
if (-not $Out) { $Out = Join-Path $Root '04_资源分析\资源ID表.txt' }
$b = [IO.File]::ReadAllBytes((Join-Path $Root '02_解包\resources.arsc'))

function U16([int]$o) { [BitConverter]::ToUInt16($b, $o) }
function U32([int]$o) { [BitConverter]::ToUInt32($b, $o) }

function Read-Pool([int]$off) {
  if ((U16 $off) -ne 0x0001) { throw ("string pool expected at 0x{0:X}" -f $off) }
  $size  = U32 ($off + 4)
  $count = U32 ($off + 8)
  $flags = U32 ($off + 16)
  $start = U32 ($off + 20)
  $base  = $off + $start
  $utf8  = ($flags -band 0x100) -ne 0
  $list  = New-Object System.Collections.Generic.List[string]
  for ($i = 0; $i -lt $count; $i++) {
    $p = [int]($base + (U32 ($off + 28 + 4 * $i)))
    if ($utf8) {
      $n1 = $b[$p]; $p++
      if ($n1 -band 0x80) { $len = (($n1 -band 0x7F) -shl 8) -bor $b[$p]; $p++ }
      $n2 = $b[$p]; $p++
      if ($n2 -band 0x80) { $blen = (($n2 -band 0x7F) -shl 8) -bor $b[$p]; $p++ } else { $blen = $n2 }
      $list.Add([Text.Encoding]::UTF8.GetString($b, $p, $blen))
    } else {
      $len = [BitConverter]::ToUInt16($b, $p); $p += 2
      $list.Add([Text.Encoding]::Unicode.GetString($b, $p, $len * 2))
    }
  }
  [pscustomobject]@{ Strings = $list; Size = [int]$size }
}

$global = Read-Pool 12
$pkgCount = U32 8
$pkgPos = 12 + $global.Size
$map = @{}
$dup = 0
$rows = New-Object System.Collections.Generic.List[object]

for ($pi = 0; $pi -lt $pkgCount; $pi++) {
  if ((U16 $pkgPos) -ne 0x0200) { break }
  $pkgSize = U32 ($pkgPos + 4)
  $headerSize = U16 ($pkgPos + 2)
  $pkgId = U32 ($pkgPos + 8)
  $typePoolOff = $pkgPos + (U32 ($pkgPos + 268))
  $keyPoolOff  = $pkgPos + (U32 ($pkgPos + 276))
  $typePool = Read-Pool $typePoolOff
  $keyPool  = Read-Pool $keyPoolOff

  $pos = $pkgPos + $headerSize
  $end = $pkgPos + $pkgSize
  while ($pos -lt $end) {
    $ctype = U16 $pos
    $csize = U32 ($pos + 4)
    if ($csize -eq 0) { break }
    if ($ctype -eq 0x0201) {
      $typeId = $b[$pos + 8]
      $entryCount = U32 ($pos + 12)
      $entriesStart = U32 ($pos + 16)
      # 注意：entry offset 数组的起点是 *类型块自己的* headerSize，
      # 不是 package headerSize（那会让偏移整体越界）。
      $entriesOff = $pos + (U16 ($pos + 2))
      for ($i = 0; $i -lt $entryCount; $i++) {
        $eo = U32 ($entriesOff + 4 * $i)
        # PS 5.1 里 0xFFFFFFFF 可能被解析成 -1，必须显式按 uint32 比较
        if ([uint32]$eo -eq [uint32]::MaxValue) { continue }
        $entryPos = $pos + $entriesStart + $eo
        $keyIdx = U32 ($entryPos + 4)
        $dataType = $b[$entryPos + 11]
        $data = U32 ($entryPos + 12)
        $id = ([uint32]$pkgId -shl 24) -bor ([uint32]$typeId -shl 16) -bor [uint32]$i
        $value = '<complex>'
        switch ($dataType) {
          0x03 { $value = $global.Strings[[int]$data] }
          0x00 { $value = 'null' }
          0x01 { $value = ('@0x{0:X8}' -f $data) }
          0x10 { $value = ([BitConverter]::ToInt32([BitConverter]::GetBytes([uint32]$data), 0)).ToString() }
          0x11 { $value = ('0x{0:X}' -f $data) }
          0x12 { $value = if ($data -ne 0) { 'true' } else { 'false' } }
          0x1c { $value = ('#{0:X8}' -f $data) }
        }
        $typeName = if ($typeId -ge 1 -and $typeId -le $typePool.Strings.Count) { $typePool.Strings[$typeId - 1] } else { "type$typeId" }
        $entryName = if ($keyIdx -lt $keyPool.Strings.Count) { $keyPool.Strings[[int]$keyIdx] } else { "entry$i" }
        if ($map.ContainsKey($id)) { $dup++; continue }
        $map[$id] = $true
        $rows.Add([pscustomobject]@{
          id = ('0x{0:X8}' -f $id); type = $typeName; name = $entryName; value = $value
        })
      }
    }
    $pos += [int]$csize
  }
  $pkgPos += [int]$pkgSize
}

$lines = New-Object System.Collections.Generic.List[string]
$lines.Add('# resources.arsc ID 表（0x7Fxxxxxx）')
$lines.Add('')
$lines.Add("条目数=$($rows.Count) 重复配置跳过的同 ID 记录=$dup")
$lines.Add('')
$lines.Add('| ID | 类型 | 名称 | 值 |')
$lines.Add('|---|---|---|---|')
foreach ($r in ($rows | Sort-Object { [Convert]::ToUInt32($_.id.Substring(2), 16) })) {
  $lines.Add(("| {0} | {1} | {2} | {3} |" -f $r.id, $r.type, $r.name, ($r.value -replace '\|', '\|')))
}
[IO.File]::WriteAllText($Out, (($lines -join "`r`n") + "`r`n"), [Text.UTF8Encoding]::new($false))
Write-Output ("OK: {0} entries={1} dupConfigs={2} -> {3}" -f $rows.Count, $rows.Count, $dup, $Out)
