"""Interactive creation of the first instructor account."""

import getpass
from app.seed_demo import bootstrap


def main():
    username = input("Instructor username: ").strip()
    password = getpass.getpass("Instructor password (12+ characters): ")
    confirm = getpass.getpass("Confirm password: ")
    if len(username) < 3:
        raise SystemExit("Username must contain at least 3 characters.")
    if len(password) < 12:
        raise SystemExit("Password must contain at least 12 characters.")
    if password != confirm:
        raise SystemExit("Passwords do not match.")
    bootstrap(username, password)


if __name__ == "__main__":
    main()
