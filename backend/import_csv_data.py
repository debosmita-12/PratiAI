from pathlib import Path
import pandas as pd

from app.db.database import SessionLocal
from app.db.models import Station


# Project root:
# PratiAI-main/
BASE_DIR = Path(__file__).resolve().parents[1]

# Your original datasets
DATA_DIR = BASE_DIR / "data" / "raw"


def import_stations():
    csv_path = DATA_DIR / "stations.csv"

    if not csv_path.exists():
        print(f"ERROR: File not found: {csv_path}")
        return

    print(f"Reading: {csv_path}")

    df = pd.read_csv(csv_path)

    required_columns = [
        "code",
        "name",
        "latitude",
        "longitude",
    ]

    for column in required_columns:
        if column not in df.columns:
            print(f"ERROR: Missing column: {column}")
            return

    db = SessionLocal()

    try:
        imported = 0
        skipped = 0

        for _, row in df.iterrows():
            code = str(row["code"]).strip().upper()
            name = str(row["name"]).strip()

            if not code or code == "NAN":
                skipped += 1
                continue

            existing = (
                db.query(Station)
                .filter(Station.code == code)
                .first()
            )

            if existing:
                existing.name = name
                existing.lat = float(row["latitude"])
                existing.lon = float(row["longitude"])
            else:
                station = Station(
                    code=code,
                    name=name,
                    lat=float(row["latitude"]),
                    lon=float(row["longitude"]),
                )

                db.add(station)

            imported += 1

        db.commit()

        print(f"Successfully imported/updated {imported} stations.")
        print(f"Skipped {skipped} rows.")

    except Exception as error:
        db.rollback()
        print("ERROR while importing stations:")
        print(error)

    finally:
        db.close()


if __name__ == "__main__":
    import_stations()