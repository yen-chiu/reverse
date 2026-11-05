<#
.SYNOPSIS
  make_checksums.ps1 — 为项目内所有文件生成 SHA256SUMS.txt。

.DESCRIPTION
  路径相对项目根，使用正斜杠，便于跨工具比对。排除 SHA256SUMS.txt 自身与
  99_临时 目录。用于回答"解包出来的字节是否就是包里那一份"。

.EXAMPLE
  pwsh -File make_checksums.ps1 -Root ..
#>
param(
  [Parameter(Mandatory = $true)][string]$Root,
  [string]$SumsName = 'SHA256SUMS.txt'
)

$ErrorActionPreference = 'Stop'
$rootFull = (Resolve-Path -LiteralPath $Root).Path
$sumsPath = Join-Path $rootFull $SumsName

$files = Get-ChildItem $rootFull -Recurse -File -Force |
  Where-Object {
    $_.FullName -ne $sumsPath -and
    -not $_.FullName.StartsWith((Join-Path $rootFull '99_临时'), [StringComparison]::OrdinalIgnoreCase)
  } | Sort-Object FullName

$lines = New-Object System.Collections.Generic.List[string]
foreach ($f in $files) {
  $rel = $f.FullName.Substring($rootFull.Length + 1).Replace('\', '/')
  $h = (Get-FileHash -LiteralPath $f.FullName -Algorithm SHA256).Hash.ToUpper()
  $lines.Add("$h  $rel")
}
[IO.File]::WriteAllText($sumsPath, (($lines -join "`n") + "`n"), [Text.UTF8Encoding]::new($false))
Write-Output ("OK: {0}  共 {1} 个文件" -f $sumsPath, $lines.Count)
