import pandas as pd
import numpy as np
import os
import sys
from datetime import datetime
import uuid

# Add backend app to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/backend")
from app.db.database import SessionLocal, engine
from app.db.models import Base, Station, Section, Asset, MaintenanceTask, BlockWindow, TrainMovement

def seed_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    
    print("Seeding REAL Indian Railways stations (Delhi-Mumbai Corridor snippet)...")
    real_stations = [
        {"code": "NDLS", "name": "New Delhi", "lat": 28.6415, "lon": 77.2209},
        {"code": "MTJ", "name": "Mathura Jn", "lat": 27.4725, "lon": 77.6726},
        {"code": "AGC", "name": "Agra Cantt", "lat": 27.1598, "lon": 77.9890},
        {"code": "GWL", "name": "Gwalior", "lat": 26.2166, "lon": 78.1751},
        {"code": "VGLJ", "name": "VGL Jhansi", "lat": 25.4484, "lon": 78.5804},
        {"code": "BPL", "name": "Bhopal Jn", "lat": 23.2599, "lon": 77.4126},
        {"code": "ET", "name": "Itarsi Jn", "lat": 22.6178, "lon": 77.7667},
        {"code": "KNW", "name": "Khandwa", "lat": 21.8242, "lon": 76.3533},
        {"code": "BSL", "name": "Bhusaval Jn", "lat": 21.0455, "lon": 75.8011},
        {"code": "MMR", "name": "Manmad Jn", "lat": 20.2458, "lon": 74.4357},
        {"code": "NK", "name": "Nashik Road", "lat": 19.9809, "lon": 73.8155},
        {"code": "KYN", "name": "Kalyan Jn", "lat": 19.2354, "lon": 73.1299},
        {"code": "CSMT", "name": "Mumbai CSMT", "lat": 18.9398, "lon": 72.8354}
    ]
    
    for st in real_stations:
        db.add(Station(**st))
        
    print("Generating Sections...")
    sections = []
    for i in range(len(real_stations) - 1):
        st_from = real_stations[i]
        st_to = real_stations[i+1]
        dist = np.sqrt((st_from["lat"] - st_to["lat"])**2 + (st_from["lon"] - st_to["lon"])**2) * 111
        sec_id = f"SEC_{st_from['code']}_{st_to['code']}"
        sections.append(sec_id)
        db.add(Section(id=sec_id, station_from=st_from["code"], station_to=st_to["code"], distance_km=dist))

    # Read synthetic maintenance data
    print("Loading synthetic ML maintenance data into DB...")
    tasks_df = pd.read_csv("data/synthetic/maintenance_tasks.csv")
    blocks_df = pd.read_csv("data/synthetic/block_windows.csv")
    
    # We map the synthetic data into the new DB schema
    # Just creating a few mock assets and tasks to fill the dashboard
    for sec_id in sections:
        for _ in range(3):
            ast_id = f"AST_{uuid.uuid4().hex[:8]}"
            db.add(Asset(id=ast_id, department_id="ENGINEERING", asset_type="TRACK", section_id=sec_id, location_km=10.0, criticality_class="HIGH", condition_score=0.6))
            db.add(MaintenanceTask(id=f"TSK_{ast_id}", asset_id=ast_id, department_id="ENGINEERING", task_type="PREVENTIVE", priority_class="P1", required_duration_min=120, safety_critical=True))
        
        # Add blocks
        for b in range(2):
            b_id = f"BLK_{sec_id}_{b}"
            db.add(BlockWindow(id=b_id, section_id=sec_id, date=datetime.now(), window_start=datetime.now(), window_end=datetime.now(), max_duration_min=240, availability_status="AVAILABLE"))
            
    db.commit()
    db.close()
    print("Database seeding complete!")

if __name__ == "__main__":
    seed_db()
