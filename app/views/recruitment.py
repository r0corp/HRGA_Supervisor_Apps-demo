from datetime import date

from flask import Blueprint, abort, flash, redirect, request, url_for

from .. import db
from ..constants import REC_CLOSED
from ..helpers import audit, form_date, form_text, staff_required
from ..models import Recruitment, RecruitmentUpdate
from .crud import Column, Entity, Field, register_crud


bp = Blueprint("recruitment", __name__, url_prefix="/rekrutmen")

REC = Entity(
    key="recruitment", model=Recruitment, title="Posisi", icon="bi-people",
    subtitle="1 baris = 1 permintaan posisi; action plan mingguan dicatat per posisi",
    fields=[
        Field("req_date", "Req. date", "date", default=date.today),
        Field("position", "Position", "text", required=True, limit=150),
        Field("placement", "Placement", "select", kind="placement", default="Head Office"),
        Field("total_candidate", "Total candidate", "int"),
        Field("stage", "Current stage", "select", kind="rec_stage", default="Shortlist"),
        Field("expected_join", "Expected / join date", "date"),
        Field("specification", "Detail specification", "textarea"),
        Field("status", "Status", "select", kind="rec_status", default="OPEN"),
        Field("remarks", "Remarks", "textarea",
              help="Keterangan umum. Dipakai di report WA hanya kalau posisi belum punya action plan."),
        Field("updated_on", "Tgl update terakhir", "date", default=date.today),
        Field("wa_label", "Nama di report WA", "text", limit=150,
              help='Kosongkan = sama dengan Position. Contoh: "Site Coordinator (Sinar Mas Project)".'),
        Field("wa_order", "Urutan di report WA", "int", default=0,
              help="Angka kecil tampil lebih dulu; sama = urut Req. date."),
    ],
    columns=[],
    order_by=[Recruitment.req_date.desc().nulls_last(), Recruitment.id.desc()],
    date_field="req_date",
    search=["position", "placement", "remarks", "specification", "wa_label"],
    status_field="status", status_kind="rec_status",
    list_template="recruitment/list.html", form_template="recruitment/form.html",
)


def _after_save(obj, _is_new):
    if obj.wa_order is None:
        obj.wa_order = 0
    if obj.status == REC_CLOSED and not obj.closed_on:
        obj.closed_on = date.today()
    elif obj.status != REC_CLOSED:
        obj.closed_on = None


register_crud(bp, REC, staff_required, after_save=_after_save)


def _back(rec):
    return request.form.get("next") or url_for("recruitment.edit", obj_id=rec.id)


@bp.route("/<int:obj_id>/update", methods=["POST"])
@staff_required
def add_update(obj_id):
    """Tambah action plan / progres posisi (dari daftar, form, atau halaman Report WA)."""

    rec = db.session.get(Recruitment, obj_id) or abort(404)
    text = form_text("text", 1000)
    if not text:
        flash("Isi action plan kosong.", "danger")
        return redirect(_back(rec))

    when = form_date("date") if request.form.get("date") else None
    upd = RecruitmentUpdate(recruitment=rec, date=when, text=text)
    db.session.add(upd)
    rec.updated_on = date.today()

    stage = form_text("stage", 50)
    if stage:
        rec.stage = stage
    db.session.flush()
    audit("recruitment_update", upd.id, "create", {"recruitment": rec.id, "text": text})
    db.session.commit()
    flash(f"Action plan {rec.label} ditambahkan.", "success")
    return redirect(_back(rec))


@bp.route("/update/<int:upd_id>", methods=["POST"])
@staff_required
def edit_update(upd_id):
    upd = db.session.get(RecruitmentUpdate, upd_id) or abort(404)
    text = form_text("text", 1000)
    if not text:
        flash("Isi action plan kosong.", "danger")
    else:
        upd.text = text
        upd.date = form_date("date") if request.form.get("date") else None
        audit("recruitment_update", upd.id, "update", {"text": text})
        db.session.commit()
        flash("Action plan disimpan.", "success")
    return redirect(_back(upd.recruitment))


@bp.route("/update/<int:upd_id>/hapus", methods=["POST"])
@staff_required
def delete_update(upd_id):
    upd = db.session.get(RecruitmentUpdate, upd_id) or abort(404)
    rec = upd.recruitment
    audit("recruitment_update", upd.id, "delete", {"text": upd.text})
    db.session.delete(upd)
    db.session.commit()
    flash("Action plan dihapus.", "success")
    return redirect(_back(rec))
