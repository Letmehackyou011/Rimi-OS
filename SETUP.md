# 🚀 Quick Setup Guide

Step-by-step instructions to get the project running locally.

---

## 📋 Prerequisites

### Windows/Mac/Linux Users

**Option 1: Docker (Easiest)** ✅ Recommended
- Docker Desktop https://www.docker.com/products/docker-desktop
- That's it! Everything else runs in containers.

**Option 2: Manual Setup**
- Python 3.9+ https://www.python.org/downloads/
- Node.js 16+ https://nodejs.org/
- PostgreSQL https://www.postgresql.org/download/
- Ollama https://ollama.ai/download

---

## ⚡ 5-Minute Setup (Docker)

### Step 1: Get the Code

```bash
# Clone the repository
git clone https://github.com/yourusername/ai-security-os.git
cd ai-security-os

# Or download ZIP and extract
# Download from GitHub → Code → Download ZIP
```

### Step 2: Setup Environment

```bash
# Copy environment template
cp .env.example .env

# On Windows (PowerShell)
# Copy-Item .env.example .env
```

**Edit `.env`** (optional, defaults work):
```env
# Use this to switch LLM providers
ACTIVE_LLM=ollama    # or "claude", "gemini", "openai"
OLLAMA_MODEL=mistral # or "llama2"
```

### Step 3: Start Everything

```bash
# Start all services (takes 1-2 minutes on first run)
docker-compose up -d

# Wait for startup
sleep 30

# Check if everything started
docker-compose ps
```

### Step 4: Access the Application

- **Frontend:** http://localhost:5173
- **Backend API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs

### Done! 🎉

```bash
# To stop everything
docker-compose down

# To view logs
docker-compose logs -f

# To restart
docker-compose restart
```

---

## 🔧 Manual Setup (If Not Using Docker)

### Option A: Linux/Mac

#### Step 1: Setup Backend

```bash
# Navigate to backend
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Mac: source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Setup environment
cp ../.env.example ../.env
# Edit .env with your settings

# Run backend
python main.py
# Server should run on http://localhost:8000
```

#### Step 2: Setup Frontend (New Terminal)

```bash
# Navigate to frontend
cd frontend

# Install dependencies
npm install

# Create environment
cp .env.example .env.local

# Start development server
npm run dev
# Server should run on http://localhost:5173
```

#### Step 3: Setup Ollama (New Terminal)

```bash
# Download from https://ollama.ai/download
# Install and run
ollama serve

# In another terminal, download a model
ollama pull mistral

# Or: ollama pull llama2
```

#### Step 4: Setup PostgreSQL

```bash
# Create database (you might need to adjust credentials)
psql -U postgres -c "CREATE DATABASE security_os;"

# Or use Docker just for Postgres
docker run --name postgres-security \
  -e POSTGRES_PASSWORD=password \
  -p 5432:5432 \
  -d postgres:15
```

### Option B: Windows (Using WSL2 Recommended)

```powershell
# Install WSL2 if you haven't
wsl --install

# Then follow Linux instructions in WSL2 terminal
```

**Or manually:**

1. Install Python from https://www.python.org/
2. Install Node.js from https://nodejs.org/
3. Install PostgreSQL from https://www.postgresql.org/
4. Install Ollama from https://ollama.ai/
5. Follow the same commands as above in Windows PowerShell

---

## 🎯 Your First Scan

### Step 1: Start the Dashboard

Visit http://localhost:5173

### Step 2: Configure LLM (If Not Using Ollama)

1. Go to **Settings** tab
2. Choose your LLM provider:
   - **Ollama** (Default) - Already running locally
   - **Claude** - Add your API key
   - **Gemini** - Add your API key
   - **OpenAI** - Add your API key
3. Click "Test Connection"

### Step 3: Start a Scan

1. Go to **New Scan** tab
2. Enter target: `example.com`
3. Choose mode: **normal** (safe for learning)
4. Click **Start Scan**

### Step 4: Monitor Progress

1. Watch the status update in real-time
2. See vulnerabilities discovered
3. Wait for report generation

### Step 5: View Report

Once completed:
1. Go to **Reports** tab
2. Download as PDF, DOCX, or JSON
3. Review findings and recommendations

---

## 🐛 Troubleshooting

### Problem: Port Already in Use

```bash
# Port 8000 (Backend)
lsof -i :8000
# Kill the process: kill -9 PID

# Port 5173 (Frontend)
lsof -i :5173
# Or use different port: npm run dev -- --port 5174

# Port 11434 (Ollama)
lsof -i :11434
```

### Problem: Database Connection Error

```bash
# Check if PostgreSQL is running
psql -U user -h localhost -c "SELECT 1;"

# If using Docker
docker exec postgres-security psql -U postgres -c "SELECT 1;"

# Reset database (WARNING: Deletes data)
# Stop backend first, then:
python -c "from database.db import init_db; import asyncio; asyncio.run(init_db())"
```

### Problem: Ollama Not Responding

```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Restart Ollama
# Kill current process and run: ollama serve
```

### Problem: Dependencies Error

```bash
# Clear and reinstall
cd backend
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt --force-reinstall

# Or for frontend
cd frontend
rm -rf node_modules package-lock.json
npm install
```

### Problem: "Module not found" errors

```bash
# Backend
pip install -r requirements.txt -U

# Frontend
npm install --legacy-peer-deps
```

### Problem: Can't Connect to API

1. Check backend is running: http://localhost:8000/health
2. Check CORS settings in `.env`
3. Check frontend API URL in `.env.local`

```env
# .env.local in frontend folder
VITE_API_URL=http://localhost:8000
```

### Problem: Ollama Model Not Found

```bash
# List available models
ollama list

# Download model
ollama pull mistral
ollama pull llama2

# Check what model is configured
# In .env: OLLAMA_MODEL=mistral
```

---

## 📚 Next Steps

### Learn the Architecture
Read `docs/ARCHITECTURE.md` to understand how components work together.

### Explore the API
Visit http://localhost:8000/docs for interactive API documentation.

### Modify for Your Needs

**Change the project name:**
1. Edit `.env` - `APP_NAME`
2. Edit frontend - `src/App.vue` - `toolbar-title`
3. Edit docs - Update project name everywhere

**Add new features:**
1. Backend: Add to `backend/agents/`
2. Frontend: Add to `frontend/src/components/`
3. API: Add to `backend/routes/`

---

## 🔗 Useful Commands

```bash
# Start everything (Docker)
docker-compose up -d

# View logs
docker-compose logs -f backend
docker-compose logs -f frontend

# Restart specific service
docker-compose restart backend

# Stop everything
docker-compose down

# Clean everything (including data!)
docker-compose down -v

# Backend only (manual)
cd backend && python main.py

# Frontend only (manual)
cd frontend && npm run dev

# Run tests
pytest backend/tests/
npm run test
```

---

## 🎓 Learning Path

1. **Start here** - Get it running (this guide)
2. **Read** - `docs/ARCHITECTURE.md` - Understand the system
3. **Explore** - `docs/API.md` - See all endpoints
4. **Code** - Make changes in your team's area
5. **Test** - Create a scan, view results
6. **Deploy** - Package as custom OS

---

## 📞 Help

- **API Docs:** http://localhost:8000/docs
- **GitHub Issues:** Report problems
- **Architecture:** Read `docs/ARCHITECTURE.md`
- **API Reference:** Read `docs/API.md`

---

## ✅ Checklist

Before you start coding:

- [ ] Code cloned from GitHub
- [ ] `.env` file created (copy from `.env.example`)
- [ ] Docker installed OR Python+Node+PostgreSQL installed
- [ ] `docker-compose up -d` running (OR all services started manually)
- [ ] Frontend loads at http://localhost:5173
- [ ] Backend API responds at http://localhost:8000/health
- [ ] Ollama running if using local models
- [ ] Can access API docs at http://localhost:8000/docs

---

**You're ready! 🚀**

Happy coding! If you hit issues, check the Troubleshooting section or ask your team members.
