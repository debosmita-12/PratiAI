import pandas as pd
import numpy as np
import os

def load_data(data_dir):
    assets = pd.read_csv(f"{data_dir}/assets.csv")
    tasks = pd.read_csv(f"{data_dir}/maintenance_tasks.csv")
    return assets, tasks

def build_features(assets, tasks):
    # Join assets with tasks to create a predictive dataset
    # We want to predict if a task is HIGH priority or high risk
    df = pd.merge(assets, tasks, on=['asset_id', 'department', 'section_id'], how='inner')
    
    # Target: 1 if priority_class is P1 or P2, else 0
    df['target_high_priority'] = df['priority_class'].apply(lambda x: 1 if x in ['P1', 'P2'] else 0)
    
    # Features
    df['age_days'] = (pd.to_datetime('today') - pd.to_datetime(df['installation_date'])).dt.days
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
    
    # Fill missing overdue days with 0
    df['overdue_days'] = df['overdue_days'].fillna(0)
    
    X = df[features]
    y = df['target_high_priority']
    
    return X, y, df

if __name__ == "__main__":
    out_dir = "../data/processed"
    os.makedirs(out_dir, exist_ok=True)
    assets, tasks = load_data("../data/synthetic")
    X, y, full_df = build_features(assets, tasks)
    
    X.to_csv(f"{out_dir}/X_features.csv", index=False)
    y.to_csv(f"{out_dir}/y_target.csv", index=False)
    full_df.to_csv(f"{out_dir}/full_features.csv", index=False)
    print("Features built successfully.")
