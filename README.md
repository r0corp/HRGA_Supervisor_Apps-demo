# HRGA Supervisor Apps (Weekly Report HRGA)

> Versi demo untuk portofolio: seluruh data, nama, alamat server, dan logo di repo ini adalah contoh.

Pengganti template Excel "Weekly Report HRGA.xlsx" milik Supervisor HRGA:
data rekrutmen, onboarding, head count, kegiatan GA, scrap, site project, dan
issue & action plan diisi di aplikasi; dashboard mingguan dihitung otomatis dan
halaman **Report WA** menyusun teks "Action Plan Recruitment - Week n" siap salin
ke WhatsApp.

- Server: `http://<IP-SERVER>:8400` (service Windows `HRGA_Supervisor_Apps`, backup terjadwal `HRGA_Supervisor_Apps Backup`)
- Stack: Flask + SQLite + waitress, tampilan Legal Contract (header kartu & tabel hitam)
- Database: `instance\weekly.db`

## Akses

Hanya dua peran: **Administrator (IT)** dan **Supervisor HRGA**. Admin bisa semua,
plus menu User, Impor Excel, Audit Log. Salah password 5x -> akun terkunci 15 menit.

## Minggu laporan

Senin-Minggu. Default sama dengan Excel lama (`TODAY()-3` mundur ke Senin): Senin-Rabu
masih menampilkan minggu lalu. Judul WA memakai minggu ke-n dalam bulan, ikut bulan
hari Kamis-nya (Senin 5 Okt 2026 = October Week 2).

## Report WA

Tiap posisi rekrutmen punya daftar **action plan** (tanggal + teks), dicatat lewat tombol
(+) di daftar Rekrutmen atau langsung di halaman Report WA. Yang masuk report: semua posisi
OPEN + posisi lain yang punya action plan minggu itu. Default tercentang = action plan di
minggu itu, kalau belum ada pakai yang terakhir; posisi tanpa action plan memakai Remarks.
Centang bisa diubah, teks bisa diedit sebelum disalin.

## Instalasi pertama di server

1. Di laptop dev: `powershell -ExecutionPolicy Bypass -File .\package_server.ps1 -Excel "<path Weekly Report HRGA.xlsx>"`
2. Extract `dist\HRGA_Supervisor_Apps-server.zip` ke `C:\Users\<user>\HRGA_Supervisor_Apps`.
3. PowerShell **Run as Administrator** di server:
   ```
   Set-Location C:\Users\<user>\HRGA_Supervisor_Apps
   powershell -ExecutionPolicy Bypass -File .\setup_server.ps1
   ```
   Catat password `it` dan `spv.hrga` yang tampil sekali di layar.
   Nama organisasi di footer & dashboard diisi lewat `APP_ORG=...` di `.env`
   (kosong = tidak ditampilkan).
4. Backup harian: `powershell -ExecutionPolicy Bypass -File .\install_backup_task.ps1`

Setup tidak menyentuh aplikasi lain di server dan berhenti kalau port 8400 sudah dipakai.

## Update

Siapkan file yang berubah di folder `update\` (struktur sama), lalu di server
(Run as Administrator): `powershell -ExecutionPolicy Bypass -File .\update_server.ps1`.
Database di-backup otomatis; `.env`, `instance\`, `venv\`, `logs\` tidak disentuh.

## Development

```
venv\Scripts\python.exe run.py          # http://127.0.0.1:8400
venv\Scripts\python.exe -m pytest -q
```
