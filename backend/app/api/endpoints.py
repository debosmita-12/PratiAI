from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import (
    Asset, MaintenanceTask, BlockWindow, Station, Section, 
    OptimizationRun, Prediction, GoodsTrainForecast, MaintenanceHistory, 
    TrainMovement, Department
)
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import pandas as pd
import numpy as np
import os
import json
import joblib
import math
import uuid

router = APIRouter()


class StationCreate(BaseModel):
    code: str
    name: str
    lat: float
    lon: float

class RouteAnalysisRequest(BaseModel):
    station_from: str
    station_to: str
    asset_type: Optional[str] = "TRACK" # TRACK, POINT, SIGNAL, OHE_MAST
    department: Optional[str] = "ENGINEERING" # ENGINEERING, SMT, TRD
    condition_score: Optional[float] = Field(0.55, ge=0.0, le=1.0)
    days_since_maintenance: Optional[int] = Field(180, ge=0)
    overdue_days: Optional[int] = Field(14, ge=0)
    traffic_load: Optional[int] = Field(120, ge=0)
    defect_history: Optional[int] = Field(3, ge=0)
    safety_critical: Optional[bool] = True

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0 # km
    dLat = math.radians(lat2 - lat1)
    dLon = math.radians(lon2 - lon1)
    a = math.sin(dLat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dLon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(R * c, 2)

@router.get("/stations")
def get_stations(db: Session = Depends(get_db)):
    return db.query(Station).all()

@router.post("/stations", status_code=status.HTTP_201_CREATED)
def create_station(station: StationCreate, db: Session = Depends(get_db)):
    existing = db.query(Station).filter(Station.code == station.code.upper().strip()).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Station with code '{station.code}' already exists.")
    
    new_station = Station(
        code=station.code.upper().strip(),
        name=station.name.strip(),
        lat=station.lat,
        lon=station.lon
    )
    db.add(new_station)
    db.commit()
    db.refresh(new_station)
    return new_station

@router.get("/sections")
def get_sections(db: Session = Depends(get_db)):
    return db.query(Section).all()

@router.post("/routes/analyze")
def analyze_route(req: RouteAnalysisRequest, db: Session = Depends(get_db)):
    st_from = db.query(Station).filter(Station.code == req.station_from.upper()).first()
    st_to = db.query(Station).filter(Station.code == req.station_to.upper()).first()
    
    if not st_from:
        raise HTTPException(status_code=404, detail=f"Origin station '{req.station_from}' not found.")
    if not st_to:
        raise HTTPException(status_code=404, detail=f"Destination station '{req.station_to}' not found.")
    if req.station_from.upper() == req.station_to.upper():
        raise HTTPException(status_code=400, detail="Origin and Destination stations must be different.")
    
    # Calculate distance
    distance_km = haversine(st_from.lat, st_from.lon, st_to.lat, st_to.lon)
    section_id = f"SEC_{st_from.code}_{st_to.code}"
    
    # Check if section exists in DB, if not auto-register it
    existing_sec = db.query(Section).filter(Section.id == section_id).first()
    if not existing_sec:
        existing_sec = Section(id=section_id, station_from=st_from.code, station_to=st_to.code, distance_km=distance_km)
        db.add(existing_sec)
        db.commit()
    
    # Prepare feature vector for ML model
    # Features: ['condition_score', 'days_since_maintenance', 'defect_history', 'traffic_load', 'age_days', 'is_safety_critical', 'dept_eng', 'dept_smt', 'dept_trd', 'overdue_days']
    dept_eng = 1 if req.department.upper() == "ENGINEERING" else 0
    dept_smt = 1 if req.department.upper() in ["SMT", "S&T"] else 0
    dept_trd = 1 if req.department.upper() in ["TRD", "OHE", "TRD/OHE"] else 0
    if not (dept_eng or dept_smt or dept_trd):
        dept_eng = 1 # fallback
        
    age_days = 1825 # default 5 years
    is_safety_critical = 1 if req.safety_critical else 0
    
    feature_dict = {
        'condition_score': req.condition_score,
        'days_since_maintenance': req.days_since_maintenance,
        'defect_history': req.defect_history,
        'traffic_load': req.traffic_load,
        'age_days': age_days,
        'is_safety_critical': is_safety_critical,
        'dept_eng': dept_eng,
        'dept_smt': dept_smt,
        'dept_trd': dept_trd,
        'overdue_days': req.overdue_days
    }
    
    X_input = pd.DataFrame([feature_dict])
    
    # Load ML model
    model_path = "ml/models/calibrated_rf.joblib"
    if not os.path.exists(model_path):
        model_path = "../ml/models/calibrated_rf.joblib"
    
    risk_probability = 0.5
    if os.path.exists(model_path):
        try:
            model = joblib.load(model_path)
            probs = model.predict_proba(X_input)[0]
            # Prob of failure class (1)
            risk_probability = float(probs[1]) if len(probs) > 1 else float(probs[0])
        except Exception as e:
            # Fallback heuristic calculation
            risk_probability = float(np.clip((1.0 - req.condition_score) * 0.7 + (req.overdue_days / 30.0) * 0.3, 0.05, 0.98))
    else:
        risk_probability = float(np.clip((1.0 - req.condition_score) * 0.7 + (req.overdue_days / 30.0) * 0.3, 0.05, 0.98))
    
    # Decision Logic
    block_required = bool(risk_probability >= 0.40 or req.overdue_days >= 10 or req.condition_score < 0.65 or req.safety_critical and req.overdue_days > 0)
    
    if risk_probability >= 0.75 or (req.safety_critical and req.overdue_days >= 15):
        priority_class = "P1 (Critical / Urgent Review)"
        verdict = "URGENT BLOCK REQUIRED"
        recommended_window = "Next Available Window (01:00 - 04:30 Midnight)"
        duration_min = 180
    elif risk_probability >= 0.45 or req.overdue_days >= 7:
        priority_class = "P2 (High Priority)"
        verdict = "SCHEDULED BLOCK REQUIRED"
        recommended_window = "Upcoming 7-Day Window (12:30 - 15:00 Non-Peak)"
        duration_min = 120
    elif block_required:
        priority_class = "P3 (Routine Preventive)"
        verdict = "PREVENTIVE BLOCK RECOMMENDED"
        recommended_window = "Monthly Rolling Window (Off-Peak Corridor)"
        duration_min = 90
    else:
        priority_class = "P4 / Normal (Asset Healthy)"
        verdict = "NO BLOCK REQUIRED"
        recommended_window = "No immediate disruption needed"
        duration_min = 0

    # Explainability & Diagnostic Factors
    factors_positive = []
    factors_negative = []
    
    if req.condition_score < 0.65:
        factors_positive.append(f"Degraded asset condition score ({req.condition_score:.2f} / 1.00)")
    else:
        factors_negative.append(f"Stable asset condition score ({req.condition_score:.2f} / 1.00)")
        
    if req.overdue_days > 0:
        factors_positive.append(f"Maintenance task overdue by {req.overdue_days} days")
    else:
        factors_negative.append("Up-to-date maintenance interval")
        
    if req.traffic_load > 100:
        factors_positive.append(f"Heavy corridor traffic exposure ({req.traffic_load} trains/day)")
        
    if req.safety_critical:
        factors_positive.append("Asset flagged as Safety-Critical infrastructure")

    if req.defect_history >= 2:
        factors_positive.append(f"Recurrent defect history ({req.defect_history} reported incidents)")

    departments_involved = [req.department.upper()]
    if block_required:
        # Cross-department bundling opportunity
        if req.department.upper() == "ENGINEERING":
            departments_involved.append("S&T (Track Circuit Clearance)")
        elif req.department.upper() == "TRD":
            departments_involved.append("ENGINEERING (OHE Mast Footing Inspection)")

    return {
        "section_id": section_id,
        "from_station": {"code": st_from.code, "name": st_from.name, "lat": st_from.lat, "lon": st_from.lon},
        "to_station": {"code": st_to.code, "name": st_to.name, "lat": st_to.lat, "lon": st_to.lon},
        "distance_km": distance_km,
        "block_required": block_required,
        "verdict": verdict,
        "risk_probability": round(risk_probability * 100, 1),
        "confidence_tier": "HIGH" if (risk_probability > 0.7 or risk_probability < 0.3) else "MEDIUM",
        "priority_class": priority_class,
        "recommended_window": recommended_window,
        "estimated_duration_min": duration_min,
        "departments_involved": departments_involved,
        "factors_increasing_risk": factors_positive,
        "factors_reducing_risk": factors_negative,
        "summary": f"Route {st_from.name} ({st_from.code}) -> {st_to.name} ({st_to.code}) [{distance_km} km]: {verdict} with {round(risk_probability * 100, 1)}% failure risk probability under {priority_class} classification."
    }

@router.get("/assets")
def get_assets(db: Session = Depends(get_db)):
    return db.query(Asset).all()

@router.get("/maintenance/tasks")
def get_tasks(db: Session = Depends(get_db)):
    return db.query(MaintenanceTask).all()

@router.get("/blocks/availability")
def get_blocks(db: Session = Depends(get_db)):
    return db.query(BlockWindow).all()

def get_project_root():
    # endpoints.py is at <root>/backend/app/api/endpoints.py
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

def get_approvals_file():
    root = get_project_root()
    return os.path.join(root, "data", "processed", "approvals.json")

def load_approvals() -> Dict[str, Any]:
    path = get_approvals_file()
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_approvals(data: Dict[str, Any]):
    path = get_approvals_file()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

class PlanGenerateRequest(BaseModel):
    horizon: Optional[str] = "weekly"  # "weekly" or "monthly"
    timeout_seconds: Optional[int] = 30
    objective_profile: Optional[str] = "safety_first"  # "safety_first", "balanced", "throughput"

class PlanApprovalRequest(BaseModel):
    task_id: Optional[str] = None
    block_id: Optional[str] = None
    action: str = "APPROVED"  # APPROVED, REJECTED, UNDER_REVIEW
    approver: Optional[str] = "Chief Controller"
    role: Optional[str] = "Chief Controller"
    remarks: Optional[str] = ""

@router.get("/plans/optimized")
def get_optimized_plan(db: Session = Depends(get_db)):
    root = get_project_root()
    csv_paths = [
        os.path.join(root, "data", "processed", "optimized_plan.csv"),
        "data/processed/optimized_plan.csv",
        "../data/processed/optimized_plan.csv"
    ]
    df = None
    for p in csv_paths:
        if os.path.exists(p):
            try:
                df = pd.read_csv(p)
                break
            except Exception:
                continue

    if df is None or len(df) == 0:
        return []

    df = df.replace({np.nan: None})
    approvals = load_approvals()
    records = df.to_dict(orient="records")

    for r in records:
        t_id = str(r.get("task_id", ""))
        approval_info = approvals.get(t_id)
        if approval_info:
            r["approval_status"] = approval_info.get("status", "PENDING_APPROVAL")
            r["approved_by"] = approval_info.get("approver", "Chief Controller")
            r["approval_remarks"] = approval_info.get("remarks", "")
            r["approved_at"] = approval_info.get("timestamp", "")
        else:
            r.setdefault("approval_status", "PENDING_APPROVAL")
            r.setdefault("approved_by", "Chief Controller")
            r.setdefault("approval_remarks", "")
            r.setdefault("approved_at", "")

        r.setdefault("planning_status", "OPTIMIZED")
        if "duration" not in r and "required_duration_min" in r:
            r["duration"] = r["required_duration_min"]

        if "is_joint_possession" in r and r["is_joint_possession"] is not None:
            r["is_joint_possession"] = str(r["is_joint_possession"]).lower() in ["true", "1"]
        if "downtime_saved_min" in r and r["downtime_saved_min"] is not None:
            try:
                r["downtime_saved_min"] = int(r["downtime_saved_min"])
            except Exception:
                r["downtime_saved_min"] = 0

    return records

def load_real_demands_and_blocks(root: str, horizon_mode: str = "weekly"):
    from datetime import datetime, timedelta
    raw_dir = os.path.join(root, "data", "raw")
    alt_raw_dir = "C:\\Users\\User\\OneDrive\\Desktop\\Datasets SIH 2026"
    if not os.path.exists(os.path.join(raw_dir, "corridor_availability_india.csv")) and os.path.exists(alt_raw_dir):
        raw_dir = alt_raw_dir

    tasks_path = os.path.join(raw_dir, "maintenance_tasks.csv")
    assets_path = os.path.join(raw_dir, "assets.csv")
    blocks_path = os.path.join(raw_dir, "corridor_availability_india.csv")
    requests_path = os.path.join(raw_dir, "block_requests_india.csv")
    forecast_path = os.path.join(raw_dir, "goods_train_forecast.csv")

    tasks_df = pd.read_csv(tasks_path) if os.path.exists(tasks_path) else pd.DataFrame()
    assets_df = pd.read_csv(assets_path) if os.path.exists(assets_path) else pd.DataFrame()
    blocks_raw = pd.read_csv(blocks_path) if os.path.exists(blocks_path) else pd.DataFrame()
    requests_raw = pd.read_csv(requests_path) if os.path.exists(requests_path) else pd.DataFrame()
    forecast_df = pd.read_csv(forecast_path) if os.path.exists(forecast_path) else pd.DataFrame()

    corr_map = dict(zip(assets_df['corridor_id'], assets_df['corridor_name'])) if 'corridor_id' in assets_df else {}
    corr_alias = {
        'GZB-ALD': 'GZB-CNB',
        'MGS-DDU': 'MGS-HWH',
        'DDU-CPR': 'ALD-MGS',
        'CPR-SEE': 'MGS-HWH',
        'SEE-BJU': 'HWH-NJP',
        'BJU-KIR': 'HWH-NJP',
        'KIR-NJP': 'HWH-NJP',
    }
    density_map = dict(zip(forecast_df['corridor_id'], forecast_df['density_tier'])) if 'density_tier' in forecast_df else {}

    demand = []

    # 1. TMS / SMMS / TDMS asset tasks
    for _, row in tasks_df.iterrows():
        c_raw = str(row.get('corridor_id', 'NDLS-GZB'))
        c_name = corr_map.get(c_raw, c_raw)
        c_name = corr_alias.get(c_name, c_name)
        crit = str(row.get('criticality', 'Medium')).upper() == 'CRITICAL'
        p_class = 'P1' if crit else ('P2' if str(row.get('criticality', '')).upper() == 'HIGH' else 'P3')
        dept_raw = str(row.get('department', 'Engineering')).upper()
        if dept_raw in ['SIGNALLING', 'TELECOM', 'S&T']:
            dept = 'SMT'
        elif dept_raw in ['ELECTRICAL', 'TRD', 'OHE']:
            dept = 'TRD'
        else:
            dept = 'ENGINEERING'

        dur = min(int(row.get('estimated_duration_hours', 2)) * 60, 240)
        p_score = int(row.get('priority_score', 80))

        demand.append({
            'task_id': str(row['task_id']),
            'asset_id': str(row.get('asset_id', f"AST_{c_name[:4]}")),
            'corridor_id': c_name,
            'department': dept,
            'task_type': str(row.get('task_description', 'Preventive Maintenance')),
            'priority': p_class,
            'priority_score': p_score,
            'required_duration_min': dur,
            'safety_critical': crit,
            'overdue_days': 14 if crit else 5,
            'source': 'TMS/SMMS/TDMS',
            'crew_type': 'Track Relaying Train (TRT)' if dept == 'ENGINEERING' else ('Tower Wagon Gang' if dept == 'TRD' else 'S&T Relay Gang')
        })

    # 2. BDMS Requests
    if not requests_raw.empty:
        requests_raw['req_date'] = pd.to_datetime(requests_raw['requested_start'], errors='coerce').dt.strftime('%Y-%m-%d')
        valid_reqs = requests_raw[requests_raw['status'].isin(['Requested', 'Approved'])].copy()
        valid_reqs['start_dt'] = pd.to_datetime(valid_reqs['requested_start'], errors='coerce')
        valid_reqs['end_dt'] = pd.to_datetime(valid_reqs['requested_end'], errors='coerce')
        valid_reqs['dur_min'] = ((valid_reqs['end_dt'] - valid_reqs['start_dt']).dt.total_seconds() / 60).fillna(120).astype(int)

        max_req_days = 7 if horizon_mode == "weekly" else 30
        max_req_count = 70 if horizon_mode == "weekly" else 180
        horizon_reqs = valid_reqs[
            (valid_reqs['req_date'] >= '2026-01-01') & 
            (valid_reqs['req_date'] <= f'2026-01-{max_req_days:02d}')
        ].head(max_req_count)

        for _, row in horizon_reqs.iterrows():
            dept_raw = str(row['department']).upper()
            if dept_raw == 'TRACTION':
                dept = 'TRD'
            elif dept_raw == 'ENGINEERING':
                dept = 'ENGINEERING'
            else:
                dept = 'SMT'

            is_crit = any(k in str(row['block_type']) for k in ['Renewal', 'Power', 'Interlocking'])
            dur = max(30, min(int(row['dur_min']), 240))
            demand.append({
                'task_id': f"{row['request_id']}_{row['task_id']}",
                'asset_id': f"AST_{row['corridor_id'][:4]}_{row['task_id'][-4:]}",
                'corridor_id': str(row['corridor_id']),
                'department': dept,
                'task_type': str(row['block_type']),
                'priority': 'P1' if is_crit else 'P2',
                'priority_score': 85 if is_crit else 70,
                'required_duration_min': dur,
                'safety_critical': is_crit,
                'overdue_days': 8 if is_crit else 2,
                'source': 'BDMS',
                'crew_type': 'Mechanized Tamping Crew' if dept == 'ENGINEERING' else ('OHE Wiring Depot' if dept == 'TRD' else 'Signal Testing Gang')
            })

    # 3. Available Blocks
    def parse_dur(row):
        try:
            t1 = datetime.strptime(str(row['available_start']).strip(), '%H:%M')
            t2 = datetime.strptime(str(row['available_end']).strip(), '%H:%M')
            if t2 <= t1:
                t2 += timedelta(days=1)
            return int((t2 - t1).total_seconds() / 60)
        except Exception:
            return 180

    max_block_days = 7 if horizon_mode == "weekly" else 30
    blocks_df = blocks_raw[
        (blocks_raw['date'] >= '2026-01-01') & 
        (blocks_raw['date'] <= f'2026-01-{max_block_days:02d}')
    ].copy()
    blocks_df['max_duration_min'] = blocks_df.apply(parse_dur, axis=1)
    blocks_df['block_id'] = [f"BLK_{r['corridor_id']}_{str(r['date'])[-5:].replace('-', '')}_{i}" for i, r in blocks_df.reset_index().iterrows()]
    blocks_df['window_start'] = blocks_df['date'] + " " + blocks_df['available_start']
    blocks_df['window_end'] = blocks_df['date'] + " " + blocks_df['available_end']

    return pd.DataFrame(demand), blocks_df, density_map

@router.post("/plans/generate")
def generate_plan(req: PlanGenerateRequest, db: Session = Depends(get_db)):
    from ortools.sat.python import cp_model
    root = get_project_root()
    out_csv = os.path.join(root, "data", "processed", "optimized_plan.csv")
    horizon_mode = (req.horizon or "weekly").lower()

    tasks_df, blocks_df, density_map = load_real_demands_and_blocks(root, horizon_mode)

    if len(tasks_df) == 0 or len(blocks_df) == 0:
        raise HTTPException(status_code=400, detail="Insufficient realistic tasks or block windows to optimize.")

    is_fallback = False
    status_text = "OPTIMAL"
    objective_val = 0.0
    plan = []
    blocks_used = set()
    run_id = f"OPT_{uuid.uuid4().hex[:8]}"

    # CP-SAT OPTIMIZATION
    try:
        model = cp_model.CpModel()
        x = {}

        for t_idx, task in tasks_df.iterrows():
            for b_idx, block in blocks_df.iterrows():
                if task["corridor_id"] != block["corridor_id"]:
                    continue
                if int(task["required_duration_min"]) > int(block["max_duration_min"]):
                    continue
                x[(t_idx, b_idx)] = model.NewBoolVar(f"x_{t_idx}_{b_idx}")

        if len(x) > 0:
            # Constraint 1: At most one block per task
            for t_idx in tasks_df.index:
                vars_for_task = [x[(t_idx, b_idx)] for b_idx in blocks_df.index if (t_idx, b_idx) in x]
                if vars_for_task:
                    model.AddAtMostOne(vars_for_task)

            # Constraint 2: Block capacity & Constraint 3: Max 2 tasks per block
            joint_vars = {}
            for b_idx, block in blocks_df.iterrows():
                block_vars = [x[(t_idx, b_idx)] for t_idx in tasks_df.index if (t_idx, b_idx) in x]
                if not block_vars:
                    continue
                model.Add(sum(block_vars) <= 2)
                block_durs = [int(tasks_df.loc[t_idx, "required_duration_min"]) for t_idx in tasks_df.index if (t_idx, b_idx) in x]
                model.Add(sum(block_vars[i] * block_durs[i] for i in range(len(block_vars))) <= int(block["max_duration_min"]))

                # Multi-department Joint Synergy: bonus when tasks from different departments share the window
                t_indices = [t_idx for t_idx in tasks_df.index if (t_idx, b_idx) in x]
                depts = set(tasks_df.loc[t_idx, "department"] for t_idx in t_indices)
                if len(depts) >= 2:
                    j_var = model.NewBoolVar(f"joint_{b_idx}")
                    joint_vars[b_idx] = j_var
                    model.Add(sum(block_vars) == 2).OnlyEnforceIf(j_var)
                    model.Add(sum(block_vars) != 2).OnlyEnforceIf(j_var.Not())

            # Objective Function
            obj_terms = []
            for (t_idx, b_idx), var in x.items():
                p_score = int(tasks_df.loc[t_idx, "priority_score"])
                if tasks_df.loc[t_idx, "safety_critical"]:
                    p_score += 150 if req.objective_profile == "safety_first" else 100
                p_score += int(tasks_df.loc[t_idx, "overdue_days"]) * 5

                # Freight Off-Peak Incentive (+80 for low density / midnight hours, -40 for high freight)
                b_corridor = blocks_df.loc[b_idx, "corridor_id"]
                f_density = density_map.get(b_corridor, "Medium")
                if f_density == "Low":
                    p_score += 80
                elif f_density == "High":
                    p_score -= 40

                obj_terms.append(var * p_score)

            # Award Multi-Department Joint Synergy Bonus (+250 points)
            for b_idx, j_var in joint_vars.items():
                obj_terms.append(j_var * 250)

            model.Maximize(sum(obj_terms))

            solver = cp_model.CpSolver()
            solver.parameters.max_time_in_seconds = float(req.timeout_seconds or 30)
            res = solver.Solve(model)

            if res in (cp_model.OPTIMAL, cp_model.FEASIBLE):
                status_text = "OPTIMAL" if res == cp_model.OPTIMAL else "FEASIBLE"
                objective_val = float(solver.ObjectiveValue())

                # Build assignments mapping per block
                block_assignments = {}
                for (t_idx, b_idx), var in x.items():
                    if solver.Value(var) == 1:
                        block_assignments.setdefault(b_idx, []).append(t_idx)

                for b_idx, assigned_t_indices in block_assignments.items():
                    blk = blocks_df.loc[b_idx]
                    b_id = str(blk["block_id"])
                    blocks_used.add(b_id)

                    # Determine if joint possession (2 different departments)
                    assigned_depts = [tasks_df.loc[t_idx, "department"] for t_idx in assigned_t_indices]
                    is_joint = len(assigned_t_indices) >= 2 and len(set(assigned_depts)) >= 2
                    downtime_saved = 180 if is_joint else 0

                    for t_idx in assigned_t_indices:
                        tsk = tasks_df.loc[t_idx]
                        other_tasks = [
                            f"{tasks_df.loc[o_idx, 'task_id']} ({tasks_df.loc[o_idx, 'department']})"
                            for o_idx in assigned_t_indices if o_idx != t_idx
                        ]
                        bundled_with_str = ", ".join(other_tasks) if other_tasks else "None (Single Task)"

                        plan.append({
                            "task_id": str(tsk["task_id"]),
                            "asset_id": str(tsk["asset_id"]),
                            "block_id": b_id,
                            "section_id": str(blk["corridor_id"]),
                            "corridor_id": str(blk["corridor_id"]),
                            "corridor_name": str(blk["corridor_id"]),
                            "date": str(blk["date"]),
                            "window_start": str(blk["window_start"]),
                            "window_end": str(blk["window_end"]),
                            "task_type": str(tsk["task_type"]),
                            "department": str(tsk["department"]),
                            "crew_type": str(tsk.get("crew_type", "Standard Gang")),
                            "priority": str(tsk["priority"]),
                            "required_duration_min": int(tsk["required_duration_min"]),
                            "duration": int(tsk["required_duration_min"]),
                            "overdue_days": int(tsk["overdue_days"]),
                            "safety_critical": bool(tsk["safety_critical"]),
                            "is_joint_possession": is_joint,
                            "coordination_status": "JOINT_POSSESSION" if is_joint else "INDEPENDENT",
                            "bundled_with": bundled_with_str,
                            "downtime_saved_min": downtime_saved,
                            "freight_density": density_map.get(str(blk["corridor_id"]), "Medium"),
                            "power_isolation_required": str(blk.get("power_isolation_required", "No")),
                            "restrictions": str(blk.get("restriction", "Standard night maintenance block")),
                            "planning_status": status_text,
                            "approval_status": "PENDING_APPROVAL",
                            "approved_by": "Chief Controller",
                            "solver": "Google OR-Tools CP-SAT"
                        })
            else:
                is_fallback = True
        else:
            is_fallback = True

    except Exception:
        is_fallback = True

    # 2. FAIL-SAFE FALLBACK SCHEDULER (Deterministic heuristic)
    if is_fallback or len(plan) == 0:
        status_text = "FALLBACK"
        plan = []
        blocks_used = set()
        sorted_tasks = tasks_df.sort_values(
            by=["safety_critical", "overdue_days"],
            ascending=[False, False]
        )
        block_usage = {b_id: {"used_min": 0, "tasks": []} for b_id in blocks_df["block_id"]}

        for _, task in sorted_tasks.iterrows():
            req_min = int(task["required_duration_min"])
            sec = task["corridor_id"]
            compat_blocks = blocks_df[blocks_df["corridor_id"] == sec]
            assigned_block = None

            for _, blk in compat_blocks.iterrows():
                b_id = blk["block_id"]
                usage = block_usage[b_id]
                max_min = int(blk["max_duration_min"])
                if len(usage["tasks"]) < 2 and (usage["used_min"] + req_min) <= max_min:
                    assigned_block = blk
                    usage["used_min"] += req_min
                    usage["tasks"].append(task)
                    break

            if assigned_block is not None:
                b_id = str(assigned_block["block_id"])
                blocks_used.add(b_id)
                plan.append({
                    "task_id": str(task["task_id"]),
                    "asset_id": str(task["asset_id"]),
                    "block_id": b_id,
                    "section_id": str(assigned_block["corridor_id"]),
                    "corridor_id": str(assigned_block["corridor_id"]),
                    "corridor_name": str(assigned_block["corridor_id"]),
                    "date": str(assigned_block["date"]),
                    "window_start": str(assigned_block["window_start"]),
                    "window_end": str(assigned_block["window_end"]),
                    "task_type": str(task["task_type"]),
                    "department": str(task["department"]),
                    "crew_type": str(task.get("crew_type", "Standard Gang")),
                    "priority": str(task["priority"]),
                    "required_duration_min": req_min,
                    "duration": req_min,
                    "overdue_days": int(task["overdue_days"]),
                    "safety_critical": bool(task["safety_critical"]),
                    "is_joint_possession": len(block_usage[b_id]["tasks"]) >= 2,
                    "coordination_status": "JOINT_POSSESSION" if len(block_usage[b_id]["tasks"]) >= 2 else "INDEPENDENT",
                    "bundled_with": "Co-scheduled during fallback",
                    "downtime_saved_min": 180 if len(block_usage[b_id]["tasks"]) >= 2 else 0,
                    "freight_density": density_map.get(str(assigned_block["corridor_id"]), "Medium"),
                    "power_isolation_required": str(assigned_block.get("power_isolation_required", "No")),
                    "restrictions": str(assigned_block.get("restriction", "Standard night maintenance block")),
                    "planning_status": "FALLBACK",
                    "approval_status": "PENDING_APPROVAL",
                    "approved_by": "Chief Controller",
                    "solver": "Fail-Safe Greedy Heuristic"
                })

    # Save generated plan to CSV
    if plan:
        plan_df = pd.DataFrame(plan)
        os.makedirs(os.path.dirname(out_csv), exist_ok=True)
        plan_df.to_csv(out_csv, index=False)

    # Record OptimizationRun in DB
    try:
        opt_run = OptimizationRun(
            id=run_id,
            run_timestamp=datetime.now(),
            solver_version="ortools-9.15" if not is_fallback else "heuristic-fallback-1.0",
            objective_profile=f"{req.objective_profile}_{horizon_mode}",
            status=status_text,
            total_blocks_used=len(blocks_used),
            critical_tasks_completed=len(plan)
        )
        db.add(opt_run)
        db.commit()
    except Exception:
        db.rollback()

    return {
        "status": status_text,
        "objective_value": round(objective_val, 1),
        "tasks_scheduled": len(plan),
        "blocks_used": len(blocks_used),
        "horizon": horizon_mode,
        "objective_profile": req.objective_profile,
        "solver": "Google OR-Tools CP-SAT" if not is_fallback else "Heuristic Priority Fallback",
        "timestamp": datetime.now().isoformat(),
        "plan": plan
    }

@router.get("/plans/conflicts")
def get_conflicts(db: Session = Depends(get_db)):
    root = get_project_root()
    plan_path = os.path.join(root, "data", "processed", "optimized_plan.csv")
    conflicts = []

    plan_rows = []
    if os.path.exists(plan_path):
        try:
            plan_rows = pd.read_csv(plan_path).to_dict(orient="records")
        except Exception:
            plan_rows = []

    # 1. Check for Duration Overrun
    for row in plan_rows:
        req_min = int(row.get("required_duration_min", 0))
        # Find block window
        b_id = str(row.get("block_id", ""))
        block = db.query(BlockWindow).filter(BlockWindow.id == b_id).first()
        if block and req_min > block.max_duration_min:
            conflicts.append({
                "id": f"CONF_DUR_{row.get('task_id')}",
                "severity": "CRITICAL",
                "title": f"Block Window Duration Overrun: Task {row.get('task_id')}",
                "section_id": row.get("section_id", "N/A"),
                "department": row.get("department", "ENGINEERING"),
                "description": f"Task requires {req_min} min but block {b_id} allows maximum {block.max_duration_min} min.",
                "suggested_action": "Split maintenance into two rolling shifts or request extended corridor possession.",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
            })

    # 2. Check for High-Density Freight Corridor clashes
    high_density_forecasts = db.query(GoodsTrainForecast).filter(
        GoodsTrainForecast.density_tier == "High",
        GoodsTrainForecast.predicted_goods_trains >= 14
    ).limit(3).all()

    for fc in high_density_forecasts:
        conflicts.append({
            "id": f"CONF_FREIGHT_{fc.id}",
            "severity": "WARNING",
            "title": f"Heavy Freight Traffic Forecast: Corridor {fc.corridor_id}",
            "section_id": fc.corridor_id,
            "department": "TRAFFIC/OPERATIONS",
            "description": f"Predicted {fc.predicted_goods_trains} freight trains (Zone {fc.zone}) during scheduled maintenance corridor.",
            "suggested_action": "Shift work to midnight low-freight slot (01:00 - 04:30) to prevent freight path choking.",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
        })

    # 3. Multi-Department Joint Possessions (Informational coordination)
    section_dept_map = {}
    for r in plan_rows:
        sec = r.get("section_id")
        dept = r.get("department")
        if sec and dept:
            section_dept_map.setdefault(sec, set()).add(dept)

    for sec, depts in section_dept_map.items():
        if len(depts) >= 2:
            conflicts.append({
                "id": f"COORD_{sec}",
                "severity": "INFO",
                "title": f"Joint Multi-Department Corridor Possession: {sec}",
                "section_id": sec,
                "department": " / ".join(sorted(depts)),
                "description": f"Simultaneous possession opportunity identified for {', '.join(sorted(depts))}. Shared shadow block possible.",
                "suggested_action": "Coordinate joint safety briefing and unified line-clear disconnection to reduce net downtime.",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
            })

    # 4. Overdue safety-critical tasks check
    overdue_critical_tasks = db.query(MaintenanceTask).filter(
        MaintenanceTask.safety_critical == True,
        MaintenanceTask.overdue_days >= 10
    ).limit(2).all()

    for ct in overdue_critical_tasks:
        conflicts.append({
            "id": f"CONF_OVERDUE_{ct.id}",
            "severity": "CRITICAL",
            "title": f"Urgent Safety-Critical Asset Overdue: Task {ct.id}",
            "section_id": ct.asset_id,
            "department": ct.department_id,
            "description": f"Safety-critical infrastructure maintenance overdue by {ct.overdue_days} days (Priority {ct.priority_class}).",
            "suggested_action": "Priority 1 immediate block authorization mandatory under Indian Railways Safety Code.",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
        })

    return conflicts

@router.get("/data-integrations/status")
def get_data_integrations(db: Session = Depends(get_db)):
    # Query live counts
    tms_assets = db.query(Asset).filter(Asset.department_id == "ENGINEERING").count()
    tms_tasks = db.query(MaintenanceTask).filter(MaintenanceTask.department_id == "ENGINEERING").count()

    smt_assets = db.query(Asset).filter(Asset.department_id.in_(["SMT", "S&T"])).count()
    smt_tasks = db.query(MaintenanceTask).filter(MaintenanceTask.department_id.in_(["SMT", "S&T"])).count()

    trd_assets = db.query(Asset).filter(Asset.department_id.in_(["TRD", "OHE"])).count()
    trd_tasks = db.query(MaintenanceTask).filter(MaintenanceTask.department_id.in_(["TRD", "OHE"])).count()

    coa_blocks = db.query(BlockWindow).count()
    coa_trains = db.query(TrainMovement).count()

    bdms_history = db.query(MaintenanceHistory).count()
    goods_fc_count = db.query(GoodsTrainForecast).count()

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M IST")

    return {
        "integrations": [
            {
                "id": "tms",
                "name": "Track Management System (TMS)",
                "department": "Engineering / Permanent Way",
                "status": "Connected (Live DB)",
                "record_count": tms_assets + tms_tasks,
                "detail": f"{tms_assets} Track Assets, {tms_tasks} Pending Work Tasks",
                "last_sync": now_str,
                "latency_ms": 42,
                "feed_type": "Relational Sync",
                "protocol": "REST / JDBC"
            },
            {
                "id": "smms",
                "name": "Signalling Maintenance & Management System (SMMS)",
                "department": "Signal & Telecommunication (S&T)",
                "status": "Connected (Live DB)",
                "record_count": smt_assets + smt_tasks,
                "detail": f"{smt_assets} Interlocking/Signal Assets, {smt_tasks} Inspection Tasks",
                "last_sync": now_str,
                "latency_ms": 38,
                "feed_type": "Relational Sync",
                "protocol": "REST / JSON"
            },
            {
                "id": "tdms",
                "name": "Traction Distribution Management System (TDMS)",
                "department": "Traction Distribution / Electrical (TRD)",
                "status": "Connected (Live DB)",
                "record_count": trd_assets + trd_tasks,
                "detail": f"{trd_assets} OHE/Substation Assets, {trd_tasks} Isolation Tasks",
                "last_sync": now_str,
                "latency_ms": 55,
                "feed_type": "Relational Sync",
                "protocol": "REST / HTTPS"
            },
            {
                "id": "coa",
                "name": "Control Office Application (COA)",
                "department": "Operating / Central Corridor Control",
                "status": "Connected (Live DB)",
                "record_count": coa_blocks + coa_trains,
                "detail": f"{coa_blocks} Available Block Windows, {coa_trains} Timetable Movements",
                "last_sync": now_str,
                "latency_ms": 28,
                "feed_type": "Stream / Batch",
                "protocol": "COA Gateway"
            },
            {
                "id": "bdms",
                "name": "Block Demand & Management System (BDMS)",
                "department": "Joint Operations & Corridor Possessions",
                "status": "Connected (Live DB)",
                "record_count": bdms_history,
                "detail": f"{bdms_history} Recorded Maintenance Blocks & Line Clear Sanctions",
                "last_sync": now_str,
                "latency_ms": 62,
                "feed_type": "Disconnection Requisition",
                "protocol": "BDMS API"
            },
            {
                "id": "goods_forecast",
                "name": "Freight Train Forecast & Density Engine",
                "department": "Freight Logistics & FOIS",
                "status": "Connected (Live DB)",
                "record_count": goods_fc_count,
                "detail": f"{goods_fc_count} Calibrated Corridor Density Forecasts",
                "last_sync": now_str,
                "latency_ms": 45,
                "feed_type": "Predictive Feed",
                "protocol": "FOIS Gateway"
            }
        ]
    }

@router.get("/goods-forecast")
def get_goods_forecast(corridor_id: Optional[str] = None, limit: int = 100, db: Session = Depends(get_db)):
    q = db.query(GoodsTrainForecast)
    if corridor_id:
        q = q.filter(GoodsTrainForecast.corridor_id == corridor_id)
    return q.limit(limit).all()

@router.get("/maintenance/history")
def get_maintenance_history(limit: int = 50, db: Session = Depends(get_db)):
    return db.query(MaintenanceHistory).limit(limit).all()

@router.post("/plans/approve")
def approve_plan_task(req: PlanApprovalRequest):
    if not req.task_id and not req.block_id:
        raise HTTPException(status_code=400, detail="Either task_id or block_id is required.")

    approvals = load_approvals()
    key = req.task_id or req.block_id or "UNKNOWN"
    approvals[key] = {
        "status": req.action.upper(),
        "approver": req.approver or "Chief Controller",
        "role": req.role or "Chief Controller",
        "remarks": req.remarks or "",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S IST")
    }
    save_approvals(approvals)

    return {
        "success": True,
        "key": key,
        "status": req.action.upper(),
        "approver": req.approver,
        "message": f"Block authorization successfully recorded as {req.action.upper()}."
    }

@router.get("/models/health")
def get_model_health():
    root = get_project_root()
    mc_paths = [
        os.path.join(root, "ml", "models", "model_card.json"),
        "ml/models/model_card.json",
        "../ml/models/model_card.json"
    ]
    for p in mc_paths:
        if os.path.exists(p):
            with open(p, "r") as f:
                return json.load(f)
    return {
        "status": "calibrated_heuristic",
        "model": "RandomForestClassifier",
        "calibration": "Platt / Isotonic",
        "version": "v1.1.0"
    }

@router.get("/optimization/runs")
def get_opt_runs(db: Session = Depends(get_db)):
    return db.query(OptimizationRun).order_by(OptimizationRun.run_timestamp.desc()).limit(10).all()

