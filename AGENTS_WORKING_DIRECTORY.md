# 🤖 Agents Working Directory Structure

## 📁 Complete Directory Layout

```
backend/
├── agents/
│   ├── __init__.py
│   ├── reconnaissance_agent.py      # Reconnaissance agent
│   ├── exploitation_agent.py         # Exploitation agent
│   ├── reporting_agent.py            # Reporting agent
│   ├── tools/                        # Agent tools
│   │   ├── __init__.py
│   │   ├── port_scanner.py           # Port scanning tools
│   │   ├── service_detector.py       # Service detection
│   │   ├── vulnerability_db.py       # Vulnerability database access
│   │   ├── exploit_engine.py         # Exploitation utilities
│   │   └── report_generators.py      # Report generation
│   ├── prompts/                      # LLM prompts
│   │   ├── reconnaissance_prompts.json
│   │   ├── exploitation_prompts.json
│   │   ├── reporting_prompts.json
│   │   └── system_prompts.json
│   ├── state/                        # State management
│   │   ├── __init__.py
│   │   ├── scan_state.py             # Scan state types
│   │   └── state_manager.py          # State persistence
│   ├── config/                       # Agent configuration
│   │   ├── agent_config.yaml
│   │   ├── tool_config.yaml
│   │   └── llm_config.yaml
│   └── logs/                         # Agent execution logs
│       ├── reconnaissance/
│       ├── exploitation/
│       └── reporting/
├── orchestrator.py                   # Main LangGraph orchestrator
├── workflow_graph.py                 # Graph definition
├── config.py                         # Global configuration
└── main.py                           # FastAPI integration
```

---

## 🔧 Agent Configuration Files

### `agents/config/agent_config.yaml`

```yaml
agents:
  reconnaissance:
    name: "Reconnaissance Agent"
    description: "Gathers information about target"
    enabled: true
    timeout: 600  # 10 minutes
    retries: 3
    llm_provider: "ollama"
    model: "mistral"
    temperature: 0.7
    max_tokens: 2000
    
  exploitation:
    name: "Exploitation Agent"
    description: "Verifies and exploits vulnerabilities"
    enabled: true
    timeout: 900  # 15 minutes
    retries: 2
    llm_provider: "ollama"
    model: "mistral"
    temperature: 0.5
    max_tokens: 2000
    
  reporting:
    name: "Reporting Agent"
    description: "Generates comprehensive reports"
    enabled: true
    timeout: 300  # 5 minutes
    retries: 1
    llm_provider: "ollama"
    model: "mistral"
    temperature: 0.3  # Lower temp for consistency
    max_tokens: 3000

scanning:
  modes:
    stealth:
      timeout_multiplier: 2.0
      aggressiveness: 1
      description: "Slow, careful scanning"
    moderate:
      timeout_multiplier: 1.0
      aggressiveness: 5
      description: "Balanced scanning"
    aggressive:
      timeout_multiplier: 0.5
      aggressiveness: 10
      description: "Fast, intensive scanning"

tools:
  port_scanner:
    tool: "nmap"
    enabled: true
    timeout: 300
  
  service_detector:
    tool: "nmap"
    enabled: true
    timeout: 300
  
  vulnerability_db:
    tool: "local_db"
    enabled: true
    update_frequency: 86400  # 24 hours
  
  exploit_engine:
    tool: "custom"
    enabled: true
    safe_mode: true  # Don't actually exploit unless confirmed
```

### `agents/config/llm_config.yaml`

```yaml
llm_providers:
  ollama:
    type: "local"
    endpoint: "http://localhost:11434"
    models:
      - "mistral"
      - "llama2"
      - "neural-chat"
    default_model: "mistral"
    temperature: 0.7
    max_tokens: 2000
    
  claude:
    type: "remote"
    endpoint: "https://api.anthropic.com"
    api_key_env: "CLAUDE_API_KEY"
    models:
      - "claude-3-5-sonnet-20241022"
      - "claude-3-opus-20240229"
    default_model: "claude-3-5-sonnet-20241022"
    temperature: 0.7
    max_tokens: 2000
    
  gemini:
    type: "remote"
    endpoint: "https://api.google.com"
    api_key_env: "GEMINI_API_KEY"
    models:
      - "gemini-1.5-pro"
    default_model: "gemini-1.5-pro"
    temperature: 0.7
    max_tokens: 2000
    
  openai:
    type: "remote"
    endpoint: "https://api.openai.com"
    api_key_env: "OPENAI_API_KEY"
    models:
      - "gpt-4"
    default_model: "gpt-4"
    temperature: 0.7
    max_tokens: 2000

fallback_order:
  - "ollama"      # Try local first
  - "claude"      # Then Claude
  - "gemini"      # Then Gemini
  - "openai"      # Then OpenAI
```

### `agents/config/tool_config.yaml`

```yaml
tools:
  nmap:
    binary_path: "/usr/bin/nmap"
    timeout: 300
    max_ports: 65535
    output_format: "xml"
    
  sqlmap:
    binary_path: "/usr/bin/sqlmap"
    timeout: 120
    risk_level: 1  # 1-3
    detection_level: 1  # 1-5
    
  nikto:
    binary_path: "/usr/bin/nikto"
    timeout: 300
    
  curl:
    binary_path: "/usr/bin/curl"
    timeout: 10
    
  netcat:
    binary_path: "/usr/bin/nc"
    timeout: 5

vulnerability_databases:
  - name: "NVD"
    type: "cve"
    update_url: "https://services.nvd.nist.gov/rest/json/cves"
    cache_dir: "/var/cache/nvd"
    
  - name: "CVEDetails"
    type: "exploit"
    url: "https://www.cvedetails.com"
    
  - name: "Local Database"
    type: "custom"
    path: "/app/data/vulnerabilities.json"
```

---

## 📊 Agent Workflow Execution Flow

```
                                    ┌─────────────────┐
                                    │   Scan Request  │
                                    └────────┬────────┘
                                             │
                                             ▼
                                    ┌─────────────────┐
                                    │  Initialize     │
                                    │  Scan State     │
                                    └────────┬────────┘
                                             │
                        ┌────────────────────┴────────────────────┐
                        │                                         │
                        ▼                                         ▼
          ┌──────────────────────────┐         ┌──────────────────────────┐
          │ RECONNAISSANCE AGENT     │         │  Load Agent Config       │
          │                          │         └──────────────────────────┘
          │ 1. Port Scanning        │
          │ 2. Service Detection    │
          │ 3. OS Fingerprinting    │
          │ 4. Banner Grabbing      │
          │ 5. Vuln DB Lookup       │
          │ 6. DNS Enumeration      │
          │ 7. Tech Detection       │
          └────────────┬────────────┘
                       │
                       ▼
          ┌──────────────────────────┐
          │ Store Results            │
          │ Update State (40%)        │
          └────────────┬────────────┘
                       │
                       ▼
          ┌──────────────────────────┐
          │ EXPLOITATION AGENT       │
          │                          │
          │ For each vulnerability:  │
          │ 1. Verify vuln           │
          │ 2. Test exploit          │
          │ 3. Assign severity       │
          │ 4. Gather evidence       │
          └────────────┬────────────┘
                       │
                       ▼
          ┌──────────────────────────┐
          │ Store Results            │
          │ Update State (70%)        │
          └────────────┬────────────┘
                       │
                       ▼
          ┌──────────────────────────┐
          │ REPORTING AGENT          │
          │                          │
          │ 1. Generate summary      │
          │ 2. Create remediation    │
          │ 3. Technical analysis    │
          │ 4. Risk assessment       │
          │ 5. Export formats        │
          └────────────┬────────────┘
                       │
                       ▼
          ┌──────────────────────────┐
          │ Store Final Report       │
          │ Update State (100%)       │
          └────────────┬────────────┘
                       │
                       ▼
                  ┌─────────────┐
                  │ Return      │
                  │ Results     │
                  └─────────────┘
```

---

## 🎯 Agent Responsibilities

### **Reconnaissance Agent**

**Input:**
```python
{
    "target": "192.168.1.1",
    "scope": ["192.168.1.0/24"],
    "mode": "moderate",
    "scan_type": "full",
    "llm_provider": "ollama"
}
```

**Output:**
```python
{
    "target": "192.168.1.1",
    "open_ports": [22, 80, 443, 3306],
    "services": {
        "22": {"service": "ssh", "version": "OpenSSH 7.4"},
        "80": {"service": "http", "version": "Apache 2.4.6"},
        "443": {"service": "https", "version": "Apache 2.4.6"},
        "3306": {"service": "mysql", "version": "5.7.30"}
    },
    "os_fingerprint": "Linux 3.10 - 4.15",
    "vulnerabilities_found": [
        {
            "vulnerability": "Outdated SSH Version",
            "service": "ssh",
            "severity": "high",
            "cve_id": "CVE-2018-15473"
        }
    ],
    "web_technologies": ["Apache", "PHP", "MySQL"],
    "scan_log": [...]
}
```

### **Exploitation Agent**

**Input:** (Reconnaissance output + target)

**Output:**
```python
{
    "vulnerabilities": [
        {
            "title": "Outdated SSH Version",
            "severity": "high",
            "service": "ssh",
            "port": 22,
            "verified": True,
            "confidence_score": 95,
            "verification_evidence": ["ssh version matches CVE data"]
        }
    ],
    "successful_exploits": [...],
    "exploit_attempts": [...],
    "post_exploitation_findings": {}
}
```

### **Reporting Agent**

**Input:** (Reconnaissance + Exploitation outputs)

**Output:**
```python
{
    "scan_id": "scan_123",
    "target": "192.168.1.1",
    "report_title": "Security Assessment Report - 192.168.1.1",
    "executive_summary": "...",
    "risk_assessment": "HIGH (85/100)",
    "vulnerability_count": 12,
    "critical_count": 2,
    "high_count": 5,
    "remediation_plan": [...],
    "recommendations": [...],
    "technical_details": {...}
}
```

---

## 💾 State Management

### `agents/state/scan_state.py`

State is persisted throughout the workflow:

```python
class ScanState(TypedDict):
    # Metadata
    scan_id: str
    target: str
    scan_type: str
    scope: List[str]
    mode: str
    llm_provider: str
    
    # Status
    status: str  # pending, running, completed, failed
    progress: int  # 0-100
    current_phase: str
    
    # Results (populated by agents)
    reconnaissance_data: Optional[Dict]
    exploitation_data: Optional[Dict]
    report_data: Optional[Dict]
    
    # Tracking
    messages: List[Dict]
    errors: List[str]
    start_time: str
    end_time: Optional[str]
```

### State Transitions

```
┌─────────────┐
│   PENDING   │
└──────┬──────┘
       │
       ▼
┌──────────────────┐
│     RUNNING      │ (progress: 0-99%)
│ RECONNAISSANCE   │ (progress: 0-40%)
│ EXPLOITATION     │ (progress: 40-70%)
│ REPORTING        │ (progress: 70-95%)
│ FINALIZING       │ (progress: 95-99%)
└──────┬───────────┘
       │
       ▼
┌─────────────┐
│  COMPLETED  │ ✅
└─────────────┘

OR

┌─────────────┐
│   FAILED    │ ❌
└─────────────┘
```

---

## 🔄 Message Logging

All agent activities are logged to messages:

```python
{
    'type': 'agent',
    'agent': 'reconnaissance',
    'message': 'Found 5 open ports: 22, 80, 443, 3306, 8080',
    'timestamp': '2024-10-01T15:30:45.123Z',
    'data': {
        'ports': [22, 80, 443, 3306, 8080],
        'phase': 'port_scanning'
    }
}
```

---

## 🛠️ Tool Integration

### Port Scanner (Nmap)

```python
from agents.tools.port_scanner import PortScanner

scanner = PortScanner(mode='moderate', timeout=300)
results = scanner.scan('192.168.1.1', ports='1-65535')
```

### Service Detector

```python
from agents.tools.service_detector import ServiceDetector

detector = ServiceDetector()
services = detector.detect('192.168.1.1', ports=[22, 80, 443])
```

### Vulnerability Database

```python
from agents.tools.vulnerability_db import VulnerabilityDB

db = VulnerabilityDB()
vulns = db.lookup_service('ssh', version='7.4')
```

---

## 📝 LLM Prompts

Prompts are stored in JSON for easy management:

### `agents/prompts/reconnaissance_prompts.json`

```json
{
  "vulnerability_analysis": {
    "system": "You are a security expert analyzing scan results...",
    "user": "Analyze these detected services for vulnerabilities: {services}",
    "max_tokens": 2000,
    "temperature": 0.7
  },
  "service_summary": {
    "system": "Summarize discovered services...",
    "user": "Service information: {services}",
    "max_tokens": 500
  }
}
```

---

## 📈 Performance Metrics

Agent execution is tracked:

```python
{
    "scan_id": "scan_123",
    "agents": {
        "reconnaissance": {
            "start_time": "2024-10-01T15:30:00Z",
            "end_time": "2024-10-01T15:35:00Z",
            "duration_seconds": 300,
            "status": "completed",
            "results_count": 15
        },
        "exploitation": {
            "start_time": "2024-10-01T15:35:00Z",
            "end_time": "2024-10-01T15:50:00Z",
            "duration_seconds": 900,
            "status": "completed",
            "results_count": 12
        },
        "reporting": {
            "start_time": "2024-10-01T15:50:00Z",
            "end_time": "2024-10-01T15:55:00Z",
            "duration_seconds": 300,
            "status": "completed"
        }
    },
    "total_duration_seconds": 1500,
    "success": true
}
```

---

## 🚀 Running Agents

### Direct Execution

```python
from backend.orchestrator import execute_scan_sync

scan_request = {
    'scan_id': 'scan_001',
    'target': '192.168.1.1',
    'scan_type': 'full',
    'scope': ['192.168.1.0/24'],
    'mode': 'moderate',
    'llm_provider': 'ollama'
}

result = execute_scan_sync(scan_request)
```

### Async Execution

```python
from backend.orchestrator import execute_scan

result = await execute_scan(scan_request)
```

### Streaming Execution

```python
from backend.orchestrator import stream_scan_execution

for event in stream_scan_execution(scan_request):
    print(f"Progress: {event.progress}%")
    print(f"Phase: {event.current_phase}")
```

---

## 📊 Logging & Monitoring

Enable detailed logging:

```python
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/app/logs/agents.log'),
        logging.StreamHandler()
    ]
)
```

Agent logs are stored in:
```
backend/agents/logs/
├── reconnaissance/scan_001.log
├── exploitation/scan_001.log
└── reporting/scan_001.log
```

---

## 🔒 Security Considerations

1. **Safe Mode:** Agents don't actually exploit unless confirmed
2. **Timeout Protection:** Each agent has configurable timeouts
3. **Error Handling:** Graceful failure with detailed error logs
4. **Rate Limiting:** Tool calls are rate-limited
5. **Sandbox Execution:** Tools run in controlled environment
6. **Access Control:** Tools check authorization before execution

---

## 📚 Testing Agents

### Unit Tests

```bash
pytest backend/tests/agents/test_reconnaissance.py
pytest backend/tests/agents/test_exploitation.py
pytest backend/tests/agents/test_reporting.py
```

### Integration Tests

```bash
pytest backend/tests/integration/test_workflow.py
```

### Performance Tests

```bash
pytest backend/tests/performance/test_agent_speed.py
```

---

**Agent System Ready! 🤖**
