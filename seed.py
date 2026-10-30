"""
Membuat akun pertama: IT (administrator) dan Supervisor HRGA. Aman
dijalankan ulang: username yang sudah ada dilewati.

    python seed.py [--admin-name "Admin IT"] [--spv-name "Supervisor HRGA"]

Password acak tampil SEKALI di layar - catat lalu segera ganti lewat
menu profil > Password setelah login.
"""

import argparse
import secrets

from app import create_app, db
from app.constants import ROLE_ADMIN, ROLE_SPV
from app.models import User


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--admin-name", default="Admin IT")
    parser.add_argument("--spv-name", default="Supervisor HRGA")
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        for username, name, role in (("it", args.admin_name, ROLE_ADMIN),
                                     ("spv.hrga", args.spv_name, ROLE_SPV)):
            if User.query.filter_by(username=username).first():
                print(f"User {username} sudah ada, dilewati.")
                continue
            password = secrets.token_urlsafe(9)
            user = User(username=username, name=name, role=role)
            user.set_password(password)
            db.session.add(user)
            print(f"User dibuat  -> username: {username:<9} password: {password}  ({name})")
        db.session.commit()
        print("Catat password di atas, lalu ganti setelah login (menu profil > Password).")


if __name__ == "__main__":
    main()
