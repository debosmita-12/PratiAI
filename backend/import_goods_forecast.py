import pandas as pd
from pathlib import Path
from datetime import datetime
from sqlalchemy.orm import Session

from app.db.database import engine
from app.db.models import GoodsTrainForecast


CSV_PATH = Path("../data/raw/goods_train_forecast_generated.csv")


def import_goods_forecasts():
    df = pd.read_csv(CSV_PATH)

    imported = 0
    skipped = 0

    with Session(engine) as db:
        for index, row in df.iterrows():
            try:
                forecast_date = pd.to_datetime(row["forecast_date"]).to_pydatetime()

                forecast_id = (
                    f"{row['corridor_id']}_"
                    f"{row['forecast_date']}"
                )

                existing = db.query(GoodsTrainForecast).filter_by(
                    id=forecast_id
                ).first()

                if existing:
                    forecast = existing
                else:
                    forecast = GoodsTrainForecast(id=forecast_id)
                    db.add(forecast)

                forecast.forecast_date = forecast_date
                forecast.corridor_id = str(row["corridor_id"])
                forecast.zone = str(row["zone"])
                forecast.density_tier = str(row["density_tier"])
                forecast.predicted_goods_trains = int(
                    row["predicted_goods_trains"]
                )
                forecast.lower_bound = int(row["lower_bound"])
                forecast.upper_bound = int(row["upper_bound"])
                forecast.forecast_horizon_days = int(
                    row["forecast_horizon_days"]
                )
                forecast.data_source = str(row["data_source"])

                imported += 1

            except Exception as error:
                skipped += 1
                print(f"Skipped row {index}: {error}")

        db.commit()

    print(f"Imported/updated: {imported}")
    print(f"Skipped: {skipped}")


if __name__ == "__main__":
    import_goods_forecasts()