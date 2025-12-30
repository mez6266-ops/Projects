"""
workout_history.py

Drop this file into the same folder as your export:
    workouts_log_(2025).tab

Then you can:
- Just press ▶ Run in VS Code (no terminal arguments) and get the graph.

Optional (if you ever want):
- python workout_history.py --csv "some_other_file.tab"
- python workout_history.py --exercise "Smith Squat"
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt


# -----------------------------
# CONFIG (matches your export headers)
# -----------------------------
DATE_COL = "Date"
EXERCISE_COL = "Exercise Name"
WEIGHT_COL = "Weight"
REPS_COL = "Reps"

# Your file is tab-delimited and may include a UTF-8 BOM
TAB_SEPARATOR = "\t"
FILE_ENCODING = "utf-8-sig"  # strips BOM cleanly

# Units
CONVERT_KG_TO_LBS = False
KG_TO_LBS = 2.2046226218

# Keep 1RM estimates sane
MIN_REPS = 1
MAX_REPS = 20


@dataclass
class OneRMConfig:
    formula: str = "epley"  # "epley" or "brzycki"


def estimate_1rm(weight: float, reps: int, cfg: OneRMConfig) -> float:
    """Estimate 1RM from a set using Epley or Brzycki."""
    if reps <= 1:
        return float(weight)

    f = cfg.formula.lower()
    if f == "epley":
        return float(weight) * (1.0 + reps / 30.0)

    if f == "brzycki":
        reps = min(reps, 36)
        return float(weight) * (36.0 / (37.0 - reps))

    raise ValueError(f"Unknown formula: {cfg.formula}")


def load_workout_export(path: str) -> pd.DataFrame:
    """
    Robust loader for your tab file:
    - forces tab delimiter
    - handles BOM (utf-8-sig)
    - strips column names
    """
    df = pd.read_csv(path, sep=TAB_SEPARATOR, encoding=FILE_ENCODING, engine="python")
    df.columns = [str(c).strip() for c in df.columns]

    print("\nLoaded file:", path)
    print("Column count:", len(df.columns))
    print("Detected columns:", df.columns.tolist())

    # If we got one column, delimiter didn't split (wrong file or wrong delimiter)
    if len(df.columns) == 1:
        raise ValueError(
            "Your file loaded as a single column (did not split on tabs).\n"
            "Make sure you're using the .tab export and it is tab-delimited."
        )

    return df


def require_columns(df: pd.DataFrame, required: list[str]) -> None:
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(
            f"Missing required columns: {missing}\n"
            f"Columns found: {df.columns.tolist()}\n"
            "Tip: Compare required names to your Excel header exactly."
        )


def load_and_prepare(path: str, cfg: OneRMConfig) -> pd.DataFrame:
    df = load_workout_export(path)
    require_columns(df, [DATE_COL, EXERCISE_COL, WEIGHT_COL, REPS_COL])

    # Parse date
    df[DATE_COL] = pd.to_datetime(df[DATE_COL], errors="coerce")
    df = df.dropna(subset=[DATE_COL])

    # Numeric cleanup
    df[WEIGHT_COL] = pd.to_numeric(df[WEIGHT_COL], errors="coerce")
    df[REPS_COL] = pd.to_numeric(df[REPS_COL], errors="coerce")
    df = df.dropna(subset=[WEIGHT_COL, REPS_COL, EXERCISE_COL])

    df[REPS_COL] = df[REPS_COL].astype(int)

    if CONVERT_KG_TO_LBS:
        df[WEIGHT_COL] = df[WEIGHT_COL] * KG_TO_LBS

    # Filter reps to reasonable range
    df = df[(df[REPS_COL] >= MIN_REPS) & (df[REPS_COL] <= MAX_REPS)]

    # Standardize exercise strings
    df[EXERCISE_COL] = df[EXERCISE_COL].astype(str).str.strip()

    # Compute estimated 1RM per set
    df["est_1rm"] = [
        estimate_1rm(w, r, cfg)
        for w, r in zip(df[WEIGHT_COL].tolist(), df[REPS_COL].tolist())
    ]

    print("Rows after cleaning:", len(df))
    return df


def best_1rm_per_day(df: pd.DataFrame) -> pd.DataFrame:
    """
    Best estimated 1RM per day per exercise (so multiple sets collapse nicely).
    """
    daily = (
        df.groupby([DATE_COL, EXERCISE_COL], as_index=False)["est_1rm"]
        .max()
        .sort_values([EXERCISE_COL, DATE_COL])
    )
    return daily


def plot_exercise_history(daily: pd.DataFrame, exercise: str) -> None:
    """
    Line chart of estimated 1RM over time for one exercise.
    Labels PR points.
    """
    sub = daily[daily[EXERCISE_COL].str.lower() == exercise.lower()].copy()
    if sub.empty:
        examples = daily[EXERCISE_COL].drop_duplicates().head(30).tolist()
        raise ValueError(
            f"No rows found for exercise '{exercise}'.\n"
            f"Examples from your file:\n{examples}"
        )

    sub = sub.sort_values(DATE_COL)
    sub["pr"] = sub["est_1rm"].cummax()
    sub["is_pr"] = sub["est_1rm"] >= sub["pr"] - 1e-9

    plt.figure()
    plt.plot(sub[DATE_COL], sub["est_1rm"], marker="o", linewidth=1)
    plt.title(f"Estimated 1RM over time — {exercise}")
    plt.xlabel("Date")
    plt.ylabel("Estimated 1RM (lbs)")
    plt.grid(True, alpha=0.3)

    # Label PR points
    pr_points = sub[sub["is_pr"]]
    for _, row in pr_points.iterrows():
        plt.annotate(
            f'{row["est_1rm"]:.0f}',
            (row[DATE_COL], row["est_1rm"]),
            textcoords="offset points",
            xytext=(0, 8),
            ha="center",
            fontsize=8
        )

    plt.tight_layout()
    plt.show()


def plot_days_since_pr(daily: pd.DataFrame, top_n: int = 20, min_sessions: int = 6) -> None:
    """
    Bar chart: exercises with the longest time since estimated-1RM PR.
    """
    stats = []
    for ex, g in daily.groupby(EXERCISE_COL):
        g = g.sort_values(DATE_COL)
        sessions = len(g)
        if sessions < min_sessions:
            continue

        pr_value = g["est_1rm"].max()
        pr_date = g.loc[g["est_1rm"].idxmax(), DATE_COL]
        last_date = g[DATE_COL].max()
        days_since_pr = (last_date - pr_date).days

        stats.append((ex, sessions, float(pr_value), pr_date, last_date, int(days_since_pr)))

    if not stats:
        raise ValueError(
            "Not enough data to compute PR gaps.\n"
            "Try lowering min_sessions (example: --min_sessions 3)."
        )

    stats_df = pd.DataFrame(
        stats,
        columns=["exercise", "sessions", "pr_1rm", "pr_date", "last_date", "days_since_pr"]
    ).sort_values("days_since_pr", ascending=False).head(top_n)

    plt.figure()
    plt.barh(stats_df["exercise"], stats_df["days_since_pr"])
    plt.title(f"How long since PR (estimated 1RM) — top {len(stats_df)} exercises")
    plt.xlabel("Days since PR")
    plt.ylabel("Exercise")
    plt.gca().invert_yaxis()
    plt.grid(True, axis="x", alpha=0.3)

    for i, row in enumerate(stats_df.itertuples(index=False)):
        plt.text(row.days_since_pr, i, f"  {row.days_since_pr}d", va="center", fontsize=8)

    plt.tight_layout()
    plt.show()

    print("\n--- Days since PR summary ---")
    print(stats_df.to_string(index=False))


def main():
    """
    Run-without-typing mode:
    - If --csv is not provided, we automatically use workouts_log_(2025).tab
      from the same folder as this script.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", default=None, help="Optional path to workout export (tab-delimited)")
    parser.add_argument("--exercise", default=None, help="Optional: exercise name to plot 1RM history")
    parser.add_argument("--formula", default="epley", choices=["epley", "brzycki"], help="1RM formula")
    parser.add_argument("--top_n", type=int, default=20, help="How many exercises to show")
    parser.add_argument("--min_sessions", type=int, default=6, help="Min logged days to include an exercise")

    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent

    if args.csv:
        data_file = Path(args.csv)
    else:
        # This is the “forever default” file name in the same folder
        data_file = script_dir / "workouts_log_(2025).tab"

    if not data_file.exists():
        raise FileNotFoundError(
            f"Could not find workout file:\n{data_file}\n\n"
            "Fix:\n"
            "- Put workouts_log_(2025).tab in the same folder as workout_history.py\n"
            "- OR run with: python workout_history.py --csv <path>"
        )

    print(f"\nUsing workout file: {data_file}")

    cfg = OneRMConfig(formula=args.formula)
    df = load_and_prepare(str(data_file), cfg)
    daily = best_1rm_per_day(df)

    # Optional single exercise history chart
    if args.exercise:
        plot_exercise_history(daily, args.exercise)

    # Always show the PR-gap chart
    plot_days_since_pr(daily, top_n=args.top_n, min_sessions=args.min_sessions)


if __name__ == "__main__":
    main()
