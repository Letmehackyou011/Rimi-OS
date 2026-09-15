"""
SQLAlchemy Database Models
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, JSON, Enum
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import enum
import uuid

Base = declarative_base()

class ScanStatusEnum(str, enum.Enum):
    """Scan status enumeration"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class SeverityEnum(str, enum.Enum):
    """Vulnerability severity enumeration"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

class Scan(Base):
    """Scan model - stores scan information"""
    __tablename__ = "scans"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    target = Column(String, nullable=False)
    scope = Column(Text, nullable=True)
    mode = Column(String, default="normal")  # "normal", "aggressive", "stealth"
    status = Column(Enum(ScanStatusEnum), default=ScanStatusEnum.PENDING)
    
    # LLM Configuration
    llm_provider = Column(String, default="ollama")
    llm_model = Column(String, default="mistral")
    
    # Findings
    findings_json = Column(JSON, nullable=True)
    vulnerabilities_found = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    
    # Progress
    progress_percentage = Column(Float, default=0.0)
    current_stage = Column(String, nullable=True)  # "reconnaissance", "exploitation", "reporting"
    
    # Report
    report_generated = Column(Boolean, default=False)
    report_path = Column(String, nullable=True)
    
    # Error handling
    error_message = Column(Text, nullable=True)

class Vulnerability(Base):
    """Vulnerability model - stores discovered vulnerabilities"""
    __tablename__ = "vulnerabilities"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    scan_id = Column(String, nullable=False)
    
    # Vulnerability details
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    severity = Column(Enum(SeverityEnum), default=SeverityEnum.MEDIUM)
    
    # Technical information
    vulnerability_type = Column(String, nullable=False)  # "sql_injection", "xss", etc.
    affected_endpoint = Column(String, nullable=True)
    affected_parameter = Column(String, nullable=True)
    
    # Proof of concept
    proof_of_concept = Column(Text, nullable=True)
    evidence = Column(JSON, nullable=True)
    
    # Remediation
    remediation = Column(Text, nullable=True)
    cvss_score = Column(Float, nullable=True)
    
    # Timestamps
    discovered_at = Column(DateTime, default=datetime.utcnow)
    verified = Column(Boolean, default=False)

class Report(Base):
    """Report model - stores generated reports"""
    __tablename__ = "reports"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    scan_id = Column(String, nullable=False)
    
    # Report details
    title = Column(String, nullable=False)
    executive_summary = Column(Text, nullable=True)
    
    # Report content
    report_format = Column(String, default="pdf")  # "pdf", "docx", "json"
    report_path = Column(String, nullable=False)
    
    # Statistics
    total_vulnerabilities = Column(Integer, default=0)
    critical_count = Column(Integer, default=0)
    high_count = Column(Integer, default=0)
    medium_count = Column(Integer, default=0)
    low_count = Column(Integer, default=0)
    
    # Risk assessment
    overall_risk_score = Column(Float, default=0.0)
    
    # Timestamps
    generated_at = Column(DateTime, default=datetime.utcnow)
    generated_by = Column(String, default="system")

class LLMConfig(Base):
    """LLM Configuration model - stores user's LLM settings"""
    __tablename__ = "llm_configs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Active provider
    active_provider = Column(String, default="ollama")
    
    # Ollama
    ollama_endpoint = Column(String, default="http://localhost:11434")
    ollama_model = Column(String, default="mistral")
    
    # Claude
    claude_api_key_encrypted = Column(String, nullable=True)
    claude_model = Column(String, default="claude-3-5-sonnet-20241022")
    
    # Gemini
    gemini_api_key_encrypted = Column(String, nullable=True)
    gemini_model = Column(String, default="gemini-2.0-flash")
    
    # OpenAI
    openai_api_key_encrypted = Column(String, nullable=True)
    openai_model = Column(String, default="gpt-4")
    
    # Nvidia
    nvidia_api_key_encrypted = Column(String, nullable=True)
    nvidia_endpoint = Column(String, default="https://integrate.api.nvidia.com/v1")
    
    # Token settings
    max_tokens = Column(Integer, default=8000)
    context_window = Column(Integer, default=32000)
    
    # Updated
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ScanTemplate(Base):
    """Scan Template model - predefined scan configurations"""
    __tablename__ = "scan_templates"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Template details
    name = Column(String, nullable=False, unique=True)
    description = Column(Text, nullable=True)
    
    # Configuration
    mode = Column(String, default="normal")
    scope = Column(Text, nullable=True)
    
    # Included agents
    enable_reconnaissance = Column(Boolean, default=True)
    enable_exploitation = Column(Boolean, default=True)
    enable_reporting = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    is_default = Column(Boolean, default=False)
