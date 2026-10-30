"""Impor template Excel lama "Weekly Report HRGA.xlsx" ke database.

Dipakai dari menu Impor Excel (admin) dan dari baris perintah:
    venv\\Scripts\\python.exe import_excel.py "Weekly Report HRGA.xlsx" [--replace]
"""

from datetime import date, datetime

import openpyxl

from . import db
from .constants import CHECK_DONE, CHECK_NA, ONBOARD_CHECKS
from .models import (
    GAActivity, HeadcountSnapshot, Issue, Motivation, Onboard, Option, Recruitment,
    RecruitmentUpdate, Scrap, SiteUpdate, set_setting,
)
from .weeks import monday_of


DATA_MODELS = [RecruitmentUpdate, Recruitment, Onboard, HeadcountSnapshot, GAActivity, Scrap,
               SiteUpdate, Issue, Motivation]

# Kolom sheet "Daftar" -> jenis pilihan.
DAFTAR_KINDS = ["ga_category", "ga_status", "pic", "rec_stage", "rec_status", "placement",
                "site_status", "issue_category", "issue_status"]


def _text(value, limit=None):
    if value is None:
        return None
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    text = str(value).replace("⁠", "").strip()
    if not text:
        return None
    return text[:limit] if limit else text


def _date(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d/%m/%y", "%d-%m-%Y"):
            try:
                return datetime.strptime(value.strip(), fmt).date()
            except ValueError:
                pass
    return None


def _int(value):
    try:
        return int(round(float(value)))
    except (TypeError, ValueError):
        return None


def _float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _check(value):
    text = _text(value) or ""
    if text in ("√", "v", "V", "✓", "x", "X"):
        return CHECK_DONE
    if text == "-":
        return CHECK_NA
    return ""


def _rows(ws, first_row):
    for row in ws.iter_rows(min_row=first_row, values_only=True):
        yield row


def existing_counts():
    return {m.__tablename__: m.query.count() for m in DATA_MODELS}


def import_workbook(path_or_file, replace=False):
    """Kembalikan dict ringkasan jumlah baris yang diimpor."""

    # data_only: ambil hasil rumus yang tersimpan Excel (Headcount berisi
    # rumus seperti =58+1).
    wb = openpyxl.load_workbook(path_or_file, data_only=True)
    names = set(wb.sheetnames)
    missing = {"Rekrutmen", "GA", "Issue & Action"} - names
    if missing:
        raise ValueError("Bukan template Weekly Report HRGA (sheet tidak ada: "
                         + ", ".join(sorted(missing)) + ").")

    if replace:
        for model in DATA_MODELS:
            model.query.delete()
    elif any(existing_counts().values()):
        raise ValueError("Database sudah berisi data. Centang 'ganti data yang ada' "
                         "untuk menimpa.")

    summary = {}

    # ---------- Daftar pilihan ----------
    if "Daftar" in names:
        ws = wb["Daftar"]
        added = 0
        for col, kind in enumerate(DAFTAR_KINDS):
            have = {o.value for o in Option.query.filter_by(kind=kind)}
            sort = len(have)
            for row in _rows(ws, 4):
                value = _text(row[col] if col < len(row) else None, 100)
                if value and value not in have:
                    db.session.add(Option(kind=kind, value=value, sort=sort))
                    have.add(value)
                    sort += 1
                    added += 1
        summary["Daftar pilihan baru"] = added

    # ---------- Rekrutmen ----------
    ws = wb["Rekrutmen"]
    n = 0
    for row in _rows(ws, 5):
        position = _text(row[2], 150)
        if not position:
            continue
        status = (_text(row[8]) or "OPEN").upper()
        rec = Recruitment(
            req_date=_date(row[1]), position=position, placement=_text(row[3], 100),
            total_candidate=_int(row[4]), stage=_text(row[5], 50), expected_join=_date(row[6]),
            specification=_text(row[7]), status=status, remarks=_text(row[9]),
            updated_on=_date(row[10]), wa_order=0,
        )
        if status == "CLOSED":
            rec.closed_on = rec.updated_on or rec.expected_join
        db.session.add(rec)
        n += 1
    summary["Posisi rekrutmen"] = n

    # ---------- Onboard ----------
    if "Onboard" in names:
        ws = wb["Onboard"]
        n = 0
        for row in _rows(ws, 4):
            name = _text(row[4], 150)
            if not name:
                continue
            ob = Onboard(position=_text(row[1], 150) or "-", placement=_text(row[2], 100),
                         hire_date=_date(row[3]), name=name, phone=_text(row[5], 50),
                         email=_text(row[6], 150), poh=_text(row[7], 150),
                         status=(_text(row[17]) or "OPEN").upper())
            for i, (field, _label) in enumerate(ONBOARD_CHECKS):
                setattr(ob, field, _check(row[8 + i]))
            db.session.add(ob)
            n += 1
        summary["Onboarding"] = n

    # ---------- Headcount ----------
    if "Headcount" in names:
        ws = wb["Headcount"]

        def pairs(name_col, count_col, first, last):
            out = []
            for r in range(first, last + 1):
                label = _text(ws.cell(r, name_col).value, 100)
                if label and label.upper() != "TOTAL":
                    out.append([label, _int(ws.cell(r, count_col).value) or 0])
            return out

        snap_date = _date(ws["C4"].value)
        if snap_date:
            snap = HeadcountSnapshot(date=snap_date, note="Impor dari Excel")
            snap.data = {
                "entity": pairs(2, 3, 7, 8),
                "gender": pairs(5, 6, 7, 8),
                "department": pairs(2, 3, 13, 34),
                "location": pairs(5, 6, 13, 24),
            }
            db.session.add(snap)
            summary["Snapshot head count"] = 1

    # ---------- GA ----------
    ws = wb["GA"]
    n = 0
    for row in _rows(ws, 5):
        when, desc = _date(row[1]), _text(row[3])
        if not when or not desc:
            continue
        db.session.add(GAActivity(date=when, category=_text(row[2], 100), description=desc,
                                  status=_text(row[4], 30), pic=_text(row[5], 100),
                                  cost=_int(row[6]) or 0, note=_text(row[7])))
        n += 1
    summary["Kegiatan GA"] = n

    # ---------- Scrap ----------
    if "Scrap" in names:
        ws = wb["Scrap"]
        opening = _float(ws["C4"].value)
        if opening is not None:
            set_setting("scrap_opening_kg", opening)
            opening_date = _date(ws["C5"].value)
            set_setting("scrap_opening_date", opening_date.isoformat() if opening_date else "")
        n = 0
        for row in _rows(ws, 9):
            when, kg = _date(row[1]), _float(row[2])
            if not when or kg is None:
                continue
            db.session.add(Scrap(date=when, weight_kg=kg, material=_text(row[3], 100),
                                 note=_text(row[4])))
            n += 1
        summary["Data scrap"] = n

    # ---------- Site Project ----------
    if "Site Project" in names:
        ws = wb["Site Project"]
        n = 0
        for row in _rows(ws, 5):
            when, site = _date(row[1]), _text(row[2], 150)
            if not when or not site:
                continue
            progress = _float(row[5])
            if progress is not None and progress <= 1:
                progress *= 100     # sel berformat persen tersimpan 0.75
            db.session.add(SiteUpdate(
                date=when, site=site, location=_text(row[3], 100), manpower=_int(row[4]),
                progress=_int(progress), status=_text(row[6], 30), condition=_text(row[7]),
                obstacle=_text(row[8]), pic=_text(row[9], 100)))
            n += 1
        summary["Update site"] = n

    # ---------- Issue & Action ----------
    ws = wb["Issue & Action"]
    n = 0
    for row in _rows(ws, 5):
        when, issue = _date(row[1]), _text(row[3])
        if not when or not issue:
            continue
        db.session.add(Issue(date=when, category=_text(row[2], 100), issue=issue,
                             action_plan=_text(row[4]), pic=_text(row[5], 100),
                             target_date=_date(row[6]), status=_text(row[7], 30) or "Open",
                             closed_date=_date(row[8])))
        n += 1
    summary["Issue & action"] = n

    # ---------- Motivasi ----------
    if "Motivasi" in names:
        ws = wb["Motivasi"]
        n = 0
        seen = set()
        for row in _rows(ws, 5):
            week, text = _date(row[0]), _text(row[1])
            if week and text and monday_of(week) not in seen:
                seen.add(monday_of(week))
                db.session.add(Motivation(week_start=monday_of(week), text=_strip_quotes(text),
                                          author=_text(row[2], 100)))
                n += 1
        bank = [_strip_quotes(_text(row[6])) for row in _rows(ws, 5)
                if len(row) > 6 and _text(row[6])]
        if bank:
            Option.query.filter_by(kind="motivation_bank").delete()
            for i, text in enumerate(bank):
                db.session.add(Option(kind="motivation_bank", value=text,
                                      sort=i))
        summary["Motivasi mingguan"] = n
        summary["Bank kata motivasi"] = len(bank)

    db.session.commit()
    return summary


def _strip_quotes(text):
    return text.strip().strip('"“”').strip() if text else text
