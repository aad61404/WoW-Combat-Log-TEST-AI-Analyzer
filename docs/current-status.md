# 目前開發進度

> 更新日期：2026-10-10  
> 資料狀態：**目前未使用 Warcraft Logs API 真實資料；暫時使用 mock／fixture 資料。**

## 已完成

- FastAPI 後端與 Swagger 文件可正常啟動。
- `GET /api/health` 可正常回傳服務狀態。
- 報告、戰鬥與玩家的資料模型及持久化流程已有基礎實作。
- 專案已有本機 demo 路由，可使用 fixture 執行報告查詢與戰鬥分析。
- 測試會使用 fixture／mock，不會呼叫 Warcraft Logs 或付費 AI API。
- `data/public-report-candidates.json` 已整理 20 個公開來源的 report code 候選。

## 目前限制

- 尚未取得可用的 Warcraft Logs OAuth Client ID／Client Secret。
- 尚未完成 Warcraft Logs GraphQL API 的 live validation。
- `data/public-report-candidates.json` 只有公開來源與 report code，尚未透過官方 API 驗證其目前可讀性及內容。
- 現階段 demo 中的 fights、players、abilities、events、傷害與死亡資料都是開發用 fixture；不能宣稱為即時或已驗證的真實 Warcraft Logs 資料。
- PostgreSQL 延後啟動；目前不要把本機 SQLite／fixture 結果視為正式資料庫成果。

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
- 啟動 PostgreSQL 後，將同一套 fixture 寫入 `reports`、`fights`、`players` 三張表。
- Warcraft Logs 憑證取得後，再替換資料來源，不重寫既有路由與資料模型。
