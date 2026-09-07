from pathlib import Path

import pandas as pd

from app.db.database import SessionLocal
from app.db.models import TrainMovement, Section


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data" / "synthetic"


def clean_text(value):
    if pd.isna(value):
        return None

    text = str(value).strip()

    if text.lower() in {"", "nan", "none"}:
        return None

    return text


def get_or_create_section(db, section_id):
    if not section_id:
        return None

    section = (
        db.query(Section)
        .filter(Section.id == section_id)
        .first()
    )

    if section:
        return section_id

    section = Section(
        id=section_id,
        station_from=None,
        station_to=None,
        distance_km=None,
    )

    db.add(section)
    db.flush()

    return section_id


def import_train_movements():
    csv_path = DATA_DIR / "train_movements.csv"

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
        "id",
        "train_id",
        "section_id",
        "service_date",
        "scheduled_entry",
        "scheduled_exit",
        "train_type",
        "priority_class",
    ]

    for column in required_columns:
        if column not in df.columns:
            print(f"ERROR: Missing column: {column}")
            return

    db = SessionLocal()

    imported = 0
    skipped = 0

    try:
        for index, row in df.iterrows():

            movement_id = clean_text(row["id"])
            train_id = clean_text(row["train_id"])
            section_id = clean_text(row["section_id"])

            service_date = pd.to_datetime(
                row["service_date"],
                errors="coerce",
            )

            scheduled_entry = pd.to_datetime(
                row["scheduled_entry"],
                errors="coerce",
            )

            scheduled_exit = pd.to_datetime(
                row["scheduled_exit"],
                errors="coerce",
            )

            train_type = clean_text(row["train_type"])
            priority_class = clean_text(row["priority_class"])

            if (
                not movement_id
                or not train_id
                or not section_id
                or pd.isna(service_date)
                or pd.isna(scheduled_entry)
                or pd.isna(scheduled_exit)
            ):
                skipped += 1
                print(f"Skipping row {index + 1}: missing required data")
                continue

            # Create or reuse the related section.
            get_or_create_section(db, section_id)

            movement = (
                db.query(TrainMovement)
                .filter(TrainMovement.id == movement_id)
                .first()
            )

            if movement:
                print(f"Updating movement: {movement_id}")
            else:
                print(f"Adding movement: {movement_id}")
                movement = TrainMovement(id=movement_id)
                db.add(movement)

            movement.train_id = train_id
            movement.section_id = section_id
            movement.service_date = service_date.to_pydatetime()
            movement.scheduled_entry = scheduled_entry.to_pydatetime()
            movement.scheduled_exit = scheduled_exit.to_pydatetime()
            movement.train_type = train_type
            movement.priority_class = priority_class

            imported += 1

        db.commit()

        print()
        print(
            f"Successfully imported/updated "
            f"{imported} train movements."
        )
        print(f"Skipped {skipped} rows.")

    except Exception as error:
        db.rollback()

        print()
        print("ERROR while importing train movements:")
        print(error)

    finally:
        db.close()


if __name__ == "__main__":
    import_train_movements()