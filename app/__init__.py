import os

from flask import Flask, render_template
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect


db = SQLAlchemy()

login_manager = LoginManager()

csrf = CSRFProtect()


def create_app(config_object="config.Config"):

    app = Flask(__name__)

    app.config.from_object(config_object)

    if not app.config.get("SECRET_KEY"):
        raise RuntimeError(
            "SECRET_KEY belum diset. Buat file .env berisi "
            "SECRET_KEY=<hasil generate>, misalnya lewat:\n"
            "  python -c \"import secrets; print(secrets.token_hex(32))\""
        )

    os.makedirs(app.instance_path, exist_ok=True)

    db.init_app(app)

    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Silakan login terlebih dahulu."
    login_manager.login_message_category = "warning"

    csrf.init_app(app)

    from . import models  # noqa: F401  (daftarkan tabel)
    from .views import register_views

    register_views(app)

    from .helpers import register_template_helpers

    register_template_helpers(app)

    @app.errorhandler(403)
    def forbidden(_e):
        return render_template("error.html", code=403,
                               message="Anda tidak punya akses ke halaman ini."), 403

    @app.errorhandler(404)
    def not_found(_e):
        return render_template("error.html", code=404,
                               message="Halaman atau data tidak ditemukan."), 404

    @app.errorhandler(413)
    def too_large(_e):
        return render_template("error.html", code=413,
                               message="File terlalu besar (maksimal 20 MB)."), 413

    @app.after_request
    def harden(response):
        h = response.headers
        h.setdefault("X-Frame-Options", "DENY")
        h.setdefault("X-Content-Type-Options", "nosniff")
        h.setdefault("Referrer-Policy", "same-origin")
        # Data karyawan jangan tersimpan di cache browser (PC bersama /
        # tombol Back setelah logout).
        if response.mimetype == "text/html":
            h["Cache-Control"] = "no-store"
        return response

    with app.app_context():
        db.create_all()
        add_missing_columns()
        seed_options()

    return app


def seed_options():
    """Isi daftar pilihan bawaan kalau jenisnya masih kosong."""

    from .constants import DEFAULT_OPTIONS
    from .models import Option

    existing = {kind for (kind,) in db.session.query(Option.kind).distinct()}
    added = False
    for kind, values in DEFAULT_OPTIONS.items():
        if kind in existing:
            continue
        for i, value in enumerate(values):
            db.session.add(Option(kind=kind, value=value, sort=i))
        added = True
    if added:
        db.session.commit()


def add_missing_columns():
    """
    create_all() hanya membuat tabel baru, tidak menambah kolom ke tabel
    yang sudah ada. Kolom baru (yang boleh kosong) ditambahkan di sini
    lewat ALTER TABLE, supaya update di server cukup lewat
    update_server.ps1 tanpa migrasi manual.
    """

    from sqlalchemy import inspect, text

    inspector = inspect(db.engine)
    added = []

    for table in db.metadata.sorted_tables:
        existing = {c["name"] for c in inspector.get_columns(table.name)}
        for column in table.columns:
            if column.name in existing:
                continue
            if not column.nullable:
                raise RuntimeError(
                    f"Kolom wajib baru {table.name}.{column.name} butuh migrasi manual."
                )
            ddl = column.type.compile(db.engine.dialect)
            db.session.execute(
                text(f'ALTER TABLE "{table.name}" ADD COLUMN "{column.name}" {ddl}')
            )
            added.append(f"{table.name}.{column.name}")

    if added:
        db.session.commit()
        print("Kolom baru ditambahkan:", ", ".join(added))


@login_manager.user_loader
def load_user(user_id):

    from .models import User

    user = db.session.get(User, int(user_id))

    return user if user and user.active else None
