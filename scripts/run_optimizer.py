import pandas as pd
import numpy as np
import os
import sys
import uuid
from datetime import datetime

# Add backend app to path to track OptimizationRun
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/backend")
from app.db.database import SessionLocal
from app.db.models import OptimizationRun

from ortools.sat.python import cp_model

def run_optimization(tasks_file, blocks_file, output_file):
    tasks_df = pd.read_csv(tasks_file)
    blocks_df = pd.read_csv(blocks_file)
    
    # We will optimize a subset for the demo (e.g., one section for one day)
    section_id = blocks_df['section_id'].iloc[0]
    target_date = blocks_df['date'].iloc[0]
    
    tasks = tasks_df[tasks_df['section_id'] == section_id].copy()
    blocks = blocks_df[(blocks_df['section_id'] == section_id) & (blocks_df['date'] == target_date)].copy()
    
    if len(blocks) == 0 or len(tasks) == 0:
        print("No tasks or blocks for optimization.")
        return
        
    model = cp_model.CpModel()
    
    # x[t, b] = 1 if task t is assigned to block b
    x = {}
    for t_idx, row_t in tasks.iterrows():
        for b_idx, row_b in blocks.iterrows():
            x[(t_idx, b_idx)] = model.NewBoolVar(f'x_{t_idx}_{b_idx}')
            
    # Hard Constraint 1: A task can be assigned to at most one block
    for t_idx, row_t in tasks.iterrows():
        model.AddAtMostOne([x[(t_idx, b_idx)] for b_idx, row_b in blocks.iterrows()])
        
    # Hard Constraint 2: Block capacity (max block duration limit)
    # We assume concurrent execution of different departments, sequential for same department
    for b_idx, row_b in blocks.iterrows():
        # simplified constraint: sum of all durations must be <= max block duration (pessimistic sequential assumption)
        model.Add(
            sum(x[(t_idx, b_idx)] * int(row_t['required_duration_min']) for t_idx, row_t in tasks.iterrows()) 
            <= int(row_b['max_duration_min'])
        )
        
    # Hard Constraint 3: Crew limits (Max 2 simultaneous tasks per block due to crew size)
    for b_idx, row_b in blocks.iterrows():
        model.Add(
            sum(x[(t_idx, b_idx)] for t_idx, row_t in tasks.iterrows()) <= 2
        )

    # Soft Objective: Maximize priority (P1 = 300, P2 = 200, P3 = 100) + Asset Availability Weight
    priority_map = {'P1': 300, 'P2': 200, 'P3': 100}
    objective_terms = []
    for t_idx, row_t in tasks.iterrows():
        prio = priority_map.get(row_t['priority_class'], 100)
        # Give higher weight to safety_critical
        prio += 50 if row_t['safety_critical'] else 0
        for b_idx, row_b in blocks.iterrows():
            objective_terms.append(x[(t_idx, b_idx)] * prio)
            
    model.Maximize(sum(objective_terms))
    
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 10.0
    status = solver.Solve(model)
    
    db = SessionLocal()
    run_id = f"OPT_{uuid.uuid4().hex[:8]}"
    
    plan = []
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        obj_val = solver.ObjectiveValue()
        print(f"CP-SAT Optimal! Objective value: {obj_val}")
        tasks_completed = 0
        for t_idx, row_t in tasks.iterrows():
            for b_idx, row_b in blocks.iterrows():
                if solver.Value(x[(t_idx, b_idx)]) == 1:
                    tasks_completed += 1
                    plan.append({
                        'task_id': row_t['task_id'],
                        'block_id': row_b['block_id'],
                        'section_id': section_id,
                        'task_type': row_t['task_type'],
                        'department': row_t['department'],
                        'priority': row_t['priority_class']
                    })
        plan_df = pd.DataFrame(plan)
        plan_df.to_csv(output_file, index=False)
        print(f"Plan saved to {output_file}")
        
        # Log to DB
        opt_run = OptimizationRun(
            id=run_id,
            run_timestamp=datetime.now(),
            solver_version="ortools-9.15",
            objective_profile="maximize_critical_tasks",
            status="FEASIBLE" if status == cp_model.FEASIBLE else "OPTIMAL",
            total_blocks_used=len(set([p['block_id'] for p in plan])),
            critical_tasks_completed=tasks_completed
        )
        db.add(opt_run)
    else:
        print("STATUS = INFEASIBLE")
        opt_run = OptimizationRun(
            id=run_id,
            run_timestamp=datetime.now(),
            solver_version="ortools-9.15",
            objective_profile="maximize_critical_tasks",
            status="INFEASIBLE",
            total_blocks_used=0,
            critical_tasks_completed=0
        )
        db.add(opt_run)

    db.commit()
    db.close()

if __name__ == "__main__":
    out_dir = "data/processed"
    os.makedirs(out_dir, exist_ok=True)
    run_optimization(
        "data/synthetic/maintenance_tasks.csv",
        "data/synthetic/block_windows.csv",
        f"{out_dir}/optimized_plan.csv"
    )
