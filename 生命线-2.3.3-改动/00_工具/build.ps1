# 生命线 改动版 —— 一键构建（重新打包 → 签名 → 校验）
# 用法:
#   powershell -ExecutionPolicy Bypass -File .\00_工具\build.ps1
#   可选: -OutName "生命线-2.3.3-mod.apk"
# 注意: 本文件必须保存为 UTF-8 with BOM，否则 PS 5.1 会按 ANSI 解码而报语法错。
# 注意: 不要把函数的参数命名为 $Args（PowerShell 自动变量），否则 @Args 展开为空，
#       会让 python 进入交互式 REPL 而“卡死”。

param(
    [string]$OutName = '生命线-2.3.3-mod.apk'
)

$ErrorActionPreference = 'Continue'
[Console]::OutputEncoding = [Text.Encoding]::UTF8

$ToolDir  = $PSScriptRoot
$Proj     = Split-Path $ToolDir -Parent
$Apk      = Join-Path $Proj '01_原始\生命线-2.3.3.apk'
$Tree     = Join-Path $Proj '02_工作区'
$OutDir   = Join-Path $Proj '03_产物'
$Unsigned = Join-Path $OutDir '_unsigned.apk'
$Final    = Join-Path $OutDir $OutName
$Ks       = Join-Path $ToolDir 'lifeline-mod.keystore'
$KsPass   = 'lifeline'
$KsAlias  = 'lifeline'

foreach ($p in @($Apk, $Tree)) {
    if (-not (Test-Path $p)) { throw "缺少必需路径: $p" }
}
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

function Invoke-Native {
    param([string]$Exe, [string[]]$ArgList, [string]$What)
    $out = & $Exe @ArgList 2>&1
    $code = $LASTEXITCODE
    if ($out) { $out | ForEach-Object { Write-Host "   | $_" } }
    if ($code -ne 0) { throw "$What 失败，exit=$code" }
}

# ---- 工具链 ----
$Java = $null
foreach ($c in @('C:\01_SOFTWARE\12_Tool\Java\jdk-21.0.13+9\bin\java.exe', "$env:JAVA_HOME\bin\java.exe")) {
    if ($c -and (Test-Path $c)) { $Java = $c; break }
}
if (-not $Java) {
    $cmd = Get-Command java -ErrorAction SilentlyContinue
    if ($cmd) { $Java = $cmd.Source }
}
if (-not $Java) { throw '找不到 java.exe（可用 JAVA_HOME 指定）' }
$Keytool = Join-Path (Split-Path $Java -Parent) 'keytool.exe'

$ApksignerJar = $null
foreach ($r in @('C:\03_Github\reverse\_tools', (Join-Path (Split-Path $Proj -Parent) '_tools'))) {
    if (-not $r -or -not (Test-Path $r)) { continue }
    $ApksignerJar = Get-ChildItem $r -Recurse -Filter 'apksigner.jar' -File -ErrorAction SilentlyContinue |
        Where-Object { $_.FullName -like '*\lib\apksigner.jar' } |
        Select-Object -First 1 -ExpandProperty FullName
    if ($ApksignerJar) { break }
}
if (-not $ApksignerJar) { throw '找不到 apksigner.jar（应为 reverse\_tools\android-*\lib\apksigner.jar）' }

$Python = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $Python) { throw '找不到 python' }

Write-Host ''
Write-Host '== 1/5 重新打包 ==' -ForegroundColor Cyan
Write-Host "   java      : $Java"
Write-Host "   apksigner : $ApksignerJar"
Write-Host "   python    : $Python"
Invoke-Native -Exe $Python -ArgList @((Join-Path $ToolDir 'repack.py'), $Apk, $Tree, $Unsigned) -What '重新打包'

Write-Host ''
Write-Host '== 2/5 准备签名密钥 ==' -ForegroundColor Cyan
if (-not (Test-Path $Ks)) {
    Invoke-Native -Exe $Keytool -ArgList @(
        '-genkeypair', '-keystore', $Ks, '-alias', $KsAlias,
        '-keyalg', 'RSA', '-keysize', '2048', '-validity', '10000',
        '-storepass', $KsPass, '-keypass', $KsPass,
        '-dname', 'CN=Lifeline Mod, OU=Modding, O=Local, L=NA, ST=NA, C=CN'
    ) -What '生成 keystore'
    Write-Host '   已生成 lifeline-mod.keystore'
} else {
    Write-Host '   复用已有 lifeline-mod.keystore'
}

Write-Host ''
Write-Host '== 3/5 签名（v1+v2+v3）==' -ForegroundColor Cyan
if (Test-Path $Final) { Remove-Item $Final -Force }
Invoke-Native -Exe $Java -ArgList @(
    '-jar', $ApksignerJar, 'sign',
    '--ks', $Ks, '--ks-pass', "pass:$KsPass", '--key-pass', "pass:$KsPass", '--ks-key-alias', $KsAlias,
    '--min-sdk-version', '14',
    '--v1-signing-enabled', 'true', '--v2-signing-enabled', 'true', '--v3-signing-enabled', 'true',
    '--out', $Final, $Unsigned
) -What '签名'

Write-Host ''
Write-Host '== 4/5 校验签名 ==' -ForegroundColor Cyan
Invoke-Native -Exe $Java -ArgList @('-jar', $ApksignerJar, 'verify', '--verbose', '--print-certs', $Final) -What 'apksigner verify'

Write-Host ''
Write-Host '== 5/5 产物信息 ==' -ForegroundColor Cyan
Remove-Item $Unsigned -Force -ErrorAction SilentlyContinue
$h = (Get-FileHash $Final -Algorithm SHA256).Hash
$len = (Get-Item $Final).Length
Write-Host ("   输出: {0}" -f $Final)
Write-Host ("   大小: {0:N0} B" -f $len)
Write-Host ("   SHA-256: {0}" -f $h)
Write-Host ''
Write-Host '安装提醒: 签名与原版不同，需先卸载已装的原版（会清空存档）。' -ForegroundColor Yellow
