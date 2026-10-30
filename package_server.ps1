# Buat paket untuk dicopy ke PC server:
#   dist\HRGA_Supervisor_Apps-server.zip -> extract ke C:\Users\<user>\HRGA_Supervisor_Apps
#
# Jalankan: powershell -ExecutionPolicy Bypass -File .\package_server.ps1
#   -Excel "<path>"  ikut sertakan template Excel lama untuk diimpor otomatis
#                    saat setup_server.ps1 (hanya kalau database masih kosong)

param(
    [string]$Excel = ""
)

$ErrorActionPreference = "Stop"

$root = $PSScriptRoot
$dist = Join-Path $root "dist"
$staging = Join-Path $env:TEMP "HRGA_Supervisor_Apps-package"

Remove-Item -Recurse -Force $staging -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force $dist, $staging | Out-Null

# Tanpa venv, database, .env, cache dan tests.
foreach ($item in @("app", "config.py", "run.py", "serve_production.py", "seed.py",
                    "import_excel.py", "backup.py", "install_backup_task.ps1",
                    "requirements.txt", "README.md",
                    "setup_server.ps1", "update_server.ps1")) {
    Copy-Item (Join-Path $root $item) $staging -Recurse
}

if ($Excel) {
    New-Item -ItemType Directory -Force (Join-Path $staging "data") | Out-Null
    Copy-Item $Excel (Join-Path $staging "data\Weekly Report HRGA.xlsx")
}

Get-ChildItem $staging -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force

$zip = Join-Path $dist "HRGA_Supervisor_Apps-server.zip"
Compress-Archive -Path (Join-Path $staging "*") -DestinationPath $zip -Force

Remove-Item -Recurse -Force $staging

Get-ChildItem $dist | Select-Object Name, @{ n = "KB"; e = { [math]::Round($_.Length / 1KB) } }
