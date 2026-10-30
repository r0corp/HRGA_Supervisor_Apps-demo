"""CRUD generik untuk sheet data (GA, Scrap, Site, Issue, Onboard, Rekrutmen).

Tiap entitas didefinisikan lewat daftar Field; form dan tabel daftar
dirender dari definisi yang sama (templates/crud/*.html)."""

from dataclasses import dataclass, field
from datetime import date, timedelta

from flask import abort, flash, redirect, render_template, request, url_for

from .. import db
from ..helpers import audit, form_date, form_float, form_int, form_text, options
from ..weeks import monday_of, parse_week


@dataclass
class Field:
    name: str
    label: str
    type: str = "text"          # text, textarea, date, int, float, money, select, check
    required: bool = False
    kind: str = None            # jenis Option untuk type="select"
    choices: list = None        # pilihan tetap untuk type="select"
    help: str = ""
    limit: int = None
    default: object = None
    wide: bool = False          # textarea lebar penuh


@dataclass
class Column:
    label: str
    attr: str = None
    fmt: str = None             # tgl, rupiah, angka, badge, pct, kg
    css: str = ""
    template: str = None        # potongan template khusus


@dataclass
class Entity:
    key: str                    # nama blueprint, mis. "ga"
    model: type
    title: str                  # "Kegiatan GA"
    icon: str
    fields: list
    columns: list
    order_by: list
    date_field: str = "date"    # untuk filter minggu/bulan
    search: list = field(default_factory=list)
    status_field: str = None
    status_kind: str = None
    subtitle: str = ""
    list_template: str = "crud/list.html"
    form_template: str = "crud/form.html"
    period_default: str = "all"     # "week", "month", "all"
    per_page: int = 100


def _parse_month(text):
    try:
        y, m = text.split("-")
        return date(int(y), int(m), 1)
    except (AttributeError, ValueError):
        return None


def list_view(entity, extra=None):

    q = entity.model.query
    args = request.args
    period = args.get("period") or entity.period_default
    date_col = getattr(entity.model, entity.date_field) if entity.date_field else None

    week = parse_week(args.get("week"), monday_of(date.today()))
    month = _parse_month(args.get("month")) or date.today().replace(day=1)

    if date_col is not None and period == "week":
        q = q.filter(date_col.between(week, week + timedelta(days=6)))
    elif date_col is not None and period == "month":
        nxt = (month.replace(day=28) + timedelta(days=4)).replace(day=1)
        q = q.filter(date_col >= month, date_col < nxt)

    status = args.get("status", "")
    if entity.status_field and status:
        q = q.filter(getattr(entity.model, entity.status_field) == status)

    term = args.get("q", "").strip()
    if term and entity.search:
        like = f"%{term}%"
        q = q.filter(db.or_(*[getattr(entity.model, f).ilike(like) for f in entity.search]))

    rows = q.order_by(*entity.order_by).all()

    return render_template(
        entity.list_template, e=entity, rows=rows, period=period, week=week, month=month,
        status=status, term=term,
        statuses=options(entity.status_kind) if entity.status_kind else [],
        **(extra or {}),
    )


def fill(obj, entity):
    """Isi objek dari request.form. Kembalikan pesan error atau None."""

    for f in entity.fields:
        if f.type == "date":
            value = form_date(f.name)
        elif f.type in ("int", "money"):
            value = form_int(f.name)
            if f.type == "money" and value is None:
                value = 0
        elif f.type == "float":
            value = form_float(f.name)
        elif f.type == "check":
            value = request.form.get(f.name, "")
            value = value if value in ("v", "-") else ""
        else:
            value = form_text(f.name, f.limit) or None

        if f.required and value in (None, ""):
            return f"{f.label} wajib diisi."
        setattr(obj, f.name, value)
    return None


def form_view(entity, obj=None, after_save=None, extra=None):

    is_new = obj is None
    if is_new:
        obj = entity.model()
        for f in entity.fields:
            default = f.default() if callable(f.default) else f.default
            if default is not None:
                setattr(obj, f.name, default)

    if request.method == "POST":
        error = fill(obj, entity)
        if error:
            flash(error, "danger")
        else:
            if is_new:
                db.session.add(obj)
            db.session.flush()
            if after_save:
                after_save(obj, is_new)
            audit(entity.key, obj.id, "create" if is_new else "update")
            db.session.commit()
            flash(f"{entity.title} {'ditambahkan' if is_new else 'disimpan'}.", "success")
            if request.form.get("again"):
                return redirect(url_for(f"{entity.key}.new"))
            return redirect(request.args.get("next") or url_for(f"{entity.key}.index"))

    return render_template(entity.form_template, e=entity, obj=obj, is_new=is_new,
                           **(extra or {}))


def delete_view(entity, obj_id):
    obj = db.session.get(entity.model, obj_id) or abort(404)
    audit(entity.key, obj.id, "delete")
    db.session.delete(obj)
    db.session.commit()
    flash(f"{entity.title} dihapus.", "success")
    return redirect(request.args.get("next") or url_for(f"{entity.key}.index"))


def register_crud(bp, entity, guard, list_extra=None, form_extra=None, after_save=None):
    """Pasang route index/new/edit/delete standar ke blueprint."""

    @bp.route("/")
    @guard
    def index():
        return list_view(entity, list_extra() if list_extra else None)

    @bp.route("/baru", methods=["GET", "POST"])
    @guard
    def new():
        return form_view(entity, after_save=after_save,
                         extra=form_extra(None) if form_extra else None)

    @bp.route("/<int:obj_id>", methods=["GET", "POST"])
    @guard
    def edit(obj_id):
        obj = db.session.get(entity.model, obj_id) or abort(404)
        return form_view(entity, obj, after_save=after_save,
                         extra=form_extra(obj) if form_extra else None)

    @bp.route("/<int:obj_id>/hapus", methods=["POST"])
    @guard
    def delete(obj_id):
        return delete_view(entity, obj_id)
