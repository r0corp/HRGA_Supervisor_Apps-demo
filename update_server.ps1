# Terapkan update Weekly Report HRGA yang sudah disiapkan di folder "update\".
# .env, database (instance\), venv\ dan logs\ TIDAK disentuh.
#
# Jalankan di PC server, PowerShell "Run as Administrator":
#   Set-Location C:\Users\<user>\HRGA_Supervisor_Apps
#   powershell -ExecutionPolicy Bypass -File .\update_server.ps1

param(
    [string]$ServiceName = "HRGA_Supervisor_Apps",
    [int]$Port = 8400
)

$ErrorActionPreference = "Stop"

$root = $PSScriptRoot
$src = Join-Path $root "update"
$nssm = Join-Path $root "nssm.exe"
$python = Join-Path $root "venv\Scripts\python.exe"

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    throw "Jalankan PowerShell dengan 'Run as Administrator'."
}

if (-not (Test-Path $src)) {
    throw "Folder update tidak ditemukan: $src"
}

# Backup database dulu, jaga-jaga.
$db = Join-Path $root "instance\weekly.db"

if (Test-Path $db) {
    $backup = Join-Path $root ("instance\weekly-" + (Get-Date -Format "yyyyMMdd-HHmmss") + ".db.bak")
    Copy-Item $db $backup
    Write-Host "Backup database: $backup"
}

Write-Host "Menghentikan service $ServiceName..."
& $nssm stop $ServiceName | Out-Null

# /E = termasuk subfolder. Exit code robocopy < 8 berarti sukses.
robocopy $src $root /E /NFL /NDL /NJH /NJS /NP | Out-Null

if ($LASTEXITCODE -ge 8) {
    & $nssm start $ServiceName | Out-Null
    throw "Copy file update gagal (robocopy exit $LASTEXITCODE). Service dijalankan lagi dengan versi lama."
}

& $python -m pip install -q --disable-pip-version-check -r (Join-Path $root "requirements.txt")

Write-Host "Menjalankan service $ServiceName..."
& $nssm start $ServiceName | Out-Null

Start-Sleep -Seconds 3

try {
    $code = (Invoke-WebRequest "http://127.0.0.1:$Port/login" -UseBasicParsing -TimeoutSec 10).StatusCode
    Remove-Item -Recurse -Force $src
    Write-Host "`nUPDATE SELESAI (HTTP $code). Folder update sudah dibersihkan." -ForegroundColor Green
} catch {
    Write-Host "`nService belum merespons. Cek $root\logs\service.log" -ForegroundColor Yellow
    & $nssm status $ServiceName
}
