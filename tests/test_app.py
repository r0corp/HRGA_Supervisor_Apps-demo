import os
import sys
from datetime import date

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db  # noqa: E402
from app.models import Issue, Recruitment, RecruitmentUpdate, Scrap, User  # noqa: E402
from app.weekly import dashboard_data, recruitment_wa_rows  # noqa: E402
from app.weeks import default_week, week_number, week_of_month, workweek_range_en  # noqa: E402


@pytest.fixture
def app():
    app = create_app("config.TestConfig")
    with app.app_context():
        for username, role in (("it", "admin"), ("spv", "spv")):
            u = User(username=username, name=username.upper(), role=role)
            u.set_password("rahasia123")
            db.session.add(u)
        db.session.commit()
        yield app


def login(client, username="spv", password="rahasia123"):
    return client.post("/login", data={"username": username, "password": password})


def test_weeks():
    assert week_of_month(date(2026, 10, 5)) == (2, 10, 2026)
    assert week_of_month(date(2026, 9, 28)) == (1, 10, 2026)
    assert workweek_range_en(date(2026, 10, 5)) == "5 - 9 October 2026"
    assert workweek_range_en(date(2026, 9, 28)) == "28 September - 2 October 2026"
    assert week_number(date(2026, 9, 28)) == 40
    # Senin-Rabu masih minggu lalu (report dikirim awal minggu).
    assert default_week(date(2026, 10, 12)) == date(2026, 10, 5)
    assert default_week(date(2026, 10, 15)) == date(2026, 10, 12)


def test_login_required_and_lockout(app):
    c = app.test_client()
    assert c.get("/").status_code == 302
    for _ in range(5):
        login(c, password="salah")
    assert login(c).status_code == 429
    assert db.session.get(User, 2).locked_until is not None


def test_spv_cannot_open_admin_pages(app):
    c = app.test_client()
    login(c)
    assert c.get("/").status_code == 200
    assert c.get("/user").status_code == 403
    assert c.get("/impor").status_code == 403
    c.post("/logout")
    from flask import g
    g.pop("_login_user", None)  # app context fixture dipakai lintas request
    login(c, "it")
    assert c.get("/user").status_code == 200


def test_recruitment_update_and_wa(app):
    c = app.test_client()
    login(c)
    c.post("/rekrutmen/baru", data={"position": "Trucking Supervisor", "status": "OPEN",
                                    "wa_label": "Trucking Spv", "wa_order": "0"})
    rec = Recruitment.query.one()
    c.post(f"/rekrutmen/{rec.id}/update", data={"date": "2026-10-02", "text": "2 Candidate User Interview"})
    c.post(f"/rekrutmen/{rec.id}/update", data={"date": "2026-10-05", "text": "Shortlist new CV",
                                                 "stage": "User Interview"})
    assert RecruitmentUpdate.query.count() == 2
    assert db.session.get(Recruitment, rec.id).stage == "User Interview"

    rows = recruitment_wa_rows(date(2026, 10, 5))
    assert rows[0]["label"] == "Trucking Spv"
    checked = [u["text"] for u in rows[0]["updates"] if u["checked"]]
    assert checked == ["Shortlist new CV"]
    assert rows[0]["updates"][0]["date"] == "02/10/26"

    page = c.get("/report-wa?week=2026-10-05").get_data(as_text=True)
    assert "Action Plan Recruitment - Week 2 (5 - 9 October 2026) :" in page


def test_closed_position_leaves_wa_unless_updated_that_week(app):
    db.session.add(Recruitment(position="Old", status="CLOSED"))
    db.session.commit()
    assert recruitment_wa_rows(date(2026, 10, 5)) == []


def test_dashboard_scrap_and_issue(app):
    from app.models import set_setting
    set_setting("scrap_opening_kg", 100)
    db.session.add_all([Scrap(date=date(2026, 9, 30), weight_kg=10),
                        Scrap(date=date(2026, 10, 6), weight_kg=5.5),
                        Issue(date=date(2026, 10, 1), issue="X", status="Open",
                              target_date=date(2020, 1, 1))])
    db.session.commit()
    d = dashboard_data(date(2026, 10, 5))
    assert d["scrap_before"] == 110
    assert d["scrap_week"] == 5.5
    assert d["kpi"]["scrap_total"] == 115.5
    assert d["kpi"]["issues_overdue"] == 1


def test_issue_closed_date_auto(app):
    c = app.test_client()
    login(c)
    c.post("/issue/baru", data={"date": "2026-10-05", "issue": "AC rusak", "status": "Closed"})
    assert Issue.query.one().closed_date == date.today()


def test_all_pages_render(app):
    c = app.test_client()
    login(c, "it")
    for url in ["/", "/report-wa", "/rekrutmen/", "/rekrutmen/baru", "/onboard/", "/onboard/baru",
                "/headcount", "/headcount/baru", "/ga/", "/ga/baru", "/scrap/", "/scrap/baru",
                "/site/", "/site/baru", "/issue/", "/issue/baru", "/pilihan", "/motivasi",
                "/user", "/impor", "/audit", "/password"]:
        assert c.get(url).status_code == 200, url
