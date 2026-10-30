r"""
Impor template Excel lama ke database (sama dengan menu Impor Excel).

    venv\Scripts\python.exe import_excel.py "Weekly Report HRGA.xlsx" [--replace]

--replace  hapus data yang sudah ada lalu ganti dengan isi Excel.
"""

import argparse
import sys

from app import create_app
from app.excel_import import import_workbook


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("file")
    parser.add_argument("--replace", action="store_true")
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        try:
            summary = import_workbook(args.file, replace=args.replace)
        except ValueError as exc:
            print(f"Impor dibatalkan: {exc}")
            sys.exit(1)
        for key, value in summary.items():
            print(f"  {key}: {value}")
        print("Impor selesai.")


if __name__ == "__main__":
    main()
