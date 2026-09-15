# System Architecture

## 🏗️ Overview

The AI Security Research OS is built on a **multi-agent AI architecture** that coordinates multiple specialized LLM-powered agents to perform security research automation.

```
┌─────────────────────────────────────────────────────────────┐
│                    User Interface                            │
│              (Vue.js 3 Dashboard / Web UI)                  │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                   FastAPI Backend                            │
│          (REST API, Request Handling, Routing)              │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              LangGraph Orchestrator                          │
│         (Multi-Agent Workflow Management)                   │
└──────────────────────┬──────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
    ┌────────┐   ┌──────────┐   ┌─────────┐
    │Recon   │   │Exploit   │   │Report   │
    │Agent   │   │Agent     │   │Agent    │
    └──┬─────┘   └────┬─────┘   └────┬────┘
       │              │              │
       └──────────────┼──────────────┘
                      ▼
         ┌─────────────────────────┐
         │  LLM Provider Router    │
         │  (Ollama/Claude/Gemini/ │
         │   OpenAI/Nvidia)        │
         └──────────────┬──────────┘
                        │
        ┌───────────────┼───────────────┐
        ▼               ▼               ▼
    ┌────────┐   ┌──────────┐   ┌─────────┐
    │Ollama  │   │Claude    │   │Gemini   │
    │(Local) │   │(API)     │   │(API)    │
    └────────┘   └──────────┘   └─────────┘
                      │
                      ▼
         ┌──────────────────────────┐
         │  PostgreSQL Database     │
         │  (Scan Results Storage)  │
         └──────────────────────────┘
```

---

## 🔄 Agent Architecture

### Agent Workflow

```
Input: Target, Scope, Mode
  │
  ├─► Reconnaissance Agent
  │   ├─ Analyzes target for vulnerabilities
  │   ├─ Uses LLM for intelligent scanning
  │   └─ Returns: List of found vulnerabilities
  │
  ├─► Exploitation Agent
  │   ├─ Takes discovered vulnerabilities
  │   ├─ Verifies each vulnerability
  │   ├─ Tests feasibility of exploitation
  │   └─ Returns: Verified vulnerabilities
  │
  └─► Report Agent
      ├─ Analyzes verified findings
      ├─ Generates comprehensive report
      ├─ Formats as PDF/DOCX/JSON
      └─ Returns: Complete security report
```

### LangGraph State Management

Each agent communicates through a shared `ScanState`:

```python
class ScanState(TypedDict):
    scan_id: str                          # Unique scan identifier
    target: str                           # Target to scan
    scope: str                            # Scope specification
    mode: str                             # Testing mode
    
    # Results from each agent
    reconnaissance_results: Dict[str, Any]
    discovered_vulnerabilities: List[Dict]
    exploitation_results: Dict[str, Any]
    verified_vulnerabilities: List[Dict]
    
    # Final output
    report_path: str
    report_findings: Dict[str, Any]
    
    # Metadata
    status: str                           # pending/running/completed/failed
    stage: str                            # Current stage
    error: str                            # Error message if any
```

---

## 🗄️ Database Schema

### Core Tables

**Scans Table**
- `id` (PK): UUID
- `target`: URL/IP being scanned
- `scope`: Scan scope definition
- `mode`: Testing mode (normal/aggressive/stealth)
- `status`: Current status
- `progress_percentage`: Scan progress
- `created_at`, `started_at`, `completed_at`: Timestamps
- `duration_seconds`: Total duration
- `vulnerabilities_found`: Count

**Vulnerabilities Table**
- `id` (PK): UUID
- `scan_id` (FK): Associated scan
- `title`: Vulnerability name
- `description`: Detailed description
- `severity`: critical/high/medium/low/info
- `type`: SQL injection, XSS, etc.
- `proof_of_concept`: PoC code/steps
- `cvss_score`: CVSS rating
- `verified`: Boolean

**Reports Table**
- `id` (PK): UUID
- `scan_id` (FK): Associated scan
- `title`: Report title
- `report_format`: pdf/docx/json
- `report_path`: File path
- `vulnerability_count`: Total count
- `overall_risk_score`: Risk rating
- `generated_at`: Timestamp

**LLM Config Table**
- `active_provider`: Currently active LLM
- `ollama_endpoint`: Ollama URL
- `claude_api_key`: Encrypted API key
- `gemini_api_key`: Encrypted API key
- `max_tokens`: Token limit
- `context_window`: Context window size

---

## 🔌 LLM Integration

### Multi-Provider Architecture

```
┌─────────────────────┐
│   LLM Client        │
│  (Main Interface)   │
└──────────┬──────────┘
           │
    ┌──────┼──────┬──────┬────────┐
    ▼      ▼      ▼      ▼        ▼
┌────────┐ ┌────┐ ┌────┐ ┌──────┐ ┌──────┐
│Ollama  │ │CLA │ │GEM │ │OpenAI│ │NVIDIA│
│Provider│ │IDE │ │INI │ │Prov. │ │Prov. │
└────────┘ └────┘ └────┘ └──────┘ └──────┘
   Local    Cloud   Cloud  Cloud   Cloud
```

### Provider Selection Logic

```python
def select_provider(task_type, priority):
    if priority == "speed":
        return "gemini-2.0-flash"    # Fastest
    elif priority == "quality":
        return "claude-3.5-sonnet"   # Best reasoning
    elif priority == "cost":
        return "ollama-mistral"      # Free
    
    # Default: Use configured active provider
    return settings.ACTIVE_LLM
```

---

## 🔐 Security Architecture

### API Security

```
Request
  │
  ├─► CORS Validation
  ├─► Input Validation (Pydantic)
  ├─► Authentication (JWT)
  └─► Authorization (RBAC)
        │
        ▼
   Process Request
        │
        ├─► Encrypt sensitive data (API keys)
        ├─► Database queries (SQLAlchemy)
        └─► LLM API calls
             │
             ▼
        Response (filtered)
```

### Encryption

- **API Keys:** Fernet (symmetric encryption)
- **Database:** Plain storage (keys encrypted)
- **Transport:** HTTPS (in production)

### Database Security

- SQL Injection Protection: SQLAlchemy ORM
- Authentication: JWT tokens
- Authorization: Role-based access control
- Audit Logging: All scans logged

---

## 📊 Data Flow

### Scan Workflow

```
1. User submits scan request
   └─ Target, Scope, Mode

2. Scan record created in DB
   └─ Status: PENDING

3. Background task triggered
   └─ Status: RUNNING

4. Reconnaissance Agent
   ├─ LLM analyzes target
   ├─ Identifies vulnerabilities
   └─ Store findings

5. Exploitation Agent
   ├─ LLM verifies findings
   ├─ Tests feasibility
   └─ Update database

6. Report Agent
   ├─ Compile findings
   ├─ Generate report file
   └─ Status: COMPLETED

7. User retrieves report
   └─ Via API endpoint
```

### API Request/Response Flow

```
Frontend Request
  │
  ├─ POST /api/scan/start
  │  └─ {target, scope, mode}
  │
  ▼
Backend Receives
  │
  ├─ Validate input
  ├─ Create Scan record
  ├─ Queue background task
  └─ Return scan_id
  
Background Processing
  │
  ├─ Execute LangGraph workflow
  ├─ Update database progressively
  └─ Generate report
  
Frontend Polls Status
  │
  ├─ GET /api/scan/{scan_id}/status
  ├─ Shows progress
  └─ Enables report download when ready
```

---

## 🚀 Deployment Architecture

### Docker Compose Setup

```
┌─────────────────────────────────────────┐
│         Docker Compose Network          │
├─────────────────────────────────────────┤
│                                         │
│  ┌──────────┐  ┌──────────┐  ┌────────┐│
│  │Frontend  │  │Backend   │  │Ollama  ││
│  │(Port    │  │(Port    │  │(Port  ││
│  │5173)    │  │8000)    │  │11434)  ││
│  └────┬─────┘  └────┬─────┘  └────────┘│
│       │             │                   │
│       │      ┌──────┴────────┐         │
│       │      ▼               ▼         │
│       │   ┌────────────────────────┐   │
│       │   │   PostgreSQL DB        │   │
│       │   │   (Port 5432)          │   │
│       │   └────────────────────────┘   │
│       │                                │
│       └───────── Shared Volume ────────┘
│                (Reports)               │
│                                         │
└─────────────────────────────────────────┘
```

### Custom OS Architecture

```
Boot Loader (GRUB)
    │
    ├─► Kernel (Linux)
    │
    ├─► Initramfs
    │   └─ Live-boot system
    │
    ├─► Root Filesystem
    │   ├─ Security tools (nmap, wireshark, etc.)
    │   ├─ Backend application
    │   ├─ Frontend application
    │   └─ Database
    │
    └─► Services (Systemd)
        ├─ Backend API
        ├─ Frontend server
        └─ Ollama LLM
```

---

## 🔄 Message Flow Between Agents

### Inter-Agent Communication

```
Recon Agent Output:
{
  "vulnerabilities": [
    {
      "title": "SQL Injection",
      "endpoint": "/login",
      "type": "sql_injection",
      "severity": "critical"
    }
  ]
}
    │
    ▼ (Passed via ScanState)
Exploit Agent Input:
    └─ Takes each vulnerability
       └─ Verifies if exploitable
    │
    ▼ (Passed via ScanState)
Report Agent Input:
    └─ Takes verified findings
       └─ Generates comprehensive report
```

---

## 🌐 API Structure

### REST Endpoints

**Scanning**
- `POST /api/scan/start` - Start scan
- `GET /api/scan/{id}/status` - Get status
- `GET /api/scan/{id}/results` - Get results
- `POST /api/scan/{id}/cancel` - Cancel scan

**Configuration**
- `GET /api/config/llm` - Get LLM config
- `PUT /api/config/llm` - Update LLM config
- `POST /api/config/llm/test` - Test connection

**Reports**
- `POST /api/reports/generate` - Generate report
- `GET /api/reports/{id}` - Get report
- `GET /api/reports/{id}/download` - Download

---

## 📈 Scalability Considerations

### Current (MVP)
- Single backend instance
- Single database connection
- Ollama on same machine
- No load balancing

### Future (Production)
- Multiple backend instances (Docker Swarm/K8s)
- Database connection pooling
- Separate Ollama instances or cloud LLMs
- Load balancer (nginx/HAProxy)
- Redis caching layer
- Message queue (RabbitMQ/Celery)

---

## 🔍 Monitoring & Logging

### Log Levels

```
DEBUG    - Detailed development info
INFO     - General information (agent progress)
WARNING  - Warnings (LLM issues, retries)
ERROR    - Errors (failed scans, API errors)
CRITICAL - Critical system failures
```

### Metrics to Track

- Scan duration
- Vulnerability discovery rate
- LLM API latency
- Database query performance
- Error rates by type

---

## 🧪 Testing Architecture

```
Unit Tests
└─ Individual functions
   ├─ LLM client
   ├─ Agent logic
   └─ Utility functions

Integration Tests
└─ Component interaction
   ├─ Agent orchestration
   ├─ Database operations
   └─ API endpoints

E2E Tests
└─ Full workflow
   ├─ Start to finish scan
   ├─ Report generation
   └─ User interactions
```

---

**Version:** 1.0  
**Last Updated:** [Current Date]  
**Status:** In Development
