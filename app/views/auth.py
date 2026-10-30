from datetime import datetime, timedelta

from flask import (
    Blueprint, current_app, flash, redirect, render_template, request, session, url_for,
)
from flask_login import current_user, login_required, login_user, logout_user

from .. import db
from ..helpers import audit
from ..models import User


bp = Blueprint("auth", __name__)


def _safe_next(target):
    # Hanya izinkan redirect ke path internal, bukan URL luar.
    if target and target.startswith("/") and not target.startswith("//"):
        return target
    return None


@bp.route("/login", methods=["GET", "POST"])
def login():

    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":

        # Username disimpan huruf kecil saat user dibuat.
        username = request.form.get("username", "").strip().lower()[:50]
        password = request.form.get("password", "")
        now = datetime.now()

        user = User.query.filter_by(username=username).first()

        if user and user.locked_until and user.locked_until > now:
            minutes = max(1, int((user.locked_until - now).total_seconds() // 60) + 1)
            flash(f"Terlalu banyak percobaan login gagal. Coba lagi dalam {minutes} menit "
                  "atau hubungi IT.", "danger")
            return render_template("login.html"), 429

        if user and user.active and user.check_password(password):
            user.failed_logins = 0
            user.locked_until = None
            user.last_login_at = now
            db.session.commit()
            # Sesi lama dibuang dulu (session fixation).
            session.clear()
            session.permanent = True
            login_user(user)
            return redirect(_safe_next(request.args.get("next")) or url_for("dashboard.index"))

        if user:
            user.failed_logins = (user.failed_logins or 0) + 1
            if user.failed_logins >= current_app.config["LOGIN_MAX_FAILS"]:
                user.locked_until = now + timedelta(minutes=current_app.config["LOGIN_LOCK_MINUTES"])
                user.failed_logins = 0
            db.session.commit()

        # Pesan sengaja sama untuk semua alasan.
        flash("Username atau password salah.", "danger")

    return render_template("login.html")


@bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    session.clear()
    return redirect(url_for("auth.login"))


@bp.route("/password", methods=["GET", "POST"])
@login_required
def change_password():

    if request.method == "POST":

        old = request.form.get("old_password", "")
        new = request.form.get("new_password", "")
        confirm = request.form.get("confirm_password", "")

        if not current_user.check_password(old):
            flash("Password lama salah.", "danger")
        elif len(new) < 8:
            flash("Password baru minimal 8 karakter.", "danger")
        elif new != confirm:
            flash("Konfirmasi password tidak sama.", "danger")
        else:
            current_user.set_password(new)
            audit("user", current_user.id, "change_password")
            db.session.commit()
            flash("Password berhasil diganti.", "success")
            return redirect(url_for("dashboard.index"))

    return render_template("change_password.html")
