param(
  [string]$Root = (Split-Path $PSScriptRoot -Parent)
)
# Rewrite @0x7Fxxxxxx references in decoded XML to @type/name using 资源ID表.txt.
$ErrorActionPreference = 'Stop'
$table = Join-Path $Root '04_资源分析\资源ID表.txt'
if (-not (Test-Path $table)) { throw "missing $table (run arsc_ids.ps1 first)" }
$map = @{}
foreach ($line in [IO.File]::ReadAllLines($table, [Text.Encoding]::UTF8)) {
  if ($line -notmatch '^\| (0x7F[0-9A-F]{6}) \| ([^|]+) \| ([^|]+) \|') { continue }
  # 去掉 0x 前缀，与 XML 里的 @0x7Fxxxxxx 归一
  $key = $Matches[1].Substring(2).ToLower()
  $map[$key] = ($Matches[2].Trim() + '/' + $Matches[3].Trim())
}
$dirs = @((Join-Path $Root '03_反编译\布局'), (Join-Path $Root '03_反编译\清单'))
$rx = [regex]'@0x(7F[0-9A-Fa-f]{6})'
$n = 0
foreach ($dir in $dirs) {
  if (-not (Test-Path $dir)) { continue }
  $outDir = Join-Path $dir '标注'
  New-Item -ItemType Directory -Force -Path $outDir | Out-Null
  foreach ($f in Get-ChildItem $dir -File -Filter *.xml) {
    $xml = [IO.File]::ReadAllText($f.FullName, [Text.Encoding]::UTF8)
    $sb = New-Object System.Text.StringBuilder
    $last = 0
    foreach ($m in $rx.Matches($xml)) {
      [void]$sb.Append($xml.Substring($last, $m.Index - $last))
      $k = $m.Groups[1].Value.ToLower()
      if ($map.ContainsKey($k)) { [void]$sb.Append('@' + $map[$k]) } else { [void]$sb.Append($m.Value) }
      $last = $m.Index + $m.Length
    }
    [void]$sb.Append($xml.Substring($last))
    [IO.File]::WriteAllText((Join-Path $outDir $f.Name), $sb.ToString(), [Text.UTF8Encoding]::new($false))
    $n++
  }
}
Write-Output ("annotated={0} files" -f $n)
