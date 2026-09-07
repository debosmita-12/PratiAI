import os
import sys
import uuid
from datetime import datetime

import pandas as pd
from ortools.sat.python import cp_model

# Add the project root to Python's import path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(PROJECT_ROOT, "backend")

sys.path.insert(0, BACKEND_DIR)

from app.db.database import SessionLocal
from app.db.models import OptimizationRun


def run_optimization(tasks_file, blocks_file, output_file):
    print("=" * 60)
    print("AI-POWERED AUTOMATIC BLOCK PLANNING")
    print("=" * 60)

    # ---------------------------------------------------------
    # 1. LOAD DATA
    # ---------------------------------------------------------

    print("\nLoading maintenance tasks...")
    tasks_df = pd.read_csv(tasks_file)

    print("Loading block windows...")
    blocks_df = pd.read_csv(blocks_file)

    print(f"Maintenance tasks loaded: {len(tasks_df)}")
    print(f"Block windows loaded: {len(blocks_df)}")

    # ---------------------------------------------------------
    # 2. CLEAN DATA
    # ---------------------------------------------------------

    tasks_df["required_duration_min"] = (
        pd.to_numeric(
            tasks_df["required_duration_min"],
            errors="coerce"
        )
        .fillna(0)
        .astype(int)
    )

    tasks_df["overdue_days"] = (
        pd.to_numeric(
            tasks_df["overdue_days"],
            errors="coerce"
        )
        .fillna(0)
        .astype(int)
    )

    tasks_df["safety_critical"] = (
        tasks_df["safety_critical"]
        .astype(str)
        .str.lower()
        .isin(["true", "1", "yes"])
    )

    blocks_df["max_duration_min"] = (
        pd.to_numeric(
            blocks_df["max_duration_min"],
            errors="coerce"
        )
        .fillna(0)
        .astype(int)
    )

    blocks_df["date"] = pd.to_datetime(
        blocks_df["date"],
        errors="coerce"
    ).dt.date

    blocks_df["window_start"] = pd.to_datetime(
        blocks_df["window_start"],
        errors="coerce"
    )

    blocks_df["window_end"] = pd.to_datetime(
        blocks_df["window_end"],
        errors="coerce"
    )

    # Use only available block windows
    blocks_df = blocks_df[
        blocks_df["availability_status"]
        .astype(str)
        .str.upper()
        == "AVAILABLE"
    ].copy()

    print(f"Available block windows: {len(blocks_df)}")

    if len(tasks_df) == 0:
        print("No maintenance tasks available.")
        return

    if len(blocks_df) == 0:
        print("No available block windows.")
        return

    # ---------------------------------------------------------
    # 3. CREATE CP-SAT MODEL
    # ---------------------------------------------------------

    model = cp_model.CpModel()

    # x[t, b] = 1 when task t is assigned to block b
    x = {}

    for t_idx, task in tasks_df.iterrows():

        for b_idx, block in blocks_df.iterrows():

            # A task can only be assigned to a block
            # belonging to the same section.
            if task["section_id"] != block["section_id"]:
                continue

            # The task must fit inside the block.
            if (
                task["required_duration_min"]
                > block["max_duration_min"]
            ):
                continue

            x[(t_idx, b_idx)] = model.NewBoolVar(
                f"x_{t_idx}_{b_idx}"
            )

    print(f"Decision variables created: {len(x)}")

    if len(x) == 0:
        print("No valid task/block combinations found.")
        return

    # ---------------------------------------------------------
    # 4. CONSTRAINT 1
    # EACH TASK CAN BE ASSIGNED AT MOST ONCE
    # ---------------------------------------------------------

    for t_idx in tasks_df.index:

        variables = [
            x[(t_idx, b_idx)]
            for b_idx in blocks_df.index
            if (t_idx, b_idx) in x
        ]

        if variables:
            model.AddAtMostOne(variables)

    # ---------------------------------------------------------
    # 5. CONSTRAINT 2
    # BLOCK CAPACITY
    # ---------------------------------------------------------

    for b_idx, block in blocks_df.iterrows():

        variables = []
        durations = []

        for t_idx, task in tasks_df.iterrows():

            if (t_idx, b_idx) in x:
                variables.append(x[(t_idx, b_idx)])

                durations.append(
                    int(task["required_duration_min"])
                )

        if variables:
            model.Add(
                sum(
                    variables[i] * durations[i]
                    for i in range(len(variables))
                )
                <= int(block["max_duration_min"])
            )

    # ---------------------------------------------------------
    # 6. CONSTRAINT 3
    # MAXIMUM TWO TASKS PER BLOCK
    # ---------------------------------------------------------

    for b_idx in blocks_df.index:

        variables = [
            x[(t_idx, b_idx)]
            for t_idx in tasks_df.index
            if (t_idx, b_idx) in x
        ]

        if variables:
            model.Add(sum(variables) <= 2)

    # ---------------------------------------------------------
    # 7. OBJECTIVE FUNCTION
    # ---------------------------------------------------------

    priority_map = {
        "P1": 300,
        "P2": 200,
        "P3": 100
    }

    objective_terms = []

    for t_idx, task in tasks_df.iterrows():

        priority = priority_map.get(
            str(task["priority_class"]).upper(),
            100
        )

        # Give additional importance to safety-critical tasks.
        if task["safety_critical"]:
            priority += 100

        # Give additional importance to overdue tasks.
        overdue_days = int(task["overdue_days"])
        overdue_bonus = min(overdue_days * 5, 100)
        priority += overdue_bonus

        for b_idx in blocks_df.index:

            if (t_idx, b_idx) in x:
                objective_terms.append(
                    x[(t_idx, b_idx)] * priority
                )

    # Maximize the total importance of scheduled tasks.
    model.Maximize(sum(objective_terms))

    # ---------------------------------------------------------
    # 8. RUN CP-SAT
    # ---------------------------------------------------------

    print("\nRunning CP-SAT optimizer...")

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 30.0

    status = solver.Solve(model)

    # ---------------------------------------------------------
    # 9. PREPARE DATABASE LOG
    # ---------------------------------------------------------

    db = SessionLocal()

    run_id = f"OPT_{uuid.uuid4().hex[:8]}"

    plan = []
    tasks_completed = 0
    blocks_used = set()

    try:

        if status in (
            cp_model.OPTIMAL,
            cp_model.FEASIBLE
        ):

            if status == cp_model.OPTIMAL:
                status_text = "OPTIMAL"
            else:
                status_text = "FEASIBLE"

            print(f"\nOptimization status: {status_text}")
            print(
                f"Objective value: "
                f"{solver.ObjectiveValue()}"
            )

            # -------------------------------------------------
            # 10. CREATE OPTIMIZED PLAN
            # -------------------------------------------------

            for t_idx, task in tasks_df.iterrows():

                for b_idx, block in blocks_df.iterrows():

                    if (t_idx, b_idx) not in x:
                        continue

                    if solver.Value(x[(t_idx, b_idx)]) == 1:

                        tasks_completed += 1

                        blocks_used.add(
                            block["block_id"]
                        )

                        plan.append({
                            "task_id": task["task_id"],
                            "asset_id": task["asset_id"],
                            "block_id": block["block_id"],
                            "section_id": task["section_id"],
                            "date": block["date"],
                            "window_start": block["window_start"],
                            "window_end": block["window_end"],
                            "task_type": task["task_type"],
                            "department": task["department"],
                            "crew_type": task["crew_type"],
                            "priority": task["priority_class"],
                            "required_duration_min": (
                                task["required_duration_min"]
                            ),
                            "overdue_days": task["overdue_days"],
                            "safety_critical": (
                                task["safety_critical"]
                            )
                        })

            # -------------------------------------------------
            # 11. SAVE OPTIMIZED PLAN
            # -------------------------------------------------

            plan_df = pd.DataFrame(plan)

            output_directory = os.path.dirname(output_file)

            if output_directory:
                os.makedirs(
                    output_directory,
                    exist_ok=True
                )

            plan_df.to_csv(
                output_file,
                index=False
            )

            print("\nOptimized plan saved to:")
            print(output_file)

            print(f"Tasks scheduled: {tasks_completed}")
            print(f"Blocks used: {len(blocks_used)}")

            # -------------------------------------------------
            # 12. LOG SUCCESSFUL OPTIMIZATION RUN
            # -------------------------------------------------

            opt_run = OptimizationRun(
                id=run_id,
                run_timestamp=datetime.now(),
                solver_version="ortools-9.15",
                objective_profile=(
                    "maximize_priority_safety_overdue_tasks"
                ),
                status=status_text,
                total_blocks_used=len(blocks_used),
                critical_tasks_completed=tasks_completed
            )

            db.add(opt_run)

        else:

            print("\nOptimization status: INFEASIBLE")

            opt_run = OptimizationRun(
                id=run_id,
                run_timestamp=datetime.now(),
                solver_version="ortools-9.15",
                objective_profile=(
                    "maximize_priority_safety_overdue_tasks"
                ),
                status="INFEASIBLE",
                total_blocks_used=0,
                critical_tasks_completed=0
            )

            db.add(opt_run)

        db.commit()

    finally:
        db.close()

    print("\n" + "=" * 60)
    print("OPTIMIZATION COMPLETE")
    print("=" * 60)


# =============================================================
# MAIN
# =============================================================

if __name__ == "__main__":

    run_optimization(
        os.path.join(
            PROJECT_ROOT,
            "data",
            "synthetic",
            "maintenance_tasks.csv"
        ),

        os.path.join(
            PROJECT_ROOT,
            "data",
            "synthetic",
            "block_windows.csv"
        ),

        os.path.join(
            PROJECT_ROOT,
            "data",
            "processed",
            "optimized_plan.csv"
        )
    )