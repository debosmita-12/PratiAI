from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import Asset, MaintenanceTask, BlockWindow, Station, Section
import pandas as pd
import os

router = APIRouter()

@router.get("/stations")
def get_stations(db: Session = Depends(get_db)):
    return db.query(Station).all()

@router.get("/sections")
def get_sections(db: Session = Depends(get_db)):
    return db.query(Section).all()

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
    # Serve the ML optimizer CSV output from data/processed for prototype parity
    PROC_DIR = "data/processed"
    if os.path.exists(f"../{PROC_DIR}/optimized_plan.csv"):
        df = pd.read_csv(f"../{PROC_DIR}/optimized_plan.csv")
    elif os.path.exists(f"{PROC_DIR}/optimized_plan.csv"):
        df = pd.read_csv(f"{PROC_DIR}/optimized_plan.csv")
    else:
        return []
    return df.to_dict(orient="records")
