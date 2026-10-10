# Active Roadmap — Full-stack AI Product Engineer

> 決策日期：2026-10-07  
> 狀態：**目前唯一有效的兩個月執行方向**

## 核心決策

兩個月的目標不是把 Python、Node、RAG、Agent、MCP 全部學完，而是把目前的
「Cocos 前端」經驗重新包裝成：

> **能獨立完成 Full-stack AI Product 的 Software Engineer，並開始取得面試。**

這段期間只做一個主專案：**WoW Combat Log AI Coach**。Cocos AI automation 保留為
工作上的加分案例，不占用這兩個月的主要學習與開發時間。

市場定位以 `AI Application Engineer`、`Full-stack AI Engineer`、`Applied AI Engineer`
與 `Forward Deployed Engineer (FDE)` 為主。2026 年 10 月的職缺觀察顯示，相關職缺重視：

- Full-stack / Product Engineering
- Python、FastAPI、REST API、testing
- Container、Cloud 與 production delivery
- 將需求快速轉化為 Prototype，再推進到 Production
- AI Agent、MCP、Tool Use 是加分的上層能力，不是近期底座

參考職缺：

- [Michael Page — Forward Deployed Engineer (FDE)](https://www.michaelpage.com.tw/zh/job-detail/forward-deployed-engineer-fde/ref/jn-092026-7096044?lang=en)
- [hirist.tech — Applied AI Engineer (Python)](https://www.hirist.tech/j/applied-ai-engineer-python-1676402)

## 產品敘事

最終產品只需清楚完成這條使用者價值鏈：

```text
貼上 Warcraft Logs URL
        ↓
系統解析戰鬥
        ↓
找出 cooldown / downtime / death / mechanic 問題
        ↓
AI 排出最值得優先改善的 3 件事
        ↓
每項結論附上證據與時間點
```

專案的面試價值不只在 WoW，而是證明已完整實作：

```text
External API → Backend → Data Processing → Database → Frontend
             → AI → Evaluation → Deployment
```

核心技術原則不變：

> **先由 deterministic combat analysis engine 算出事實，再由 LLM 解釋、排序與提供教練建議。**

不要把 raw combat log 直接交給 LLM 猜測。

## 八週執行順序

| 時間 | 主目標 | 可驗收產出 |
| --- | --- | --- |
| Week 1–2 | Python Backend 基礎 | FastAPI + PostgreSQL + Docker，可獨立完成 API |
| Week 3–4 | Full-stack 能力 | Next.js / TypeScript + FastAPI + DB，完成可用產品流程 |
| Week 5–6 | Applied AI | LLM structured output、Tool Calling、基本 Agent、Evals |
| Week 7 | Production 化 | Logging、error handling、retry、deployment、CI |
| Week 8 | 求職包裝與面試 | GitHub、履歷、Demo、System Design 說法、面試題 |

原則：每一層完成並可驗收後，才往下一層疊加。AI 必須晚於資料取得、持久化與
deterministic analysis。

## 下一個七天：只做五件事

### 1. Python 補到能寫 Backend

- Syntax、typing、async
- Pydantic
- pytest
- 不刷演算法，不上完整 Python 課

### 2. 建立乾淨的 FastAPI backend

- `GET /health`
- `POST /reports`
- `GET /reports/{id}`
- Swagger 可正常操作

### 3. 接上 PostgreSQL

- 只建立 `reports`、`fights`、`players` 三張核心表
- 能 create、query、update
- 暫不導入 Redis、Queue、Vector DB

### 4. 打通 Warcraft Logs API

- 接收 report URL 或 code
- 取得至少一場 fight、玩家與基本 combat data
- 將資料存入 PostgreSQL

### 5. 立即做市場測試

- 收集 10 個真實的 `AI Application / Full-stack AI / Applied AI / FDE` JD
- 投遞 3–5 個目前約有 60–70% match 的職缺
- 記錄面試或職缺中答不好的題目，回饋到後續學習清單

## 下一個七天的唯一成功標準

```text
Warcraft Logs URL
        ↓
FastAPI
        ↓
WCL API
        ↓
解析 fight
        ↓
PostgreSQL
        ↓
GET API 能查回來
```

成功不是「學完 FastAPI」，而是上述端到端流程可以實際執行與展示。

## 明確延後的項目

在完成上述成功標準前，不投入時間於：

- RAG
- LangGraph
- MCP
- Multi-Agent
- Redis
- Kubernetes
- 微服務
- Fine-tuning
- Claude 與 GPT 的自動協作
- 第二個主專案

這些項目不是永久取消，而是必須服從目前的產品交付順序。第二週再開始把真正的
combat analysis engine 接到已持久化的資料流程；Applied AI 排在基礎產品流程之後。

## 執行時的取捨規則

遇到新工具、新框架或新點子時，依序判斷：

1. 它是否直接幫助目前週次的可驗收產出？
2. 它是否讓核心端到端流程更可靠或更容易展示？
3. 若本週不做，是否真的會阻塞下一個里程碑？

三題都不是，就記入 backlog，不切換主線。

## 一句話版本

> 接下來兩個月：**Python Backend → 做完一個 WoW Full-stack 產品 → 加 AI → Production 化 → 一邊開始面試。**

