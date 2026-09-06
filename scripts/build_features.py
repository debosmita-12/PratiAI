import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta

def load_data(data_dir):
    assets = pd.read_csv(f"{data_dir}/assets.csv")
    tasks = pd.read_csv(f"{data_dir}/maintenance_tasks.csv")
    return assets, tasks

def build_features(assets, tasks):
    # Merge for ML dataset
    df = pd.merge(assets, tasks, on=['asset_id', 'department', 'section_id'], how='inner')
    
    # NEW TARGET: Instead of predicting priority class, predict future failure risk
    # Simulate a future failure label (1 if failed in next 30 days, else 0)
    # Since we are using synthetic data for the prototype, we create a causal synthetic label based on condition & overdue
    np.random.seed(42)
    risk_factor = (1 - df['condition_score']) * 1.5 + (df['overdue_days'].fillna(0) / 30)
    # Add random noise to simulate real-world uncertainty
    noise = np.random.normal(0, 0.2, len(df))
    df['target_failure_next_30d'] = ((risk_factor + noise) > 1.0).astype(int)
    
    # Temporal feature: simulate observation timestamp
    # We assign random timestamps over the last 2 years, sorted to allow temporal splitting
    base_time = datetime(2024, 1, 1)
    df['observation_timestamp'] = [base_time + timedelta(days=np.random.randint(0, 730)) for _ in range(len(df))]
    df = df.sort_values('observation_timestamp').reset_index(drop=True)
    
    # Features (historical only)
    df['age_days'] = (pd.to_datetime(df['observation_timestamp']) - pd.to_datetime(df['installation_date'])).dt.days
    df['is_safety_critical'] = df['safety_flag'].astype(int)
    
    # Categorical encodings
    df['dept_eng'] = (df['department'] == 'ENGINEERING').astype(int)
    df['dept_smt'] = (df['department'] == 'SMT').astype(int)
    df['dept_trd'] = (df['department'] == 'TRD').astype(int)
    
    features = [
        'condition_score',
        'days_since_maintenance',
        'defect_history',
        'traffic_load',
        'age_days',
        'is_safety_critical',
        'dept_eng',
        'dept_smt',
        'dept_trd',
        'overdue_days'
    ]
    
    df['overdue_days'] = df['overdue_days'].fillna(0)
    
    X = df[features + ['observation_timestamp', 'asset_id']]
    y = df['target_failure_next_30d']
    
    return X, y, df

if __name__ == "__main__":
    out_dir = "data/processed"
    os.makedirs(out_dir, exist_ok=True)
    assets, tasks = load_data("data/synthetic")
    X, y, full_df = build_features(assets, tasks)
    
    X.to_csv(f"{out_dir}/X_features.csv", index=False)
    y.to_csv(f"{out_dir}/y_target.csv", index=False)
    full_df.to_csv(f"{out_dir}/full_features.csv", index=False)
    print("Features built successfully with Temporal Sort and Future-Event Target.")
