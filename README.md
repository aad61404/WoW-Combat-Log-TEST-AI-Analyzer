# WoW Combat Log AI Analyzer

Warcraft Logs → Python 規則分析 → 結構化證據 → Gemini 中文教練報告。

## macOS 開發環境

使用 Python 3.13、uv、Node 24.21.0（見 `.nvmrc`）與 npm。
本機 Python 套件放在根目錄 `.venv`；Node 透過 nvm 選定版本。
換電腦時重新安裝依賴，不要複製 Windows 的 `.venv` 或 `node_modules`。

在專案根目錄執行：

```sh
make setup
make dev
```

`make setup` 安裝鎖定的 Python／npm 依賴，建立缺少的環境檔，不會覆蓋既有設定。
若尚未安裝指定的 Node，先執行 `nvm install`。
`make dev` 同時啟動兩個服務，按 Ctrl+C 停止；也可以分別在兩個終端機執行 `make api`、`make web`。

- 前端：http://localhost:3000
- API 文件：http://localhost:8000/docs
- 健康檢查：http://localhost:8000/api/health

首頁提供戰報輸入 → 戰鬥選擇 → 分析結果。點選「開啟範例戰報」即可免金鑰體驗。
範例僅包含第 1 場的事件資料，由後端分析引擎處理；不會呼叫 WCL 或 Gemini。
結果可篩選事件、展開死前 5 秒傷害，並查看紀錄摘要。
真實戰報目前僅啟用死亡紀錄分析；現有 Boss 規則尚未驗證，僅用於範例模式。

## API 憑證

在根目錄 `.env` 填入 `WCL_CLIENT_ID`、`WCL_CLIENT_SECRET` 和 `GEMINI_API_KEY`，然後重新啟動後端。
無金鑰時仍可執行單元測試、開啟前端與 API 文件；讀取真實 WCL 戰報需要 WCL 憑證；Gemini 未設定或呼叫失敗時會提供標示來源的紀錄摘要。
Gemini 模型可用 `GEMINI_MODEL` 指定（預設 `gemini-2.5-flash`）。
請勿把金鑰提交到 Git。

後端固定從專案根目錄讀取 `.env`，若有 `apps/api/.env` 則覆蓋同名設定；系統環境變數優先。
前端使用 `apps/web/.env.local` 的 `NEXT_PUBLIC_API_URL`。此變數是公開設定，不能放秘密金鑰。
目前 `make dev` 固定使用本機 3000／8000 port。

## 驗證

```sh
make test   # fixtures 單元測試，不呼叫付費 API
make check  # 後端測試、前端 ESLint 與正式建置
```

Python 依賴鎖定在 `apps/api/requirements-dev.lock`，npm 使用 `apps/web/package-lock.json`。
修改 Python 依賴後可用以下指令更新 lock，再執行 `make setup`：

```sh
uv pip compile apps/api/pyproject.toml --extra dev --python-version 3.13 -o apps/api/requirements-dev.lock
```

架構與後續功能規劃見 [implementation_plan.md](docs/implementation_plan.md)。

## 瀏覽器回歸測試與 CI

首次安裝測試瀏覽器後，從根目錄執行：

```sh
bash scripts/npm.sh exec -- playwright install chromium
make e2e
```

測試會自行建立正式版前端並啟動獨立的前端 `3100`／後端 `8100`，
使用 `.next-e2e` 建置目錄，不會重用目前的 3000／8000 開發服務。
若測試埠號已被占用會直接失敗，請先停止占用它們的程序。
測試後服務會自動結束。WCL／Gemini 憑證在測試程序中固定為空，
不呼叫外部分析服務，也不會修改本機 `.env`。
首次安裝依賴／瀏覽器與建置字體仍需要網路。

同一組案例分別驗證 Chromium 桌面與 Pixel 7 尺寸：

- 真實本機後端的範例分析、死亡明細、事件篩選與返回操作。
- 無效網址、缺少憑證，以及錯誤後仍可切換至範例。
- 分析失敗後重新嘗試、後端狀態重新檢查。
- 首頁、結果與錯誤提示頁面的水平溢出檢查。

失敗時會產生 `apps/web/playwright-report` 與 `apps/web/test-results`，
包含截圖與 trace；這些檔案不會提交 Git。
這是 Chromium 手機尺寸模擬，尚不代表 iOS Safari 或實機驗收。

GitHub Actions 設定在 `.github/workflows/check.yml`，於 push／pull request 執行
Python 測試、前端 lint、正式版建置與瀏覽器測試。遠端首次執行仍需 push 後確認。
