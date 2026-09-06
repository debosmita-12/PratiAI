from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Department(Base):
    __tablename__ = "departments"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)

class Station(Base):
    __tablename__ = "stations"
    code = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    lat = Column(Float)
    lon = Column(Float)

class Section(Base):
    __tablename__ = "sections"
    id = Column(String, primary_key=True)
    station_from = Column(String, ForeignKey("stations.code"))
    station_to = Column(String, ForeignKey("stations.code"))
    distance_km = Column(Float)

class Asset(Base):
    __tablename__ = "assets"
    id = Column(String, primary_key=True)
    department_id = Column(String, ForeignKey("departments.id"))
    asset_type = Column(String, nullable=False)
    section_id = Column(String, ForeignKey("sections.id"))
    location_km = Column(Float)
    installation_date = Column(DateTime)
    criticality_class = Column(String)
    safety_flag = Column(Boolean, default=False)
    condition_score = Column(Float)
    
class MaintenanceTask(Base):
    __tablename__ = "maintenance_tasks"
    id = Column(String, primary_key=True)
    asset_id = Column(String, ForeignKey("assets.id"))
    department_id = Column(String, ForeignKey("departments.id"))
    task_type = Column(String, nullable=False)
    priority_class = Column(String)
    required_duration_min = Column(Integer)
    days_since_last_maintenance = Column(Integer)
    overdue_days = Column(Integer)
    safety_critical = Column(Boolean, default=False)
    dependency_group = Column(String)
    crew_type = Column(String)

class Defect(Base):
    __tablename__ = "defects"
    id = Column(String, primary_key=True)
    asset_id = Column(String, ForeignKey("assets.id"))
    defect_type = Column(String, nullable=False)
    defect_severity = Column(String, nullable=False)
    reported_date = Column(DateTime)
    status = Column(String)

class BlockWindow(Base):
    __tablename__ = "block_windows"
    id = Column(String, primary_key=True)
    section_id = Column(String, ForeignKey("sections.id"))
    date = Column(DateTime)
    window_start = Column(DateTime)
    window_end = Column(DateTime)
    max_duration_min = Column(Integer)
    power_block_allowed = Column(Boolean, default=True)
    track_block_allowed = Column(Boolean, default=True)
    signal_block_allowed = Column(Boolean, default=True)
    availability_status = Column(String)

class TrainMovement(Base):
    __tablename__ = "train_movements"
    id = Column(String, primary_key=True)
    train_id = Column(String)
    section_id = Column(String, ForeignKey("sections.id"))
    service_date = Column(DateTime)
    scheduled_entry = Column(DateTime)
    scheduled_exit = Column(DateTime)
    train_type = Column(String)
    priority_class = Column(String)

class Plan(Base):
    __tablename__ = "plans"
    id = Column(String, primary_key=True)
    horizon_start = Column(DateTime)
    horizon_end = Column(DateTime)
    status = Column(String) # DRAFT, REVIEW_REQUIRED, APPROVED, REJECTED
    created_at = Column(DateTime)

class PlanTask(Base):
    __tablename__ = "plan_tasks"
    id = Column(String, primary_key=True)
    plan_id = Column(String, ForeignKey("plans.id"))
    task_id = Column(String, ForeignKey("maintenance_tasks.id"))
    block_id = Column(String, ForeignKey("block_windows.id"))
    scheduled_start = Column(DateTime)
    scheduled_end = Column(DateTime)
    expected_impact = Column(Float)
    confidence = Column(Float)
    rationale = Column(String)
