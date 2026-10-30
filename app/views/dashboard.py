from datetime import timedelta

from flask import Blueprint, render_template, request

from ..helpers import staff_required
from ..weekly import dashboard_data, recruitment_wa_rows, wa_sections
from ..weeks import (
    MONTHS_EN, default_week, parse_week, week_label, week_number, week_of_month,
    workweek_range_en,
)


bp = Blueprint("dashboard", __name__)


def _week():
    return parse_week(request.args.get("week"), default_week())


def _week_nav(monday):
    return {
        "week": monday,
        "week_label": week_label(monday),
        "prev_week": monday - timedelta(days=7),
        "next_week": monday + timedelta(days=7),
        "this_week": default_week(),
    }


@bp.route("/")
@staff_required
def index():
    monday = _week()
    return render_template("dashboard.html", d=dashboard_data(monday), **_week_nav(monday))


@bp.route("/report-wa")
@staff_required
def wa():
    monday = _week()
    n, month, year = week_of_month(monday)
    sections, _data = wa_sections(monday)
    payload = {
        "title": f"Action Plan Recruitment - Week {n} ({workweek_range_en(monday)}) :",
        "week_title": f"Week {n} - {MONTHS_EN[month - 1]} {year}",
        "recruitment": recruitment_wa_rows(monday),
        "sections": sections,
        "iso_week": week_number(monday),
    }
    return render_template("wa.html", payload=payload, **_week_nav(monday))
