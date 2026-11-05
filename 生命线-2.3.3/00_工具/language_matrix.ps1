param(
  [string]$Root = (Split-Path $PSScriptRoot -Parent)
)
# Language completeness matrix: story text + in-app string tables.
$ErrorActionPreference = 'Stop'
$unpack = Join-Path $Root '02_解包'
$res    = Join-Path $Root '04_资源分析'
New-Item -ItemType Directory -Force -Path $res | Out-Null

$langs = @('', 'cn', 'de', 'en', 'es', 'fr', 'ja', 'ko', 'ru')

function Get-StoryInfo([string]$file) {
  $text = [IO.File]::ReadAllText($file, [Text.Encoding]::UTF8)
  $lines = $text -split "`r?`n"
  $names = New-Object System.Collections.Generic.List[string]
  foreach ($l in $lines) { if ($l.StartsWith(':: ')) { $names.Add($l.Substring(3).Trim()) } }
  $uniq = @($names | Sort-Object -Unique)
  $nameSet = New-Object 'System.Collections.Generic.HashSet[string]'
  foreach ($n in $uniq) { [void]$nameSet.Add($n) }
  $targets = New-Object System.Collections.Generic.List[string]
  foreach ($m in [regex]::Matches($text, '\[\[([^\]|]+)\|([^\]]+)\]\]')) { $targets.Add($m.Groups[2].Value.Trim()) }
  $uniqTargets = @($targets | Sort-Object -Unique)
  $dangling = @($uniqTargets | Where-Object { -not $nameSet.Contains($_) })
  $choices = ([regex]::Matches($text, [regex]::Escape('<<choice'))).Count
  $vars = @{}
  foreach ($m in [regex]::Matches($text, '\$[A-Za-z_][A-Za-z0-9_]*')) { $vars[$m.Value] = 1 }
  [pscustomobject]@{
    bytes = (Get-Item $file).Length
    passages = $names.Count
    unique = $uniq.Count
    choices = $choices
    targets = $uniqTargets.Count
    dangling = $dangling.Count
    vars = $vars.Count
    names = $uniq
  }
}

function Get-StringTable([string]$file) {
  [xml]$doc = [IO.File]::ReadAllText($file, [Text.Encoding]::UTF8)
  $map = @{}
  foreach ($n in $doc.resources.string) {
    $v = $n.'#text'; if ($null -eq $v) { $v = $n.InnerText }
    $map[$n.name] = ([string]$v).Trim()
  }
  $map
}

$story = [ordered]@{}
foreach ($l in $langs) {
  $f = if ($l) { Join-Path $unpack ("assets\StoryData_" + $l + ".txt") } else { Join-Path $unpack 'assets\StoryData.txt' }
  if (Test-Path $f) { $story[$l] = Get-StoryInfo $f }
}

$enNames = New-Object 'System.Collections.Generic.HashSet[string]'
foreach ($n in $story['en'].names) { [void]$enNames.Add($n) }

$strings = [ordered]@{}
foreach ($l in @('cn', 'de', 'en', 'es', 'fr', 'ja', 'ko', 'ru')) {
  $f = Join-Path $unpack ("assets\strings_" + $l + ".xml")
  if (Test-Path $f) { $strings[$l] = Get-StringTable $f }
}
$enKeys = New-Object 'System.Collections.Generic.HashSet[string]'
foreach ($k in $strings['en'].Keys) { [void]$enKeys.Add($k) }

$md = New-Object System.Collections.Generic.List[string]
$md.Add('# 语言完整性矩阵')
$md.Add('')
$md.Add('| 语言 | 剧本 KB | 段落 | 唯一段落 | choice | 唯一目标 | 悬空 | 变量种类 | 文案键 | 缺 en 键 | 多出键 | 与 en 完全相同 |')
$md.Add('|---|---|---|---|---|---|---|---|---|---|---|---|')
foreach ($l in $story.Keys) {
  $s = $story[$l]
  $label = if ($l) { $l } else { '(base)' }
  $sk = if ($strings.Contains($l)) { $strings[$l] } else { $null }
  $nKeys = if ($sk) { $sk.Count } else { 0 }
  $missing = 0; $extra = 0; $same = 0
  if ($sk) {
    foreach ($k in $enKeys) { if (-not $sk.ContainsKey($k)) { $missing++ } }
    foreach ($k in $sk.Keys) { if (-not $enKeys.Contains($k)) { $extra++ } }
    foreach ($k in $sk.Keys) {
      if ($strings['en'].ContainsKey($k) -and $sk[$k] -eq $strings['en'][$k] -and $sk[$k].Length -gt 1) { $same++ }
    }
  }
  $md.Add(("| {0} | {1:N1} | {2} | {3} | {4} | {5} | {6} | {7} | {8} | {9} | {10} | {11} |" -f `
    $label, ($s.bytes / 1KB), $s.passages, $s.unique, $s.choices, $s.targets, $s.dangling, $s.vars, $nKeys, $missing, $extra, $same))
}
$md.Add('')
$md.Add('## 段落集合差异（相对 en）')
$md.Add('')
foreach ($l in $story.Keys) {
  if ($l -eq 'en') { continue }
  $label = if ($l) { $l } else { '(base)' }
  $set = New-Object 'System.Collections.Generic.HashSet[string]'
  foreach ($n in $story[$l].names) { [void]$set.Add($n) }
  $only = @($story[$l].names | Where-Object { -not $enNames.Contains($_) })
  $miss = @($enNames | Where-Object { -not $set.Contains($_) })
  $md.Add("- **$label**：独有 $($only.Count) 段；缺 en $($miss.Count) 段")
  if ($only.Count -and $only.Count -le 20) { $md.Add('  - 独有：' + ($only -join '、')) }
  if ($miss.Count -and $miss.Count -le 20) { $md.Add('  - 缺失：' + ($miss -join '、')) }
}
$md.Add('')
$md.Add('## 文案键差异明细')
$md.Add('')
foreach ($l in $strings.Keys) {
  if ($l -eq 'en') { continue }
  $sk = $strings[$l]
  $missing = @($enKeys | Where-Object { -not $sk.ContainsKey($_) } | Sort-Object)
  $extra = @($sk.Keys | Where-Object { -not $enKeys.Contains($_) } | Sort-Object)
  $missTxt = if ($missing.Count) { '（' + ($missing -join '、') + '）' } else { '' }
  $md.Add("- **$l**：缺 $($missing.Count) 键$missTxt")
  if ($extra.Count) { $md.Add("  - 多出 $($extra.Count) 键：" + ($extra -join '、')) }
}

$out = Join-Path $res '语言矩阵.md'
[IO.File]::WriteAllText($out, (($md -join "`r`n") + "`r`n"), [Text.UTF8Encoding]::new($false))
Write-Output "OK: $out"
