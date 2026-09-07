from app.db.database import engine
from app.db.models import Base, MaintenanceHistory


if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)

    print("Maintenance history table created successfully.")