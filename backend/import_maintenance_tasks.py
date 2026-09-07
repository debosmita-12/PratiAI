from pathlib import Path

import pandas as pd

from app.db.database import SessionLocal
from app.db.models import Asset, Department, MaintenanceTask, Section


# Project root:
# C:\Users\User\Downloads\PratiAI-main
BASE_DIR = Path(__file__).resolve().parents[1]

# CSV location:
# C:\Users\User\Downloads\PratiAI-main\data\raw
DATA_DIR = BASE_DIR / "data" / "raw"


def clean_text(value):
    """Convert a CSV value into clean text."""
    if pd.isna(value):
        return None

    text = str(value).strip()

    if text.lower() in {"", "nan", "none"}:
        return None

    return text


def clean_int(value):
    """Convert a CSV value into an integer."""
    try:
        if pd.isna(value):
            return None

        return int(float(value))

    except (ValueError, TypeError):
        return None


def clean_bool(value):
    """Convert common CSV values into True or False."""
    if pd.isna(value):
        return False

    text = str(value).strip().lower()

    return text in {
        "true",
        "yes",
        "y",
        "1",
        "critical",
        "high",
    }


def clean_date(value):
    """Convert a CSV date into a Python datetime."""
    if pd.isna(value):
        return None

    parsed_date = pd.to_datetime(value, errors="coerce")

    if pd.isna(parsed_date):
        return None

    return parsed_date.to_pydatetime()


def get_or_create_department(db, department_name):
    """Find or create a department."""

    if not department_name:
        return None

    department_id = (
        department_name.upper()
        .replace(" ", "_")
        .replace("-", "_")
    )

    department = (
        db.query(Department)
        .filter(Department.id == department_id)
        .first()
    )

    if department:
        return department_id

    department = Department(
        id=department_id,
        name=department_name,
    )

    db.add(department)
    db.flush()

    return department_id


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


def import_maintenance_tasks():
    csv_path = DATA_DIR / "maintenance_tasks.csv"

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
        "task_id",
        "asset_id",
        "corridor_id",
        "department",
        "task_description",
        "criticality",
        "status",
        "last_due_date",
        "recommended_date",
        "estimated_duration_hours",
        "risk_if_delayed",
        "priority_score",
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

            task_id = clean_text(row["task_id"])
            asset_id = clean_text(row["asset_id"])
            corridor_id = clean_text(row["corridor_id"])
            department_name = clean_text(row["department"])

            # Every task must have an ID and an existing asset.
            if not task_id or not asset_id:
                skipped += 1
                print("Skipping row: missing task_id or asset_id")
                continue

            asset = (
                db.query(Asset)
                .filter(Asset.id == asset_id)
                .first()
            )

            if not asset:
                skipped += 1
                print(
                    f"Skipping task {task_id}: "
                    f"asset {asset_id} does not exist"
                )
                continue

            # Create or reuse related department and corridor.
            department_id = get_or_create_department(
                db,
                department_name,
            )

            section_id = get_or_create_section(
                db,
                corridor_id,
            )

            criticality = clean_text(row["criticality"])
            status = clean_text(row["status"])
            task_description = clean_text(row["task_description"])

            # Convert the CSV priority score into a priority class.
            priority_score = clean_int(row["priority_score"])

            if priority_score is not None:
                if priority_score >= 80:
                    priority_class = "CRITICAL"
                elif priority_score >= 60:
                    priority_class = "HIGH"
                elif priority_score >= 40:
                    priority_class = "MEDIUM"
                else:
                    priority_class = "LOW"
            else:
                priority_class = criticality

            # Check whether the task already exists.
            task = (
                db.query(MaintenanceTask)
                .filter(MaintenanceTask.id == task_id)
                .first()
            )

            if task:
                print(f"Updating task: {task_id}")
            else:
                print(f"Adding task: {task_id}")
                task = MaintenanceTask(id=task_id)
                db.add(task)

            # Map CSV columns to database fields.
            task.asset_id = asset_id
            task.department_id = department_id
            task.task_type = task_description or "Maintenance"
            task.priority_class = priority_class
            task.required_duration_min = (
                clean_int(row["estimated_duration_hours"]) * 60
                if clean_int(row["estimated_duration_hours"]) is not None
                else None
            )

            task.days_since_last_maintenance = None
            task.overdue_days = None

            task.safety_critical = (
                criticality.upper()
                in {
                    "HIGH",
                    "CRITICAL",
                    "SAFETY",
                    "SAFETY-CRITICAL",
                    "SAFETY_CRITICAL",
                }
                if criticality
                else False
            )

            task.dependency_group = section_id
            task.crew_type = department_name

            imported += 1

        db.commit()

        print()
        print(
            f"Successfully imported/updated "
            f"{imported} maintenance tasks."
        )
        print(f"Skipped {skipped} rows.")

    except Exception as error:
        db.rollback()

        print()
        print("ERROR while importing maintenance tasks:")
        print(error)

    finally:
        db.close()


if __name__ == "__main__":
    import_maintenance_tasks()