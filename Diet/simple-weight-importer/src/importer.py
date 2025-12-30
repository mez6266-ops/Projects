from pathlib import Path
import csv

def read_sample_calories(file_path: Path):
    with file_path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)

def append_to_weight_history(data: list, weight_history_path: Path):
    existing_dates = set()
    
    if weight_history_path.exists():
        with weight_history_path.open("r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            existing_dates = {row['date'] for row in reader}

    with weight_history_path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["date", "calories"])
        if f.tell() == 0:  # Check if the file is empty
            writer.writeheader()

        for entry in data:
            if entry['date'] not in existing_dates:
                writer.writerow(entry)

def import_calories(sample_file: Path, weight_history_file: Path):
    data = read_sample_calories(sample_file)
    append_to_weight_history(data, weight_history_file)