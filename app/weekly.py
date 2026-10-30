"""Perhitungan Dashboard mingguan (pengganti sheet Dashboard Excel) dan
bahan report WA."""

from collections import OrderedDict
from datetime import timedelta

from sqlalchemy import func

from . import db
from .constants import (
    DEFAULT_MOTIVATION_BANK, GA_DONE, ISSUE_CLOSED, REC_HOLD, REC_OPEN, SITE_ATTENTION,
)
from .helpers import options
from .models import (
    GAActivity, HeadcountSnapshot, Issue, Motivation, Onboard, Recruitment,
    RecruitmentUpdate, Scrap, SiteUpdate, get_setting,
)
from .weeks import HARI, short_date, week_number


TREND_WEEKS = 8


def week_bounds(monday):
    return monday, monday + timedelta(days=6)


def scrap_opening():
    try:
        return float(get_setting("scrap_opening_kg", "0") or 0)
    except ValueError:
        return 0.0


def motivation_for(monday):
    row = Motivation.query.filter_by(week_start=monday).first()
    if row:
        return row.text, row.author
    bank = options("motivation_bank") or DEFAULT_MOTIVATION_BANK
    return bank[(week_number(monday) - 1) % len(bank)], None


def latest_headcount(until):
    return (HeadcountSnapshot.query.filter(HeadcountSnapshot.date <= until)
            .order_by(HeadcountSnapshot.date.desc(), HeadcountSnapshot.id.desc()).first())


def dashboard_data(monday):

    start, end = week_bounds(monday)
    in_week = lambda col: col.between(start, end)  # noqa: E731

    # ---------------- Rekrutmen ----------------
    recs = Recruitment.query.all()
    open_recs = [r for r in recs if r.status == REC_OPEN]
    hold_recs = [r for r in recs if r.status == REC_HOLD]

    stages = options("rec_stage")
    for r in recs:
        if r.stage and r.stage not in stages:
            stages.append(r.stage)
    pipeline = [
        (s, sum(1 for r in open_recs if r.stage == s), sum(1 for r in hold_recs if r.stage == s))
        for s in stages
    ]
    pipeline = [p for p in pipeline if p[1] or p[2]] or pipeline

    statuses = options("rec_status")
    status_counts = [(s, sum(1 for r in recs if r.status == s)) for s in statuses]

    joiners = (Onboard.query.filter(in_week(Onboard.hire_date))
               .order_by(Onboard.hire_date, Onboard.id).all())

    new_reqs = sum(1 for r in recs if r.req_date and start <= r.req_date <= end)

    trend = []
    for i in range(TREND_WEEKS - 1, -1, -1):
        w_start = start - timedelta(weeks=i)
        w_end = w_start + timedelta(days=6)
        trend.append({
            "label": f"M{week_number(w_start)}",
            "start": w_start,
            "req": sum(1 for r in recs if r.req_date and w_start <= r.req_date <= w_end),
            "join": Onboard.query.filter(Onboard.hire_date.between(w_start, w_end)).count(),
        })

    oldest = sorted((r for r in open_recs if r.req_date), key=lambda r: r.req_date)[:5]

    # ---------------- Head count ----------------
    headcount = latest_headcount(end)

    # ---------------- GA ----------------
    ga = (GAActivity.query.filter(in_week(GAActivity.date))
          .order_by(GAActivity.date, GAActivity.id).all())
    ga_done = sum(1 for a in ga if a.status == GA_DONE)
    ga_cost = sum(a.cost or 0 for a in ga)

    ga_categories = options("ga_category")
    for a in ga:
        if a.category and a.category not in ga_categories:
            ga_categories.append(a.category)
    ga_by_category = [
        (c, sum(1 for a in ga if a.category == c), sum(a.cost or 0 for a in ga if a.category == c))
        for c in ga_categories
    ]
    ga_by_status = [(s, sum(1 for a in ga if a.status == s)) for s in options("ga_status")]
    ga_by_day = []
    for i in range(7):
        d = start + timedelta(days=i)
        day = [a for a in ga if a.date == d]
        done = sum(1 for a in day if a.status == GA_DONE)
        ga_by_day.append({"hari": HARI[i], "date": d, "count": len(day), "done": done,
                          "open": len(day) - done, "cost": sum(a.cost or 0 for a in day)})

    # ---------------- Scrap ----------------
    opening = scrap_opening()
    before = db.session.query(func.coalesce(func.sum(Scrap.weight_kg), 0)).filter(
        Scrap.date < start).scalar() or 0
    scrap_before = opening + before
    scrap_days = []
    for i in range(7):
        d = start + timedelta(days=i)
        kg = db.session.query(func.coalesce(func.sum(Scrap.weight_kg), 0)).filter(
            Scrap.date == d).scalar() or 0
        scrap_days.append({"hari": HARI[i], "date": d, "kg": kg})
    scrap_week = sum(x["kg"] for x in scrap_days)
    scrap_trend = []
    for i in range(TREND_WEEKS - 1, -1, -1):
        w_start = start - timedelta(weeks=i)
        kg = db.session.query(func.coalesce(func.sum(Scrap.weight_kg), 0)).filter(
            Scrap.date.between(w_start, w_start + timedelta(days=6))).scalar() or 0
        scrap_trend.append({"label": f"M{week_number(w_start)}", "start": w_start, "kg": kg})

    # ---------------- Site ----------------
    sites = (SiteUpdate.query.filter(in_week(SiteUpdate.date))
             .order_by(SiteUpdate.date, SiteUpdate.id).all())
    site_attention = sum(1 for s in sites if s.status in SITE_ATTENTION)

    # ---------------- Issue ----------------
    issues = (Issue.query.filter(
        db.or_(in_week(Issue.date), db.and_(Issue.status != ISSUE_CLOSED, Issue.date <= end)))
        .order_by(Issue.date, Issue.id).all())
    issues_open = Issue.query.filter(Issue.status != ISSUE_CLOSED).count()
    issues_overdue = sum(1 for i in Issue.query.filter(Issue.status != ISSUE_CLOSED) if i.overdue)

    motivation, motivation_author = motivation_for(monday)

    return {
        "start": start, "end": end,
        "kpi": {
            "open": len(open_recs), "hold": len(hold_recs),
            "join": len(joiners), "new_req": new_reqs,
            "headcount": headcount.total("entity") if headcount else None,
            "headcount_date": headcount.date if headcount else None,
            "ga": len(ga), "ga_done": ga_done, "ga_cost": ga_cost,
            "ga_pct": round(ga_done * 100 / len(ga)) if ga else 0,
            "scrap_week": scrap_week, "scrap_total": scrap_before + scrap_week,
            "issues_open": issues_open, "issues_overdue": issues_overdue,
            "site_attention": site_attention, "site_updates": len(sites),
        },
        "pipeline": pipeline, "status_counts": status_counts, "joiners": joiners,
        "trend": trend, "oldest": oldest,
        "headcount": headcount,
        "ga": ga, "ga_by_category": ga_by_category, "ga_by_status": ga_by_status,
        "ga_by_day": ga_by_day,
        "scrap_before": scrap_before, "scrap_days": scrap_days, "scrap_week": scrap_week,
        "scrap_trend": scrap_trend,
        "sites": sites, "issues": issues,
        "motivation": motivation, "motivation_author": motivation_author,
    }


# ============================================================
# REPORT WA
# ============================================================

RECENT_UPDATES = 6


def recruitment_wa_rows(monday):
    """Posisi untuk "Action Plan Recruitment": semua posisi OPEN + posisi
    lain yang punya update di minggu ini. Tiap posisi membawa beberapa
    update terakhir (s.d. akhir minggu); default tercentang = update di
    minggu ini, atau update terakhir kalau minggu ini belum ada."""

    start, end = week_bounds(monday)

    week_ids = {rid for (rid,) in db.session.query(RecruitmentUpdate.recruitment_id)
                .filter(RecruitmentUpdate.date.between(start, end)).distinct()}

    recs = Recruitment.query.filter(
        db.or_(Recruitment.status == REC_OPEN, Recruitment.id.in_(week_ids))).all()
    recs.sort(key=lambda r: (r.wa_order or 0, r.req_date is None, r.req_date or start, r.id))

    rows = []
    for r in recs:
        updates = [u for u in r.updates if u.date is None or u.date <= end][:RECENT_UPDATES]
        # Tampil urut lama -> baru, seperti ditulis di WA.
        updates.sort(key=lambda u: (u.date is not None, u.date or start, u.id))
        in_week = [u for u in updates if u.date and start <= u.date <= end]
        if in_week:
            default = {u.id for u in in_week}
        elif updates:
            dated = [u for u in updates if u.date]
            default = {(dated or updates)[-1].id}
        else:
            default = set()
        rows.append({
            "id": r.id,
            "label": r.label,
            "status": r.status,
            "stage": r.stage,
            "remarks": (r.remarks or "").strip(),
            "updates": [{"id": u.id, "text": u.text.strip(), "date": short_date(u.date),
                         "iso": u.date.isoformat() if u.date else "",
                         "checked": u.id in default, "in_week": u in in_week}
                        for u in updates],
            # Belum ada update sama sekali -> pakai Remarks (tanpa tanggal).
            "use_remarks": not updates and bool((r.remarks or "").strip()),
        })
    return rows


def wa_sections(monday):
    """Bagian lain report WA (selain rekrutmen), sudah berupa baris teks."""

    data = dashboard_data(monday)
    start, end = data["start"], data["end"]
    sections = OrderedDict()

    issues = [i for i in data["issues"] if i.status != ISSUE_CLOSED]
    sections["issue"] = {
        "title": "Issue & Action Plan",
        "lines": [
            f"{i.issue.strip()} : {(i.action_plan or '-').strip()}"
            f"{' (' + i.pic + ')' if i.pic else ''}"
            f"{' - target ' + short_date(i.target_date) if i.target_date else ''}"
            for i in issues
        ],
    }

    sections["ga"] = {
        "title": "General Affair",
        "lines": [
            f"{a.description.strip()} ({short_date(a.date)})"
            f"{' - ' + a.status if a.status and a.status != GA_DONE else ''}"
            for a in data["ga"]
        ],
    }

    sections["join"] = {
        "title": "New Joiner",
        "lines": [f"{o.name} - {o.position}{' (' + o.placement + ')' if o.placement else ''}"
                  f" ({short_date(o.hire_date)})" for o in data["joiners"]],
    }

    sections["site"] = {
        "title": "Site Project / Branch",
        "lines": [
            f"{s.site}{' (' + s.status + ')' if s.status else ''} : {(s.condition or '-').strip()}"
            f"{'; kendala: ' + s.obstacle.strip() if s.obstacle else ''}"
            for s in data["sites"]
        ],
    }

    def kg(value):
        return f"{value:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")

    scrap_lines = [f"{d['hari']} {short_date(d['date'])} : {kg(d['kg'])} kg"
                   for d in data["scrap_days"] if d["kg"]]
    if scrap_lines:
        scrap_lines += [f"Total minggu ini : {kg(data['scrap_week'])} kg",
                        f"Total kumulatif : {kg(data['kpi']['scrap_total'])} kg"]
    sections["scrap"] = {"title": "Scrap", "lines": scrap_lines}

    return sections, data


def used_option_values(kind):
    """Nilai pilihan yang sedang dipakai data (tidak boleh dihapus)."""
    column = {
        "ga_category": GAActivity.category, "ga_status": GAActivity.status,
        "pic": None, "rec_stage": Recruitment.stage, "rec_status": Recruitment.status,
        "placement": Recruitment.placement, "site_status": SiteUpdate.status,
        "issue_category": Issue.category, "issue_status": Issue.status,
        "scrap_material": Scrap.material,
    }.get(kind)
    if column is None:
        return set()
    return {v for (v,) in db.session.query(column).distinct() if v}
