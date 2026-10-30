"""Sheet data: Kegiatan GA, Scrap, Site Project, Issue & Action, Onboarding."""

from datetime import date

from flask import Blueprint, flash, redirect, request, url_for

from .. import db
from ..constants import CHECK_DONE, ONBOARD_CHECKS
from ..helpers import audit, form_float, staff_required
from ..models import GAActivity, Issue, Onboard, Scrap, SiteUpdate, get_setting, set_setting
from .crud import Column, Entity, Field, register_crud


today = date.today


# ============================================================
# GENERAL AFFAIR
# ============================================================

ga_bp = Blueprint("ga", __name__, url_prefix="/ga")

GA = Entity(
    key="ga", model=GAActivity, title="Kegiatan GA", icon="bi-tools",
    subtitle="1 baris = 1 kegiatan General Affair",
    fields=[
        Field("date", "Tanggal", "date", required=True, default=today),
        Field("category", "Kategori", "select", kind="ga_category"),
        Field("description", "Uraian kegiatan", "textarea", required=True),
        Field("status", "Status", "select", kind="ga_status", default="Selesai"),
        Field("pic", "PIC", "select", kind="pic", default="GA"),
        Field("cost", "Biaya (Rp)", "money"),
        Field("note", "Keterangan", "text", limit=500),
    ],
    columns=[
        Column("Tanggal", "date", "tgl", "text-nowrap"),
        Column("Kategori", "category"),
        Column("Uraian", "description", css="text-pre"),
        Column("Status", "status", "badge"),
        Column("PIC", "pic"),
        Column("Biaya", "cost", "rupiah", "text-end text-nowrap"),
        Column("Ket.", "note", css="small text-secondary"),
    ],
    order_by=[GAActivity.date.desc(), GAActivity.id.desc()],
    search=["description", "note", "category"],
    status_field="status", status_kind="ga_status", period_default="month",
)
register_crud(ga_bp, GA, staff_required)


# ============================================================
# SCRAP
# ============================================================

scrap_bp = Blueprint("scrap", __name__, url_prefix="/scrap")

SCRAP = Entity(
    key="scrap", model=Scrap, title="Data Scrap", icon="bi-recycle",
    subtitle="Berat scrap per tanggal (kg); rekap mingguan & kumulatif dihitung otomatis",
    fields=[
        Field("date", "Tanggal", "date", required=True, default=today),
        Field("weight_kg", "Berat (kg)", "float", required=True),
        Field("material", "Jenis / material", "select", kind="scrap_material"),
        Field("note", "Keterangan", "text", limit=500),
    ],
    columns=[
        Column("Tanggal", "date", "tgl", "text-nowrap"),
        Column("Berat (kg)", "weight_kg", "kg", "text-end"),
        Column("Jenis / Material", "material"),
        Column("Keterangan", "note", css="small text-secondary"),
    ],
    order_by=[Scrap.date.desc(), Scrap.id.desc()],
    search=["material", "note"],
    list_template="crud/scrap_list.html", period_default="all",
)


def _scrap_extra():
    total = db.session.query(db.func.coalesce(db.func.sum(Scrap.weight_kg), 0)).scalar() or 0
    opening = float(get_setting("scrap_opening_kg", "0") or 0)
    return {"opening": opening, "opening_date": get_setting("scrap_opening_date", ""),
            "total_all": opening + total}


register_crud(scrap_bp, SCRAP, staff_required, list_extra=_scrap_extra)


@scrap_bp.route("/saldo-awal", methods=["POST"])
@staff_required
def opening():
    value = form_float("opening")
    if value is None:
        flash("Saldo awal harus angka.", "danger")
    else:
        set_setting("scrap_opening_kg", value)
        set_setting("scrap_opening_date", request.form.get("opening_date", "").strip())
        audit("setting", None, "update", {"scrap_opening_kg": value})
        db.session.commit()
        flash("Saldo awal kumulatif scrap disimpan.", "success")
    return redirect(url_for("scrap.index"))


# ============================================================
# SITE PROJECT / BRANCH
# ============================================================

site_bp = Blueprint("site", __name__, url_prefix="/site")

SITE = Entity(
    key="site", model=SiteUpdate, title="Update Site", icon="bi-geo-alt",
    subtitle="1 baris per site per minggu; dashboard menampilkan update di minggu laporan",
    fields=[
        Field("date", "Tanggal update", "date", required=True, default=today),
        Field("site", "Site / project", "text", required=True, limit=150),
        Field("location", "Lokasi", "text", limit=100),
        Field("manpower", "Manpower (org)", "int"),
        Field("progress", "Progress (%)", "int"),
        Field("status", "Status", "select", kind="site_status", default="On Track"),
        Field("condition", "Kondisi / update", "textarea"),
        Field("obstacle", "Kendala", "textarea"),
        Field("pic", "PIC", "text", limit=100),
    ],
    columns=[
        Column("Tanggal", "date", "tgl", "text-nowrap"),
        Column("Site / Project", "site", css="fw-semibold"),
        Column("Lokasi", "location"),
        Column("MP", "manpower", css="text-end"),
        Column("Progress", "progress", "pct", "text-end"),
        Column("Status", "status", "badge"),
        Column("Kondisi / Update", "condition", css="text-pre small"),
        Column("Kendala", "obstacle", css="text-pre small"),
        Column("PIC", "pic"),
    ],
    order_by=[SiteUpdate.date.desc(), SiteUpdate.id.desc()],
    search=["site", "location", "condition", "obstacle", "pic"],
    status_field="status", status_kind="site_status", period_default="all",
)
register_crud(site_bp, SITE, staff_required)


# ============================================================
# ISSUE & ACTION PLAN
# ============================================================

issue_bp = Blueprint("issue", __name__, url_prefix="/issue")

ISSUE = Entity(
    key="issue", model=Issue, title="Issue & Action", icon="bi-flag",
    subtitle="1 baris = 1 issue; update status setiap minggu sampai Closed",
    fields=[
        Field("date", "Tanggal", "date", required=True, default=today),
        Field("category", "Kategori", "select", kind="issue_category"),
        Field("issue", "Issue", "textarea", required=True),
        Field("action_plan", "Action plan", "textarea"),
        Field("pic", "PIC", "text", limit=100),
        Field("target_date", "Target date", "date"),
        Field("status", "Status", "select", kind="issue_status", default="Open"),
        Field("closed_date", "Tgl closed", "date",
              help="Diisi otomatis hari ini saat status diubah ke Closed."),
    ],
    columns=[
        Column("Tanggal", "date", "tgl", "text-nowrap"),
        Column("Kategori", "category"),
        Column("Issue", "issue", css="text-pre small"),
        Column("Action Plan", "action_plan", css="text-pre small"),
        Column("PIC", "pic"),
        Column("Target", template="issue_target"),
        Column("Status", "status", "badge"),
    ],
    order_by=[Issue.date.desc(), Issue.id.desc()],
    search=["issue", "action_plan", "pic", "category"],
    status_field="status", status_kind="issue_status", period_default="all",
)


def _issue_after_save(obj, _is_new):
    if obj.is_closed and not obj.closed_date:
        obj.closed_date = date.today()
    if not obj.is_closed:
        obj.closed_date = None


register_crud(issue_bp, ISSUE, staff_required, after_save=_issue_after_save)


# ============================================================
# ONBOARDING
# ============================================================

onboard_bp = Blueprint("onboard", __name__, url_prefix="/onboard")

ONBOARD = Entity(
    key="onboard", model=Onboard, title="Onboarding", icon="bi-person-check",
    subtitle="Karyawan baru dan kelengkapan onboarding",
    fields=[
        Field("name", "Nama", "text", required=True, limit=150),
        Field("position", "Posisi", "text", required=True, limit=150),
        Field("placement", "Placement", "select", kind="placement"),
        Field("hire_date", "Date of hire", "date"),
        Field("phone", "No. HP", "text", limit=50),
        Field("email", "Email", "text", limit=150),
        Field("poh", "POH", "text", limit=150),
        *[Field(name, label, "check") for name, label in ONBOARD_CHECKS],
        Field("status", "Status", "select", choices=["OPEN", "CLOSED"], default="OPEN"),
        Field("note", "Catatan", "text", limit=500),
    ],
    columns=[],
    order_by=[Onboard.hire_date.desc().nulls_last(), Onboard.id.desc()],
    date_field="hire_date",
    search=["name", "position", "placement", "email", "phone"],
    status_field="status", list_template="crud/onboard_list.html",
    form_template="crud/onboard_form.html", period_default="all",
)
register_crud(onboard_bp, ONBOARD, staff_required)


@onboard_bp.route("/<int:obj_id>/cek/<field>", methods=["POST"])
@staff_required
def toggle_check(obj_id, field):
    """Klik ikon checklist di daftar: kosong -> sudah -> tidak perlu -> kosong."""

    if field not in dict(ONBOARD_CHECKS):
        return ("", 404)
    obj = db.session.get(Onboard, obj_id) or None
    if not obj:
        return ("", 404)
    cycle = {"": CHECK_DONE, CHECK_DONE: "-", "-": ""}
    setattr(obj, field, cycle.get(getattr(obj, field) or "", ""))
    db.session.commit()
    done, need = obj.completeness
    return {"value": getattr(obj, field), "done": done, "need": need}
