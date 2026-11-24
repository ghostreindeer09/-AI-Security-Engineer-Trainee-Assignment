"""
UCI "Student Performance" dataset: download it, calculate average grades,
and plot a bar chart.

Source: https://archive.ics.uci.edu/dataset/320/student+performance
Two Portuguese schools, two subjects (Math: 395 students, Portuguese: 649).
Grades are on a 0-20 scale: G1 = period 1, G2 = period 2, G3 = final grade.

Install:  pip install requests matplotlib
Run:      python student_scores.py
"""

import csv
import io
import zipfile
from pathlib import Path

import requests
import matplotlib.pyplot as plt

ZIP_URL = "https://archive.ics.uci.edu/static/public/320/student+performance.zip"
LOCAL_ZIP = Path("student_performance.zip")    # cached copy, so we download once
GRADE_COLUMNS = ["G1", "G2", "G3"]
SUBJECTS = {"student-mat.csv": "Math", "student-por.csv": "Portuguese"}


def get_zip_bytes() -> bytes:
    if LOCAL_ZIP.exists():
        return LOCAL_ZIP.read_bytes()
    print(f"Downloading {ZIP_URL} ...")
    resp = requests.get(ZIP_URL, timeout=30)
    resp.raise_for_status()
    LOCAL_ZIP.write_bytes(resp.content)
    return resp.content


def read_csv_from_zip(zf: zipfile.ZipFile, filename: str) -> list[dict]:
    """Find a CSV inside the zip (also looks in nested zips) and parse it."""
    for name in zf.namelist():
        if name.endswith(filename):
            with zf.open(name) as f:
                text = io.TextIOWrapper(f, encoding="utf-8")
                return list(csv.DictReader(text, delimiter=";"))    # file uses ';'
    for name in zf.namelist():                                       # nested zip
        if name.endswith(".zip"):
            with zipfile.ZipFile(io.BytesIO(zf.read(name))) as inner:
                try:
                    return read_csv_from_zip(inner, filename)
                except FileNotFoundError:
                    pass
    raise FileNotFoundError(f"{filename} not found in zip")


def load_data(zip_bytes: bytes) -> dict[str, list[dict]]:
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        return {label: read_csv_from_zip(zf, fn) for fn, label in SUBJECTS.items()}


def average_grades(rows: list[dict]) -> dict[str, float]:
    return {g: sum(float(r[g]) for r in rows) / len(rows) for g in GRADE_COLUMNS}


def plot(averages: dict[str, dict[str, float]]) -> None:
    labels = ["Period 1 (G1)", "Period 2 (G2)", "Final (G3)"]
    width = 0.38
    fig, ax = plt.subplots(figsize=(9, 5.5))
    for i, (subject, avg) in enumerate(averages.items()):
        xs = [x + (i - 0.5) * width for x in range(len(GRADE_COLUMNS))]
        bars = ax.bar(xs, [avg[g] for g in GRADE_COLUMNS], width, label=subject)
        ax.bar_label(bars, fmt="%.2f", padding=3)
    ax.set_xticks(range(len(labels)), labels)
    ax.set_ylabel("Average grade (0-20)")
    ax.set_ylim(0, 20)
    ax.set_title("Average Student Grades by Period and Subject")
    ax.legend()
    plt.tight_layout()
    plt.savefig("student_scores.png", dpi=150)
    plt.show()


def main() -> None:
    data = load_data(get_zip_bytes())

    averages = {}
    for subject, rows in data.items():
        averages[subject] = average_grades(rows)
        print(f"{subject:<11} ({len(rows)} students)  "
              + "  ".join(f"{g}: {v:.2f}" for g, v in averages[subject].items()))

    all_rows = [r for rows in data.values() for r in rows]
    print(f"\nOverall average final grade (G3): "
          f"{sum(float(r['G3']) for r in all_rows) / len(all_rows):.2f} / 20")

    plot(averages)


if __name__ == "__main__":
    main()