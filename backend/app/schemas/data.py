from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List

class AssetSchema(BaseModel):
    id: str
    department_id: str
    asset_type: str
    section_id: str
    location_km: float
    installation_date: Optional[datetime]
    criticality_class: str
    safety_flag: bool
    condition_score: Optional[float]
    
class MaintenanceTaskSchema(BaseModel):
    id: str
    asset_id: str
    department_id: str
    task_type: str
    priority_class: str
    required_duration_min: int = Field(gt=0)
    days_since_last_maintenance: Optional[int]
    overdue_days: Optional[int]
    safety_critical: bool
    dependency_group: Optional[str]
    crew_type: Optional[str]

class BlockWindowSchema(BaseModel):
    id: str
    section_id: str
    date: datetime
    window_start: datetime
    window_end: datetime
    max_duration_min: int = Field(gt=0)
    power_block_allowed: bool
    track_block_allowed: bool
    signal_block_allowed: bool
    availability_status: str

class TrainMovementSchema(BaseModel):
    id: str
    train_id: str
    section_id: str
    service_date: datetime
    scheduled_entry: datetime
    scheduled_exit: datetime
    train_type: str
    priority_class: str
