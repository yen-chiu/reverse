<#
.SYNOPSIS
  verify_hashes.ps1 — 校验 SHA256SUMS.txt，确认解包产物与原始包一致。

.DESCRIPTION
  SHA256SUMS.txt 由 make_checksums.ps1 生成（每行 "HASH 相对路径"），
  路径相对项目根。本脚本重新计算并报告 OK / MISMATCH / MISSING。

.EXAMPLE
  pwsh -File verify_hashes.ps1 -Root ..\..\生命线-2.3.3
#>
param(
  [Parameter(Mandatory = $true)][string]$Root,
  [string]$SumsName = 'SHA256SUMS.txt'
)

$ErrorActionPreference = 'Stop'
$rootFull = (Resolve-Path -LiteralPath $Root).Path
$sums = Join-Path $rootFull $SumsName
if (-not (Test-Path -LiteralPath $sums)) { throw "找不到 $sums" }

$ok = 0; $bad = 0; $missing = 0
foreach ($line in [IO.File]::ReadAllLines($sums)) {
  if (-not $line.Trim()) { continue }
  $parts = $line -split '\s+', 2
  if ($parts.Count -lt 2) { continue }
  $want = $parts[0].Trim().ToUpper()
  $rel = $parts[1].Trim().Replace('/', '\')
  $f = Join-Path $rootFull $rel
  if (-not (Test-Path -LiteralPath $f)) { Write-Output "MISSING  $rel"; $missing++; continue }
  $got = (Get-FileHash -LiteralPath $f -Algorithm SHA256).Hash.ToUpper()
  if ($got -eq $want) { $ok++ } else { Write-Output "MISMATCH $rel`n  want=$want`n  got =$got"; $bad++ }
}
Write-Output ""
Write-Output ("校验完成: OK={0}  MISMATCH={1}  MISSING={2}" -f $ok, $bad, $missing)
if ($bad -or $missing) { exit 1 }
