#!/usr/bin/env python3
"""Read user data from a CSV file and insert it into a SQLite database.

Usage:
    python csv_to_sqlite.py users.csv users.db

Expected CSV columns (header row required): name, email
"""

import argparse
import csv
import re
import sqlite3
import sys

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def create_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id    INTEGER PRIMARY KEY AUTOINCREMENT,
            name  TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE
        )
        """
    )


def read_users(csv_path: str):
    """Yield (name, email) tuples from the CSV, skipping invalid rows."""
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError("CSV file is empty.")

        # Normalize header names so 'Name' / ' EMAIL ' still work
        reader.fieldnames = [h.strip().lower() for h in reader.fieldnames]
        missing = {"name", "email"} - set(reader.fieldnames)
        if missing:
            raise ValueError(f"CSV is missing required column(s): {', '.join(sorted(missing))}")

        for line_no, row in enumerate(reader, start=2):
            name = (row.get("name") or "").strip()
            email = (row.get("email") or "").strip().lower()

            if not name or not EMAIL_RE.match(email):
                print(f"Skipping line {line_no}: invalid data -> {row}", file=sys.stderr)
                continue

            yield name, email


def insert_users(conn: sqlite3.Connection, users) -> tuple[int, int]:
    """Insert users, ignoring duplicate emails. Returns (inserted, skipped)."""
    inserted = skipped = 0
    for name, email in users:
        cur = conn.execute(
            "INSERT OR IGNORE INTO users (name, email) VALUES (?, ?)",
            (name, email),
        )
        if cur.rowcount:
            inserted += 1
        else:
            skipped += 1
    return inserted, skipped


def main() -> int:
    parser = argparse.ArgumentParser(description="Load users from a CSV file into SQLite.")
    parser.add_argument("csv_file", help="Path to the input CSV file")
    parser.add_argument("db_file", nargs="?", default="users.db", help="SQLite database file (default: users.db)")
    args = parser.parse_args()

    try:
        with sqlite3.connect(args.db_file) as conn:  # commits on success, rolls back on error
            create_table(conn)
            inserted, skipped = insert_users(conn, read_users(args.csv_file))
    except FileNotFoundError:
        print(f"Error: file not found: {args.csv_file}", file=sys.stderr)
        return 1
    except (ValueError, sqlite3.Error) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    print(f"Done. Inserted {inserted} user(s), skipped {skipped} duplicate(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())