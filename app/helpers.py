import json
from datetime import date, datetime
from functools import wraps

from flask import abort, request
from flask_login import current_user, login_required

from . import db
from .constants import ROLE_ADMIN, ROLE_SPV
from .models import AuditLog, Option
from .weeks import format_date, short_date


def role_required(*roles):
    """Hanya IT (admin) dan Spv HRGA yang boleh membuka aplikasi ini;
    admin selalu lolos."""

    def decorator(view):
        @wraps(view)
        @login_required
        def wrapper(*args, **kwargs):
            if current_user.role != ROLE_ADMIN and current_user.role not in roles:
                abort(403)
            return view(*args, **kwargs)
        return wrapper
    return decorator


staff_required = role_required(ROLE_SPV)
admin_required = role_required()


def options(kind):
    return [o.value for o in Option.query.filter_by(kind=kind).order_by(Option.sort, Option.id)]


def audit(entity, entity_id, action, detail=None):
    db.session.add(AuditLog(
        user_id=current_user.id if current_user.is_authenticated else None,
        entity=entity, entity_id=entity_id, action=action,
        detail=json.dumps(detail, ensure_ascii=False, default=str) if detail else None,
    ))


# ------------------------------------------------------------
# Baca isian form
# ------------------------------------------------------------

def form_text(name, limit=None):
    value = (request.form.get(name) or "").strip()
    return value[:limit] if limit else value


def form_date(name):
    try:
        return date.fromisoformat(request.form.get(name, "").strip())
    except ValueError:
        return None


def form_int(name):
    text = (request.form.get(name) or "").strip().replace(".", "").replace(",", "")
    try:
        return int(text)
    except ValueError:
        return None


def form_float(name):
    text = (request.form.get(name) or "").strip().replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return None


# ------------------------------------------------------------
# Filter template
# ------------------------------------------------------------

def rupiah(value):
    if value in (None, ""):
        return ""
    return "Rp " + f"{int(value):,}".replace(",", ".")


def number(value, decimals=0):
    if value in (None, ""):
        return ""
    text = f"{value:,.{decimals}f}"
    # 1,234.56 -> 1.234,56
    return text.replace(",", "_").replace(".", ",").replace("_", ".")


def register_template_helpers(app):

    from . import constants as C

    @app.context_processor
    def template_globals():
        return {"now": datetime.now, "C": C, "options": options}

    app.add_template_filter(lambda v: format_date(v), "tgl")
    app.add_template_filter(lambda v: format_date(v, with_day=True), "tgl_hari")
    app.add_template_filter(short_date, "tgl_pendek")
    app.add_template_filter(rupiah, "rupiah")
    app.add_template_filter(number, "angka")
