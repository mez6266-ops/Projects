from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# ----------------------------
# CONFIG
# ----------------------------
INPUT_FILENAME = "sample_calories.csv"
OUTPUT_FILENAME = "weight_history.csv"

# Output format (matches your file)
OUTPUT_HEADERS = ["week_start", "avg_weight", "avg_food", "avg_exercise", "avg_net"]

# Accept common date formats + your "15-Dec-25" style
DATE_PATTERNS = [
    "%Y-%m-%d",   # 2025-12-22
    "%m/%d/%Y",   # 12/22/2025
    "%m/%d/%y",   # 12/22/25
    "%d-%b-%y",   # 15-Dec-25   <-- YOUR FILE
    "%d-%b-%Y",   # 15-Dec-2025 (just in case)
]

# Exact / common header aliases (after normalization)
ALIASES = {
    "date": ["date", "day", "entry_date", "log_date", "timestamp"],
    "food": ["food", "calories", "cals", "kcal", "intake", "eaten"],
    "exercise": ["exercise", "exer", "exer.", "burned", "calories_burned", "activity"],
    "weight": ["weight", "weight_lbs", "lbs", "bodyweight", "scale_weight"],
}


# ----------------------------
# DATA
# ----------------------------
@dataclass
class DailyRow:
    date_iso: str
    weight: Optional[float]
    food: Optional[float]
    exercise: Optional[float]


# ----------------------------
# HELPERS
# ----------------------------
def _normalize_header(h: str) -> str:
    return (h or "").strip().lower().replace(" ", "_")


def _parse_date_to_iso(raw: str) -> str:
    raw = (raw or "").strip()
    if not raw:
        raise ValueError("Missing date")

    for pat in DATE_PATTERNS:
        try:
            return datetime.strptime(raw, pat).strftime("%Y-%m-%d")
        except ValueError:
            pass

    # last resort: swap / to -
    raw2 = raw.replace("/", "-")
    for pat in ("%Y-%m-%d",):
        try:
            return datetime.strptime(raw2, pat).strftime("%Y-%m-%d")
        except ValueError:
            pass

    raise ValueError(f"Unrecognized date format: '{raw}'")


def _to_float(s: str) -> Optional[float]:
    """
    Handles values like: 1,932  or "1,222"
    """
    s = (s or "").strip().replace(",", "").replace('"', "")
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _read_csv(path: Path) -> Tuple[List[Dict[str, str]], List[str]]:
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError(f"{path.name} has no headers.")
        return list(reader), list(reader.fieldnames)


def _build_column_map(headers: List[str]) -> Dict[str, str]:
    """
    canonical -> actual header name
    """
    norm_to_original = {_normalize_header(h): h for h in headers}
    col_map: Dict[str, str] = {}

    for canonical, alias_list in ALIASES.items():
        for a in alias_list:
            key = _normalize_header(a)
            if key in norm_to_original:
                col_map[canonical] = norm_to_original[key]
                break

    return col_map


def _monday_week_start(date_iso: str) -> str:
    dt = datetime.strptime(date_iso, "%Y-%m-%d")
    monday = dt - timedelta(days=dt.weekday())  # Monday = 0
    return monday.strftime("%Y-%m-%d")


def _load_existing_weekly(path: Path) -> Dict[str, Dict[str, str]]:
    if not path.exists():
        return {}
    rows, _ = _read_csv(path)
    out: Dict[str, Dict[str, str]] = {}
    for r in rows:
        ws = (r.get("week_start") or "").strip()
        if ws:
            out[ws] = r
    return out


def _extract_daily_rows(rows: List[Dict[str, str]], headers: List[str]) -> Tuple[List[DailyRow], Dict[str, str]]:
    col_map = _build_column_map(headers)

    if "date" not in col_map:
        raise ValueError(f"{INPUT_FILENAME} must have a Date column (your header should be 'Date').")

    # In YOUR file the exact headers are: Date, Food, Exer., Weight
    # This mapping will pick those up properly, but we also allow aliases.
    daily: List[DailyRow] = []

    for r in rows:
        raw_date = (r.get(col_map["date"]) or "").strip()
        if not raw_date:
            continue

        try:
            date_iso = _parse_date_to_iso(raw_date)
        except ValueError:
            continue

        weight = _to_float(r.get(col_map.get("weight", ""), "")) if "weight" in col_map else None
        food = _to_float(r.get(col_map.get("food", ""), "")) if "food" in col_map else None
        exercise = _to_float(r.get(col_map.get("exercise", ""), "")) if "exercise" in col_map else None

        daily.append(DailyRow(date_iso=date_iso, weight=weight, food=food, exercise=exercise))

    return daily, col_map


def _avg(vals: List[float]) -> Optional[float]:
    if not vals:
        return None
    return sum(vals) / len(vals)


def _aggregate_weekly(daily: List[DailyRow]) -> Dict[str, Dict[str, Optional[float]]]:
    buckets: Dict[str, Dict[str, List[float]]] = {}

    for d in daily:
        ws = _monday_week_start(d.date_iso)
        if ws not in buckets:
            buckets[ws] = {"weight": [], "food": [], "exercise": [], "net": []}

        if d.weight is not None:
            buckets[ws]["weight"].append(d.weight)
        if d.food is not None:
            buckets[ws]["food"].append(d.food)
        if d.exercise is not None:
            buckets[ws]["exercise"].append(d.exercise)
        if d.food is not None and d.exercise is not None:
            buckets[ws]["net"].append(d.food - d.exercise)

    weekly: Dict[str, Dict[str, Optional[float]]] = {}
    for ws, v in buckets.items():
        weekly[ws] = {
            "avg_weight": _avg(v["weight"]),
            "avg_food": _avg(v["food"]),
            "avg_exercise": _avg(v["exercise"]),
            "avg_net": _avg(v["net"]),
        }
    return weekly


def _fmt_1(x: Optional[float]) -> str:
    return "" if x is None else f"{x:.1f}"


def _fmt_0(x: Optional[float]) -> str:
    return "" if x is None else f"{x:.0f}"


def _write_weekly(path: Path, rows_by_week: Dict[str, Dict[str, str]]) -> None:
    keys = sorted(rows_by_week.keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_HEADERS)
        writer.writeheader()
        for ws in keys:
            writer.writerow(rows_by_week[ws])


def main() -> None:
    script_dir = Path(__file__).resolve().parent
    input_path = script_dir / INPUT_FILENAME
    output_path = script_dir / OUTPUT_FILENAME

    print("=== update_weight_history.py (weekly) ===")
    print(f"Input file:  {input_path}")
    print(f"Output file: {output_path}")

    if not input_path.exists():
        raise SystemExit(f"ERROR: Missing {input_path}")

    input_rows, input_headers = _read_csv(input_path)
    print(f"\nRead {len(input_rows)} rows from {INPUT_FILENAME}")

    daily, col_map = _extract_daily_rows(input_rows, input_headers)

    print("\nDetected columns in sample_calories.csv:")
    print(f"  date     -> {col_map.get('date')}")
    print(f"  food     -> {col_map.get('food')}")
    print(f"  exercise -> {col_map.get('exercise')}")
    print(f"  weight   -> {col_map.get('weight')}")

    print(f"\nParsed {len(daily)} daily rows (rows with a valid date).")

    weekly = _aggregate_weekly(daily)
    print(f"Computed {len(weekly)} week(s) from the input file.")

    existing = _load_existing_weekly(output_path)
    print(f"Loaded {len(existing)} existing week(s) from {OUTPUT_FILENAME}.")

    added = 0
    updated = 0

    for ws, vals in weekly.items():
        new_row = {
            "week_start": ws,
            "avg_weight": _fmt_1(vals["avg_weight"]),
            "avg_food": _fmt_0(vals["avg_food"]),
            "avg_exercise": _fmt_0(vals["avg_exercise"]),
            "avg_net": _fmt_0(vals["avg_net"]),
        }

        if ws not in existing:
            existing[ws] = new_row
            added += 1
        else:
            before = dict(existing[ws])
            existing[ws] = new_row
            if existing[ws] != before:
                updated += 1

    _write_weekly(output_path, existing)

    print("\nDone.")
    print(f"Added weeks:   {added}")
    print(f"Updated weeks: {updated}")
    print(f"Total weeks:   {len(existing)}")
    print(f"Wrote:         {output_path}")


if __name__ == "__main__":
    main()
