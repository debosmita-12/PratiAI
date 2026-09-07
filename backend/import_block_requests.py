from pathlib import Path

import pandas as pd

from app.db.database import SessionLocal
from app.db.models import BlockWindow, Section


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data" / "raw"


def clean_text(value):
    """Convert a CSV value into clean text."""
    if pd.isna(value):
        return None

    text = str(value).strip()

    if text.lower() in {"", "nan", "none"}:
        return None

    return text


def clean_date(value):
    """Convert a CSV date/time into a Python datetime."""
    if pd.isna(value):
        return None

    parsed_date = pd.to_datetime(value, errors="coerce")

    if pd.isna(parsed_date):
        return None

    return parsed_date.to_pydatetime()


def get_or_create_section(db, corridor_id):
    """Find or create a corridor/section."""

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


def import_block_requests():
    csv_path = DATA_DIR / "block_requests_india.csv"

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
        "request_id",
        "task_id",
        "department",
        "corridor_id",
        "requested_start",
        "requested_end",
        "block_type",
        "status",
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

            request_id = clean_text(row["request_id"])
            task_id = clean_text(row["task_id"])
            department = clean_text(row["department"])
            corridor_id = clean_text(row["corridor_id"])
            requested_start = clean_date(row["requested_start"])
            requested_end = clean_date(row["requested_end"])
            block_type = clean_text(row["block_type"])
            status = clean_text(row["status"])

            if not request_id or not corridor_id:
                skipped += 1
                print(
                    "Skipping row: missing request_id "
                    "or corridor_id"
                )
                continue

            if not requested_start or not requested_end:
                skipped += 1
                print(
                    f"Skipping request {request_id}: "
                    "invalid requested_start or requested_end"
                )
                continue

            # Create or reuse the corridor.
            section_id = get_or_create_section(
                db,
                corridor_id,
            )

            # Check whether this request already exists.
            block = (
                db.query(BlockWindow)
                .filter(BlockWindow.id == request_id)
                .first()
            )

            if block:
                print(f"Updating block request: {request_id}")
            else:
                print(f"Adding block request: {request_id}")
                block = BlockWindow(id=request_id)
                db.add(block)

            # Map CSV columns to database fields.
            block.section_id = section_id
            block.date = requested_start
            block.window_start = requested_start
            block.window_end = requested_end

            # Calculate the requested duration in minutes.
            duration_seconds = (
                requested_end - requested_start
            ).total_seconds()

            block.max_duration_min = max(
                0,
                int(duration_seconds / 60),
            )

            # Allow all block types initially.
            # Later, these permissions can be restricted
            # according to actual railway rules.
            block.power_block_allowed = True
            block.track_block_allowed = True
            block.signal_block_allowed = True

            block.availability_status = status or "REQUESTED"

            imported += 1

        db.commit()

        print()
        print(
            f"Successfully imported/updated "
            f"{imported} block requests."
        )
        print(f"Skipped {skipped} rows.")

    except Exception as error:
        db.rollback()

        print()
        print("ERROR while importing block requests:")
        print(error)

    finally:
        db.close()


if __name__ == "__main__":
    import_block_requests()