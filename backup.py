"""
Backup Weekly Report HRGA.

    python backup.py --dest "<folder tujuan>" [--keep 30]

Database: snapshot konsisten lewat SQLite backup API (aman walau
aplikasi sedang dipakai), di-zip jadi <dest>\\database\\weekly-YYYYMMDD-HHMMSS.zip.
Hanya `keep` file terbaru yang disimpan.

Restore: stop service, extract zip terbaru -> instance\\weekly.db, start service.
"""

import argparse
import os
import sqlite3
import sys
import tempfile
import traceback
import zipfile
from datetime import datetime


BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "instance", "weekly.db")
LOG_PATH = os.path.join(BASE_DIR, "logs", "backup.log")


def log(message):
    """Tulis ke layar dan ke logs\\backup.log (Task Scheduler tidak punya layar)."""

    line = f"{datetime.now():%Y-%m-%d %H:%M:%S} {message}"
    print(line)
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def snapshot_database(dest_dir, stamp):

    os.makedirs(dest_dir, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        snap = os.path.join(tmp, "weekly.db")

        src = sqlite3.connect(DB_PATH)
        dst = sqlite3.connect(snap)
        with dst:
            src.backup(dst)
        dst.close()
        src.close()

        # Tulis ke nama sementara dulu supaya OneDrive tidak mengunggah
        # zip yang belum selesai ditulis.
        final = os.path.join(dest_dir, f"weekly-{stamp}.zip")
        partial = final + ".partial"
        with zipfile.ZipFile(partial, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(snap, "weekly.db")
        os.replace(partial, final)

    return final


def prune(dest_dir, keep):

    files = sorted(
        f for f in os.listdir(dest_dir)
        if f.startswith("weekly-") and f.endswith(".zip")
    )
    removed = files[:-keep] if keep > 0 else []
    for f in removed:
        os.remove(os.path.join(dest_dir, f))
    return removed


def run(dest, keep):

    if not os.path.exists(DB_PATH):
        raise RuntimeError(f"Database tidak ditemukan: {DB_PATH}")

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    db_dir = os.path.join(dest, "database")

    db_zip = snapshot_database(db_dir, stamp)
    removed = prune(db_dir, keep)

    log(f"OK database={os.path.basename(db_zip)} zip_lama_dihapus={len(removed)}")


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("--dest", required=True)
    parser.add_argument("--keep", type=int, default=30)
    args = parser.parse_args()

    try:
        run(args.dest, args.keep)
    except Exception:
        log("GAGAL\n" + traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
