param(
  [string]$Root = (Split-Path $PSScriptRoot -Parent)
)
# Package content inventory: res types, assets, raw media, META-INF, embedded
# Wear APK, dex class counts. Writes Markdown + CSV into 04_资源分析.
$ErrorActionPreference = 'Stop'
$unpack = Join-Path $Root '02_解包'
$res    = Join-Path $Root '04_资源分析'
$dec    = Join-Path $Root '03_反编译'
$tmp    = Join-Path $Root '99_临时'
New-Item -ItemType Directory -Force -Path $res, $tmp | Out-Null

function Get-Magic([string]$file) {
  $b = [IO.File]::ReadAllBytes($file)
  $n = [Math]::Min(4, $b.Length)
  ([BitConverter]::ToString($b[0..($n-1)]) -replace '-', ' ')
}

$md = New-Object System.Collections.Generic.List[string]
$csv = New-Object System.Collections.Generic.List[object]
$md.Add('# 包内容清单')
$md.Add('')
$md.Add('> 由 `00_工具\content_inventory.ps1` 生成；字节与哈希以 `SHA256SUMS.txt` 为准。')
$md.Add('')

# ---- 1. res type table ----
$md.Add('## 1. res 资源分布（按类型）')
$md.Add('')
$md.Add('| 类型 | 目录数 | 文件数 | KB |')
$md.Add('|---|---|---|---|')
$resRoot = Join-Path $unpack 'res'
$groups = Get-ChildItem $resRoot -Directory | Group-Object { ($_.Name -split '-')[0] } | Sort-Object Name
$totalRes = 0; $totalResBytes = 0
foreach ($g in $groups) {
  $files = Get-ChildItem $g.Group.FullName -Recurse -File
  $kb = ($files | Measure-Object Length -Sum).Sum / 1KB
  $totalRes += $files.Count; $totalResBytes += ($files | Measure-Object Length -Sum).Sum
  $md.Add(("| {0} | {1} | {2} | {3:N1} |" -f $g.Name, $g.Count, $files.Count, $kb))
  foreach ($f in $files) { $csv.Add([pscustomobject]@{ area='res'; type=$g.Name; path=$f.FullName.Substring($unpack.Length+1); bytes=$f.Length }) }
}
$md.Add(("| **合计** | | **{0}** | **{1:N1}** |" -f $totalRes, ($totalResBytes / 1KB)))
$md.Add('')

# ---- 2. assets ----
$md.Add('## 2. assets')
$md.Add('')
$md.Add('| 文件 | KB | 角色 |')
$md.Add('|---|---|---|')
$assets = Get-ChildItem (Join-Path $unpack 'assets') -Recurse -File | Sort-Object FullName
foreach ($a in $assets) {
  $rel = $a.FullName.Substring((Join-Path $unpack 'assets').Length + 1)
  $role = switch -Regex ($a.Name) {
    '\.otf$|\.ttf$'        { '字体' }
    '^StoryData'           { '剧本正文（DSL）' }
    '^strings_.*\.xml$'    { '自研文案表' }
    '\.json$|\.properties$' { '配置' }
    '^baseline\.prof'      { 'dexopt 基线' }
    default                { '其他' }
  }
  $md.Add(("| {0} | {1:N1} | {2} |" -f $rel, ($a.Length/1KB), $role))
  $csv.Add([pscustomobject]@{ area='assets'; type=$role; path=('assets\' + $rel); bytes=$a.Length })
}
$md.Add('')

# ---- 3. raw media ----
$md.Add('## 3. res/raw（音频与配置）')
$md.Add('')
$md.Add('| 文件 | KB | magic | 判定 |')
$md.Add('|---|---|---|---|')
foreach ($r in (Get-ChildItem (Join-Path $unpack 'res\raw') -File | Sort-Object Name)) {
  $mg = Get-Magic $r.FullName
  $kind = switch -Regex ($r.Name) {
    '\.mp3$'  { if ($mg.StartsWith('49 44 33')) { 'MP3（带 ID3 标签）' } else { 'MP3（裸 MPEG 帧）' } }
    '\.apk$'  { 'ZIP/APK（内嵌）' }
    '\.json$' { 'JSON' }
    default   { '未知' }
  }
  $md.Add(("| {0} | {1:N1} | `{2}` | {3} |" -f $r.Name, ($r.Length/1KB), $mg, $kind))
  $csv.Add([pscustomobject]@{ area='raw'; type=$kind; path=('res\raw\' + $r.Name); bytes=$r.Length })
}
$md.Add('')

# ---- 4. own drawables + mipmaps ----
$md.Add('## 4. 自有 drawable / mipmap')
$md.Add('')
$md.Add('| 文件 | KB |')
$md.Add('|---|---|')
$skip = '^(abc_|mtrl_|common_google|btn_checkbox|btn_radio|notification_template|tooltip_|design_|material_)'
$ownDraw = Get-ChildItem (Join-Path $unpack 'res') -Recurse -File |
  Where-Object { $_.Directory.Name -like 'drawable*' -and $_.Name -notmatch $skip } | Sort-Object FullName
foreach ($d in $ownDraw) {
  $md.Add(("| {0} | {1:N1} |" -f $d.FullName.Substring($unpack.Length+1), ($d.Length/1KB)))
  $csv.Add([pscustomobject]@{ area='drawable'; type='own'; path=$d.FullName.Substring($unpack.Length+1); bytes=$d.Length })
}
$md.Add('')
$md.Add('| mipmap | KB |')
$md.Add('|---|---|')
foreach ($m in (Get-ChildItem (Join-Path $unpack 'res') -Recurse -File | Where-Object { $_.Directory.Name -like 'mipmap*' } | Sort-Object FullName)) {
  $md.Add(("| {0} | {1:N1} |" -f $m.FullName.Substring($unpack.Length+1), ($m.Length/1KB)))
  $csv.Add([pscustomobject]@{ area='mipmap'; type='launcher'; path=$m.FullName.Substring($unpack.Length+1); bytes=$m.Length })
}
$md.Add('')

# ---- 5. META-INF / fabric / kotlin ----
$md.Add('## 5. META-INF / fabric / kotlin')
$md.Add('')
foreach ($dirName in @('META-INF', 'fabric', 'kotlin')) {
  $dir = Join-Path $unpack $dirName
  if (Test-Path $dir) {
    $fs = Get-ChildItem $dir -Recurse -File
    $md.Add(("- **{0}**：{1} 个文件，{2:N1} KB；" -f $dirName, $fs.Count, (($fs | Measure-Object Length -Sum).Sum/1KB)) + (($fs | Select-Object -First 6 | ForEach-Object { $_.Name }) -join '、') + '…')
    foreach ($f in $fs) { $csv.Add([pscustomobject]@{ area=$dirName; type='meta'; path=$f.FullName.Substring($unpack.Length+1); bytes=$f.Length }) }
  }
}
$md.Add('')

# ---- 6. embedded wear apk ----
$md.Add('## 6. 内嵌 Wear APK（res/raw/android_wear_micro_apk.apk）')
$md.Add('')
$wearPath = Join-Path $unpack 'res\raw\android_wear_micro_apk.apk'
if (Test-Path $wearPath) {
  Add-Type -AssemblyName System.IO.Compression.FileSystem
  $hash = (Get-FileHash $wearPath -Algorithm SHA256).Hash
  $zip = [IO.Compression.ZipFile]::OpenRead($wearPath)
  try {
    $entries = $zip.Entries
    $md.Add("- SHA-256：``$hash``")
    $md.Add("- 条目数：$($entries.Count)")
    $md.Add("- classes.dex：" + ($entries | Where-Object { $_.FullName -eq 'classes.dex' } | ForEach-Object { "$($_.Length) B（压缩 $($_.CompressedLength) B）" }))
    $md.Add('')
    $md.Add('| 条目 | 原始 B | 压缩 B |')
    $md.Add('|---|---|---|')
    foreach ($e in ($entries | Sort-Object FullName)) {
      $md.Add(("| {0} | {1} | {2} |" -f $e.FullName, $e.Length, $e.CompressedLength))
      $csv.Add([pscustomobject]@{ area='wear-apk'; type='entry'; path=$e.FullName; bytes=$e.Length })
    }
    # extract + decode its manifest
    $wearDir = Join-Path $tmp 'wear'
    New-Item -ItemType Directory -Force -Path $wearDir | Out-Null
    $mw = $entries | Where-Object { $_.FullName -eq 'AndroidManifest.xml' }
    if ($mw) {
      $bin = Join-Path $wearDir 'AndroidManifest.xml'
      [void][IO.Compression.ZipFileExtensions]::ExtractToFile($mw, $bin, $true)
      $xmlOut = Join-Path $dec '清单\wear_AndroidManifest.xml'
      & (Join-Path $PSScriptRoot 'axml2xml.ps1') -Path $bin -Out $xmlOut
      $md.Add('')
      $md.Add("- 内嵌清单：``" + $xmlOut + "``")
    }
  } finally { $zip.Dispose() }
}
$md.Add('')

# ---- 7. dex class inventory ----
$md.Add('## 7. DEX 类清点')
$md.Add('')
$md.Add('| dex | 字节 | 类数 | 类清单 |')
$md.Add('|---|---|---|---|')
foreach ($d in @('classes.dex', 'classes2.dex')) {
  $df = Join-Path $unpack $d
  if (-not (Test-Path $df)) { continue }
  $base = [IO.Path]::GetFileNameWithoutExtension($df)
  $cf = Join-Path $dec ("dex\" + $base + "_classes.txt")
  $cnt = if (Test-Path $cf) { (Get-Content $cf | Where-Object { $_ -ne '' }).Count } else { '（未生成）' }
  $md.Add(("| {0} | {1:N0} | {2} | ``03_反编译\dex\{3}_classes.txt`` |" -f $d, (Get-Item $df).Length, $cnt, $base))
}
$md.Add('')

$mdOut = Join-Path $res '包内容清单.md'
[IO.File]::WriteAllText($mdOut, (($md -join "`r`n") + "`r`n"), [Text.UTF8Encoding]::new($false))
$csv | Export-Csv -LiteralPath (Join-Path $res '包内容清单.csv') -NoTypeInformation -Encoding UTF8
Write-Output "OK: $mdOut"
