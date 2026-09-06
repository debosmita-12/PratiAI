from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import Asset, MaintenanceTask, BlockWindow, Station, Section, OptimizationRun, Prediction
from pydantic import BaseModel, Field
from typing import Optional, List
import pandas as pd
import numpy as np
import os
import json
import joblib
import math

router = APIRouter()

class StationCreate(BaseModel):
    code: str = Field(..., example="BVI")
    name: str = Field(..., example="Borivali")
    lat: float = Field(..., example=19.2290)
    lon: float = Field(..., example=72.8573)

class RouteAnalysisRequest(BaseModel):
    station_from: str = Field(..., example="NDLS")
    station_to: str = Field(..., example="MTJ")
    asset_type: Optional[str] = Field("TRACK", example="TRACK") # TRACK, POINT, SIGNAL, OHE_MAST
    department: Optional[str] = Field("ENGINEERING", example="ENGINEERING") # ENGINEERING, SMT, TRD
    condition_score: Optional[float] = Field(0.55, ge=0.0, le=1.0, example=0.55)
    days_since_maintenance: Optional[int] = Field(180, ge=0, example=180)
    overdue_days: Optional[int] = Field(14, ge=0, example=14)
    traffic_load: Optional[int] = Field(120, ge=0, example=120)
    defect_history: Optional[int] = Field(3, ge=0, example=3)
    safety_critical: Optional[bool] = Field(True, example=True)

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

@router.get("/plans/optimized")
def get_optimized_plan(db: Session = Depends(get_db)):
    PROC_DIR = "data/processed"
    if os.path.exists(f"../{PROC_DIR}/optimized_plan.csv"):
        df = pd.read_csv(f"../{PROC_DIR}/optimized_plan.csv")
    elif os.path.exists(f"{PROC_DIR}/optimized_plan.csv"):
        df = pd.read_csv(f"{PROC_DIR}/optimized_plan.csv")
    else:
        return []
    return df.to_dict(orient="records")

@router.get("/models/health")
def get_model_health():
    mc_path = "ml/models/model_card.json"
    if not os.path.exists(mc_path):
        mc_path = "../ml/models/model_card.json"
    if os.path.exists(mc_path):
        with open(mc_path, "r") as f:
            return json.load(f)
    return {"status": "unavailable"}

@router.get("/optimization/runs")
def get_opt_runs(db: Session = Depends(get_db)):
    return db.query(OptimizationRun).order_by(OptimizationRun.run_timestamp.desc()).limit(5).all()
