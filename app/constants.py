ROLE_ADMIN = "admin"
ROLE_SPV = "spv"

ROLES = {
    ROLE_ADMIN: "Administrator (IT)",
    ROLE_SPV: "Supervisor HRGA",
}


# Daftar pilihan (sheet "Daftar" di Excel lama). Bisa diubah dari menu
# Daftar Pilihan; nilai di bawah hanya isi awal database.
OPTION_KINDS = {
    "ga_category": "GA - Kategori",
    "ga_status": "GA - Status",
    "pic": "PIC",
    "rec_stage": "Rekrutmen - Current Stage",
    "rec_status": "Rekrutmen - Status",
    "placement": "Placement / Lokasi",
    "site_status": "Site Project - Status",
    "issue_category": "Issue - Kategori",
    "issue_status": "Issue - Status",
    "scrap_material": "Scrap - Jenis / Material",
}

DEFAULT_OPTIONS = {
    "ga_category": ["Transportasi", "Tamu", "Asset Management", "Office Facility",
                    "Operational Support"],
    "ga_status": ["Selesai", "Pending", "In Progress"],
    "pic": ["GA", "HR", "HRGA"],
    "rec_stage": ["Shortlist", "Screening", "User Interview", "Technical Test", "Offering",
                  "Hiring Confirmation"],
    "rec_status": ["OPEN", "HOLD", "CLOSED"],
    # Contoh saja; daftar asli diatur dari menu Daftar Pilihan dan
    # tersimpan di database (bawaan ini hanya dipakai saat jenisnya masih kosong).
    "placement": ["Head Office", "Project Site A", "Project Site B", "Project Site C",
                  "Cabang Surabaya", "Cabang Balikpapan", "Cabang Palembang"],
    "site_status": ["On Track", "Perlu Perhatian", "Kritis"],
    "issue_category": ["Branch Update", "Remuneration Update", "Manpower Related", "Recruitment",
                       "General Affair", "Site Project", "Administration"],
    "issue_status": ["Open", "On Progress", "Closed"],
    "scrap_material": ["Scrap Limbah", "Scrap LGS"],
}

# Status yang punya arti khusus di dashboard - tidak boleh dihapus dari
# daftar pilihan.
REC_OPEN = "OPEN"
REC_HOLD = "HOLD"
REC_CLOSED = "CLOSED"
GA_DONE = "Selesai"
ISSUE_CLOSED = "Closed"
SITE_ATTENTION = ("Perlu Perhatian", "Kritis")
LOCKED_OPTIONS = {
    "rec_status": [REC_OPEN, REC_HOLD, REC_CLOSED],
    "ga_status": [GA_DONE],
    "issue_status": [ISSUE_CLOSED],
}

# Checklist onboarding (kolom I-Q sheet Onboard).
ONBOARD_CHECKS = [
    ("chk_invitation", "Email Invitation"),
    ("chk_workspace", "Working Space"),
    ("chk_laptop", "Laptop / PC"),
    ("chk_email", "Email"),
    ("chk_hp", "HP"),
    ("chk_number", "Number"),
    ("chk_contract", "Contract"),
    ("chk_talenta", "Talenta"),
    ("chk_wob", "WOB"),
]
# "v" = sudah, "-" = tidak perlu, "" = belum.
CHECK_DONE = "v"
CHECK_NA = "-"

HEADCOUNT_GROUPS = [
    ("entity", "Entitas"),
    ("gender", "Gender"),
    ("department", "Departemen"),
    ("location", "Lokasi"),
]

# Bank kata motivasi bawaan (dipakai bergiliran kalau minggu itu tidak
# diisi khusus). Disalin dari sheet Motivasi.
DEFAULT_MOTIVATION_BANK = [
    "Work hard with sincerity, trust Allah with the results, and keep moving forward.",
]
