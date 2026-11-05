param(
  [string]$Root = (Split-Path $PSScriptRoot -Parent)
)
# Decode the game's own binary layouts into 03_反编译\布局 as readable XML.
$ErrorActionPreference = 'Stop'
$unpack = Join-Path $Root '02_解包'
$out    = Join-Path $Root '03_反编译\布局'
New-Item -ItemType Directory -Force -Path $out | Out-Null

$own = @(
  'activity_story', 'choice', 'confirmation_popup', 'splash_screen',
  'notification_action_layout', 'text', 'spinner', 'single_button', 'image_frame'
)
$tool = Join-Path $PSScriptRoot 'axml2xml.ps1'

$files = Get-ChildItem (Join-Path $unpack 'res') -Recurse -File -Filter *.xml |
  Where-Object { $_.Directory.Name -like 'layout*' -and ($own -contains $_.BaseName) }

foreach ($f in ($files | Sort-Object FullName)) {
  # qualifier dir in the name avoids collisions: layout-sw600dp_activity_story.xml
  $target = Join-Path $out ($f.Directory.Name + '_' + $f.Name)
  & $tool -Path $f.FullName -Out $target
}
Write-Output ("decoded={0} -> {1}" -f $files.Count, $out)
