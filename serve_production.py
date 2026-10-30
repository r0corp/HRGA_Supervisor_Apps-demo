"""
Menjalankan HRGA Supervisor Apps (Weekly Report HRGA) dengan waitress (server produksi).

Dipasang di PC server yang sama dengan Asset Tracker.
Port yang sudah dipakai: 8000 Asset Tracker, 8100 Remote Tracker,
8200 Legal Contract, 8300 Report Harian. Aplikasi ini port 8400.

Cara pakai:
    python serve_production.py
"""

import os

from waitress import serve

from app import create_app


HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", 8400))

app = create_app()

app.config["DEBUG"] = False


if __name__ == "__main__":

    print(f"HRGA Supervisor Apps berjalan di http://{HOST}:{PORT}")

    serve(app, host=HOST, port=PORT, threads=4)
