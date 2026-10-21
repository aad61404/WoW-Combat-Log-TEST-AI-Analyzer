# 範例資料儲存：先完成一條可靠的流程

目前所有 combat data 都是 **合成 fixture**，不是已取得的 Warcraft Logs 真實資料。
範例版本為 Retail Nerub-ar Palace，不是美服 TBC Anniversary。

## 畫面怎麼操作

1. 開啟前端首頁，按「儲存範例到 DB」。後端將固定範例寫入目前設定的資料庫。
2. 前端接著送出獨立的 GET，顯示資料庫中讀回的分析結果與 20 名玩家。
3. 重新整理頁面，按「從 DB 讀取範例」。不必再次寫入，也不會呼叫 WCL／Gemini。
4. 上方會顯示 PostgreSQL 或 SQLite 與儲存時間；`MOCK DATA` 標示會一直保留。

重複儲存會更新 `code=demo` 的單一範例，不會新增 20 個重複玩家；
這個保留代碼不是合法的 16 碼 WCL 代碼，因此不會覆寫真實 WCL 戰報。
它是共享的本機開發範例，不是每位使用者獨立的私人儲存空間。

「開啟範例戰報」仍可直接從 JSON 執行分析，與 DB 快照讀取是兩條明確分開的路徑。
DB 寫入失敗時，畫面保留原本已載入的分析，不會假裝儲存成功。

## API 合約

| 操作 | 路徑 | 行為 |
| --- | --- | --- |
| POST | `/api/demo/import` | 驗證後原子性建立／更新範例；成功為 200 |
| GET | `/api/demo/stored` | 只讀 DB，不讀 fixture、不重新分析 |
| GET | `/api/demo/report` | 原有的 JSON 範例戰報 |
| GET | `/api/demo/fights/1/combat-data` | 原有的 JSON 玩家統計 |

儲存與讀取回傳：`schema_version`、`data_origin=fixture`、`storage=database`、
`database_engine`、`saved_at`、`analysis`、`combat_data`。
`saved_at` 為帶時區的 UTC 時間，前端轉為本機時間顯示。

沒有快照回傳 404；資料庫操作失敗回傳不含連線密碼的 503。POST 不接受任意玩家資料，
只匯入專案內建的固定範例。API 現階段沒有使用者認證，應只在本機使用。

## 四張表各自做什麼

| 資料表 | 職責 |
| --- | --- |
| `reports` | 戰報基本資料 |
| `fights` | 戰鬥時間、Boss、難度、擊殺結果 |
| `actors` | 參與者名單；包含 20 名玩家和 1 名 NPC，不只是玩家 |
| `demo_snapshots` | 以 report_id 關聯的版本化 JSON；保存玩家統計、技能、證據與摘要 |

`demo_snapshots.report_id` 同時為主鍵與外鍵，一份戰報最多有一份範例快照。
JSON 保留巢狀資料，現在不需要先拆出技能、事件、裝備等更多表。
未來需要跨戰報搜尋「某玩家某技能的平均表現」時，再建立適合該查詢的正規化統計表。

核心名單與快照在同一個資料庫交易中更新，任何寫入失敗都 rollback。
只更新基本戰報資料時，舊快照會一起失效，避免顯示不相符的統計。

## 對照程式學習

- `app/models/schemas.py`：Pydantic 檢查資料格式和跨檔案一致性。死亡統計必須對上分析事件，不能默默容忍兩種答案。
- `app/models/database.py`：SQLAlchemy 定義資料表、主鍵與外鍵。
- `app/repositories/reports.py`：集中讀寫與 transaction；路由不用自己組 SQL。
- `app/routers/demo.py`：處理 HTTP 路徑、呼叫流程與安全的錯誤訊息。
- `tests/test_demo_storage.py`：驗證真的存進 DB、更新不重複、失敗能回復、讀取不依賴原始 JSON。

上述 Python 路徑均相對於 `apps/api/`。

## Windows：只啟動 PostgreSQL

專案根目錄：

```powershell
docker compose up -d postgres
$env:DATABASE_URL = 'postgresql+asyncpg://wow:wow@127.0.0.1:5432/wow_analyzer'
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir apps/api --host 127.0.0.1 --port 8000
```

另一個終端機：

```powershell
cd apps/web
npm run dev
```

這裡的 wow/wow 是 compose 的本機開發帳密，不適合正式部署。
上面的環境設定只影響當前終端機；換視窗或重啟時需重新設定。
若未設定 DATABASE_URL，預設是 SQLite，畫面也會如實顯示 SQLite。
若已有設定失效的 PostgreSQL URL，啟動仍會失敗，不會默默退回 SQLite。

這次只新增 `demo_snapshots`，啟動時 `create_all` 會建立缺少的表。
`create_all` **不會修改既有表欄位**；下一階段調整 site/code 結構前需導入 migration。

驗證：

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8000/api/demo/import
Invoke-RestMethod http://127.0.0.1:8000/api/demo/stored
.\.venv\Scripts\python.exe -m pytest apps/api/tests -q
```

瀏覽器測試在 `apps/web` 執行 `npm run test:e2e`，使用獨立 3100／8100 埠號、
獨立 SQLite 與空白外部憑證，不修改開發用 PostgreSQL。
