import csv
import os
import re
from datetime import datetime

CALORIES_PER_POUND = 3500.0


def get_data_dir():
    """
    Returns full path to the Data folder next to this script.
    Works on desktop and on iPhone (read-only from Dropbox is fine).
    """
    base_dir = os.path.dirname(__file__)
    data_dir = os.path.join(base_dir, "Data")
    return data_dir


def find_latest_csv(data_dir):
    """
    Find the most recently modified .csv file in Data/
    (ignores daily_log.csv).
    """
    candidates = []
    for name in os.listdir(data_dir):
        if not name.lower().endswith(".csv"):
            continue
        if name.lower().startswith("daily_log"):
            continue
        full = os.path.join(data_dir, name)
        if os.path.isfile(full):
            candidates.append(full)

    if not candidates:
        return None

    # newest by modification time
    candidates.sort(key=os.path.getmtime, reverse=True)
    return candidates[0]


def parse_int_like(x):
    """
    Convert strings like '1,729' or '2,024\xa0' or '-' into an int.
    '-' or empty becomes 0.
    """
    if x is None:
        return 0
    s = str(x).strip()
    if s in ("", "-", "–"):
        return 0
    # keep only digits and leading minus sign
    cleaned = re.sub(r"[^\d\-]", "", s)
    if cleaned in ("", "-"):
        return 0
    return int(cleaned)


def read_daily_summary(path):
    """
    Reads the 'Daily Summary' table from the LoseIt weekly CSV.
    Returns a list of dicts with date, calories_in, exercise, net.
    """
    records = []
    with open(path, newline="", encoding="utf-8", errors="ignore") as f:
        reader = csv.reader(f)
        in_daily = False

        for row in reader:
            if not row:
                continue

            # Look for the header row of the Daily Summary table
            if not in_daily:
                if (
                    len(row) >= 3
                    and row[0].strip() == ""
                    and row[1].strip() == "Budget"
                    and row[2].strip().startswith("Food")
                ):
                    in_daily = True
                continue

            # We are inside the Daily Summary section
            first = row[0].strip()

            # Stop when we reach a blank line or other section
            if (
                not first
                or first.lower().startswith("totals")
                or "calories" in first.lower()
                or first == "Nutrients"
            ):
                break

            # Expect dates like "10-Nov-25"
            try:
                dt = datetime.strptime(first, "%d-%b-%y").date()
            except ValueError:
                # Not a date row; stop
                break

            # unpack with safety
            budget = row[1] if len(row) > 1 else ""
            food = row[2] if len(row) > 2 else ""
            exer = row[3] if len(row) > 3 else ""
            net = row[4] if len(row) > 4 else ""
            plus_minus = row[5] if len(row) > 5 else ""

            records.append(
                {
                    "date": dt,
                    "budget": parse_int_like(budget),
                    "calories_in": parse_int_like(food),
                    "exercise": parse_int_like(exer),
                    "net": parse_int_like(net),
                    "plus_minus": parse_int_like(plus_minus),
                }
            )

    return records


def estimate_maintenance(records, start_weight, end_weight):
    """
    Use the same logic as your BMR script:
    average net calories + daily calorie gap from weight change.
    """
    if not records or len(records) < 2:
        print("Not enough days in this weekly export.")
        return None

    n_days = len(records)
    avg_net = sum(r["net"] for r in records) / n_days
    delta_w = end_weight - start_weight  # positive = gained weight
    daily_gap = (delta_w * CALORIES_PER_POUND) / n_days
    maintenance = avg_net + daily_gap

    return {
        "n_days": n_days,
        "avg_net": avg_net,
        "start_weight": start_weight,
        "end_weight": end_weight,
        "delta_weight": delta_w,
        "daily_gap": daily_gap,
        "maintenance": maintenance,
        "first_day": records[0]["date"],
        "last_day": records[-1]["date"],
    }


def print_report(result):
    if result is None:
        return

    n_days = result["n_days"]
    avg_net = result["avg_net"]
    start_w = result["start_weight"]
    end_w = result["end_weight"]
    delta_w = result["delta_weight"]
    daily_gap = result["daily_gap"]
    maint = result["maintenance"]
    first_day = result["first_day"]
    last_day = result["last_day"]

    print("\n=== LoseIt Weekly Maintenance Estimate ===")
    print(f"Dates:         {first_day}  to  {last_day}  ({n_days} days)")
    print(f"Start weight:  {start_w:.1f} lbs")
    print(f"End weight:    {end_w:.1f} lbs")
    print(f"Change:        {delta_w:+.1f} lbs")

    print()
    print(f"Average net calories (Food - Exercise): {avg_net:.0f} kcal/day")
    print(f"Estimated daily gap from weight trend:  {daily_gap:+.0f} kcal/day")
    print(f"→ Estimated maintenance:                {maint:.0f} kcal/day")

    print()
    print("Targets based on this estimate:")
    print(f"Maintain weight:      ~{maint:.0f} kcal/day net")
    print(f"Lose ~0.5 lb/week:    ~{maint - 250:.0f} kcal/day net")
    print(f"Lose ~1.0 lb/week:    ~{maint - 500:.0f} kcal/day net")
    print(f"Gain ~0.5 lb/week:    ~{maint + 250:.0f} kcal/day net")


def main():
    data_dir = get_data_dir()
    csv_path = find_latest_csv(data_dir)

    if not csv_path:
        print("No weekly LoseIt CSV found in Data/.")
        return

    print(f"Using CSV file:\n  {os.path.basename(csv_path)}")

    records = read_daily_summary(csv_path)
    if not records:
        print("Could not find a Daily Summary table in that CSV.")
        return

    first_day = records[0]["date"]
    last_day = records[-1]["date"]
    print(f"Dates in file: {first_day} to {last_day}")

    # Ask you for start & end weight for the period
    while True:
        try:
            start_w = float(input("Enter weight on first day (lbs): "))
            break
        except ValueError:
            print("  Please enter a number.")

    while True:
        try:
            end_w = float(input("Enter weight on last day (lbs): "))
            break
        except ValueError:
            print("  Please enter a number.")

    result = estimate_maintenance(records, start_w, end_w)
    print_report(result)


if __name__ == "__main__":
    main()