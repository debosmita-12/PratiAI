import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

def generate_stations_and_sections():
    stations = pd.DataFrame({
        'code': ['STN1', 'STN2', 'STN3', 'STN4', 'STN5'],
        'name': ['Station 1', 'Station 2', 'Station 3', 'Station 4', 'Station 5'],
        'lat': [28.6, 28.7, 28.8, 28.9, 29.0],
        'lon': [77.2, 77.3, 77.4, 77.5, 77.6]
    })
    
    sections = pd.DataFrame({
        'id': ['SEC1', 'SEC2', 'SEC3', 'SEC4'],
        'station_from': ['STN1', 'STN2', 'STN3', 'STN4'],
        'station_to': ['STN2', 'STN3', 'STN4', 'STN5'],
        'distance_km': [10.5, 12.0, 8.5, 15.0]
    })
    return stations, sections

def generate_synthetic_assets(sections):
    np.random.seed(42)
    assets = []
    
    departments = ['ENGINEERING', 'SMT', 'TRD']
    for i in range(200):
        dept = np.random.choice(departments)
        if dept == 'ENGINEERING':
            asset_type = np.random.choice(['TRACK', 'POINT', 'BRIDGE'])
        elif dept == 'SMT':
            asset_type = np.random.choice(['SIGNAL', 'TRACK_CIRCUIT', 'RELAY'])
        else:
            asset_type = np.random.choice(['OHE_MAST', 'CANTILEVER', 'INSULATOR'])
            
        sec = np.random.choice(sections['id'])
        assets.append({
            'asset_id': f'AST_{i}',
            'asset_type': asset_type,
            'department': dept,
            'section_id': sec,
            'location_from_km': np.round(np.random.uniform(0, 10), 2),
            'installation_date': datetime(2010, 1, 1) + timedelta(days=np.random.randint(0, 3650)),
            'criticality_class': np.random.choice(['HIGH', 'MEDIUM', 'LOW'], p=[0.2, 0.5, 0.3]),
            'safety_flag': np.random.choice([True, False], p=[0.3, 0.7]),
            'condition_score': np.round(np.random.uniform(0.4, 1.0), 2),
            'days_since_maintenance': np.random.randint(10, 300),
            'defect_history': np.random.randint(0, 5),
            'traffic_load': np.random.randint(50, 200)
        })
    return pd.DataFrame(assets)

def generate_maintenance_tasks(assets):
    np.random.seed(43)
    tasks = []
    for _, asset in assets.iterrows():
        # Higher risk if condition is low, days since maintenance is high, or history is high
        risk_score = (1 - asset['condition_score']) * 2 + (asset['days_since_maintenance'] / 300) + (asset['defect_history'] / 5)
        if risk_score > 1.5 or np.random.rand() > 0.8:
            tasks.append({
                'task_id': f"TSK_{asset['asset_id']}",
                'asset_id': asset['asset_id'],
                'department': asset['department'],
                'section_id': asset['section_id'],
                'task_type': 'PREVENTIVE' if risk_score < 2 else 'CORRECTIVE',
                'priority_class': 'P1' if asset['criticality_class'] == 'HIGH' else ('P2' if asset['criticality_class'] == 'MEDIUM' else 'P3'),
                'required_duration_min': np.random.choice([60, 120, 180, 240]),
                'overdue_days': np.random.randint(0, 30) if np.random.rand() > 0.5 else 0,
                'safety_critical': asset['safety_flag'],
                'crew_type': f"CREW_{asset['department']}"
            })
    return pd.DataFrame(tasks)

def generate_block_windows(sections):
    np.random.seed(44)
    blocks = []
    start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    for d in range(7):
        current_date = start_date + timedelta(days=d)
        for sec in sections['id']:
            # Generate 1-2 blocks per section per day
            for _ in range(np.random.randint(1, 3)):
                start_hour = np.random.randint(0, 20)
                duration = np.random.choice([120, 180, 240])
                w_start = current_date + timedelta(hours=start_hour)
                blocks.append({
                    'block_id': f"BLK_{sec}_{d}_{start_hour}",
                    'section_id': sec,
                    'date': current_date.strftime('%Y-%m-%d'),
                    'window_start': w_start.strftime('%Y-%m-%d %H:%M:%S'),
                    'window_end': (w_start + timedelta(minutes=int(duration))).strftime('%Y-%m-%d %H:%M:%S'),
                    'max_duration_min': duration,
                    'power_block_allowed': True,
                    'track_block_allowed': True,
                    'signal_block_allowed': True,
                    'availability_status': 'AVAILABLE'
                })
    return pd.DataFrame(blocks)

def generate_train_movements(sections):
    np.random.seed(45)
    trains = []
    start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    for d in range(7):
        current_date = start_date + timedelta(days=d)
        for t in range(50):
            train_id = f"TRN_{t}"
            t_type = np.random.choice(['PASSENGER', 'EXPRESS', 'FREIGHT'])
            priority = 'HIGH' if t_type == 'EXPRESS' else ('MEDIUM' if t_type == 'PASSENGER' else 'LOW')
            sec = np.random.choice(sections['id'])
            
            entry_hour = np.random.randint(0, 23)
            entry_min = np.random.randint(0, 59)
            entry_time = current_date + timedelta(hours=entry_hour, minutes=entry_min)
            duration = np.random.randint(15, 60)
            
            trains.append({
                'id': f"MV_{train_id}_{sec}_{d}",
                'train_id': train_id,
                'section_id': sec,
                'service_date': current_date.strftime('%Y-%m-%d'),
                'scheduled_entry': entry_time.strftime('%Y-%m-%d %H:%M:%S'),
                'scheduled_exit': (entry_time + timedelta(minutes=int(duration))).strftime('%Y-%m-%d %H:%M:%S'),
                'train_type': t_type,
                'priority_class': priority
            })
    return pd.DataFrame(trains)

if __name__ == "__main__":
    out_dir = "../data/synthetic"
    ensure_dir(out_dir)
    
    stations, sections = generate_stations_and_sections()
    stations.to_csv(f"{out_dir}/stations.csv", index=False)
    sections.to_csv(f"{out_dir}/sections.csv", index=False)
    
    assets = generate_synthetic_assets(sections)
    assets.to_csv(f"{out_dir}/assets.csv", index=False)
    
    tasks = generate_maintenance_tasks(assets)
    tasks.to_csv(f"{out_dir}/maintenance_tasks.csv", index=False)
    
    blocks = generate_block_windows(sections)
    blocks.to_csv(f"{out_dir}/block_windows.csv", index=False)
    
    trains = generate_train_movements(sections)
    trains.to_csv(f"{out_dir}/train_movements.csv", index=False)
    
    print("Synthetic data generated successfully.")
