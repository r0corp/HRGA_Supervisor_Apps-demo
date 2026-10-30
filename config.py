import os
from datetime import timedelta

from dotenv import load_dotenv


BASE_DIR = os.path.abspath(os.path.dirname(__file__))

load_dotenv(os.path.join(BASE_DIR, ".env"))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY")

    # Nama organisasi di footer & subjudul dashboard; diisi lewat .env
    # supaya tidak tertanam di repo.
    APP_ORG = os.environ.get("APP_ORG", "")

    SQLALCHEMY_DATABASE_URI = (
        os.environ.get("DATABASE_URL")
        or "sqlite:///" + os.path.join(BASE_DIR, "instance", "weekly.db")
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # File Excel lama untuk diimpor (sekali), cukup 20 MB.
    MAX_CONTENT_LENGTH = 20 * 1024 * 1024

    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)

    # Cookie browser tidak dibedakan per port. Di server yang sama ada
    # Asset Tracker (:8000), Remote Tracker (:8100), Legal Contract (:8200)
    # dan Report Harian (:8300); tanpa nama sendiri login saling menimpa.
    SESSION_COOKIE_NAME = "weekly_report_session"
    REMEMBER_COOKIE_NAME = "weekly_report_remember"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"

    # Token CSRF ikut umur sesi; form panjang (report WA) sering dibiarkan
    # terbuka lama sebelum disimpan.
    WTF_CSRF_TIME_LIMIT = None

    # Salah password sebanyak ini -> akun dikunci sementara.
    LOGIN_MAX_FAILS = 5
    LOGIN_LOCK_MINUTES = 15


class TestConfig(Config):
    TESTING = True
    SECRET_KEY = "test"
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    WTF_CSRF_ENABLED = False
