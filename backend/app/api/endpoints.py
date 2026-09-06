from fastapi import APIRouter, HTTPException
import pandas as pd
import json
import os

router = APIRouter()

DATA_DIR = "../data/synthetic"
PROC_DIR = "../data/processed"

@router.get("/assets")
def get_assets():
    if not os.path.exists(f"{DATA_DIR}/assets.csv"):
        return []
    df = pd.read_csv(f"{DATA_DIR}/assets.csv")
    return df.to_dict(orient="records")

@router.get("/maintenance/tasks")
def get_tasks():
    if not os.path.exists(f"{DATA_DIR}/maintenance_tasks.csv"):
        return []
    df = pd.read_csv(f"{DATA_DIR}/maintenance_tasks.csv")
    return df.to_dict(orient="records")

@router.get("/blocks/availability")
def get_blocks():
    if not os.path.exists(f"{DATA_DIR}/block_windows.csv"):
        return []
    df = pd.read_csv(f"{DATA_DIR}/block_windows.csv")
    return df.to_dict(orient="records")

@router.get("/plans/optimized")
def get_optimized_plan():
    if not os.path.exists(f"{PROC_DIR}/optimized_plan.csv"):
        return []
    df = pd.read_csv(f"{PROC_DIR}/optimized_plan.csv")
    return df.to_dict(orient="records")

@router.post("/optimize/block-plan")
def trigger_optimization():
    # In a real app, this would trigger a background task (e.g. Celery)
    # Here we just mock the trigger.
    return {"status": "started", "message": "Optimization started."}
