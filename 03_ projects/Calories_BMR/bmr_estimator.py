import csv
import os
from datetime import date

CALORIES_PER_POUND = 3500.0


def get_data_path():
    """Return full path to Data/daily_log.csv next to this script."""
    base_dir = os.path.dirname(__file__)          # folder of this .py file
    data_dir = os.path.join(base_dir, "Data")     # .../Calories_BMR/Data
    os.makedirs(data_dir, exist_ok=True)          # create Data/ if missing
    return os.path.join(data_dir, "daily_log.csv")


def append_today_to_csv(path):
    """Ask user for today's data and append it to the CSV."""
    print("\nEnter today's data:")

    today_str = str(date.today())  # e.g. 2025-11-21
    print(f"  Date (auto): {today_str}")

    # calories in
    while True:
        try:
            cal_in = float(input("  Calories eaten: "))
            break
        except ValueError:
            print("    Please enter a number.")

    # exercise calories
    while True:
        try:
            ex_cals = float(input("  Exercise calories (0 if none): "))
            break
        except ValueError:
            print("    Please enter a number.")

    # weight
    while True:
        try:
            weight = float(input("  Weight (lbs): "))
            break
        except ValueError:
            print("    Please enter a number.")

    file_exists = os.path.exists(path)

    with open(path, "a", newline="") as f:
        writer = csv.writer(f)
        if not file_exists:
            # write header if new file
            writer.writerow(["Date", "CaloriesIn", "ExerciseCals", "WeightLbs"])
        writer.writerow([today_str, cal_in, ex_cals, weight])

    print("  Saved.\n")


def read_daily_log(path):
    """Read all rows from the CSV into a list of dicts."""
    if not os.path.exists(path):
        print("No log file yet – add some days first.")
        return []

    records = []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                cal_in = float(row["CaloriesIn"])
                ex_cals = float(row["ExerciseCals"])
                weight = float(row["WeightLbs"])
            except (ValueError, KeyError) as e:
                print("Skipping bad row:", row, "Error:", e)
                continue

            net = cal_in - ex_cals
            records.append({
                "cal_in": cal_in,
                "ex_cals": ex_cals,
                "net": net,
                "weight": weight,
            })
    return records


def estimate_maintenance(records):
    if not records or len(records) < 2:
        print("Not enough days to estimate – need at least 2.")
        return None

    n_days = len(records)
    total_net = sum(r["net"] for r in records)
    avg_net = total_net / n_days

    start_weight = records[0]["weight"]
    end_weight = records[-1]["weight"]
    delta_weight = end_weight - start_weight

    # daily calorie gap that explains the weight change
    daily_gap = (delta_weight * CALORIES_PER_POUND) / n_days
    estimated_maintenance = avg_net + daily_gap

    return {
        "n_days": n_days,
        "avg_net": avg_net,
        "start_weight": start_weight,
        "end_weight": end_weight,
        "delta_weight": delta_weight,
        "daily_gap": daily_gap,
        "maintenance": estimated_maintenance,
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

    print("\n=== Personal Maintenance Estimator ===")
    print(f"Days in log:   {n_days}")
    print(f"Start weight:  {start_w:.1f} lbs")
    print(f"End weight:    {end_w:.1f} lbs")
    print(f"Change:        {delta_w:+.1f} lbs over {n_days} days")

    print()
    print(f"Average net calories (in - exercise): {avg_net:.0f} kcal/day")
    print(f"Estimated daily gap from trend:       {daily_gap:+.0f} kcal/day")
    print(f"→ Estimated maintenance:              {maint:.0f} kcal/day")

    print()
    print("Targets based on this estimate:")
    print(f"Maintain weight:      ~{maint:.0f} kcal/day net")
    print(f"Lose ~0.5 lb/week:    ~{maint - 250:.0f} kcal/day net")
    print(f"Lose ~1.0 lb/week:    ~{maint - 500:.0f} kcal/day net")
    print(f"Gain ~0.5 lb/week:    ~{maint + 250:.0f} kcal/day net")


def main():
    data_path = get_data_path()

    choice = input("Add today's data to the log? (y/n): ").strip().lower()
    if choice.startswith("y"):
        append_today_to_csv(data_path)

    records = read_daily_log(data_path)
    result = estimate_maintenance(records)
    print_report(result)


if __name__ == "__main__":
    main()