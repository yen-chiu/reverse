<#
.SYNOPSIS
  story_stats.ps1 — 统计 Lifeline 剧本（Twine 2 导出文本）的结构指标。

.DESCRIPTION
  统计段落数/重名、DSL token 次数、choice 目标与悬空引用、变量出现次数；
  给定多个语言文件时输出「某语言独有段落」。结果同时写 JSON（机器可读）
  与 Markdown（人读）。

.EXAMPLE
  pwsh -File story_stats.ps1 -Path ..\02_解包\assets\StoryData_cn.txt -OutJson ..\04_资源分析\剧本统计_cn.json
#>
param(
  [Parameter(Mandatory = $true)][string[]]$Path,
  [string]$OutJson,
  [string]$OutMd,
  [string]$Compare    # 对照组（例如 en）：报告"Path 中独有而 Compare 中没有"的段落
)

$ErrorActionPreference = 'Stop'

function Get-StoryStats([string]$file) {
  $full = (Resolve-Path -LiteralPath $file).Path
  $text = [IO.File]::ReadAllText($full, [Text.Encoding]::UTF8)
  $lines = $text -split "`r?`n"

  $names = New-Object System.Collections.Generic.List[string]
  foreach ($l in $lines) {
    if ($l.StartsWith(':: ')) { $names.Add($l.Substring(3).Trim()) }
  }
  $uniq = @($names | Sort-Object -Unique)

  $tokens = [ordered]@{
    '<<choice'      = ([regex]::Matches($text, [regex]::Escape('<<choice'))).Count
    '<<if'          = ([regex]::Matches($text, [regex]::Escape('<<if '))).Count
    '<<elseif'      = ([regex]::Matches($text, [regex]::Escape('<<elseif'))).Count
    '<<else'        = ([regex]::Matches($text, [regex]::Escape('<<else>>'))).Count
    '<<endif'       = ([regex]::Matches($text, [regex]::Escape('<<endif>>'))).Count
    '<<set'         = ([regex]::Matches($text, [regex]::Escape('<<set '))).Count
    '<<silently'    = ([regex]::Matches($text, [regex]::Escape('<<silently>>'))).Count
    '<<endsilently' = ([regex]::Matches($text, [regex]::Escape('<<endsilently>>'))).Count
    '<<category'    = ([regex]::Matches($text, [regex]::Escape('<<category'))).Count
    '<<textinput'   = ([regex]::Matches($text, [regex]::Escape('<<textinput'))).Count
    '<<sendemail'   = ([regex]::Matches($text, [regex]::Escape('<<sendemail'))).Count
    '<<netcheck'    = ([regex]::Matches($text, [regex]::Escape('<<netcheck'))).Count
    '[[..|..]]'     = ([regex]::Matches($text, '\[\[[^\]|]+\|[^\]]+\]\]')).Count
  }

  # choice 目标：[[文本|目标]]
  $targets = New-Object System.Collections.Generic.List[string]
  foreach ($m in [regex]::Matches($text, '\[\[([^\]|]+)\|([^\]]+)\]\]')) {
    $t = $m.Groups[2].Value.Trim()
    $t = $t -replace '^delay\s+\S+\s*$', ''      # [[delay 30s|x]] 已在上一级处理，这里防御
    if ($t) { $targets.Add($t) }
  }
  $uniqTargets = @($targets | Sort-Object -Unique)
  $nameSet = New-Object 'System.Collections.Generic.HashSet[string]'
  foreach ($n in $uniq) { [void]$nameSet.Add($n) }
  $dangling = @($uniqTargets | Where-Object { -not $nameSet.Contains($_) })

  # 变量出现次数
  $vars = @{}
  foreach ($m in [regex]::Matches($text, '\$[A-Za-z_][A-Za-z0-9_]*')) {
    $k = $m.Value
    if ($vars.ContainsKey($k)) { $vars[$k]++ } else { $vars[$k] = 1 }
  }
  $varTop = $vars.GetEnumerator() | Sort-Object -Property Value -Descending |
    Select-Object -First 25 | ForEach-Object { "$($_.Key)=$($_.Value)" }

  [pscustomobject]@{
    file          = $full
    bytes         = (Get-Item $full).Length
    chars         = $text.Length
    lines         = $lines.Count
    passages      = $names.Count
    uniquePassages= $uniq.Count
    duplicateNames= @($names | Group-Object | Where-Object { $_.Count -gt 1 } | ForEach-Object { "$($_.Name)×$($_.Count)" })
    tokens        = $tokens
    choiceTargets = $targets.Count
    uniqueTargets = $uniqTargets.Count
    danglingTargets = $dangling
    variableKinds = $vars.Count
    topVariables  = $varTop
    passageNames  = $uniq
  }
}

$results = @()
foreach ($p in $Path) { $results += (Get-StoryStats $p) }

$md = New-Object System.Collections.Generic.List[string]
$md.Add('# 剧本统计')
$md.Add('')
foreach ($r in $results) {
  $md.Add("## $([IO.Path]::GetFileName($r.file))")
  $md.Add('')
  $md.Add('| 指标 | 值 |')
  $md.Add('|---|---|')
  $md.Add("| 字节 | $($r.bytes) |")
  $md.Add("| 字符 | $($r.chars) |")
  $md.Add("| 行 | $($r.lines) |")
  $md.Add("| 段落（含重复）| $($r.passages) |")
  $md.Add("| 段落（唯一）| $($r.uniquePassages) |")
  $md.Add("| choice 目标（含重复）| $($r.choiceTargets) |")
  $md.Add("| choice 目标（唯一）| $($r.uniqueTargets) |")
  $md.Add("| 悬空目标 | $($r.danglingTargets.Count) |")
  $md.Add("| 变量种类 | $($r.variableKinds) |")
  $md.Add('')
  if ($r.duplicateNames.Count) { $md.Add("- 重名段落：" + ($r.duplicateNames -join '、')) ; $md.Add('') }
  $md.Add('| DSL token | 次数 |')
  $md.Add('|---|---|')
  foreach ($k in $r.tokens.Keys) { $md.Add("| ``$k`` | $($r.tokens[$k]) |") }
  $md.Add('')
  $md.Add('- 变量 Top25：' + ($r.topVariables -join '、'))
  $md.Add('')
  if ($r.danglingTargets.Count) {
    $md.Add('- **悬空目标**：' + ($r.danglingTargets -join '、'))
    $md.Add('')
  }
}

# 语言差分
if ($Compare) {
  $base = $results[0]
  $cmpFile = (Resolve-Path -LiteralPath $Compare).Path
  $cmpText = [IO.File]::ReadAllText($cmpFile, [Text.Encoding]::UTF8)
  $cmpNames = New-Object 'System.Collections.Generic.HashSet[string]'
  foreach ($l in ($cmpText -split "`r?`n")) {
    if ($l.StartsWith(':: ')) { [void]$cmpNames.Add($l.Substring(3).Trim()) }
  }
  $baseSet = New-Object 'System.Collections.Generic.HashSet[string]'
  foreach ($n in $base.passageNames) { [void]$baseSet.Add($n) }
  $onlyBase = @($base.passageNames | Where-Object { -not $cmpNames.Contains($_) })
  $onlyCmp = @($cmpNames | Where-Object { -not $baseSet.Contains($_) })

  $md.Add("## 语言差分：仅 $(Split-Path $base.file -Leaf) 有（对照 $(Split-Path $cmpFile -Leaf)）")
  $md.Add('')
  $md.Add("共 $($onlyBase.Count) 个段落：")
  $md.Add('')
  foreach ($n in $onlyBase) { $md.Add("- ``$n``") }
  $md.Add('')
  $md.Add("## 仅对照文件有：共 $($onlyCmp.Count) 个段落")
  $md.Add('')
  foreach ($n in $onlyCmp) { $md.Add("- ``$n``") }
  $md.Add('')

  $results[0] | Add-Member -NotePropertyName 'onlyInThis' -NotePropertyValue $onlyBase -Force
  $results[0] | Add-Member -NotePropertyName 'onlyInCompare' -NotePropertyValue $onlyCmp -Force
}

if ($OutJson) {
  ($results | ConvertTo-Json -Depth 6) | Set-Content -LiteralPath $OutJson -Encoding UTF8
  Write-Output "OK: $OutJson"
}
if ($OutMd) {
  [IO.File]::WriteAllText($OutMd, (($md -join "`r`n") + "`r`n"), [Text.UTF8Encoding]::new($false))
  Write-Output "OK: $OutMd"
}
if (-not $OutJson -and -not $OutMd) { ($md -join "`n") }
