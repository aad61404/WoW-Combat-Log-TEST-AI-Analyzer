# WoW Combat Log AI Analyzer — AI/FDE Learning Project

> [!IMPORTANT]
> **2026-10-07 路線更新：**近期工作的唯一優先順序以
> [`docs/active-roadmap.md`](docs/active-roadmap.md) 為準。本文件後續內容保留為技術設計與
> 長期 backlog；其中 Redis、RAG、Agent、MCP、微服務等項目不得早於 active roadmap
> 所定義的 FastAPI → WCL API → PostgreSQL → GET API 端到端里程碑。

## Active Focus（2026-10-07）

```text
Python Backend
      ↓
WoW Full-stack Product
      ↓
Deterministic Combat Analysis
      ↓
Applied AI + Evals
      ↓
Production + Interview Readiness
```

目前只做一個主專案。近期不新增第二專案，也不把 RAG、LangGraph、MCP、Multi-Agent、
Redis、Kubernetes、微服務或 Fine-tuning 排入當週工作。

## Current Baseline（2026-09-26）

這份 roadmap 是從現有 MVP 繼續演進，不是砍掉重做。目前已具備 FastAPI、Next.js、
WCL OAuth／GraphQL client、事件正規化、死亡時間線、基礎 deterministic rules、
Gemini coach／fallback、fixture tests 與 Playwright 流程。

第一個里程碑尚缺 PostgreSQL／Redis、Docker Compose、持久化 importer 與對應 REST API；
真實 WCL 與 Gemini 串接也尚未以憑證完成 live validation。因此接下來以 Phase 0／1 的
基礎設施與資料持久化為主，既有分析與 UI 保留並逐步接到新的資料模型。

## 1. Project Goal

建立一個可實際部署的 AI Application：

```text
Warcraft Logs URL
        ↓
WCL API
        ↓
FastAPI
        ↓
Combat Analysis Engine
        ↓
PostgreSQL / Redis
        ↓
LLM + Tool Calling
        ↓
AI Coach Report
        ↓
Next.js UI
```

使用者貼入 Warcraft Logs Report URL 後，系統自動分析戰鬥紀錄，回答：

- 為什麼滅團？
- 哪些玩家漏掉機制？
- DPS / HPS 是否異常？
- Death Timeline 發生什麼？
- 下一場應該改善什麼？
- AI 的判斷依據是什麼？

這不是單純 LLM Wrapper。

目標是練習一個 Production AI Product / FDE 會遇到的完整問題：

```text
External API
Data Processing
Backend API
Database
Cache
Frontend
LLM
Tool Calling
RAG
Evals
Observability
Deployment
CI/CD
```

---

# 2. Target Stack

## Frontend

```text
Next.js
TypeScript
React
TanStack Query
Tailwind CSS
```

重點：

- Server State
- API integration
- Streaming response
- Error handling
- Loading state
- Report visualization

---

## Backend

```text
Python
FastAPI
Pydantic
SQLAlchemy
Alembic
```

重點：

- REST API
- Async programming
- Dependency Injection
- Service / Repository separation
- Error handling
- Structured logging

---

## Data

```text
PostgreSQL
Redis
```

PostgreSQL：

- Report metadata
- Fight metadata
- Player statistics
- Analysis results
- AI reports
- Evaluation results

Redis：

- WCL API cache
- Analysis cache
- Rate limiting
- Background job state

---

## AI

```text
LLM API
Structured Output
Tool Calling
RAG
Evals
Tracing
```

模型供應商不綁死。

建立：

```text
LLMProvider

├── GeminiProvider
├── OpenAIProvider
└── MockProvider
```

讓模型可以替換。

---

# 3. Architecture

```text
                     ┌──────────────┐
                     │   Next.js    │
                     │     Web      │
                     └──────┬───────┘
                            │
                            ▼
                     ┌──────────────┐
                     │   FastAPI    │
                     │     API      │
                     └──────┬───────┘
                            │
             ┌──────────────┼──────────────┐
             │              │              │
             ▼              ▼              ▼
        WCL Service    Analysis Engine   AI Service
             │              │              │
             ▼              ▼              ▼
        Warcraft Logs   PostgreSQL      LLM Provider
             │              │
             │              ▼
             └──────────► Redis
```

核心原則：

```text
LLM ≠ Analysis Engine
```

Combat Analysis Engine 負責 deterministic analysis。

例如：

```text
death detection
mechanic failure
damage spike
DPS statistics
HPS statistics
timeline
buff/debuff
```

LLM 負責：

```text
reasoning
explanation
prioritization
coaching
```

避免：

```text
Raw combat log
      ↓
直接丟 LLM
      ↓
「請幫我分析」
```

---

# 4. Phase 0 — Engineering Foundation

目標：建立 Production-like 開發環境。

Repository：

```text
wow-ai-analyzer/

├── apps/
│   ├── web/
│   └── api/
│
├── packages/
│   └── shared/
│
├── infra/
│
├── evals/
│
├── docs/
│
├── docker-compose.yml
└── README.md
```

建立：

- Git repository
- Docker Compose
- PostgreSQL
- Redis
- Environment variables
- ESLint
- Ruff
- Pytest
- Prettier
- GitHub Actions

驗收：

```bash
docker compose up
```

即可啟動：

```text
Frontend
Backend
PostgreSQL
Redis
```

---

# 5. Phase 1 — WCL Data Pipeline

目標：

先完全不碰 AI。

完成：

```text
WCL URL
   ↓
Parse Report ID
   ↓
OAuth
   ↓
GraphQL API
   ↓
Fight Data
   ↓
Normalize
   ↓
PostgreSQL
```

API：

```http
POST /reports/import

GET /reports/{report_id}

GET /reports/{report_id}/fights

GET /fights/{fight_id}
```

建立：

```python
class WarcraftLogsClient:
    async def get_report(...)
    async def get_fights(...)
    async def get_events(...)
    async def get_players(...)
```

學習重點：

- OAuth2 Client Credentials
- GraphQL
- Async HTTP
- Rate limiting
- Retry
- Timeout
- API abstraction

驗收：

貼入 Warcraft Logs URL，可以看到：

```text
Boss
Duration
Players
Deaths
DPS
HPS
Result
```

---

# 6. Phase 2 — Combat Analysis Engine

這是專案最重要的一層。

不要先用 AI。

建立：

```text
CombatAnalysisEngine
```

輸入：

```python
FightData
```

輸出：

```json
{
  "deaths": [],
  "mechanic_failures": [],
  "damage_spikes": [],
  "player_stats": [],
  "timeline": []
}
```

第一版只分析：

### Death Analysis

```text
死亡時間
死亡前 10 秒
受到哪些傷害
有沒有 defensive
有沒有 healer coverage
```

### Mechanic Failure

```text
avoidable damage
debuff failure
interrupt miss
position mechanic
```

### Performance

```text
DPS
HPS
activity
death count
avoidable damage
```

驗收：

不用 LLM，也能產生：

```text
Player A
死亡：03:42

死亡前：
03:36 Shadow Bolt 120k
03:39 Void Explosion 240k
03:42 Void Explosion 310k

Defensive:
None

Possible issue:
Repeated avoidable damage
```

---

# 7. Phase 3 — AI Coach V1

現在才加入 LLM。

流程：

```text
Analysis Engine
      ↓
Structured Fight Summary
      ↓
LLM
      ↓
Coach Report
```

不要把完整 combat log 丟給模型。

Prompt Input：

```json
{
  "boss": "...",
  "result": "wipe",
  "duration": 245,
  "deaths": [],
  "mechanic_failures": [],
  "player_stats": []
}
```

Output 使用 Structured Output：

```python
class CoachReport(BaseModel):
    summary: str
    wipe_causes: list[Issue]
    player_feedback: list[PlayerFeedback]
    priorities: list[str]
```

驗收：

AI 必須回答：

```text
主要滅團原因

1.
2.
3.

玩家問題

Player A
問題：
證據：
改善方式：

下一場優先改善

1.
2.
3.
```

---

# 8. Phase 4 — Tool Calling

從：

```text
LLM receives everything
```

升級：

```text
LLM
 │
 ├── get_player_deaths()
 ├── get_damage_taken()
 ├── get_buff_uptime()
 ├── get_cast_timeline()
 ├── get_mechanic_failures()
 └── compare_players()
```

例如：

```python
@tool
def get_player_deaths(
    fight_id: str,
    player_name: str
):
    ...
```

AI 可以自行決定：

```text
User:
為什麼 Mage 一直死？

AI:
→ get_player_deaths()

→ get_damage_taken()

→ get_buff_uptime()

→ Generate answer
```

這一階段開始真正接近 Agentic Application。

---

# 9. Phase 5 — RAG

建立 Boss Knowledge Base：

```text
Boss Guide
Mechanics
Abilities
Role responsibilities
Common wipe reasons
```

流程：

```text
Boss
 ↓
Retrieve relevant mechanics
 ↓
Combat Evidence
 ↓
LLM
 ↓
Diagnosis
```

Vector store MVP 可以先使用：

```text
PostgreSQL
+
pgvector
```

不額外引入 Vector DB。

驗收：

AI 能區分：

```text
「玩家受到大量傷害」

vs

「這個傷害本來應該躲掉」
```

---

# 10. Phase 6 — Evals

這一階段是作品集的重要差異。

建立：

```text
evals/

├── datasets/
│   ├── death_cases.json
│   ├── mechanic_cases.json
│   └── wipe_cases.json
│
├── evaluators/
│
└── runner.py
```

評估：

```text
Death detection accuracy
Mechanic detection accuracy
Evidence correctness
Hallucination rate
Report consistency
```

例如：

```text
Case #001

Expected:
Player A died because mechanic X was missed.

AI:
Player A died because mechanic X was missed.

PASS
```

以及：

```text
AI claims:
Player A failed mechanic Y

Evidence:
No mechanic Y event

FAIL — Unsupported Claim
```

核心指標：

```text
Evidence Grounding Rate
Unsupported Claim Rate
Mechanic Detection Accuracy
```

---

# 11. Phase 7 — Observability

記錄：

```text
Request
↓
Tools called
↓
Retrieved context
↓
Prompt
↓
LLM response
↓
Tokens
↓
Latency
↓
Cost
```

Dashboard：

```text
LLM requests
Average latency
Token usage
Cost / report
Tool failures
WCL failures
AI failures
```

學習：

- tracing
- structured logging
- metrics
- AI observability

---

# 12. Phase 8 — Reliability

加入 Production Engineering。

### Retry

```text
WCL timeout

retry
1s
2s
4s
```

### Fallback

```text
Gemini
   ↓ failure
OpenAI
   ↓ failure
Deterministic report
```

### Cache

```text
WCL response
Analysis result
Boss knowledge
```

### Rate Limit

```text
User
↓
API Gateway
↓
Rate Limiter
```

### Background Jobs

大型 Report：

```text
POST /analysis
      ↓
Job Queue
      ↓
Worker
      ↓
Analysis
      ↓
Result
```

---

# 13. Phase 9 — Production Deployment

Container：

```text
Next.js
FastAPI
PostgreSQL
Redis
Worker
```

建立：

```text
Docker
CI/CD
Secrets
Health Check
Migration
Monitoring
```

GitHub Actions：

```text
PR
 ↓
Lint
 ↓
Type Check
 ↓
Unit Test
 ↓
Integration Test
 ↓
Eval
 ↓
Docker Build
```

---

# 14. Phase 10 — Multi-Agent Development Workflow

最後用這個專案實驗 AI Software Engineering。

```text
                 Architect
                     │
          ┌──────────┼──────────┐
          │          │          │
          ▼          ▼          ▼
     Frontend     Backend      Test
      Agent        Agent       Agent
          │          │          │
          ▼          ▼          ▼
     Worktree A  Worktree B Worktree C
          │          │          │
          └──────────┼──────────┘
                     ▼
               Integration
                     │
                     ▼
                    CI
```

角色：

```text
GPT
→ Architecture
→ Spec
→ Review
→ Debug analysis

Claude Code / Codex
→ Implementation

CI
→ Objective Judge
```

Judge：

```text
ESLint
TypeScript
Pytest
Integration Tests
Playwright
AI Evals
Docker Build
```

---

# 15. 8-Week Roadmap

## Week 1

Infrastructure + WCL

```text
FastAPI
PostgreSQL
Redis
Docker
WCL OAuth
GraphQL
```

Deliverable：

```text
WCL URL → Fight Data
```

---

## Week 2

Combat Analysis Engine

```text
Events
Deaths
Damage
Players
Timeline
```

Deliverable：

```text
Fight → deterministic analysis
```

---

## Week 3

Next.js UI

```text
Report page
Fight selector
Player table
Death timeline
```

Deliverable：

```text
完整可操作 Web Application
```

---

## Week 4

LLM Integration

```text
Structured Output
Prompt design
Provider abstraction
AI Coach
```

Deliverable：

```text
Fight → AI Coach Report
```

---

## Week 5

Tool Calling

```text
Player tools
Combat tools
Comparison tools
```

Deliverable：

```text
Conversational Fight Analyst
```

---

## Week 6

RAG

```text
Boss knowledge
pgvector
Retrieval
Grounding
```

Deliverable：

```text
Mechanic-aware AI Coach
```

---

## Week 7

Evals + Observability

```text
Evaluation dataset
Tracing
Token usage
Latency
Cost
```

Deliverable：

```text
可量化 AI Quality
```

---

## Week 8

Production

```text
CI/CD
Docker
Deployment
Retry
Fallback
Cache
Rate Limit
README
Architecture Diagram
Demo
```

Deliverable：

```text
Production-ready Portfolio Project
```

---

# 16. Portfolio Definition of Done

最終 GitHub README 必須能展示：

```text
1. Problem
2. Architecture
3. Demo
4. Data Pipeline
5. AI Architecture
6. Tool Calling
7. RAG
8. Evals
9. Observability
10. Reliability
11. Deployment
12. Engineering Decisions
```

不能只是：

> I built an AI Warcraft Logs analyzer.

而應該呈現：

> Designed and deployed an AI-powered combat analysis platform integrating external GraphQL APIs, deterministic event processing, LLM tool calling, RAG, evaluation pipelines and production observability.

---

# 17. Career Skills Mapping

完成專案後：

| 專案內容 | 面試能力 |
|---|---|
| Next.js | Product Frontend |
| FastAPI | Backend |
| PostgreSQL | Data Modeling |
| Redis | Cache / Distributed System |
| Docker | Infrastructure |
| WCL GraphQL | External API Integration |
| Combat Engine | Data Processing |
| LLM | AI Application |
| Tool Calling | Agentic AI |
| RAG | AI Knowledge System |
| Evals | AI Quality Engineering |
| Observability | Production AI |
| Retry/Fallback | Reliability |
| CI/CD | Software Engineering |

最終定位不再是：

```text
Cocos Game Frontend Engineer
```

而是：

```text
Product / Full-stack Engineer
        +
AI Application Engineer
        +
FDE-ready Engineer
```

---

# 18. Scope Control

第一版禁止加入：

```text
Authentication
Payment
Guild system
Social system
Multiple games
Mobile App
Complex microservices
Kubernetes
Kafka
```

原因：

這些不會直接增加這個作品對 AI Application / FDE 面試的價值。

優先順序固定：

```text
Working Product
      ↓
Deterministic Analysis
      ↓
LLM
      ↓
Tool Calling
      ↓
Evals
      ↓
Observability
      ↓
Production Reliability
```

不要反過來。

---

# 19. First Milestone

第一個 Milestone 只有一件事：

```text
Input:
https://www.warcraftlogs.com/reports/{REPORT_ID}

             ↓

WCL GraphQL API

             ↓

FastAPI

             ↓

PostgreSQL

             ↓

GET /reports/{id}

             ↓

JSON Fight Summary
```

在這條 pipeline 跑通以前：

**不做 LLM、不做 RAG、不做 Agent。**

第一階段的 Definition of Done：

```text
□ FastAPI project 建立
□ Docker Compose
□ PostgreSQL
□ Redis
□ WCL OAuth
□ GraphQL client
□ Report URL parser
□ Fight importer
□ Database schema
□ GET report API
□ Pytest
□ README setup instructions
```

完成這一步，再進 Combat Analysis Engine。

這份 Plan 的核心刻意不是「8 週學一堆框架」，而是每一週都讓同一個產品增加一層工程能力。最重要的是 **Week 1 → 4 先做出能 Demo 的 vertical slice，Week 5 → 8 再把它升級成能拿去講 FDE / AI Application Engineering 的作品**。
