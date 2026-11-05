param(
  [Parameter(Mandatory = $true)][string[]]$Path,
  [Parameter(Mandatory = $true)][string]$OutDir
)
# Minimal DEX class_defs reader: dumps every class name plus a library-level
# package histogram. No dexdump/baksmali dependency.
$ErrorActionPreference = 'Stop'
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

function Read-Uleb([byte[]]$b, [int]$o) {
  $result = 0; $shift = 0
  while ($true) {
    $x = $b[$o]; $o++
    $result = $result -bor (($x -band 0x7f) -shl $shift)
    if (($x -band 0x80) -eq 0) { break }
    $shift += 7
    if ($shift -gt 35) { throw 'malformed uleb128' }
  }
  [pscustomobject]@{ Value = [uint32]$result; Next = $o }
}

function Get-DexString([byte[]]$b, [int]$off) {
  $u = Read-Uleb $b $off
  $o = $u.Next
  $sb = New-Object System.Text.StringBuilder
  while ($true) {
    $c = $b[$o]
    if ($c -eq 0) { break }
    [void]$sb.Append([char]$c)
    $o++
  }
  $sb.ToString()
}

function Get-LibraryKey([string]$name) {
  $rules = [ordered]@{
    'com.bigfishgames'        = 'com.bigfishgames'
    'com.wh.'                 = 'com.wh (authsdk)'
    'com.whgame'              = 'com.whgame'
    'com.one.oaid'            = 'com.one.oaid'
    'com.google.android.gms'  = 'com.google.android.gms'
    'com.google.firebase'     = 'com.google.firebase'
    'com.google.gson'         = 'com.google.gson'
    'com.google.android'      = 'com.google.android'
    'com.crashlytics'         = 'fabric/crashlytics'
    'io.fabric'               = 'fabric/crashlytics'
    'com.squareup'            = 'com.squareup'
    'androidx'                = 'androidx'
    'android.support'         = 'support-lib'
    'kotlin'                  = 'kotlin'
    'kotlinx'                 = 'kotlin'
    'com.unity'               = 'com.unity'
    'okhttp3'                 = 'okhttp3'
    'io.reactivex'            = 'rx'
    'org.apache'              = 'org.apache'
    'org.json'                = 'org.json'
    'org.intellij'            = 'org.intellij'
    'com.bumptech'            = 'com.bumptech'
    'rx'                      = 'rx'
    'org.jetbrains'           = 'org.jetbrains'
    'com.amazon'              = 'com.amazon'
    'com.facebook'            = 'com.facebook'
  }
  foreach ($k in $rules.Keys) {
    if ($name.StartsWith($k)) { return $rules[$k] }
  }
  $parts = $name.Split('.')
  if ($parts.Length -ge 3) { return ($parts[0..2] -join '.') }
  $name
}

foreach ($p in $Path) {
  $full = (Resolve-Path -LiteralPath $p).Path
  $b = [IO.File]::ReadAllBytes($full)
  if ($b.Length -lt 0x70) { throw "not a dex: $full" }
  $strSize = [BitConverter]::ToUInt32($b, 0x38); $strOff = [BitConverter]::ToUInt32($b, 0x3c)
  $typeOff = [BitConverter]::ToUInt32($b, 0x44)
  $clsSize = [BitConverter]::ToUInt32($b, 0x60); $clsOff = [BitConverter]::ToUInt32($b, 0x64)

  $classes = New-Object System.Collections.Generic.List[string]
  for ($i = 0; $i -lt $clsSize; $i++) {
    $cd = [int]$clsOff + $i * 32
    $classIdx = [BitConverter]::ToUInt32($b, $cd)
    $typeIdx  = [BitConverter]::ToUInt32($b, [int]$typeOff + [int]$classIdx * 4)
    $strIdx   = [BitConverter]::ToUInt32($b, [int]$strOff + [int]$typeIdx * 4)
    $desc = Get-DexString $b ([int]$strIdx)
    if ($desc.StartsWith('L') -and $desc.EndsWith(';')) { $desc = $desc.Substring(1, $desc.Length - 2) }
    $classes.Add($desc.Replace('/', '.'))
  }

  $base = [IO.Path]::GetFileNameWithoutExtension($full)
  $classFile = Join-Path $OutDir ($base + '_classes.txt')
  [IO.File]::WriteAllText($classFile, (($classes -join "`r`n") + "`r`n"), [Text.UTF8Encoding]::new($false))

  $hist = $classes | Group-Object { Get-LibraryKey $_ } | Sort-Object Count -Descending
  $lines = New-Object System.Collections.Generic.List[string]
  $lines.Add("# $base : class_defs=$($clsSize)  distinct_packages=$($hist.Count)")
  $lines.Add('')
  $lines.Add('| 类别 | 类数 |')
  $lines.Add('|---|---|')
  foreach ($h in $hist) { $lines.Add("| $($h.Name) | $($h.Count) |") }
  $pkgFile = Join-Path $OutDir ($base + '_packages.txt')
  [IO.File]::WriteAllText($pkgFile, (($lines -join "`r`n") + "`r`n"), [Text.UTF8Encoding]::new($false))
  Write-Output ("$base classes={0} packages={1}" -f $clsSize, $hist.Count)
}
