from pathlib import Path
from datetime import datetime, timedelta

import pandas as pd

from app.db.database import SessionLocal
from app.db.models import BlockWindow, Section


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data" / "raw"


def clean_text(value):
    if pd.isna(value):
        return None

    text = str(value).strip()

    if text.lower() in {"", "nan", "none"}:
        return None

    return text


def combine_date_and_time(date_value, time_value):
    """
    Combine separate CSV date and time values.

    Example:
    date = 2026-01-01
    time = 23:00

    Result:
    2026-01-01 23:00:00
    """

    date_text = clean_text(date_value)
    time_text = clean_text(time_value)

    if not date_text or not time_text:
        return None

    try:
        return datetime.strptime(
            f"{date_text} {time_text}",
            "%Y-%m-%d %H:%M",
        )

    except ValueError:
        return None


def get_or_create_section(db, corridor_id):
    """Find an existing corridor or create it."""

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


def import_corridor_availability():
    csv_path = DATA_DIR / "corridor_availability_india.csv"

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
        "corridor_id",
        "date",
        "available_start",
        "available_end",
        "restriction",
        "power_isolation_required",
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

            corridor_id = clean_text(row["corridor_id"])
            date_value = clean_text(row["date"])
            start_time = clean_text(row["available_start"])
            end_time = clean_text(row["available_end"])
            restriction = clean_text(row["restriction"])
            power_isolation_required = clean_text(
                row["power_isolation_required"]
            )

            if not corridor_id:
                skipped += 1
                continue

            # Combine the separate date and time columns.
            available_start = combine_date_and_time(
                date_value,
                start_time,
            )

            available_end = combine_date_and_time(
                date_value,
                end_time,
            )

            if not available_start or not available_end:
                skipped += 1
                print(
                    f"Skipping row {index + 1}: "
                    "invalid date or time"
                )
                continue

            # Handle overnight windows.
            # Example: 23:00 -> 02:00
            # The ending time belongs to the next day.
            if available_end <= available_start:
                available_end = available_end + timedelta(days=1)

            section_id = get_or_create_section(
                db,
                corridor_id,
            )

            # Create a unique ID for each corridor/date/window.
            availability_id = (
                f"AVAIL_{corridor_id}_"
                f"{available_start.strftime('%Y%m%d%H%M')}_"
                f"{available_end.strftime('%Y%m%d%H%M')}"
            )

            block = (
                db.query(BlockWindow)
                .filter(BlockWindow.id == availability_id)
                .first()
            )

            if block:
                print(
                    f"Updating availability: "
                    f"{availability_id}"
                )
            else:
                print(
                    f"Adding availability: "
                    f"{availability_id}"
                )
                block = BlockWindow(id=availability_id)
                db.add(block)

            # Store the availability information.
            block.section_id = section_id
            block.date = available_start
            block.window_start = available_start
            block.window_end = available_end

            duration_seconds = (
                available_end - available_start
            ).total_seconds()

            block.max_duration_min = int(
                duration_seconds / 60
            )

            block.availability_status = (
                restriction or "AVAILABLE"
            )

            # Convert power-isolation requirement.
            power_required = (
                power_isolation_required.lower()
                if power_isolation_required
                else ""
            )

            requires_power_isolation = power_required in {
                "true",
                "yes",
                "y",
                "1",
            }

            # The current database model has no separate
            # power_isolation_required column.
            # The requirement is preserved in the CSV.
            # Power blocks remain allowed for now.
            block.power_block_allowed = True

            restriction_lower = (
                restriction.lower()
                if restriction
                else ""
            )

            block.track_block_allowed = not any(
                word in restriction_lower
                for word in [
                    "no track",
                    "track unavailable",
                    "track blocked",
                ]
            )

            block.signal_block_allowed = not any(
                word in restriction_lower
                for word in [
                    "no signal",
                    "signal unavailable",
                    "signal blocked",
                ]
            )

            imported += 1

        db.commit()

        print()
        print(
            f"Successfully imported/updated "
            f"{imported} corridor-availability records."
        )
        print(f"Skipped {skipped} rows.")

    except Exception as error:
        db.rollback()

        print()
        print("ERROR while importing corridor availability:")
        print(error)

    finally:
        db.close()


if __name__ == "__main__":
    import_corridor_availability()