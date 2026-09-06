# SIH26027 — AI-Powered Automatic Block Planning

**Ministry:** Ministry of Railways
**Theme:** Transportation & Logistics
**Problem ID:** SIH26027

## Project Mission
Build a production-style decision-support prototype for SIH26027: “AI-Powered Automatic Block Planning to Maximize Asset Availability for Train Operations on Indian Railways.”

The system integrates maintenance/defect information from Engineering, Traction Distribution (TRD/OHE), and Signal & Telecommunication (S&T), combines it with train timetable, freight/goods-train forecasts and corridor/block availability, predicts maintenance risk, prioritizes work, and generates explainable weekly/monthly block plans.

## Core Decision Chain
```
DATA
  ↓
VALIDATION / NORMALIZATION
  ↓
ASSET + MAINTENANCE RISK PREDICTION
  ↓
MAINTENANCE PRIORITIZATION
  ↓
TRAIN / CORRIDOR IMPACT ESTIMATION
  ↓
CONSTRAINT-BASED BLOCK OPTIMIZATION
  ↓
FEASIBILITY + SAFETY VALIDATION
  ↓
HUMAN REVIEW / APPROVAL
  ↓
DAILY / WEEKLY / MONTHLY BLOCK PLAN
```

## Setup Instructions
Please refer to the documentation in `docs/` for setup, data ingestion, ML training, and optimization details.
