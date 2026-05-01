"""
Database models for Build Contract persistence.

These models ensure that build state is never lost and can be resumed.
"""

from datetime import datetime
from typing import List, Dict, Optional
from sqlalchemy import (
    Column, String, Integer, DateTime, JSON, Text, ForeignKey, 
    Boolean, LargeBinary, create_engine
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
import uuid
import json

Base = declarative_base()


def generate_uuid():
    return str(uuid.uuid4())


class Job(Base):
    """
    Primary job state table.
    
    Every build/job is persisted here with full state.
    Nothing is lost on navigation, refresh, or logout.
    """
    __tablename__ = "jobs"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, index=True, nullable=False)
    workspace_id = Column(String, index=True, nullable=False)
    workspace_path = Column(String, nullable=False)
    
    # Original Input
    original_prompt = Column(Text, nullable=False)
    attachments = Column(JSON, default=list)
    
    # BuildContract State
    contract_id = Column(String, ForeignKey("build_contracts.id"))
    contract_version = Column(Integer, default=1)
    contract_status = Column(String, default="draft")  # draft, approved, frozen
    contract_json = Column(JSON, nullable=False)
    
    # DAG State
    dag_state = Column(String, default="pending")  # pending, running, paused, failed_recoverable, repair_required, waiting_for_user, cancelled, completed, archived
    current_phase = Column(String)
    completed_nodes = Column(JSON, default=list)
    failed_nodes = Column(JSON, default=list)
    paused_nodes = Column(JSON, default=list)
    resume_token = Column(String, index=True)  # For client-side reconnection
    
    # Progress Tracking
    contract_progress = Column(JSON, default=dict)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_activity_at = Column(DateTime, default=datetime.utcnow)
    
    # Export Gate State
    export_allowed = Column(Boolean, default=False)
    export_blocked_reason = Column(String)
    quality_score = Column(Integer, default=0)
    
    # Relationships
    build_contracts = relationship(
        "BuildContractModel",
        back_populates="job",
        foreign_keys="BuildContractModel.job_id",
    )
    contract_deltas = relationship("ContractDelta", back_populates="job")
    generated_files = relationship("GeneratedFile", back_populates="job")
    proof_items = relationship("ProofItem", back_populates="job")
    verifier_results = relationship("VerifierResult", back_populates="job")
    repair_attempts = relationship("RepairAttempt", back_populates="job")
    job_events = relationship("JobEvent", back_populates="job")
    screenshots = relationship("Screenshot", back_populates="job")
    export_gate_results = relationship("ExportGateResult", back_populates="job")
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "dag_state": self.dag_state,
            "contract_status": self.contract_status,
            "contract_version": self.contract_version,
            "current_phase": self.current_phase,
            "completed_nodes": self.completed_nodes,
            "failed_nodes": self.failed_nodes,
            "contract_progress": self.contract_progress,
            "export_allowed": self.export_allowed,
            "quality_score": self.quality_score,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class BuildContractModel(Base):
    """
    Frozen BuildContract snapshots.
    
    Each version of a contract is stored here.
    """
    __tablename__ = "build_contracts"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    job_id = Column(String, ForeignKey("jobs.id"))
    version = Column(Integer, nullable=False)
    contract_data = Column(JSON, nullable=False)  # Full contract JSON
    created_at = Column(DateTime, default=datetime.utcnow)
    
    job = relationship(
        "Job",
        back_populates="build_contracts",
        foreign_keys=[job_id],
    )


class ContractDelta(Base):
    """
    Contract change history.
    
    Every modification to the contract is tracked here.
    """
    __tablename__ = "contract_deltas"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    job_id = Column(String, ForeignKey("jobs.id"))
    delta_version = Column(Integer, nullable=False)
    
    changes = Column(JSON, nullable=False)
    reason = Column(Text)
    trigger = Column(String)  # repair_failed, human_request, replanning
    approved_by = Column(String)
    
    previous_contract_snapshot = Column(JSON)
    new_contract_snapshot = Column(JSON)
    failure_context = Column(JSON)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    job = relationship("Job", back_populates="contract_deltas")


class GeneratedFile(Base):
    """
    Every generated file is persisted.
    
    Files can be reconstructed even if workspace is lost.
    """
    __tablename__ = "generated_files"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    job_id = Column(String, ForeignKey("jobs.id"), index=True)
    
    # File Identity
    path = Column(String, nullable=False)
    content_hash = Column(String, nullable=False)  # SHA256
    size_bytes = Column(Integer, nullable=False)
    language = Column(String)
    
    # Generation Metadata
    writer_agent = Column(String)
    writer_job_id = Column(String)
    contract_item_id = Column(String)  # e.g., "required_files:client/src/main.tsx"
    
    # State
    syntax_valid = Column(Boolean, default=False)
    import_resolves = Column(Boolean, default=False)
    
    # Content (for disaster recovery)
    content = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    job = relationship("Job", back_populates="generated_files")


class JobEvent(Base):
    """
    Event log for replay and debugging.
    
    Every action is signed and durable.
    """
    __tablename__ = "job_events"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    job_id = Column(String, ForeignKey("jobs.id"), index=True)
    
    event_type = Column(String, nullable=False)  # node_start, node_complete, node_fail, repair_start, repair_complete, contract_delta, user_instruction, pause, resume, cancel, branch
    payload = Column(JSON)
    agent_id = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    dag_state_snapshot = Column(JSON)
    contract_progress_snapshot = Column(JSON)
    
    job = relationship("Job", back_populates="job_events")


class RepairAttempt(Base):
    """
    Repair history.
    
    Tracks what was tried and whether it succeeded.
    """
    __tablename__ = "repair_attempts"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    job_id = Column(String, ForeignKey("jobs.id"), index=True)
    
    error_type = Column(String)
    error_payload = Column(JSON)
    repair_agents = Column(JSON)
    repair_actions = Column(JSON)
    success = Column(Boolean, default=False)
    resulting_contract_delta_id = Column(String, ForeignKey("contract_deltas.id"))
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    job = relationship("Job", back_populates="repair_attempts")


class ProofItem(Base):
    """
    Proof of build progress.
    
    Build, preview, route, database proofs stored here.
    """
    __tablename__ = "proof_items"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    job_id = Column(String, ForeignKey("jobs.id"), index=True)
    
    proof_type = Column(String, nullable=False)  # build_pass, preview_pass, route_proven, database_proven, test_pass
    category = Column(String)  # generic, verified_runtime, static_analysis
    verified = Column(Boolean, default=False)
    score_value = Column(Integer, default=0)
    payload = Column(JSON)  # Proof-specific data
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    job = relationship("Job", back_populates="proof_items")


class VerifierResult(Base):
    """
    Verifier run results.
    """
    __tablename__ = "verifier_results"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    job_id = Column(String, ForeignKey("jobs.id"), index=True)
    
    verifier_name = Column(String, nullable=False)
    passed = Column(Boolean, default=False)
    blocking = Column(Boolean, default=False)
    error_details = Column(JSON)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    job = relationship("Job", back_populates="verifier_results")


class Screenshot(Base):
    """
    Visual QA screenshots.
    """
    __tablename__ = "screenshots"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    job_id = Column(String, ForeignKey("jobs.id"), index=True)
    
    route = Column(String)
    viewport = Column(String)
    image_data = Column(LargeBinary)
    visual_check_results = Column(JSON)
    dom_snapshot = Column(Text)
    console_logs = Column(JSON)
    network_errors = Column(JSON)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    job = relationship("Job", back_populates="screenshots")


class ExportGateResult(Base):
    """
    Export gate decision history.
    """
    __tablename__ = "export_gate_results"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    job_id = Column(String, ForeignKey("jobs.id"), index=True)
    
    allowed = Column(Boolean, default=False)
    reason = Column(String)
    failed_checks = Column(JSON)
    check_results = Column(JSON)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    job = relationship("Job", back_populates="export_gate_results")


# Database initialization
def init_database(database_url: str = "sqlite:///crucibai_builds.db"):
    """Initialize the database with all tables."""
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    return engine


SessionLocal = sessionmaker(autocommit=False, autoflush=False)


def get_db_session(engine):
    """Get a database session."""
    SessionLocal.configure(bind=engine)
    return SessionLocal()
