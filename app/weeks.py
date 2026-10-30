"""Perhitungan minggu laporan (Senin - Minggu), sama dengan rumus Excel lama."""

from datetime import date, timedelta


HARI = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
BULAN = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli",
         "Agustus", "September", "Oktober", "November", "Desember"]
MONTHS_EN = ["January", "February", "March", "April", "May", "June", "July",
             "August", "September", "October", "November", "December"]


def monday_of(value):
    return value - timedelta(days=value.weekday())


def default_week(today=None):
    """Minggu laporan otomatis. Excel lama: TODAY()-3 lalu mundur ke Senin,
    jadi Senin-Rabu masih menampilkan minggu lalu (report dikirim awal minggu)."""
    today = today or date.today()
    return monday_of(today - timedelta(days=3))


def parse_week(text, default=None):
    """'2026-10-05' (tanggal mana pun) -> Senin minggu itu."""
    try:
        return monday_of(date.fromisoformat(text))
    except (TypeError, ValueError):
        return default if default is not None else default_week()


def week_number(value):
    """Sama dengan WEEKNUM(tgl, 2) Excel: minggu mulai Senin, minggu 1 =
    minggu yang memuat 1 Januari."""
    first = monday_of(date(value.year, 1, 1))
    return (monday_of(value) - first).days // 7 + 1


def week_of_month(monday):
    """Minggu ke-n dalam bulan, ikut bulan hari Kamis-nya (seperti minggu ISO).
    Senin 28 Sep 2026 -> Oktober minggu 1; Senin 5 Okt 2026 -> Oktober minggu 2."""
    thursday = monday + timedelta(days=3)
    return (thursday.day - 1) // 7 + 1, thursday.month, thursday.year


def workweek_range_en(monday):
    """'5 - 9 October 2026' / '28 September - 2 October 2026'."""
    friday = monday + timedelta(days=4)
    if monday.month == friday.month:
        return f"{monday.day} - {friday.day} {MONTHS_EN[friday.month - 1]} {friday.year}"
    if monday.year == friday.year:
        return (f"{monday.day} {MONTHS_EN[monday.month - 1]} - "
                f"{friday.day} {MONTHS_EN[friday.month - 1]} {friday.year}")
    return (f"{monday.day} {MONTHS_EN[monday.month - 1]} {monday.year} - "
            f"{friday.day} {MONTHS_EN[friday.month - 1]} {friday.year}")


def format_date(value, with_day=False):
    if not value:
        return ""
    text = f"{value.day} {BULAN[value.month - 1]} {value.year}"
    return f"{HARI[value.weekday()]}, {text}" if with_day else text


def short_date(value):
    """dd/mm/yy - format tanggal di report WA."""
    return value.strftime("%d/%m/%y") if value else ""


def week_label(monday):
    sunday = monday + timedelta(days=6)
    return (f"Minggu ke-{week_number(monday)} ·{monday.strftime('%d/%m/%Y')} s/d "
            f"{sunday.strftime('%d/%m/%Y')}")
