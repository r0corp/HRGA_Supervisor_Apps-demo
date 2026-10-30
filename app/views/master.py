import secrets
from datetime import date, datetime

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user

from .. import db
from ..constants import (
    HEADCOUNT_GROUPS, LOCKED_OPTIONS, OPTION_KINDS, ROLE_ADMIN, ROLES,
)
from ..excel_import import existing_counts, import_workbook
from ..helpers import admin_required, audit, form_date, form_text, staff_required
from ..models import AuditLog, HeadcountSnapshot, Motivation, Option, User
from ..weekly import latest_headcount, used_option_values
from ..weeks import default_week, monday_of, week_number


bp = Blueprint("master", __name__)


# ============================================================
# DAFTAR PILIHAN
# ============================================================

@bp.route("/pilihan")
@staff_required
def option_list():
    kind = request.args.get("kind") if request.args.get("kind") in OPTION_KINDS else "ga_category"
    rows = Option.query.filter_by(kind=kind).order_by(Option.sort, Option.id).all()
    return render_template("master/options.html", kind=kind, rows=rows,
                           used=used_option_values(kind), locked=LOCKED_OPTIONS.get(kind, []))


@bp.route("/pilihan/simpan", methods=["POST"])
@staff_required
def option_save():
    kind = request.form.get("kind")
    if kind not in OPTION_KINDS and kind != "motivation_bank":
        abort(400)
    back = url_for("master.motivation") if kind == "motivation_bank" else \
        url_for("master.option_list", kind=kind)

    action = request.form.get("action")
    opt = db.session.get(Option, request.form.get("id", type=int) or 0)
    if opt and opt.kind != kind:
        abort(400)

    if action == "add":
        value = form_text("value", 500)
        if not value:
            flash("Isi pilihan kosong.", "danger")
        elif Option.query.filter_by(kind=kind, value=value).first():
            flash(f'"{value}" sudah ada.', "warning")
        else:
            last = db.session.query(db.func.max(Option.sort)).filter_by(kind=kind).scalar() or 0
            db.session.add(Option(kind=kind, value=value, sort=last + 1))
            audit("option", None, "create", {"kind": kind, "value": value})
            db.session.commit()
            flash(f'"{value}" ditambahkan.', "success")

    elif action == "rename" and opt:
        value = form_text("value", 500)
        if opt.value in LOCKED_OPTIONS.get(kind, []):
            flash(f'"{opt.value}" dipakai perhitungan dashboard, tidak bisa diubah.', "warning")
        elif value and value != opt.value:
            if Option.query.filter_by(kind=kind, value=value).first():
                flash(f'"{value}" sudah ada.', "warning")
            else:
                audit("option", opt.id, "update", {"old": opt.value, "new": value})
                opt.value = value
                db.session.commit()
                flash("Pilihan diubah. Data lama tetap memakai nama lama.", "success")

    elif action == "delete" and opt:
        if opt.value in LOCKED_OPTIONS.get(kind, []):
            flash(f'"{opt.value}" dipakai perhitungan dashboard, tidak bisa dihapus.', "warning")
        else:
            audit("option", opt.id, "delete", {"kind": kind, "value": opt.value})
            db.session.delete(opt)
            db.session.commit()
            flash("Pilihan dihapus (data lama yang memakainya tidak berubah).", "success")

    elif action in ("up", "down") and opt:
        rows = Option.query.filter_by(kind=kind).order_by(Option.sort, Option.id).all()
        i = rows.index(opt)
        j = i - 1 if action == "up" else i + 1
        if 0 <= j < len(rows):
            rows[i], rows[j] = rows[j], rows[i]
            for n, row in enumerate(rows):
                row.sort = n
            db.session.commit()

    return redirect(back)


# ============================================================
# MOTIVASI
# ============================================================

@bp.route("/motivasi", methods=["GET", "POST"])
@staff_required
def motivation():
    if request.method == "POST":
        week = form_date("week_start")
        text = form_text("text", 1000)
        if not week:
            flash("Pilih minggu.", "danger")
        else:
            week = monday_of(week)
            row = Motivation.query.filter_by(week_start=week).first()
            if not text:
                if row:
                    db.session.delete(row)
                    db.session.commit()
                    flash("Motivasi khusus minggu itu dihapus; kembali memakai bank.", "success")
            else:
                if not row:
                    row = Motivation(week_start=week)
                    db.session.add(row)
                row.text = text.strip('"“”')
                row.author = form_text("author", 100) or None
                audit("motivation", None, "update", {"week": week, "text": text})
                db.session.commit()
                flash("Motivasi minggu ini disimpan.", "success")
        return redirect(url_for("master.motivation"))

    rows = Motivation.query.order_by(Motivation.week_start.desc()).limit(30).all()
    bank = Option.query.filter_by(kind="motivation_bank").order_by(Option.sort, Option.id).all()
    week = default_week()
    current = None
    if bank:
        current = bank[(week_number(week) - 1) % len(bank)].id
    return render_template("master/motivation.html", rows=rows, bank=bank, week=week,
                           current=current)


# ============================================================
# HEAD COUNT
# ============================================================

@bp.route("/headcount")
@staff_required
def headcount():
    snaps = HeadcountSnapshot.query.order_by(HeadcountSnapshot.date.desc(),
                                             HeadcountSnapshot.id.desc()).all()
    return render_template("master/headcount.html", snaps=snaps, latest=snaps[0] if snaps else None)


def _headcount_from_form():
    data = {}
    for group, _label in HEADCOUNT_GROUPS:
        names = request.form.getlist(f"{group}_name")
        counts = request.form.getlist(f"{group}_count")
        rows = []
        for name, count in zip(names, counts):
            name = name.strip()[:100]
            if not name:
                continue
            try:
                value = int(count.strip() or 0)
            except ValueError:
                value = 0
            rows.append([name, value])
        data[group] = rows
    return data


@bp.route("/headcount/baru", methods=["GET", "POST"])
@bp.route("/headcount/<int:snap_id>", methods=["GET", "POST"])
@staff_required
def headcount_form(snap_id=None):
    snap = db.session.get(HeadcountSnapshot, snap_id) if snap_id else None
    if snap_id and not snap:
        abort(404)

    if request.method == "POST":
        when = form_date("date")
        if not when:
            flash("Tanggal update wajib diisi.", "danger")
        else:
            is_new = snap is None
            if is_new:
                snap = HeadcountSnapshot()
                db.session.add(snap)
            snap.date = when
            snap.note = form_text("note", 500) or None
            snap.data = _headcount_from_form()
            db.session.flush()
            audit("headcount", snap.id, "create" if is_new else "update")
            db.session.commit()
            flash("Head count disimpan.", "success")
            return redirect(url_for("master.headcount"))

    # Snapshot baru diisi dari yang terakhir supaya cukup ubah angka yang berubah.
    base = snap or latest_headcount(date.max)
    return render_template("master/headcount_form.html", snap=snap, base=base,
                           today=date.today())


@bp.route("/headcount/<int:snap_id>/hapus", methods=["POST"])
@staff_required
def headcount_delete(snap_id):
    snap = db.session.get(HeadcountSnapshot, snap_id) or abort(404)
    audit("headcount", snap.id, "delete", {"date": snap.date})
    db.session.delete(snap)
    db.session.commit()
    flash("Snapshot head count dihapus.", "success")
    return redirect(url_for("master.headcount"))


# ============================================================
# USER (admin / IT)
# ============================================================

def _new_password():
    return secrets.token_urlsafe(9)


@bp.route("/user", methods=["GET", "POST"])
@admin_required
def users():
    if request.method == "POST":
        action = request.form.get("action")
        user = db.session.get(User, request.form.get("id", type=int) or 0)

        if action == "create":
            username = form_text("username", 50).lower()
            name = form_text("name", 100)
            role = request.form.get("role")
            if not username or not name or role not in ROLES:
                flash("Username, nama, dan peran wajib diisi.", "danger")
            elif User.query.filter_by(username=username).first():
                flash("Username sudah dipakai.", "danger")
            else:
                password = _new_password()
                user = User(username=username, name=name, role=role)
                user.set_password(password)
                db.session.add(user)
                db.session.flush()
                audit("user", user.id, "create", {"username": username, "role": role})
                db.session.commit()
                flash(f"User {username} dibuat. Password awal: {password} "
                      "(tampil sekali, minta user segera menggantinya).", "success")

        elif user and action == "reset":
            password = _new_password()
            user.set_password(password)
            user.failed_logins = 0
            user.locked_until = None
            audit("user", user.id, "reset_password")
            db.session.commit()
            flash(f"Password {user.username} direset: {password} (tampil sekali).", "success")

        elif user and action == "toggle":
            if user.id == current_user.id:
                flash("Tidak bisa menonaktifkan akun sendiri.", "warning")
            else:
                user.active = not user.active
                audit("user", user.id, "activate" if user.active else "deactivate")
                db.session.commit()
                flash(f"{user.username} {'diaktifkan' if user.active else 'dinonaktifkan'}.",
                      "success")

        elif user and action == "update":
            name = form_text("name", 100)
            role = request.form.get("role")
            if user.id == current_user.id and role != ROLE_ADMIN:
                flash("Tidak bisa menurunkan peran akun sendiri.", "warning")
            elif name and role in ROLES:
                user.name = name
                user.role = role
                audit("user", user.id, "update", {"name": name, "role": role})
                db.session.commit()
                flash("User disimpan.", "success")

        elif user and action == "unlock":
            user.failed_logins = 0
            user.locked_until = None
            db.session.commit()
            flash(f"Kunci login {user.username} dibuka.", "success")

        return redirect(url_for("master.users"))

    rows = User.query.order_by(User.role, User.name).all()
    return render_template("master/users.html", rows=rows, roles=ROLES, now_dt=datetime.now())


# ============================================================
# IMPOR EXCEL (admin)
# ============================================================

@bp.route("/impor", methods=["GET", "POST"])
@admin_required
def import_excel():
    if request.method == "POST":
        file = request.files.get("file")
        if not file or not file.filename.lower().endswith((".xlsx", ".xlsm")):
            flash("Pilih file Excel (.xlsx).", "danger")
        else:
            try:
                summary = import_workbook(file, replace=bool(request.form.get("replace")))
            except ValueError as exc:
                db.session.rollback()
                flash(str(exc), "danger")
            except Exception as exc:  # noqa: BLE001 - file rusak/format lain
                db.session.rollback()
                flash(f"Gagal membaca file: {exc}", "danger")
            else:
                audit("import", None, "create", summary)
                db.session.commit()
                flash("Impor selesai: " + ", ".join(f"{k} {v}" for k, v in summary.items()),
                      "success")
                return redirect(url_for("dashboard.index"))
    return render_template("master/import.html", counts=existing_counts())


# ============================================================
# AUDIT LOG (admin)
# ============================================================

@bp.route("/audit")
@admin_required
def audit_log():
    rows = AuditLog.query.order_by(AuditLog.at.desc()).limit(300).all()
    return render_template("master/audit.html", rows=rows)
