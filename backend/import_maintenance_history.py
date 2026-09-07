from pathlib import Path

import pandas as pd

from app.db.database import SessionLocal
from app.db.models import (
    Asset,
    MaintenanceHistory,
    Section,
)


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data" / "raw"


def clean_text(value):
    if pd.isna(value):
        return None

    text = str(value).strip()

    if text.lower() in {"", "nan", "none"}:
        return None

    return text


def clean_int(value):
    try:
        if pd.isna(value):
            return None

        return int(float(value))

    except (ValueError, TypeError):
        return None


def clean_float(value):
    try:
        if pd.isna(value):
            return None

        return float(value)

    except (ValueError, TypeError):
        return None


def clean_date(value):
    if pd.isna(value):
        return None

    parsed_date = pd.to_datetime(value, errors="coerce")

    if pd.isna(parsed_date):
        return None

    return parsed_date.to_pydatetime()


def get_or_create_section(db, corridor_id):
    if not corridor_id:
        return None

    section = (
        db.query(Section)
        .filter(Section.id == corridor_id)
        .first()
    )

    if section:
        return corridor_id

    section = Section(
        id=corridor_id,
        station_from=None,
        station_to=None,
        distance_km=None,
    )

    db.add(section)
    db.flush()

    return corridor_id


def import_maintenance_history():
    csv_path = DATA_DIR / "maintenance_history.csv"

    if not csv_path.exists():
        print(f"ERROR: File not found: {csv_path}")
        return

    print(f"Reading: {csv_path}")

    try:
        df = pd.read_csv(csv_path)
    except Exception as error:
        print("ERROR while reading the CSV file:")
        print(error)
        return

    required_columns = [
        "history_id",
        "task_id",
        "asset_id",
        "corridor_id",
        "planned_date",
        "actual_date",
        "maintenance_type",
        "department",
        "planned_duration_hours",
        "actual_duration_hours",
        "completion_status",
        "delay_minutes",
        "remarks",
    ]

    for column in required_columns:
        if column not in df.columns:
            print(f"ERROR: Missing column: {column}")
            return

    db = SessionLocal()

    imported = 0
    skipped = 0

    try:
        for _, row in df.iterrows():

            history_id = clean_text(row["history_id"])
            task_id = clean_text(row["task_id"])
            asset_id = clean_text(row["asset_id"])
            corridor_id = clean_text(row["corridor_id"])

            if not history_id or not asset_id:
                skipped += 1
                continue

            # Check that the referenced asset exists.
            asset = (
                db.query(Asset)
                .filter(Asset.id == asset_id)
                .first()
            )

            if not asset:
                skipped += 1
                print(
                    f"Skipping history {history_id}: "
                    f"asset {asset_id} does not exist"
                )
                continue

            # Create or reuse the corridor.
            get_or_create_section(db, corridor_id)

            # Check whether this history record already exists.
            history = (
                db.query(MaintenanceHistory)
                .filter(MaintenanceHistory.id == history_id)
                .first()
            )

            if history:
                print(f"Updating history: {history_id}")
            else:
                print(f"Adding history: {history_id}")
                history = MaintenanceHistory(id=history_id)
                db.add(history)

            # Map CSV columns to database fields.
            history.task_id = task_id
            history.asset_id = asset_id
            history.corridor_id = corridor_id
            history.planned_date = clean_date(
                row["planned_date"]
            )
            history.actual_date = clean_date(
                row["actual_date"]
            )
            history.maintenance_type = clean_text(
                row["maintenance_type"]
            )
            history.department = clean_text(
                row["department"]
            )
            history.planned_duration_hours = clean_float(
                row["planned_duration_hours"]
            )
            history.actual_duration_hours = clean_float(
                row["actual_duration_hours"]
            )
            history.completion_status = clean_text(
                row["completion_status"]
            )
            history.delay_minutes = clean_int(
                row["delay_minutes"]
            )
            history.remarks = clean_text(
                row["remarks"]
            )

            imported += 1

        db.commit()

        print()
        print(
            f"Successfully imported/updated "
            f"{imported} maintenance-history records."
        )
        print(f"Skipped {skipped} rows.")

    except Exception as error:
        db.rollback()

        print()
        print("ERROR while importing maintenance history:")
        print(error)

    finally:
        db.close()


if __name__ == "__main__":
    import_maintenance_history()