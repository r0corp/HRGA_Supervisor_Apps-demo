import json
from datetime import date, datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from . import db
from .constants import (
    CHECK_DONE, CHECK_NA, ONBOARD_CHECKS, REC_CLOSED, ROLE_ADMIN, ROLES,
)
from .weeks import monday_of


# ============================================================
# USER - hanya IT (admin) dan Spv HRGA
# ============================================================

class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    active = db.Column(db.Boolean, nullable=False, default=True)

    failed_logins = db.Column(db.Integer, nullable=False, default=0)
    locked_until = db.Column(db.DateTime)
    last_login_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.role == ROLE_ADMIN

    @property
    def role_label(self):
        return ROLES.get(self.role, self.role)


# ============================================================
# MASTER
# ============================================================

class Option(db.Model):
    """Daftar pilihan dropdown (sheet "Daftar")."""

    __tablename__ = "options"
    __table_args__ = (db.UniqueConstraint("kind", "value", name="uq_option_kind_value"),)

    id = db.Column(db.Integer, primary_key=True)
    kind = db.Column(db.String(30), nullable=False, index=True)
    # Panjang untuk bank kata motivasi (kalimat utuh).
    value = db.Column(db.String(500), nullable=False)
    sort = db.Column(db.Integer, nullable=False, default=0)


class Setting(db.Model):
    __tablename__ = "settings"

    key = db.Column(db.String(50), primary_key=True)
    value = db.Column(db.Text)


def get_setting(key, default=None):
    row = db.session.get(Setting, key)
    return row.value if row and row.value is not None else default


def set_setting(key, value):
    row = db.session.get(Setting, key)
    if not row:
        row = Setting(key=key)
        db.session.add(row)
    row.value = None if value is None else str(value)


# ============================================================
# 1. RECRUITMENT & ONBOARDING
# ============================================================

class Recruitment(db.Model):
    """1 baris = 1 permintaan posisi (sheet "Rekrutmen")."""

    __tablename__ = "recruitments"

    id = db.Column(db.Integer, primary_key=True)
    req_date = db.Column(db.Date, index=True)
    position = db.Column(db.String(150), nullable=False)
    placement = db.Column(db.String(100))
    total_candidate = db.Column(db.Integer)
    stage = db.Column(db.String(50))
    expected_join = db.Column(db.Date)
    specification = db.Column(db.Text)
    status = db.Column(db.String(20), nullable=False, default="OPEN", index=True)
    remarks = db.Column(db.Text)
    updated_on = db.Column(db.Date)
    # Tgl status jadi CLOSED - dasar Time to Hire & umur posisi berhenti.
    closed_on = db.Column(db.Date)

    # Nama posisi di report WA, mis. "Site Coordinator (Sinar Mas Project)".
    # Kosong = pakai nama posisi.
    wa_label = db.Column(db.String(150))
    # Urutan di report WA (kecil dulu); sama -> urut tanggal request.
    wa_order = db.Column(db.Integer, nullable=False, default=0)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)

    updates = db.relationship(
        "RecruitmentUpdate", backref="recruitment", cascade="all, delete-orphan",
        order_by="(RecruitmentUpdate.date.desc().nulls_last(), RecruitmentUpdate.id.desc())",
    )

    @property
    def label(self):
        return (self.wa_label or "").strip() or self.position

    @property
    def age_days(self):
        """Umur posisi (hari) sejak request, berhenti saat ditutup."""
        if not self.req_date:
            return None
        end = self.closed_on if self.status == REC_CLOSED and self.closed_on else date.today()
        return (end - self.req_date).days

    @property
    def req_week(self):
        return monday_of(self.req_date) if self.req_date else None


class RecruitmentUpdate(db.Model):
    """Satu action plan / progres posisi - sumber report WA mingguan."""

    __tablename__ = "recruitment_updates"

    id = db.Column(db.Integer, primary_key=True)
    recruitment_id = db.Column(db.Integer, db.ForeignKey("recruitments.id"), nullable=False,
                               index=True)
    # Boleh kosong untuk keterangan umum tanpa tanggal ("On process with Head Hunter").
    date = db.Column(db.Date, index=True)
    text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)


class Onboard(db.Model):
    """Karyawan baru (sheet "Onboard")."""

    __tablename__ = "onboards"

    id = db.Column(db.Integer, primary_key=True)
    position = db.Column(db.String(150), nullable=False)
    placement = db.Column(db.String(100))
    hire_date = db.Column(db.Date, index=True)
    name = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(50))
    email = db.Column(db.String(150))
    poh = db.Column(db.String(150))
    status = db.Column(db.String(20), nullable=False, default="OPEN")
    note = db.Column(db.Text)

    chk_invitation = db.Column(db.String(1), nullable=False, default="")
    chk_workspace = db.Column(db.String(1), nullable=False, default="")
    chk_laptop = db.Column(db.String(1), nullable=False, default="")
    chk_email = db.Column(db.String(1), nullable=False, default="")
    chk_hp = db.Column(db.String(1), nullable=False, default="")
    chk_number = db.Column(db.String(1), nullable=False, default="")
    chk_contract = db.Column(db.String(1), nullable=False, default="")
    chk_talenta = db.Column(db.String(1), nullable=False, default="")
    chk_wob = db.Column(db.String(1), nullable=False, default="")

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)

    @property
    def completeness(self):
        """(sudah, perlu) - item bertanda "-" tidak dihitung."""
        values = [getattr(self, field) for field, _ in ONBOARD_CHECKS]
        needed = [v for v in values if v != CHECK_NA]
        return sum(1 for v in needed if v == CHECK_DONE), len(needed)


# ============================================================
# 2. HEAD COUNT
# ============================================================

class HeadcountSnapshot(db.Model):
    """Angka head count per tanggal. Dashboard memakai snapshot terakhir
    sampai akhir minggu laporan."""

    __tablename__ = "headcount_snapshots"

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, index=True)
    # {"entity": [["PT ...", 208], ...], "gender": [...], "department": [...], "location": [...]}
    data_json = db.Column(db.Text, nullable=False, default="{}")
    note = db.Column(db.Text)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)

    @property
    def data(self):
        try:
            return json.loads(self.data_json or "{}")
        except ValueError:
            return {}

    @data.setter
    def data(self, value):
        self.data_json = json.dumps(value, ensure_ascii=False)

    def rows(self, group):
        return [(name, int(count or 0)) for name, count in self.data.get(group, [])]

    def total(self, group):
        return sum(count for _, count in self.rows(group))


# ============================================================
# 3. GENERAL AFFAIR
# ============================================================

class GAActivity(db.Model):
    __tablename__ = "ga_activities"

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, index=True)
    category = db.Column(db.String(100))
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(30))
    pic = db.Column(db.String(100))
    cost = db.Column(db.Integer, nullable=False, default=0)
    note = db.Column(db.Text)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)


# ============================================================
# 4. SCRAP
# ============================================================

class Scrap(db.Model):
    __tablename__ = "scraps"

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, index=True)
    weight_kg = db.Column(db.Float, nullable=False, default=0)
    material = db.Column(db.String(100))
    note = db.Column(db.Text)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)


# ============================================================
# 5. SITE PROJECT / BRANCH
# ============================================================

class SiteUpdate(db.Model):
    __tablename__ = "site_updates"

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, index=True)
    site = db.Column(db.String(150), nullable=False)
    location = db.Column(db.String(100))
    manpower = db.Column(db.Integer)
    progress = db.Column(db.Integer)
    status = db.Column(db.String(30))
    condition = db.Column(db.Text)
    obstacle = db.Column(db.Text)
    pic = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)


# ============================================================
# 6. ISSUE & ACTION PLAN
# ============================================================

class Issue(db.Model):
    __tablename__ = "issues"

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, index=True)
    category = db.Column(db.String(100))
    issue = db.Column(db.Text, nullable=False)
    action_plan = db.Column(db.Text)
    pic = db.Column(db.String(100))
    target_date = db.Column(db.Date)
    status = db.Column(db.String(30), nullable=False, default="Open")
    closed_date = db.Column(db.Date)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)

    @property
    def is_closed(self):
        from .constants import ISSUE_CLOSED
        return self.status == ISSUE_CLOSED

    @property
    def overdue(self):
        return bool(self.target_date and not self.is_closed and self.target_date < date.today())

    @property
    def age_days(self):
        end = self.closed_date if self.is_closed and self.closed_date else date.today()
        return (end - self.date).days if self.date else None


# ============================================================
# MOTIVASI MINGGUAN
# ============================================================

class Motivation(db.Model):
    """Kata motivasi khusus untuk satu minggu (Senin)."""

    __tablename__ = "motivations"

    id = db.Column(db.Integer, primary_key=True)
    week_start = db.Column(db.Date, unique=True, nullable=False)
    text = db.Column(db.Text, nullable=False)
    author = db.Column(db.String(100))


class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    at = db.Column(db.DateTime, nullable=False, default=datetime.now, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    entity = db.Column(db.String(30), nullable=False)
    entity_id = db.Column(db.Integer)
    action = db.Column(db.String(20), nullable=False)
    detail = db.Column(db.Text)

    user = db.relationship("User")
