# API Documentation

## 📚 Overview

Complete REST API reference for AI Security Research OS backend.

**Base URL:** `http://localhost:8000`  
**Documentation:** `http://localhost:8000/docs` (Swagger UI)  
**API Version:** 1.0  

---

## 🔐 Authentication

Currently, the API supports token-based authentication (JWT).

### Getting a Token

```bash
# Login endpoint (to be implemented)
POST /api/auth/login
Content-Type: application/json

{
  "username": "user",
  "password": "password"
}

# Response
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer"
}
```

### Using Token

```bash
# Add to request headers
Authorization: Bearer YOUR_TOKEN_HERE
```

---

## 🔍 Scan Endpoints

### Start a Scan

**Endpoint:** `POST /api/scan/start`

**Request:**
```json
{
  "target": "example.com",
  "scope": "port:80,443",
  "mode": "normal",
  "llm_provider": "ollama",
  "llm_model": "mistral"
}
```

**Parameters:**
- `target` (required): URL or IP address to scan
- `scope` (optional): Scan scope definition
- `mode` (optional): "normal", "aggressive", or "stealth" (default: "normal")
- `llm_provider` (optional): LLM provider to use (default: from config)
- `llm_model` (optional): Specific model (default: from config)

**Response:** `200 OK`
```json
{
  "scan_id": "550e8400-e29b-41d4-a716-446655440000",
  "target": "example.com",
  "status": "pending",
  "created_at": "2024-01-15T10:30:00Z",
  "message": "Scan queued and will start shortly"
}
```

**Error Responses:**
- `400 Bad Request` - Invalid parameters
- `500 Internal Server Error` - Server error

---

### Get Scan Status

**Endpoint:** `GET /api/scan/{scan_id}/status`

**Response:** `200 OK`
```json
{
  "scan_id": "550e8400-e29b-41d4-a716-446655440000",
  "target": "example.com",
  "status": "running",
  "stage": "reconnaissance",
  "progress_percentage": 35.5,
  "vulnerabilities_found": 3,
  "error": null
}
```

**Status Values:**
- `pending` - Waiting to start
- `running` - Currently executing
- `completed` - Finished successfully
- `failed` - Failed with error
- `cancelled` - Cancelled by user

**Stages:**
- `reconnaissance` - Scanning phase
- `exploitation` - Verification phase
- `reporting` - Report generation
- `completed` - All done

---

### Get Scan Results

**Endpoint:** `GET /api/scan/{scan_id}/results`

**Response:** `200 OK`
```json
{
  "scan_id": "550e8400-e29b-41d4-a716-446655440000",
  "target": "example.com",
  "status": "completed",
  "vulnerabilities": [
    {
      "id": "vuln-001",
      "title": "SQL Injection in Login Form",
      "severity": "critical",
      "type": "sql_injection",
      "description": "Login parameter vulnerable to SQL injection",
      "affected_endpoint": "/login",
      "verified": true
    }
  ],
  "recommendations": [
    "Implement parameterized queries",
    "Add input validation",
    "Use ORM framework"
  ],
  "risk_score": 8.5
}
```

**Vulnerability Fields:**
- `id`: Unique identifier
- `title`: Vulnerability name
- `severity`: critical/high/medium/low/info
- `type`: Type of vulnerability
- `description`: Detailed description
- `affected_endpoint`: Where vulnerability found
- `verified`: Whether verified true/false

---

### Cancel a Scan

**Endpoint:** `POST /api/scan/{scan_id}/cancel`

**Response:** `200 OK`
```json
{
  "message": "Scan cancelled successfully"
}
```

**Errors:**
- `404 Not Found` - Scan doesn't exist
- `400 Bad Request` - Can't cancel completed scan

---

### List All Scans

**Endpoint:** `GET /api/scan/list/all?skip=0&limit=20`

**Parameters:**
- `skip` (optional): Number of scans to skip (default: 0)
- `limit` (optional): Maximum scans to return (default: 20)

**Response:** `200 OK`
```json
{
  "scans": [
    {
      "scan_id": "550e8400-e29b-41d4-a716-446655440000",
      "target": "example.com",
      "status": "completed",
      "created_at": "2024-01-15T10:30:00Z",
      "duration": 245.5,
      "vulnerabilities": 5
    }
  ],
  "total": 42
}
```

---

## ⚙️ Configuration Endpoints

### Get LLM Configuration

**Endpoint:** `GET /api/config/llm`

**Response:** `200 OK`
```json
{
  "active_provider": "ollama",
  "ollama_model": "mistral",
  "claude_model": "claude-3-5-sonnet-20241022",
  "gemini_model": "gemini-2.0-flash",
  "openai_model": "gpt-4",
  "max_tokens": 8000,
  "context_window": 32000
}
```

---

### Update LLM Configuration

**Endpoint:** `PUT /api/config/llm`

**Request:**
```json
{
  "active_provider": "claude",
  "claude": {
    "api_key": "sk-...",
    "model": "claude-3-5-sonnet-20241022"
  },
  "max_tokens": 8000,
  "context_window": 200000
}
```

**Parameters:**
- `active_provider` (required): "ollama", "claude", "gemini", "openai", or "nvidia"
- Provider-specific config (required if active_provider selected):
  - `ollama`: endpoint, model
  - `claude`: api_key, model
  - `gemini`: api_key, model
  - `openai`: api_key, model
  - `nvidia`: api_key, endpoint
- `max_tokens`: Token limit for requests
- `context_window`: Context window size

**Response:** `200 OK` - Same as GET

---

### Test LLM Connection

**Endpoint:** `POST /api/config/llm/test`

**Response:** `200 OK`
```json
{
  "status": "success",
  "message": "LLM connection successful",
  "response_preview": "LLM connection successful"
}
```

---

### Get App Configuration

**Endpoint:** `GET /api/config/app`

**Response:** `200 OK`
```json
{
  "app_name": "AI Security Research OS",
  "version": "1.0.0",
  "debug": true,
  "default_llm": "ollama",
  "default_model": "mistral",
  "max_tokens": 8000,
  "context_window": 32000
}
```

---

### Health Check

**Endpoint:** `GET /api/config/health`

**Response:** `200 OK`
```json
{
  "status": "healthy",
  "database": "ok",
  "llm": "ok",
  "app": "running"
}
```

**Possible Values:**
- `status`: "healthy" / "degraded" / "unhealthy"
- `database`: "ok" / "error"
- `llm`: "ok" / "error"
- `app`: "running" / "error"

---

## 📄 Report Endpoints

### Generate Report

**Endpoint:** `POST /api/reports/generate`

**Request:**
```json
{
  "scan_id": "550e8400-e29b-41d4-a716-446655440000",
  "format": "pdf",
  "include_recommendations": true,
  "include_evidence": true
}
```

**Parameters:**
- `scan_id` (required): ID of completed scan
- `format` (optional): "pdf", "docx", or "json" (default: "pdf")
- `include_recommendations` (optional): Include fix recommendations
- `include_evidence` (optional): Include proof of concepts

**Response:** `200 OK`
```json
{
  "report_id": "report-001",
  "scan_id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "Security Assessment Report - example.com",
  "format": "pdf",
  "generated_at": "2024-01-15T11:30:00Z",
  "vulnerability_count": 5,
  "download_url": "/api/reports/report-001/download"
}
```

---

### Get Report Details

**Endpoint:** `GET /api/reports/{report_id}`

**Response:** `200 OK`
```json
{
  "report_id": "report-001",
  "scan_id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "Security Assessment Report - example.com",
  "format": "pdf",
  "generated_at": "2024-01-15T11:30:00Z",
  "vulnerabilities": {
    "total": 5,
    "critical": 2,
    "high": 2,
    "medium": 1,
    "low": 0
  },
  "risk_score": 8.5,
  "download_url": "/api/reports/report-001/download"
}
```

---

### Download Report

**Endpoint:** `GET /api/reports/{report_id}/download`

**Response:** File download (PDF/DOCX/JSON)

**Headers:**
- `Content-Type`: application/pdf or application/vnd.openxmlformats-officedocument.wordprocessingml.document or application/json
- `Content-Disposition`: attachment; filename="report.pdf"

---

### Get Scan Reports

**Endpoint:** `GET /api/reports/scan/{scan_id}/reports`

**Response:** `200 OK`
```json
{
  "scan_id": "550e8400-e29b-41d4-a716-446655440000",
  "reports": [
    {
      "report_id": "report-001",
      "format": "pdf",
      "generated_at": "2024-01-15T11:30:00Z",
      "vulnerability_count": 5,
      "risk_score": 8.5
    }
  ]
}
```

---

### Delete Report

**Endpoint:** `DELETE /api/reports/{report_id}`

**Response:** `200 OK`
```json
{
  "message": "Report deleted successfully"
}
```

---

## 🌐 General Endpoints

### Root Endpoint

**Endpoint:** `GET /`

**Response:** `200 OK`
```json
{
  "message": "AI Security Research OS API",
  "docs": "/docs",
  "status": "running"
}
```

---

### Health Check

**Endpoint:** `GET /health`

**Response:** `200 OK`
```json
{
  "status": "healthy",
  "service": "AI Security Research OS",
  "version": "1.0.0"
}
```

---

## 📊 Request/Response Examples

### Complete Scan Workflow

```bash
# 1. Start scan
curl -X POST http://localhost:8000/api/scan/start \
  -H "Content-Type: application/json" \
  -d '{
    "target": "example.com",
    "mode": "normal"
  }'

# Response
{
  "scan_id": "123e4567-e89b-12d3-a456-426614174000",
  "target": "example.com",
  "status": "pending",
  "message": "Scan queued"
}

# 2. Check status (repeat every 5 seconds)
curl http://localhost:8000/api/scan/123e4567-e89b-12d3-a456-426614174000/status

# Response (in progress)
{
  "scan_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "running",
  "stage": "reconnaissance",
  "progress_percentage": 45.0
}

# Response (completed)
{
  "scan_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "completed",
  "stage": "completed",
  "progress_percentage": 100.0,
  "vulnerabilities_found": 5
}

# 3. Get results
curl http://localhost:8000/api/scan/123e4567-e89b-12d3-a456-426614174000/results

# Response with vulnerabilities

# 4. Generate report
curl -X POST http://localhost:8000/api/reports/generate \
  -H "Content-Type: application/json" \
  -d '{
    "scan_id": "123e4567-e89b-12d3-a456-426614174000",
    "format": "pdf"
  }'

# Response with report_id

# 5. Download report
curl -O http://localhost:8000/api/reports/REPORT_ID/download
```

---

## ⚠️ Error Handling

### HTTP Status Codes

| Code | Meaning | Example |
|------|---------|---------|
| 200 | Success | Request succeeded |
| 400 | Bad Request | Invalid parameters |
| 404 | Not Found | Scan/report doesn't exist |
| 500 | Server Error | Internal error |

### Error Response Format

```json
{
  "detail": "Error message explaining what went wrong"
}
```

### Common Errors

**Scan not found:**
```json
{
  "detail": "Scan not found"
}
```

**Invalid scan mode:**
```json
{
  "detail": "Invalid mode. Must be: normal, aggressive, or stealth"
}
```

**LLM not configured:**
```json
{
  "detail": "LLM not properly configured"
}
```

---

## 🔄 Rate Limiting

Currently no rate limiting. Planned for production:
- 100 requests per minute per IP
- 1 concurrent scan per user
- 10 scans per day per user

---

## 📱 WebSocket (Planned)

Real-time scan updates via WebSocket:

```javascript
// Frontend example
const socket = new WebSocket('ws://localhost:8000/ws/scan/SCAN_ID');

socket.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Status:', data.status);
  console.log('Progress:', data.progress_percentage);
};
```

---

## 🧪 Testing API

### Using curl

```bash
# Test connection
curl http://localhost:8000/health

# Test with jq (pretty print)
curl http://localhost:8000/health | jq
```

### Using Postman

1. Import API documentation from `http://localhost:8000/openapi.json`
2. Set base URL to `http://localhost:8000`
3. Create scan request
4. Check status

### Using Python

```python
import requests

# Start scan
response = requests.post('http://localhost:8000/api/scan/start', json={
    'target': 'example.com',
    'mode': 'normal'
})
scan_data = response.json()
scan_id = scan_data['scan_id']

# Get status
response = requests.get(f'http://localhost:8000/api/scan/{scan_id}/status')
print(response.json())
```

---

**Version:** 1.0  
**Last Updated:** [Current Date]  
**Status:** In Development
