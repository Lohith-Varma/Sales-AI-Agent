"""Create an explicitly authorized local user without implicit admin seeding."""

from __future__ import annotations

import argparse
import getpass
import sys
from pathlib import Path

# Direct execution sets sys.path[0] to backend/scripts. Add the backend root so
# the documented ``python scripts/create_user.py`` command can import ``app``.
backend_root = Path(__file__).resolve().parents[1]
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from app.db.base import User
from app.db.database import SessionLocal
from app.security import hash_password


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--role", choices=("agent", "manager", "admin"), default="agent")
    args = parser.parse_args()
    password = getpass.getpass("Password (minimum 12 characters): ")
    password_hash = hash_password(password)
    with SessionLocal() as db:
        email = args.email.strip().lower()
        if db.query(User).filter(User.email == email).first():
            raise SystemExit("A user with this email already exists.")
        user = User(
            email=email,
            display_name=args.name.strip(),
            password_hash=password_hash,
            role=args.role,
        )
        db.add(user)
        db.commit()
        print(f"Created {args.role} user {email}")


if __name__ == "__main__":
    main()
