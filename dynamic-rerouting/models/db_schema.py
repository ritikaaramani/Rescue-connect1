"""
Database Schema Models for Emergency Response Coordination Platform

Uses SQLAlchemy ORM with PostgreSQL. Supports fallback to in-memory mode.
"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import create_engine, Column, String, Float, Integer, DateTime, Boolean, Text, ForeignKey, JSON, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from enum import Enum as PyEnum
import os

Base = declarative_base()


# ────────────────────────────────────────────────────────────────────────────
# Enums
# ────────────────────────────────────────────────────────────────────────────

class IncidentState(str, PyEnum):
    REPORTED = "REPORTED"
    VERIFIED = "VERIFIED"
    DISPATCHED = "DISPATCHED"
    EN_ROUTE = "EN_ROUTE"
    ON_SCENE = "ON_SCENE"
    PATIENT_PICKED = "PATIENT_PICKED"
    COMPLETED = "COMPLETED"


class VehicleState(str, PyEnum):
    AVAILABLE = "AVAILABLE"
    DISPATCHED = "DISPATCHED"
    EN_ROUTE = "EN_ROUTE"
    AT_SCENE = "AT_SCENE"
    RETURNING = "RETURNING"
    OFFLINE = "OFFLINE"


class EmergencyType(str, PyEnum):
    ACCIDENT = "accident"
    FIRE = "fire"
    MEDICAL = "medical"
    HAZARD = "hazard"
    PROTEST = "protest"


# ────────────────────────────────────────────────────────────────────────────
# Core Tables
# ────────────────────────────────────────────────────────────────────────────

class Incident(Base):
    """Central incident record - represents one emergency event."""
    __tablename__ = "incidents"

    id = Column(String(50), primary_key=True)  # INC-{timestamp}
    reporter_id = Column(String(100), nullable=False)
    location_lat = Column(Float, nullable=False)
    location_lon = Column(Float, nullable=False)
    type = Column(String(50), nullable=False)  # accident, fire, medical, hazard, protest
    severity = Column(Integer, nullable=False)  # 1-10
    state = Column(String(50), default=IncidentState.REPORTED.value)
    description = Column(Text, nullable=True)
    
    # Assignment
    assigned_vehicle_id = Column(String(50), ForeignKey("vehicles.id"), nullable=True)
    assigned_hospital_id = Column(String(50), ForeignKey("hospitals.id"), nullable=True)
    
    # Digital Emergency Scene
    video_feed_url = Column(String(255), nullable=True)
    patient_condition = Column(String(100), default="Stable", nullable=True)
    ambulance_eta_min = Column(Integer, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    witness_reports = relationship("WitnessReport", back_populates="incident", cascade="all, delete-orphan")
    dispatch_logs = relationship("DispatchLog", back_populates="incident", cascade="all, delete-orphan")
    route_updates = relationship("RouteUpdate", back_populates="incident", cascade="all, delete-orphan")
    assigned_vehicle = relationship("Vehicle", back_populates="current_incident")
    assigned_hospital = relationship("Hospital", back_populates="incidents")


class Vehicle(Base):
    """Emergency vehicle (ambulance, fire truck, etc.)"""
    __tablename__ = "vehicles"

    id = Column(String(50), primary_key=True)  # UP-14-342
    name = Column(String(100), nullable=False)  # Ambulance Name
    type = Column(String(50), default="ambulance")  # ambulance, fire, police
    status = Column(String(50), default=VehicleState.AVAILABLE.value)
    
    # Real-time Location
    current_lat = Column(Float, nullable=True)
    current_lon = Column(Float, nullable=True)
    current_speed = Column(Float, default=0.0)  # km/h
    
    # Route Information
    current_route_json = Column(JSON, nullable=True)  # Array of edges/waypoints
    current_route_index = Column(Integer, default=0)  # Current position in route
    destination_lat = Column(Float, nullable=True)
    destination_lon = Column(Float, nullable=True)
    eta_min = Column(Float, nullable=True)
    route_reliability_score = Column(Float, default=0.95)  # 0.0 - 1.0
    
    # Assignment
    assigned_incident_id = Column(String(50), ForeignKey("incidents.id"), nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_location_update = Column(DateTime, nullable=True)
    
    # Relationships
    current_incident = relationship("Incident", back_populates="assigned_vehicle", uselist=False)


class Hospital(Base):
    """Hospital/Medical Facility"""
    __tablename__ = "hospitals"

    id = Column(String(50), primary_key=True)  # H-1
    name = Column(String(200), nullable=False)
    location_lat = Column(Float, nullable=False)
    location_lon = Column(Float, nullable=False)
    icu_beds_available = Column(Integer, default=0)
    trauma_specialty = Column(Boolean, default=False)
    city = Column(String(50), nullable=False)
    
    # Relationships
    incidents = relationship("Incident", back_populates="assigned_hospital")


class WitnessReport(Base):
    """Crowdsourced witness report attached to incident."""
    __tablename__ = "witness_reports"

    id = Column(String(50), primary_key=True)
    incident_id = Column(String(50), ForeignKey("incidents.id"), nullable=False)
    reporter_id = Column(String(100), nullable=False)
    reporter_location_lat = Column(Float, nullable=True)
    reporter_location_lon = Column(Float, nullable=True)
    
    # Media
    media_urls = Column(JSON, nullable=True)  # Array of photo/video URLs
    has_photo = Column(Boolean, default=False)
    has_video = Column(Boolean, default=False)
    
    # Content
    hazard_tags = Column(JSON, nullable=True)  # Array of tags
    text_notes = Column(Text, nullable=True)
    
    # Inferred Location (from Google Vision)
    inferred_location_lat = Column(Float, nullable=True)
    inferred_location_lon = Column(Float, nullable=True)
    location_confidence = Column(Float, nullable=True)  # 0.0 - 1.0
    detected_landmarks = Column(JSON, nullable=True)  # Array of landmark names
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    incident = relationship("Incident", back_populates="witness_reports")


class DispatchLog(Base):
    """Audit log for dispatch actions."""
    __tablename__ = "dispatch_logs"

    id = Column(String(50), primary_key=True)
    incident_id = Column(String(50), ForeignKey("incidents.id"), nullable=False)
    action = Column(String(100), nullable=False)  # create, assign, dispatch, reroute, complete
    actor = Column(String(100), nullable=False)  # Dispatcher name or system
    details = Column(JSON, nullable=True)  # Extra context
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    incident = relationship("Incident", back_populates="dispatch_logs")


class RouteUpdate(Base):
    """History of route changes for debugging."""
    __tablename__ = "route_updates"

    id = Column(String(50), primary_key=True)
    incident_id = Column(String(50), ForeignKey("incidents.id"), nullable=False)
    vehicle_id = Column(String(50), ForeignKey("vehicles.id"), nullable=True)
    
    # Old vs New Route
    old_route_json = Column(JSON, nullable=True)
    new_route_json = Column(JSON, nullable=True)
    old_eta_min = Column(Float, nullable=True)
    new_eta_min = Column(Float, nullable=True)
    old_reliability_score = Column(Float, nullable=True)
    new_reliability_score = Column(Float, nullable=True)
    
    # Rerouting Reason
    reason = Column(String(255), nullable=True)  # "traffic_incident", "congestion", "rl_optimization"
    rl_action = Column(String(255), nullable=True)  # DQN action code if RL-triggered
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    incident = relationship("Incident", back_populates="route_updates")


# ────────────────────────────────────────────────────────────────────────────
# Database Engine Setup
# ────────────────────────────────────────────────────────────────────────────

def get_database_url():
    """Construct database URL from environment or use in-memory fallback."""
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT", "5432")
    db_user = os.getenv("DB_USER", "postgres")
    db_password = os.getenv("DB_PASSWORD", "postgres")
    db_name = os.getenv("DB_NAME", "emergency_routing")
    
    return f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"


def create_db_engine(use_postgres=True):
    """
    Create SQLAlchemy engine.
    
    Args:
        use_postgres: If False, uses SQLite in-memory for testing
    
    Returns:
        SQLAlchemy Engine
    """
    if use_postgres:
        try:
            url = get_database_url()
            engine = create_engine(url, echo=False, pool_pre_ping=True)
            # Test connection
            with engine.connect() as conn:
                conn.execute("SELECT 1")
            print(f"✅ Connected to PostgreSQL: {url}")
            return engine
        except Exception as e:
            print(f"⚠️ PostgreSQL connection failed: {e}")
            print("⚠️ Falling back to SQLite in-memory")
            return create_engine("sqlite:///:memory:", echo=False)
    else:
        return create_engine("sqlite:///:memory:", echo=False)


def init_db(engine):
    """Create all tables."""
    Base.metadata.create_all(engine)
    print("✅ Database schema initialized")
