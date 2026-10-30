# Setup HRGA Supervisor Apps (Weekly Report HRGA) di PC server - cukup dijalankan SEKALI.
# Aman dijalankan ulang: langkah yang sudah beres akan dilewati.
#
# Jalankan di PC server, PowerShell "Run as Administrator":
#   Set-Location C:\Users\<user>\HRGA_Supervisor_Apps
#   powershell -ExecutionPolicy Bypass -File .\setup_server.ps1

param(
    [int]$Port = 8400,
    [string]$ServiceName = "HRGA_Supervisor_Apps",
    [string]$AdminName = "Admin IT",
    [string]$SpvName = "Supervisor HRGA"
)

$ErrorActionPreference = "Stop"

$root = $PSScriptRoot
$python = Join-Path $root "venv\Scripts\python.exe"
$nssm = Join-Path $root "nssm.exe"
$excel = Join-Path $root "data\Weekly Report HRGA.xlsx"

function Step($text) { Write-Host "`n== $text" -ForegroundColor Cyan }

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    throw "Jalankan PowerShell dengan 'Run as Administrator'."
}

Set-Location $root

# Port dipakai aplikasi lain? Jangan sampai mengganggu aplikasi yang sudah live.
$busy = Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue
if ($busy -and -not (Get-Service $ServiceName -ErrorAction SilentlyContinue)) {
    throw "Port $Port sudah dipakai proses lain (PID $($busy[0].OwningProcess)). Jalankan ulang dengan -Port <port lain>."
}

# nssm.exe dipinjam (dicopy) dari aplikasi lain di sebelahnya.
if (-not (Test-Path $nssm)) {
    foreach ($sibling in @("legal-contract", "remote-tracker", "asset-tracker-simple", "report-harian")) {
        $candidate = Join-Path (Split-Path $root) "$sibling\nssm.exe"
        if (Test-Path $candidate) {
            Copy-Item $candidate $nssm
            break
        }
    }
}

if (-not (Test-Path $nssm)) {
    throw "nssm.exe tidak ditemukan. Copy nssm.exe ke $root lalu jalankan ulang."
}

# ------------------------------------------------------------
Step "1/6 Virtualenv & dependencies"

if (-not (Test-Path $python)) {

    # Pakai Python yang sama dengan venv aplikasi lain supaya tidak
    # bergantung pada PATH sesi Administrator.
    $basePython = "python"
    foreach ($sibling in @("legal-contract", "asset-tracker-simple")) {
        $baseCfg = Join-Path (Split-Path $root) "$sibling\venv\pyvenv.cfg"
        if (Test-Path $baseCfg) {
            $line = Select-String -Path $baseCfg -Pattern "^executable\s*=\s*(.+)$" | Select-Object -First 1
            if ($line -and (Test-Path $line.Matches[0].Groups[1].Value.Trim())) {
                $basePython = $line.Matches[0].Groups[1].Value.Trim()
                break
            }
        }
    }

    Write-Host "Membuat venv dengan $basePython"
    & $basePython -m venv (Join-Path $root "venv")
}

& $python -m pip install -q --disable-pip-version-check -r (Join-Path $root "requirements.txt")

if ($LASTEXITCODE -ne 0) {
    throw "pip install gagal. Cek koneksi internet PC server."
}

# ------------------------------------------------------------
Step "2/6 File .env"

$envFile = Join-Path $root ".env"

if (Test-Path $envFile) {
    Write-Host ".env sudah ada, dilewati."
} else {
    $secret = & $python -c "import secrets; print(secrets.token_hex(32))"
    @(
        "SECRET_KEY=$secret"
        "PORT=$Port"
    ) | Set-Content -Encoding ascii $envFile
    Write-Host ".env dibuat."
}

# ------------------------------------------------------------
Step "3/6 Akun IT & Spv HRGA"

# Username yang sudah ada dilewati; password baru tampil SEKALI di sini -
# catat lalu segera ganti setelah login.
& $python (Join-Path $root "seed.py") --admin-name $AdminName --spv-name $SpvName

# ------------------------------------------------------------
Step "4/6 Impor template Excel lama"

if (Test-Path $excel) {
    # Ditolak otomatis kalau database sudah berisi data (tidak menimpa).
    & $python (Join-Path $root "import_excel.py") $excel
    if ($LASTEXITCODE -ne 0) { Write-Host "Impor dilewati (database sudah berisi data)." }
} else {
    Write-Host "File $excel tidak ada, dilewati."
}

# ------------------------------------------------------------
Step "5/6 Firewall port $Port"

if (Get-NetFirewallRule -DisplayName "HRGA_Supervisor_Apps" -ErrorAction SilentlyContinue) {
    Write-Host "Rule firewall sudah ada, dilewati."
} else {
    New-NetFirewallRule -DisplayName "HRGA_Supervisor_Apps" -Direction Inbound -Action Allow `
        -Protocol TCP -LocalPort $Port | Out-Null
    Write-Host "Rule firewall dibuat."
}

# ------------------------------------------------------------
Step "6/6 Windows service '$ServiceName'"

$logDir = Join-Path $root "logs"
New-Item -ItemType Directory -Force $logDir | Out-Null

if (-not (Get-Service $ServiceName -ErrorAction SilentlyContinue)) {
    & $nssm install $ServiceName $python (Join-Path $root "serve_production.py") | Out-Null
}

& $nssm set $ServiceName AppDirectory $root | Out-Null
& $nssm set $ServiceName Start SERVICE_AUTO_START | Out-Null
& $nssm set $ServiceName AppStdout (Join-Path $logDir "service.log") | Out-Null
& $nssm set $ServiceName AppStderr (Join-Path $logDir "service.log") | Out-Null
& $nssm set $ServiceName AppRotateFiles 1 | Out-Null
& $nssm set $ServiceName AppRotateBytes 1048576 | Out-Null
& $nssm restart $ServiceName | Out-Null

Start-Sleep -Seconds 3

try {
    $code = (Invoke-WebRequest "http://127.0.0.1:$Port/login" -UseBasicParsing -TimeoutSec 10).StatusCode
    Write-Host "`nSELESAI. HRGA Supervisor Apps berjalan (HTTP $code)." -ForegroundColor Green
    Write-Host "Buka dari komputer lain: http://<IP-SERVER>:$Port"
    Write-Host "Berikutnya: pasang backup harian -> powershell -ExecutionPolicy Bypass -File .\install_backup_task.ps1"
} catch {
    Write-Host "`nService terpasang tapi belum merespons. Cek $logDir\service.log" -ForegroundColor Yellow
    & $nssm status $ServiceName
}
