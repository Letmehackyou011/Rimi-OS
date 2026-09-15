# 🔒 AI-Powered Security Research Operating System

> An intelligent, automated security testing platform powered by AI agents and custom Linux OS

**Status:** Final Year Project (In Development - Deadline: November 2024)  
**Language:** Python (Backend) • Vue.js (Frontend)  
**Architecture:** Multi-agent AI orchestration with automated security testing  
**License:** MIT  

---

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Project Structure](#project-structure)
- [Quick Start](#quick-start)
- [Team Setup](#team-setup)
- [Technology Stack](#technology-stack)
- [Configuration](#configuration)
- [Development](#development)
- [Deployment](#deployment)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)

---

## 🎯 Overview

This project combines **artificial intelligence**, **automated security testing**, and a **custom Linux operating system** to create an intelligent platform for automated security research.

### What Makes It Special?

✨ **AI-Powered Agents:** Multiple specialized LLM agents work together orchestrated through LangGraph  
✨ **Multi-LLM Support:** Works with Ollama (local), Claude, Gemini, OpenAI, and Nvidia models  
✨ **Custom OS:** Built with live-build scripts for reproducible deployments  
✨ **Complete Automation:** From reconnaissance to report generation - all automated  
✨ **Team Friendly:** Git-based configuration, easy collaboration  

---

## 🚀 Features

### Current Features (MVP)

- ✅ **Target Configuration** - Define what to test
- ✅ **Reconnaissance Agent** - Automated vulnerability discovery
- ✅ **Exploitation Agent** - Security issue verification
- ✅ **Report Agent** - Comprehensive report generation
- ✅ **API Dashboard** - FastAPI with complete REST API
- ✅ **Web UI** - Vue.js 3 interface (in development)
- ✅ **Multi-LLM Support** - Ollama, Claude, Gemini, OpenAI, Nvidia
- ✅ **Database** - PostgreSQL for findings storage
- ✅ **Reports** - PDF, DOCX, JSON formats

### Planned Features

- 🔄 **Live-Build ISO** - Custom bootable OS
- 🔄 **Docker Deployment** - Container-based distribution
- 🔄 **Advanced Agents** - More specialized roles
- 🔄 **Real-time Scanning** - WebSocket updates
- 🔄 **Compliance Reporting** - OWASP, CIS standards

---

## 📂 Project Structure

```
ai-security-os/
│
├── backend/                          # Python FastAPI Backend
│   ├── main.py                       # Application entry point
│   ├── requirements.txt              # Python dependencies
│   ├── config/
│   │   ├── settings.py              # Settings configuration
│   │   └── security.py              # Encryption utilities
│   ├── database/
│   │   ├── models.py                # SQLAlchemy models
│   │   └── db.py                    # Database setup
│   ├── agents/
│   │   └── orchestrator.py          # LangGraph orchestrator
│   ├── routes/
│   │   ├── scan.py                  # Scan endpoints
│   │   ├── config.py                # Configuration endpoints
│   │   └── reports.py               # Report endpoints
│   └── utils/
│       └── llm_client.py            # LLM client (multi-provider)
│
├── frontend/                          # Vue.js 3 Frontend
│   ├── src/
│   │   ├── App.vue
│   │   ├── components/              # Vue components
│   │   ├── views/                   # Page views
│   │   └── store/                   # Pinia store
│   └── package.json
│
├── os-build/                          # Live-build Configuration
│   ├── build.sh                     # Build script
│   ├── auto/config                  # Live-build config
│   └── config/                      # Build configuration
│
├── docs/                             # Documentation
│   ├── SETUP.md                     # Setup guide
│   ├── ARCHITECTURE.md              # System design
│   └── API.md                       # API documentation
│
├── docker-compose.yml               # Local development
├── .env.example                     # Environment template
└── PROJECT_README.md                # This file
```

---

## 🏃 Quick Start

### Prerequisites

- Python 3.9+
- Node.js 16+
- PostgreSQL 13+
- Docker & Docker Compose (optional, for easier setup)

### Option 1: Docker Compose (Recommended - 5 minutes)

```bash
# Clone repository
git clone https://github.com/yourusername/ai-security-os.git
cd ai-security-os

# Copy environment file
cp .env.example .env

# Start all services
docker-compose up -d

# Wait for services to be ready (30-60 seconds)
docker-compose logs -f

# Backend: http://localhost:8000
# Frontend: http://localhost:5173
# Ollama: http://localhost:11434
```

### Option 2: Manual Setup

#### Step 1: Backend Setup

```bash
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Setup environment
cp ../.env.example ../.env
# Edit .env with your settings

# Initialize database
python -c "from database.db import init_db; asyncio.run(init_db())"

# Run backend
python main.py
# Server runs on http://localhost:8000
```

#### Step 2: Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Create environment file
cp .env.example .env.local

# Start development server
npm run dev
# Server runs on http://localhost:5173
```

#### Step 3: Ollama Setup (Local LLM)

```bash
# Download from https://ollama.ai
# Install and run
ollama serve

# In another terminal, download a model
ollama pull mistral
# or
ollama pull llama2
```

#### Step 4: Test

```bash
# Visit http://localhost:5173 in browser
# API docs available at http://localhost:8000/docs
```

---

## 👥 Team Setup

### Team Roles

| Role | Responsibilities | Files to Work On |
|------|-----------------|------------------|
| **Backend Developer** | API, agents, database | `backend/main.py`, `backend/agents/`, `backend/routes/` |
| **Frontend Developer** | Dashboard, UI | `frontend/src/` |
| **DevOps/OS** | Docker, deployment, OS build | `docker-compose.yml`, `os-build/` |
| **Testing** | QA, bug reports | All files, test coverage |

### Getting Started as a Team

1. **Clone Repository**
   ```bash
   git clone https://github.com/yourusername/ai-security-os.git
   cd ai-security-os
   ```

2. **Create Feature Branches**
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Make Changes** (in your respective folders)

4. **Commit & Push**
   ```bash
   git add .
   git commit -m "feat: description of changes"
   git push origin feature/your-feature-name
   ```

5. **Create Pull Request** on GitHub

---

## 🛠️ Technology Stack

### Backend
- **Framework:** FastAPI (Python web framework)
- **AI/LLM:** LangChain, LangGraph (multi-agent orchestration)
- **Database:** PostgreSQL + SQLAlchemy (ORM)
- **LLM Providers:** Ollama, Claude, Gemini, OpenAI, Nvidia
- **Async:** asyncio, aiohttp

### Frontend
- **Framework:** Vue.js 3 (Composition API)
- **UI Library:** Vuetify (Material Design)
- **State Management:** Pinia
- **HTTP Client:** Axios

### Infrastructure
- **Containerization:** Docker & Docker Compose
- **Database:** PostgreSQL
- **LLM:** Ollama (local)
- **OS:** Live-build (custom Linux)

### Development
- **Version Control:** Git/GitHub
- **Package Management:** pip (Python), npm (Node.js)
- **Testing:** pytest, Vitest
- **Documentation:** Markdown

---

## ⚙️ Configuration

### LLM Configuration

Edit `.env` to select your LLM:

```env
# Use local Ollama
ACTIVE_LLM=ollama
OLLAMA_ENDPOINT=http://localhost:11434
OLLAMA_MODEL=mistral

# Or use Claude
ACTIVE_LLM=claude
CLAUDE_API_KEY=your_key_here

# Or use Gemini
ACTIVE_LLM=gemini
GEMINI_API_KEY=your_key_here
```

### Database Configuration

```env
# PostgreSQL
DATABASE_URL=postgresql://user:password@localhost:5432/security_os
```

### Security Settings

```env
# Encryption key
ENCRYPTION_KEY=generate_with_: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# API secret
SECRET_KEY=your-secret-key-change-in-production
```

---

## 💻 Development

### Running Tests

```bash
# Backend tests
cd backend
pytest tests/ -v

# Frontend tests
cd frontend
npm run test
```

### Code Style

```bash
# Backend formatting
black backend/
flake8 backend/

# Frontend formatting
cd frontend
npm run lint
```

### API Documentation

Visit `http://localhost:8000/docs` for interactive API documentation (Swagger UI)

### Common Tasks

```bash
# Start backend only
cd backend && python main.py

# Start frontend only
cd frontend && npm run dev

# Start Ollama only
ollama serve

# Run all in Docker
docker-compose up -d

# Check logs
docker-compose logs -f backend
docker-compose logs -f frontend

# Stop all services
docker-compose down
```

---

## 📦 Deployment

### Using Docker

```bash
# Build images
docker-compose build

# Run services
docker-compose up -d

# Scale backend (if needed)
docker-compose up -d --scale backend=3

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Building Custom OS (Live-build)

```bash
cd os-build

# Clean previous builds
sudo lb clean --all

# Configure
lb config

# Build ISO
sudo lb build

# Find your custom ISO
ls -lh live-image-amd64.hybrid.iso
```

---

## 🐛 Troubleshooting

### Backend Issues

**Backend won't start**
```bash
# Check if port 8000 is in use
lsof -i :8000

# Database connection error
# Ensure PostgreSQL is running and DATABASE_URL is correct

# LLM connection error
# If using Ollama, ensure it's running: ollama serve
```

**Import errors**
```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

### Frontend Issues

**Dependencies error**
```bash
# Clear cache and reinstall
rm -rf node_modules package-lock.json
npm install
```

**Port 5173 already in use**
```bash
# Use different port
npm run dev -- --port 5174
```

### Database Issues

**Database doesn't exist**
```bash
# Create database manually
psql -U user -h localhost -c "CREATE DATABASE security_os;"
```

**Migration errors**
```bash
# Reset database (development only)
python -c "from database.db import init_db; asyncio.run(init_db())"
```

---

## 📚 Documentation

- **[Setup Guide](docs/SETUP.md)** - Detailed installation instructions
- **[Architecture](docs/ARCHITECTURE.md)** - System design and components
- **[API Reference](docs/API.md)** - Complete API documentation
- **[Deployment Guide](docs/DEPLOYMENT.md)** - Production deployment

---

## 🤝 Contributing

1. **Create a branch** for your feature
   ```bash
   git checkout -b feature/amazing-feature
   ```

2. **Make changes** and test thoroughly

3. **Commit** with clear messages
   ```bash
   git commit -m "feat: add amazing feature"
   ```

4. **Push** to GitHub
   ```bash
   git push origin feature/amazing-feature
   ```

5. **Create Pull Request** with description

---

## 📋 Project Timeline (7 Weeks)

| Week | Backend | Frontend | OS |Testing |
|------|---------|----------|-------|--------|
| 1 | Setup, agents | Setup, components | Cubic install | Setup |
| 2 | LLM integration | Dashboard layout | Config | Manual tests |
| 3 | Agent orchestration | API integration | Build config | Integration |
| 4 | Report generation | Settings page | Customization | End-to-end |
| 5 | API endpoints | Report display | ISO build | Performance |
| 6 | Optimization | Polish UI | Deployment | Security |
| 7 | Testing | Demo prep | Finalization | Submit |

---

## 🎓 Learning Resources

- **LangChain:** https://python.langchain.com/
- **LangGraph:** https://github.com/langchain-ai/langgraph
- **FastAPI:** https://fastapi.tiangolo.com/
- **Vue.js:** https://vuejs.org/
- **PostgreSQL:** https://www.postgresql.org/docs/
- **Live-build:** https://live-team.pages.debian.net/live-manual/

---

## 📞 Support

- **Issues:** Create GitHub issue
- **Discussions:** Use GitHub Discussions
- **Questions:** Ask in team chat
- **Help:** Check documentation first

---

## 📝 License

This project is licensed under the MIT License - see [LICENSE](LICENSE) file for details.

---

## 🙋 FAQ

**Q: Can we use a different LLM provider?**  
A: Yes! Modify the `ACTIVE_LLM` in `.env` - we support Ollama, Claude, Gemini, OpenAI, and Nvidia.

**Q: What if we don't have PostgreSQL?**  
A: Use Docker Compose - it sets up PostgreSQL automatically.

**Q: How do we add new agents?**  
A: Create new nodes in `backend/agents/orchestrator.py` and add them to the graph.

**Q: Is this production-ready?**  
A: It's a final year project - great for learning, should be hardened for production use.

**Q: Can we deploy to the cloud?**  
A: Yes! Docker images make deployment to AWS, GCP, Azure, or any cloud easy.

---

## 📊 Project Status

```
Backend:        ████████░░ 80% - Agents, API complete
Frontend:       ██████░░░░ 60% - Dashboard in progress
OS Build:       ████░░░░░░ 40% - Configuration in progress
Testing:        ██░░░░░░░░ 20% - Unit tests starting
Documentation:  ███░░░░░░░ 30% - README, setup guide
```

---

## 🚀 Next Steps

1. **Setup your local environment** - Choose Docker or manual
2. **Understand the architecture** - Read ARCHITECTURE.md
3. **Start coding** - Create your feature branch
4. **Test frequently** - Don't wait until the end
5. **Document as you go** - Comments and docstrings help

---

**Made with ❤️ for your final year project**  
**Good luck! 🎓**

---

**Last Updated:** [Current Date]  
**Next Review:** Week 3 Integration Check
