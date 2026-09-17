# WoW Combat Log AI Analyzer — MVP v0.1 Implementation Plan (Revised)

## Core Philosophy

> **不是「AI 看 Combat Log 猜怎麼滅團」。**
>
> 而是 **WCL → Python deterministic analysis → structured evidence → LLM explanation。**

LLM 不負責判斷「這個 debuff 看起來像站錯」。Python 規則引擎先確定事實，LLM 只負責把證據轉成人類可讀的教練報告。

---

## Architecture

```
Warcraft Logs URL
        ↓
  WCL OAuth + GraphQL
        ↓
  Raw WCL Events
        ↓
  Event Normalizer
        ↓
  Encounter Rules (boss-specific)
        ↓
  Deterministic Analyzer
        ↓
  Structured Evidence (JSON)
        ↓
  Gemini LLM Coach
        ↓
  中文教練報告
        ↓
  Next.js UI
```

---

## User Review Required

> [!IMPORTANT]
> **WCL API 憑證**：你需要到 [Warcraft Logs API Clients](https://www.warcraftlogs.com/api/clients/) 建立 OAuth Client，取得 `WCL_CLIENT_ID` 和 `WCL_CLIENT_SECRET`。MVP 使用 Client Credentials Flow（公開 report 資料）。

> [!IMPORTANT]
> **Gemini API Key**：AI 教練使用 Google Gemini API。請確認你有可用的 `GEMINI_API_KEY`。

> [!WARNING]
> **WCL Rate Limit**：WCL API 有 points/hour 限制。開發 / 測試階段大量使用 fixtures，不要每次都打真實 API。

---

## Open Questions

1. **初始 Boss Rules**：MVP 先實作哪 3 個 Boss 的規則？建議從一個經典、資料豐富的 raid boss 開始（例如 TWW S2 的某個 boss，或經典 boss）。如果你有偏好的 report URL 可以直接給我，我來設計對應的 rules。
2. **Docker Compose**：MVP 先做 local dev only（`uvicorn` + `npm run dev`），還是加 docker-compose？（建議先 local dev，最後再包 Docker）

---

## MVP v0.1 Scope — 精確定義

### ✅ 做

| 功能 | 說明 |
|------|------|
| WCL OAuth | Client Credentials Flow，自動取 token |
| WCL GraphQL | 抓 report info、fight list、fight events |
| Event Normalizer | 標準化 raw event 格式 |
| Encounter Rule Engine | 可插拔的 boss-specific 規則框架 |
| Death Timeline | 每個死亡事件 + 死前 5 秒傷害來源 |
| 3 個 Boss Rules | AvoidableDamage / InterruptMissed / DebuffStack |
| Structured Evidence | 確定性分析結果，JSON 格式 |
| Gemini Coach | 結構化證據 → 中文教練報告 |
| Next.js UI | URL 輸入 → Fight 選擇 → Timeline + AI 報告 |
| Fixtures | Sample data for 開發/測試用 |

### ❌ 不做（留給 v0.2+）

| 功能 | 版本 |
|------|------|
| DPS downtime 計算 | v0.2 |
| Healing CD efficiency | v0.3 |
| 全 Boss 泛用 mechanic detection | v0.3 |
| PostgreSQL cache | v0.4 |
| User account / auth | v0.5 |
| Streaming response | v0.2 |
| 歷史紀錄 | v0.4 |

---

## Proposed Changes

### Project Structure

```
WoW-Combat-Log-TEST-AI-Analyzer/
├── apps/
│   ├── api/                         # FastAPI backend
│   │   ├── pyproject.toml
│   │   ├── app/
│   │   │   ├── main.py              # FastAPI entry + CORS
│   │   │   ├── config.py            # Pydantic Settings
│   │   │   ├── models/
│   │   │   │   └── schemas.py       # Pydantic models (= API contract)
│   │   │   ├── services/
│   │   │   │   ├── wcl_client.py    # WCL GraphQL + OAuth
│   │   │   │   ├── normalizer.py    # Raw event → normalized event
│   │   │   │   ├── analyzer.py      # Deterministic rule engine
│   │   │   │   ├── encounter_rules/ # Boss-specific rule definitions
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── base.py      # Rule ABC
│   │   │   │   │   └── generic.py   # Generic rules (avoidable dmg, interrupt, debuff stack)
│   │   │   │   └── ai_coach.py      # Gemini LLM coach
│   │   │   └── routers/
│   │   │       └── reports.py       # REST API endpoints
│   │   ├── tests/
│   │   │   ├── fixtures/            # Sample WCL responses
│   │   │   │   ├── sample_report.json
│   │   │   │   ├── sample_fights.json
│   │   │   │   ├── sample_events.json
│   │   │   │   └── sample_analysis.json
│   │   │   ├── test_normalizer.py
│   │   │   ├── test_analyzer.py
│   │   │   └── test_wcl_client.py
│   │   └── Dockerfile
│   │
│   └── web/                         # Next.js frontend
│       ├── package.json
│       ├── src/
│       │   ├── app/
│       │   │   ├── layout.tsx
│       │   │   ├── page.tsx          # URL input
│       │   │   └── report/
│       │   │       └── [code]/
│       │   │           ├── page.tsx  # Fight list
│       │   │           └── fight/
│       │   │               └── [fightId]/
│       │   │                   └── page.tsx  # Analysis
│       │   ├── lib/
│       │   │   └── api.ts           # Generated or manual API client
│       │   └── components/
│       │       ├── UrlInput.tsx
│       │       ├── FightCard.tsx
│       │       ├── Timeline.tsx
│       │       └── CoachReport.tsx
│       └── Dockerfile
│
├── .env.example
├── Makefile
└── README.md
```

注意：**沒有 `packages/shared/`**。Type safety 靠 contract-driven：

```
Pydantic Models → FastAPI OpenAPI → openapi.json → (未來) openapi-typescript → generated client
```

MVP 先手寫 `api.ts`，v0.2 再加自動生成。

---

### Component 1: Data Models (`apps/api/app/models/schemas.py`)

**先定義 contract，再寫實作。** 這是所有 agent / 模組的共同語言。

```python
from pydantic import BaseModel
from enum import Enum

# === WCL Data ===

class Actor(BaseModel):
    id: int
    name: str
    type: str           # "Player", "NPC", "Pet"
    sub_type: str       # "Paladin", "Warrior", etc.
    server: str | None = None

class FightSummary(BaseModel):
    id: int
    name: str           # Boss name
    start_time: int     # ms, relative to report start
    end_time: int
    kill: bool
    difficulty: int | None = None
    encounter_id: int
    fight_percentage: float | None = None  # HP % at wipe

class ReportSummary(BaseModel):
    code: str
    title: str
    owner: str
    start_time: int
    end_time: int
    fights: list[FightSummary]
    actors: list[Actor]

# === Normalized Events ===

class NormalizedEvent(BaseModel):
    timestamp: int          # ms, relative to fight start
    type: str               # death, damage, heal, debuff_apply, debuff_remove, cast, interrupt, begin_cast
    source_id: int | None = None
    source_name: str | None = None
    target_id: int | None = None
    target_name: str | None = None
    ability_id: int | None = None
    ability_name: str | None = None
    amount: int | None = None
    extra: dict | None = None  # overkill, overheal, absorbed, stacks, etc.

# === Analysis Evidence ===

class Severity(str, Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"

class EvidenceType(str, Enum):
    DEATH = "death"
    MECHANIC_FAIL = "mechanic_fail"
    MISSED_INTERRUPT = "missed_interrupt"
    DEBUFF_STACK_EXCEEDED = "debuff_stack_exceeded"

class Evidence(BaseModel):
    timestamp: int
    type: EvidenceType
    severity: Severity
    player: str
    description: str       # 確定性描述，不是 AI 猜的
    details: dict          # ability_id, damage_amount, stack_count, etc.

class DeathDetail(BaseModel):
    player: str
    timestamp: int
    killing_blow: str | None = None   # ability name
    damage_taken_last_5s: list[dict]   # [{source, ability, amount, timestamp}]

class AnalysisResult(BaseModel):
    fight: FightSummary
    deaths: list[DeathDetail]
    evidence: list[Evidence]
    total_deaths: int
    fight_duration_seconds: float

# === AI Coach ===

class PlayerAdvice(BaseModel):
    player: str
    issues: list[str]
    suggestions: list[str]

class CoachReport(BaseModel):
    wipe_summary: str                 # 1-2 句話總結
    primary_causes: list[str]         # 滅團主因（3-5 條）
    player_advice: list[PlayerAdvice] # 個別玩家建議
    priority_fixes: list[str]         # 下一場優先修正

class FullAnalysisResponse(BaseModel):
    report: ReportSummary
    fight: FightSummary
    analysis: AnalysisResult
    coach_report: CoachReport
```

---

### Component 2: WCL GraphQL Client (`apps/api/app/services/wcl_client.py`)

```python
class WCLClient:
    """Warcraft Logs API v2 GraphQL Client with OAuth2 Client Credentials."""

    TOKEN_URL = "https://www.warcraftlogs.com/oauth/token"
    API_URL = "https://www.warcraftlogs.com/api/v2/client"

    async def get_token(self) -> str
    async def get_report(self, code: str) -> ReportSummary
    async def get_fight_events(self, code: str, fight_id: int) -> list[dict]
    async def get_fight_table(self, code: str, fight_id: int, data_type: str) -> dict
```

**Event query filter expression（修正版）：**
```
type in (
  "begincast",
  "cast",
  "interrupt",
  "death",
  "damage",
  "heal",
  "applydebuff",
  "refreshdebuff",
  "removedebuff",
  "applydebuffstack",
  "removedebuffstack",
  "applybuff",
  "removebuff"
)
```

**Table data types（修正版）：**
- `DamageDone` ✅
- `DamageTaken` ✅
- `Healing` ✅（不是 ~~HealingDone~~）
- `Deaths` ✅
- `Interrupts` ✅

**分頁處理：** `nextPageTimestamp` 不為 null 時繼續抓下一頁。

---

### Component 3: Event Normalizer (`apps/api/app/services/normalizer.py`)

WCL raw event 格式 → 標準化的 `NormalizedEvent`。

```python
def normalize_events(
    raw_events: list[dict],
    actors: list[Actor],
    fight_start_time: int,
) -> list[NormalizedEvent]:
    """
    - WCL 的 sourceID / targetID 對應 actors 中的 name
    - timestamp 轉成相對 fight start 的 ms
    - type mapping: applydebuff → debuff_apply, etc.
    - 額外資訊放進 extra dict
    """
```

這是一個純函數，沒有 side effect，非常適合 unit test。

---

### Component 4: Encounter Rule Engine (`apps/api/app/services/encounter_rules/`)

**這是整個專案技術含量最高的部分。**

#### base.py — Rule ABC

```python
from abc import ABC, abstractmethod

class EncounterRule(ABC):
    """Base class for encounter-specific analysis rules."""
    name: str
    description: str

    @abstractmethod
    def evaluate(self, events: list[NormalizedEvent]) -> list[Evidence]:
        """Evaluate events and return evidence of issues found."""
        ...
```

#### generic.py — 通用規則（可被 Boss 定義複用）

```python
class AvoidableDamageRule(EncounterRule):
    """偵測可迴避的傷害技能。"""
    def __init__(self, ability_id: int, ability_name: str, threshold: int = 0):
        # 玩家被這個技能打到 = mechanic fail
        ...

class InterruptRule(EncounterRule):
    """偵測可打斷但沒被打斷的施法。"""
    def __init__(self, ability_id: int, ability_name: str):
        # 有 begincast 但沒有對應的 interrupt = missed interrupt
        ...

class DebuffStackRule(EncounterRule):
    """偵測 debuff 層數超標。"""
    def __init__(self, ability_id: int, ability_name: str, max_safe_stacks: int):
        # applydebuffstack 超過 max_safe_stacks = mechanic fail
        ...
```

#### Boss 定義範例

```python
# encounter_rules/__init__.py

ENCOUNTER_RULES: dict[int, list[EncounterRule]] = {
    # 範例：encounter_id → rules
    # 實際的 encounter_id 和 ability_id 會根據選定的 boss 填入
    2902: [  # 範例 encounter_id
        AvoidableDamageRule(ability_id=123456, ability_name="Shadow Explosion"),
        InterruptRule(ability_id=234567, ability_name="Dark Ritual"),
        DebuffStackRule(ability_id=345678, ability_name="Corruption", max_safe_stacks=2),
    ],
}
```

> [!NOTE]
> MVP 先支持 3 個 generic rule types + 1-2 個 boss 的具體定義。沒有定義規則的 boss 仍然可以做 death timeline 分析，只是不會有 mechanic_fail evidence。

---

### Component 5: Deterministic Analyzer (`apps/api/app/services/analyzer.py`)

```python
class CombatAnalyzer:
    def analyze(
        self,
        fight: FightSummary,
        events: list[NormalizedEvent],
        encounter_rules: list[EncounterRule] | None = None,
    ) -> AnalysisResult:
        """
        1. 建立 death timeline（每個死亡 + 死前 5 秒傷害）
        2. 執行 encounter rules → 收集 evidence
        3. 合併 + 排序所有 evidence
        4. 回傳 AnalysisResult
        """
```

**Death Analysis 邏輯（確定性，不需要 AI）：**

```python
for event in events:
    if event.type == "death":
        # 找死前 5 秒的所有 damage event
        pre_death = [e for e in events
                     if e.type == "damage"
                     and e.target_name == event.target_name
                     and (event.timestamp - 5000) <= e.timestamp <= event.timestamp]

        death_detail = DeathDetail(
            player=event.target_name,
            timestamp=event.timestamp,
            killing_blow=event.ability_name,
            damage_taken_last_5s=[...],
        )
```

---

### Component 6: AI Coach (`apps/api/app/services/ai_coach.py`)

```python
class AICoach:
    """LLM 只負責把結構化證據轉成教練報告。"""

    SYSTEM_PROMPT = """你是一位資深 WoW 團隊教練。
你會收到一場戰鬥的「確定性分析結果」，包含死亡時間線和機制失誤證據。
這些證據已經由 Python 分析引擎確認，不需要你重新判斷。

你的任務是把這些分析結果轉成清晰、可執行的中文教練報告。

回傳格式（JSON）：
{
  "wipe_summary": "一句話總結這場為什麼滅團",
  "primary_causes": ["主因1", "主因2", ...],
  "player_advice": [
    {"player": "xxx", "issues": [...], "suggestions": [...]}
  ],
  "priority_fixes": ["下一場最優先修正的事"]
}"""

    async def generate_report(
        self,
        fight: FightSummary,
        analysis: AnalysisResult,
    ) -> CoachReport:
        """
        組裝 prompt:
        - System: coaching persona + JSON format
        - User: fight summary + death details + evidence list
        呼叫 Gemini → parse JSON → return CoachReport
        """
```

**重點：LLM 輸入的是 structured evidence，不是 raw combat log。**

```json
// LLM 收到的 user message（示意）
{
  "fight": {
    "name": "Netherspite",
    "duration_seconds": 392,
    "kill": false,
    "fight_percentage": 34.2
  },
  "deaths": [
    {
      "player": "PlayerA",
      "timestamp_seconds": 43.2,
      "killing_blow": "Shadow Explosion",
      "damage_taken_last_5s": [
        {"source": "Netherspite", "ability": "Melee", "amount": 4200},
        {"source": "Netherspite", "ability": "Shadow Explosion", "amount": 18432}
      ]
    }
  ],
  "evidence": [
    {
      "type": "mechanic_fail",
      "severity": "critical",
      "player": "PlayerA",
      "description": "被可迴避技能 Shadow Explosion 命中，受到 18432 傷害",
      "timestamp_seconds": 43.2
    },
    {
      "type": "missed_interrupt",
      "severity": "warning",
      "player": null,
      "description": "Dark Ritual 施法未被打斷（01:17）",
      "timestamp_seconds": 77.0
    }
  ]
}
```

---

### Component 7: REST API (`apps/api/app/routers/reports.py`)

**修正版 API 設計：** POST for 有成本的操作。

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/reports/{code}` | 取得 report 基本資訊 + fight 列表（低成本，可 cache） |
| `POST` | `/api/reports/{code}/fights/{fightId}/analysis` | **一次完成** WCL fetch → Analyze → AI Coach → 回傳 `FullAnalysisResponse` |

MVP 只需要兩個 endpoint。Frontend 不需要了解 backend pipeline。

```python
@router.get("/reports/{code}")
async def get_report(code: str) -> ReportSummary:
    """Fetch report summary from WCL."""
    ...

@router.post("/reports/{code}/fights/{fight_id}/analysis")
async def analyze_fight(code: str, fight_id: int) -> FullAnalysisResponse:
    """
    Complete analysis pipeline:
    1. Fetch events from WCL GraphQL
    2. Normalize events
    3. Run encounter rules
    4. Deterministic analysis
    5. AI coach report
    6. Return combined result
    """
    ...
```

---

### Component 8: Next.js Frontend (`apps/web/`)

#### Design System
- **色系**：暗色底 `#0a0a0f` + WoW 品質色
  - Epic 紫 `#a335ee` — 用於重要 highlight
  - Rare 藍 `#0070dd` — 用於互動元素
  - Uncommon 綠 `#1eff00` — 用於正面指標
  - Legendary 橘 `#ff8000` — 用於 warning
  - Death 紅 `#ff3333` — 用於 critical
- **字體**：Inter（UI）+ JetBrains Mono（數據/時間軸）
- **風格**：Glassmorphism 卡片、微動畫、暗色遊戲風

#### 頁面

**首頁 `page.tsx`**
- 大型 URL 輸入框：「Paste your Warcraft Logs URL」
- 自動解析 report code（regex: `/reports/([a-zA-Z0-9]+)/`）
- 範例 URL 提示
- Loading state

**Report 頁 `report/[code]/page.tsx`**
- Report 標題、時長、Owner
- Fight 列表：每個 encounter 一張卡片
  - Boss 名稱、時長
  - ✅ Kill / ❌ Wipe（含 HP %）
  - 點擊觸發分析

**Analysis 頁 `report/[code]/fight/[fightId]/page.tsx`**
- 左右兩欄 layout
- **左欄：Timeline**
  - 時間排序的事件卡片
  - 🔴 Critical / 🟡 Warning / 🔵 Info 色碼
  - Death 事件展開顯示死前傷害
- **右欄：AI Coach Report**
  - Loading skeleton → 顯示分析
  - Wipe 主因
  - 個別玩家建議
  - 下次優先修正

---

### Component 9: Test Fixtures

**MVP 的測試不打真實 WCL API，用 fixtures。**

```
tests/fixtures/
├── sample_report.json       # GET /reports/{code} 回傳格式
├── sample_events.json       # WCL events raw data（一場 fight）
├── sample_normalized.json   # normalize 後的事件
└── sample_analysis.json     # analyzer 輸出
```

從一個真實 WCL report 手動抓一次資料存下來，之後所有開發和測試都用這份。

---

### Component 10: Configuration

#### [NEW] .env.example
```env
# Warcraft Logs API (required)
WCL_CLIENT_ID=your_wcl_client_id
WCL_CLIENT_SECRET=your_wcl_client_secret

# Google Gemini API (required)
GEMINI_API_KEY=your_gemini_api_key

# Backend
API_HOST=0.0.0.0
API_PORT=8000

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000
```

#### [MODIFY] README.md
- 專案介紹 + 核心理念（deterministic analysis → LLM explanation）
- 架構圖
- 快速開始指南（`pip install` + `npm install` + `.env`）
- API 文件（兩個 endpoint）
- 技術棧 + 設計決策說明

---

## Implementation Order

```
Phase 1: Contract + Fixtures (30 min)
├── schemas.py（Pydantic models = API contract）
├── sample fixtures（從 WCL 手動抓或構造）
└── .env.example

Phase 2: Backend Core (parallel-ready)
├── 2A: WCL Client (45 min)
│   ├── OAuth token management
│   ├── GraphQL queries
│   └── Pagination handling
│
├── 2B: Normalizer + Analyzer (60 min)  ← 可與 2A 平行，吃 fixtures
│   ├── Event normalizer
│   ├── Rule engine (ABC + 3 generic rules)
│   ├── Death timeline analysis
│   └── Unit tests
│
└── 2C: AI Coach (30 min)  ← 可與 2A/2B 平行，吃 fixtures
    ├── Gemini prompt engineering
    ├── JSON structured output
    └── CoachReport parsing

Phase 3: API Integration (30 min)
├── FastAPI main.py + config
├── reports router (2 endpoints)
└── End-to-end test with fixtures

Phase 4: Frontend (90 min)  ← 可在 Phase 2 開始後就啟動，用 mock
├── Next.js setup
├── 3 pages (home, report, analysis)
├── Components (URL input, fight card, timeline, coach report)
└── API client integration

Phase 5: Polish (30 min)
├── README.md
├── Error handling
└── Manual end-to-end verification
```

**Phase 2A / 2B / 2C 之間是真正平行的**：
- 2A 吃 WCL API
- 2B 吃 fixtures，不需要 WCL
- 2C 吃 fixtures，不需要 Analyzer

**Phase 4 也可以和 Phase 2 平行**：Frontend 用 mock data 開發。

---

## Verification Plan

### Unit Tests
```bash
cd apps/api
python -m pytest tests/ -v

# 測試覆蓋：
# - normalizer: raw events → normalized events
# - analyzer: normalized events → evidence + death details
# - encounter rules: 各規則獨立測試
```

### Integration Test
```bash
# 用 fixtures 測試完整 pipeline（不打 WCL API）
python -m pytest tests/test_pipeline.py -v
```

### Manual E2E Verification
1. 設定 `.env` with real WCL credentials + Gemini key
2. `cd apps/api && uvicorn app.main:app --reload`
3. `cd apps/web && npm run dev`
4. 貼入真實 WCL report URL
5. 選擇一個 wipe fight
6. 確認：death timeline 正確、evidence 合理、AI coach report 可讀

### Demo Flow
```
貼入 URL → 看 Fight 列表 → 點 Wipe → 看 Timeline + AI 教練報告
```

---

## Versioning Roadmap

| Version | Features |
|---------|----------|
| **v0.1** | Death timeline + 3 generic rules + 1-2 boss + Gemini coach + Basic UI |
| v0.2 | DPS downtime analysis + Streaming response + More boss rules |
| v0.3 | Interrupt / Defensive / Healing analysis + Encounter rule packs |
| v0.4 | PostgreSQL cache + History + OpenAPI → TypeScript client generation |
| v0.5 | Multi-boss rule packs + User accounts |
| v1.0 | Full AI Raid Coach |
