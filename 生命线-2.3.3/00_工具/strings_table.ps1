<#
.SYNOPSIS
  strings_table.ps1 — 把 assets/strings_<lang>.xml 转成 Markdown 对照表。

.DESCRIPTION
  strings_*.xml 不是 Android 资源（不进 resources.arsc），而是游戏自研的
  文案表，由 Utils.readLanguageFileFromAssets 解析。本脚本只做展示用转换，
  便于审阅未翻译/占位/渠道残留文案。

.EXAMPLE
  pwsh -File strings_table.ps1 -Path ..\02_解包\assets\strings_cn.xml -Out ..\04_资源分析\字符串表_cn.md
#>
param(
  [Parameter(Mandatory = $true)][string]$Path,
  [string]$Out,
  [string]$Compare   # 可选对照语言文件（如 strings_en.xml），标注两侧是否都有
)

$ErrorActionPreference = 'Stop'
$full = (Resolve-Path -LiteralPath $Path).Path
[xml]$doc = [IO.File]::ReadAllText($full, [Text.Encoding]::UTF8)

$rows = @()
foreach ($n in $doc.resources.string) {
  $v = $n.'#text'
  if ($null -eq $v) { $v = $n.InnerText }
  $rows += [pscustomobject]@{ name = $n.name; value = ($v -replace "`r?`n", '\n') }
}

$cmpMap = @{}
if ($Compare) {
  [xml]$d2 = [IO.File]::ReadAllText((Resolve-Path -LiteralPath $Compare).Path, [Text.Encoding]::UTF8)
  foreach ($n in $d2.resources.string) { $cmpMap[$n.name] = $n.InnerText }
}

$md = New-Object System.Collections.Generic.List[string]
$md.Add("# 文案表：$(Split-Path $full -Leaf)")
$md.Add('')
$md.Add("条目数：$($rows.Count)")
$md.Add('')
if ($Compare) {
  $md.Add('| key | 值 | 对照值 |')
  $md.Add('|---|---|---|')
} else {
  $md.Add('| key | 值 |')
  $md.Add('|---|---|')
}
foreach ($r in $rows) {
  $v = ($r.value -replace '\|', '\|')
  if ($Compare) {
    $cv = if ($cmpMap.ContainsKey($r.name)) { ($cmpMap[$r.name] -replace '\|', '\|') } else { '_缺_' }
    $md.Add("| ``$($r.name)`` | $v | $cv |")
  } else {
    $md.Add("| ``$($r.name)`` | $v |")
  }
}
$md.Add('')
if ($Compare) {
  $missing = @($rows | Where-Object { -not $cmpMap.ContainsKey($_.name) } | ForEach-Object { $_.name })
  $extra = @($cmpMap.Keys | Where-Object { -not ($rows.name -contains $_) })
  $md.Add("- 本文件有、对照没有：" + (($missing -join '、') -replace '^$', '无'))
  $md.Add("- 对照有、本文件没有：" + (($extra -join '、') -replace '^$', '无'))
  $md.Add('')
}

$text = ($md -join "`r`n") + "`r`n"
if ($Out) {
  [IO.File]::WriteAllText($Out, $text, [Text.UTF8Encoding]::new($false))
  Write-Output "OK: $Out ($($rows.Count) 条)"
} else { $text }
