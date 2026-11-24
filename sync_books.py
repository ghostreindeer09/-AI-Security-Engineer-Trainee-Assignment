#!/usr/bin/env python3

import argparse
import json
import sqlite3
import sys
import urllib.error
import urllib.request
import time

# Open Library's public search API.
DEFAULT_URL = (
    "https://openlibrary.org/search.json"
    "?q=subject:science_fiction&limit=20"
    "&fields=title,author_name,first_publish_year"
)



def fetch_json(url, timeout=10, retries=3):
    """GET a URL and return decoded JSON, retrying on network errors."""
    req = urllib.request.Request(
        url, headers={"Accept": "application/json", "User-Agent": "books-sync/1.0"}
    )
    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            sys.exit(f"HTTP error {e.code} while fetching {url}: {e.reason}")
        except json.JSONDecodeError as e:
            sys.exit(f"Response was not valid JSON: {e}")
        except (urllib.error.URLError, ConnectionError, TimeoutError) as e:
            if attempt == retries:
                sys.exit(f"Network error after {retries} attempts: {e}")
            print(f"Attempt {attempt} failed ({e}); retrying in {attempt * 2}s...")
            time.sleep(attempt * 2)


def extract_list(payload):
    """Find the list of books inside the JSON payload."""
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("books", "docs", "results", "data", "items"):
            if isinstance(payload.get(key), list):
                return payload[key]
    sys.exit("Could not find a list of books in the API response.")


def normalize_book(raw):
    """Map one raw API record to (title, author, year); return None if unusable."""
    title = raw.get("title") or raw.get("name")
    author = raw.get("author") or raw.get("author_name") or raw.get("authors")
    if isinstance(author, list):  # e.g. ["Frank Herbert", "Someone Else"]
        author = ", ".join(str(a.get("name", a) if isinstance(a, dict) else a) for a in author)
    year = (
        raw.get("publication_year")
        or raw.get("year")
        or raw.get("first_publish_year")
        or raw.get("published")
    )
    try:
        year = int(str(year)[:4]) if year is not None else None
    except ValueError:
        year = None
    if not title:
        return None
    return title.strip(), (author or "Unknown").strip(), year



def init_db(path):
    conn = sqlite3.connect(path)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS books (
            id     INTEGER PRIMARY KEY AUTOINCREMENT,
            title  TEXT NOT NULL,
            author TEXT NOT NULL,
            year   INTEGER,
            UNIQUE (title, author)          -- re-running won't create duplicates
        )
        """
    )
    return conn


def save_books(conn, books):
    """Insert books, skipping duplicates. Returns number of new rows."""
    before = conn.total_changes
    with conn:  
        conn.executemany(
            "INSERT OR IGNORE INTO books (title, author, year) VALUES (?, ?, ?)", books
        )
    return conn.total_changes - before



def display_books(conn):
    rows = conn.execute(
        "SELECT title, author, year FROM books ORDER BY year IS NULL, year, title"
    ).fetchall()
    if not rows:
        print("No books in the database.")
        return
    tw = min(max(len(r[0]) for r in rows), 45)
    aw = min(max(len(r[1]) for r in rows), 30)
    print(f"\n{'Title':<{tw}}  {'Author':<{aw}}  Year")
    print(f"{'-' * tw}  {'-' * aw}  ----")
    for title, author, year in rows:
        print(f"{title[:tw]:<{tw}}  {author[:aw]:<{aw}}  {year if year else 'n/a'}")
    print(f"\n{len(rows)} book(s) in database.")



def main():
    parser = argparse.ArgumentParser(description="Fetch books and store them in SQLite")
    parser.add_argument("url", nargs="?", default=DEFAULT_URL, help="API endpoint")
    parser.add_argument("--db", default="books.db", help="SQLite file (default: books.db)")
    args = parser.parse_args()

    payload = fetch_json(args.url)
    books = [b for b in (normalize_book(r) for r in extract_list(payload)) if b]
    print(f"Fetched {len(books)} valid book record(s).")

    conn = init_db(args.db)
    try:
        added = save_books(conn, books)
        print(f"Stored {added} new book(s) in {args.db}.")
        display_books(conn)
    finally:
        conn.close()


if __name__ == "__main__":
    main()