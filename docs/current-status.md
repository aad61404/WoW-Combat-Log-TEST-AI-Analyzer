# 目前開發進度

> 更新日期：2026-10-22
> 資料狀態：**目前未使用 Warcraft Logs API 真實資料；暫時使用 mock／fixture 資料。**

## 已完成

- FastAPI 後端與 Swagger 文件可正常啟動。
- `GET /api/health` 可正常回傳服務狀態。
- 報告、戰鬥與玩家的資料模型及持久化流程已有基礎實作。
- 專案已有本機 demo 路由，可使用 fixture 執行報告查詢與戰鬥分析。
- 詳細 demo combat data 已包含 20 名玩家、職業／專精／定位、DPS/HPS、死亡、斷法、活躍時間與主要技能統計。
- `POST /api/demo/import` 可將範例名單、戰鬥、20 名玩家統計、40 筆主要技能及分析結果一起寫入資料庫；重複操作更新同一份範例。
- `GET /api/demo/stored` 只從資料庫讀回快照，不會重新讀取 JSON fixture、呼叫 WCL 或 Gemini。
- 前端提供「儲存範例到 DB／從 DB 讀取範例」，並顯示實際資料庫類型、儲存時間與 fixture 標示。
- Pydantic 檢查玩家數、重複 ID、數值範圍、戰鬥時長、名單及死亡事件一致性；寫入失敗會回復整個交易。
- Docker PostgreSQL 17 已可啟動，並已驗證 SQLAlchemy 可寫入及查回 1 份 fixture report、1 場 fight 與 20 名玩家。
- 測試會使用 fixture／mock，不會呼叫 Warcraft Logs 或付費 AI API。
- `data/public-report-candidates.json` 已整理 20 個公開來源的 report code 候選。

## 目前限制

- 尚未取得可用的 Warcraft Logs OAuth Client ID／Client Secret。
- 尚未完成 Warcraft Logs GraphQL API 的 live validation。
- `data/public-report-candidates.json` 只有公開來源與 report code，尚未透過官方 API 驗證其目前可讀性及內容。
- 現階段 demo 中的 fights、players、abilities、events、傷害與死亡資料都是開發用 fixture；不能宣稱為即時或已驗證的真實 Warcraft Logs 資料。
- PostgreSQL 連線與基礎持久化已驗證；目前存入的仍是 fixture，不能視為真實 Warcraft Logs 資料。
- 現有範例是 Retail Nerub-ar Palace，不代表使用者的美服 TBC Anniversary；傷害、治療與技能總量是手工模擬，並非從完整事件流計算。死亡次數已與示範事件中的 4 次死亡對齊。
- `demo_snapshots` 以版本化 JSON 保存巢狀技能及分析資料，尚未建立可跨戰報查詢的玩家技能統計表。JSON 存進 PostgreSQL 不會因此變成真實資料。
- 現階段使用 `create_all` 建立缺少的資料表，沒有正式 schema migration；此次只新增資料表，不修改既有欄位。既有戰報的 site 尚未持久化，跨版本匯入仍須修正。

## 現階段開發方式

在取得憑證以前，使用 mock／fixture 完成下列流程：

```text
Report URL / code
        ↓
FastAPI 路由與資料驗證
        ↓
fixture fights / players / combat events
        ↓
create / query / update
        ↓
deterministic analysis
```

mock 資料必須在 API 回應、畫面或文件中標示為 `demo`、`mock` 或 `fixture`，避免和真實資料混淆。

## 切換真實資料的條件

1. 取得合法的 Warcraft Logs Client ID／Client Secret，且不提交到 Git。
2. 使用官方 OAuth Client Credentials Flow 取得 access token。
3. 透過 GraphQL API 驗證至少一份公開 report，取得 fight、players 與基本 combat data。
4. 將回傳資料正規化並存入 PostgreSQL。
5. 驗證 `POST /reports`、`GET /reports/{id}` 與 Swagger 操作結果。
6. 完成後才能把資料狀態由 mock／fixture 改成「真實 API 已驗證」。

## 下一步

- 先用 fixture 繼續完成 FastAPI、Pydantic、pytest 與資料庫 CRUD。
- 可使用 `GET /api/demo/fights/1/combat-data` 取得明確標示為 fixture 的詳細玩家資料。
- 保留 `actors`（含玩家、NPC 與寵物），避免直接更名為 `players` 造成語意遺失。未來按查詢需求另建玩家／技能統計表；目前先以快照完成可驗收流程。
- 下一個資料庫工作：建立 migration 流程，保存 `site` 並以 `(site, code)` 識別戰報，避免不同遊戲版本的資料混用。
- Warcraft Logs 憑證取得後，再替換資料來源，不重寫既有路由與資料模型。

## 本次 PostgreSQL 驗收

- 只啟動 PostgreSQL，未啟動 Redis 或 Queue。
- 連續匯入兩次，再透過獨立 GET 讀回：`database_engine=postgresql`、`data_origin=fixture`。
- SQL 查核 `code=demo`：1 場戰鬥、20 名玩家（另有 1 名 NPC）、1 份快照；包含 40 筆主要技能與 4 次死亡。
- 自動測試不使用開發 PostgreSQL；後端使用暫存 SQLite，瀏覽器測試使用獨立 SQLite 檔案。
- 本次驗證：106 項後端測試、12 項瀏覽器流程測試（桌機／手機尺寸）通過；前端 lint、E2E 正式建置與修改檔案的 Ruff 檢查通過。
- 操作說明與資料表職責見 [fixture-storage.md](fixture-storage.md)。
