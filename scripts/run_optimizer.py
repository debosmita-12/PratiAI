import pandas as pd
import numpy as np
from ortools.sat.python import cp_model
import json
import os

def run_optimization(tasks_file, blocks_file, output_file):
    tasks_df = pd.read_csv(tasks_file)
    blocks_df = pd.read_csv(blocks_file)
    
    # We will optimize a subset for the demo (e.g., one section for one day)
    section_id = blocks_df['section_id'].iloc[0]
    target_date = blocks_df['date'].iloc[0]
    
    # Filter tasks and blocks
    tasks = tasks_df[tasks_df['section_id'] == section_id].copy()
    blocks = blocks_df[(blocks_df['section_id'] == section_id) & (blocks_df['date'] == target_date)].copy()
    
    if len(blocks) == 0 or len(tasks) == 0:
        print("No tasks or blocks for optimization.")
        return
        
    model = cp_model.CpModel()
    
    # Variables
    # x[t, b] = 1 if task t is assigned to block b
    x = {}
    for t_idx, row_t in tasks.iterrows():
        for b_idx, row_b in blocks.iterrows():
            x[(t_idx, b_idx)] = model.NewBoolVar(f'x_{t_idx}_{b_idx}')
            
    # Constraints
    # 1. A task can be assigned to at most one block
    for t_idx, row_t in tasks.iterrows():
        model.AddAtMostOne([x[(t_idx, b_idx)] for b_idx, row_b in blocks.iterrows()])
        
    # 2. Block capacity: Sum of durations of tasks in a block must be <= max_duration
    # Actually, if tasks are run in parallel, it's just the max duration of any task in the block.
    # To keep it simple, we assume tasks run sequentially in the block OR they can run concurrently if they are from different departments.
    # Let's do a simple capacity constraint: total sequential duration <= max duration (pessimistic)
    for b_idx, row_b in blocks.iterrows():
        model.Add(
            sum(x[(t_idx, b_idx)] * int(row_t['required_duration_min']) for t_idx, row_t in tasks.iterrows()) 
            <= int(row_b['max_duration_min'])
        )
        
    # Objective
    # Maximize priority (P1 = 3, P2 = 2, P3 = 1)
    priority_map = {'P1': 3, 'P2': 2, 'P3': 1}
    objective_terms = []
    for t_idx, row_t in tasks.iterrows():
        prio = priority_map.get(row_t['priority_class'], 1)
        for b_idx, row_b in blocks.iterrows():
            objective_terms.append(x[(t_idx, b_idx)] * prio)
            
    model.Maximize(sum(objective_terms))
    
    # Solve
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 60.0
    status = solver.Solve(model)
    
    plan = []
    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        print(f"Objective value: {solver.ObjectiveValue()}")
        for t_idx, row_t in tasks.iterrows():
            for b_idx, row_b in blocks.iterrows():
                if solver.Value(x[(t_idx, b_idx)]) == 1:
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
    else:
        print("STATUS = INFEASIBLE")
        
if __name__ == "__main__":
    out_dir = "../data/processed"
    os.makedirs(out_dir, exist_ok=True)
    run_optimization(
        "../data/synthetic/maintenance_tasks.csv",
        "../data/synthetic/block_windows.csv",
        f"{out_dir}/optimized_plan.csv"
    )
