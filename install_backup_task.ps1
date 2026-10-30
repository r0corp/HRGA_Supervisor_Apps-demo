# Pasang jadwal backup harian Weekly Report HRGA di PC server.
# Default tujuan: folder backups\ di dalam folder aplikasi. Aman dijalankan ulang.
#
# Jalankan, PowerShell "Run as Administrator":
#   Set-Location C:\Users\<user>\HRGA_Supervisor_Apps
#   powershell -ExecutionPolicy Bypass -File .\install_backup_task.ps1
#
# Tujuan lain (mis. drive lain): tambahkan -Dest "D:\Backup\WeeklyReport"

param(
    [string]$Dest = "",
    [string]$Time = "19:00",
    [int]$Keep = 30,
    [string]$TaskName = "HRGA_Supervisor_Apps Backup"
)

$ErrorActionPreference = "Stop"

$root = $PSScriptRoot
$python = Join-Path $root "venv\Scripts\python.exe"
$script = Join-Path $root "backup.py"
$logDir = Join-Path $root "logs"
$log = Join-Path $logDir "backup.log"

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    throw "Jalankan PowerShell dengan 'Run as Administrator'."
}

if (-not $Dest) {
    $Dest = Join-Path $root "backups"
}

New-Item -ItemType Directory -Force $Dest | Out-Null

New-Item -ItemType Directory -Force $logDir | Out-Null

# Python dijalankan langsung (bukan lewat cmd /c, yang merusak path ber-
# tanda kutip); backup.py menulis log-nya sendiri ke logs\backup.log.
$action = New-ScheduledTaskAction -Execute $python `
    -Argument "`"$script`" --dest `"$Dest`" --keep $Keep" -WorkingDirectory $root
$trigger = New-ScheduledTaskTrigger -Daily -At $Time

# Jalan sebagai user server ini, juga saat tidak sedang login (S4U, tanpa
# menyimpan password). S4U hanya bisa menulis ke folder lokal.
# Nama akun diambil dari identitas Windows, bukan $env:USERDOMAIN: lewat
# SSH variabel itu berisi "WORKGROUP" sehingga akun tidak ditemukan.
$account = [Security.Principal.WindowsIdentity]::GetCurrent().Name
$principal = New-ScheduledTaskPrincipal -UserId $account -LogonType S4U
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 1)

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Principal $principal -Settings $settings -Force | Out-Null

Write-Host "Jadwal '$TaskName' terpasang: setiap hari jam $Time, simpan $Keep backup database terakhir."

# Uji langsung sekali.
Write-Host "Menjalankan backup pertama..."
Start-ScheduledTask -TaskName $TaskName

$deadline = (Get-Date).AddMinutes(2)
do {
    Start-Sleep -Seconds 2
    $state = (Get-ScheduledTask -TaskName $TaskName).State
} while ($state -eq "Running" -and (Get-Date) -lt $deadline)

$result = (Get-ScheduledTaskInfo -TaskName $TaskName).LastTaskResult

if ($result -eq 0) {
    Write-Host "`nBACKUP BERHASIL." -ForegroundColor Green
    Get-Content $log -Tail 1
    Write-Host "Cek folder: $Dest"
} else {
    Write-Host "`nBackup gagal (kode $result). Cek $log" -ForegroundColor Yellow
    if (Test-Path $log) { Get-Content $log -Tail 10 }
}
