# Architecture
This project is built using a highly decoupled ML-to-Operations pipeline:
1. Data Sources -> 2. Canonical DB -> 3. Leakage-Safe Feature Eng -> 4. Calibrated ML (Random Forest + Platt) -> 5. Priority Scoring -> 6. CP-SAT Optimization -> 7. Plan Explanations -> 8. Human Review Queue.
