# Project Name
Engineering Management Agent (EMA)

# Version
v1.0.0 (development)

# Slogan
工程管理，从"人管"到"智能体协管"

# Core Rule
- Technical standard: Refer to Manus AI agent architecture
- Work goal: "Engineering management from 'human management' to 'agent co-management'"
- Agent management: Flattened, Main-Agent coordinates 6 Sub-Agents

# Project Path
`D:\OpenClawDataworkspace\Projects\engineering-management-agent`

# Repository Structure
- EMA project: `engineering-management-agent/`
- Legacy project: `../blueprint-ai/` (TechRdAgent inherits from this)

# Architecture
```
刚哥 (Boss)
└── EngineeringManagementAgent (Main-Agent)
    ├── SafetyComplianceAgent
    ├── MarketSalesAgent
    ├── TechRdAgent (inherits blueprint-ai)
    ├── EngineeringDeliveryAgent
    ├── CostBenefitAgent
    └── CustomerServiceAgent
```

# Development Status
- Phase 1 (v1.0.0): Building project skeleton + TechRdAgent
- Phase 2: Other Sub-Agents
- Phase 3: Full system integration

# Tech Stack
- Backend: FastAPI + Python 3.10+
- Frontend: Vue3 + Vite + TypeScript
- LLM: Ollama (local) + cloud fallback
- Sandbox: Pyodide (frontend) + Docker (backend)
- Memory: ChromaDB + SQLite