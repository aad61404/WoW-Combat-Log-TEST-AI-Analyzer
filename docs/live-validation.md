# 真實服務驗收清單

目前狀態：本機範例、79 個後端測試與 8 個 Chromium 桌面／手機尺寸測試通過。
WCL／Gemini 憑證仍未設定，不能將離線 HTTP 模擬測試視為真實串接成功。

## 已核對的資料語意

依 [官方 ReportFight 欄位說明](https://tw.warcraftlogs.com/v2-api-docs/warcraft/reportfight.doc.html)，
`bossPercentage` 表示戰鬥結束時活躍 Boss 的血量，`fightPercentage` 表示整場戰鬥進度，
兩者在多 Boss、治療或其他特殊機制下不一定相同。
前端的「Boss 剩餘」只使用 `boss_percentage`，缺值顯示未提供，不能用戰鬥進度代替。
範例數值是測試資料，尚未以真實回傳核對。

## WCL

1. 在根目錄 `.env` 設定 WCL_CLIENT_ID／WCL_CLIENT_SECRET，重啟後端。
2. 檢查首頁設定狀態；已設定只代表讀到值，不代表認證成功。
3. 輸入公開戰報，確認標題、場次、時長與 Boss 血量對得上 WCL 頁面。
4. 選擇一場 wipe，核對死亡次數、玩家身分、時間與死前 5 秒傷害。
5. 使用事件需跨頁的戰鬥，核對資料完整性，再測擊殺成功的戰鬥。
6. 真實查詢若與 schema／事件格式不同，修正並保存去識別化的最小 fixture 作為回歸測試。
7. Boss 機制規則須另行以指定版本／難度驗證，通過前維持停用。

## 經典版測試戰報

經典版（classic／vanilla／fresh／sod）的公開戰報清單放在 `local-data/classic-test-reports.csv`。
`local-data/` 已列入 `.gitignore`：戰報公開但會顯示玩家名稱，只留本機。遺失時從根目錄重建（約 2 分鐘）：

```sh
python3 scripts/find_classic_reports.py
```

- 來源：GitHub issue／PR 內文中的 `<site>.warcraftlogs.com/reports/<16 碼>` 連結，
  多為伺服器模擬器（AzerothCore、VMaNGOS、ChromieCraft）、Boss 插件（BigWigs、DBM）與經典版 bug 回報。
  warcraftlogs.com、wowhead、icy-veins 對程式抓取回 403，無法直接爬。
- 未登入時 GitHub 搜尋每分鐘 10 次；設定 `GITHUB_TOKEN` 可放寬。每個查詢最多 1000 筆。
- GitHub 偶爾回傳不完整的分頁（`incomplete_results`），腳本會重試；翻頁以 `total_count` 判斷。
- 表中的團本分類只是從 issue 標題推測，已知會誤判。真實 zone／encounterID 以 WCL API 回傳為準。
- classic.warcraftlogs.com 依序承載過 60 級、TBC、WotLK、Cata 與 MoP Classic；
  標題寫 MC／BWL 的戰報可能是後期版本的角色重打舊團本。fresh 也包含 TBC 內容。
- 戰報來自 bug 回報，指定的場次常是為了某個技能，不一定有死亡或滅團。

## Gemini

1. 設定 GEMINI_API_KEY；必要時以 GEMINI_MODEL 指定帳號可用的模型，重啟後端。
2. 對已核對的真實分析產生報告，確認 source=ai、玩家與事件有依據。
3. 不把事件先後推成已確認因果；只有死亡資料時應說明限制。
4. 無金鑰或呼叫失敗時，確認仍能得到 source=deterministic 的摘要。
5. 記錄實際延遲與用量，再決定是否需要串流或快取。

## 邊界

- HTTP 層測試使用 httpx.MockTransport，不呼叫付費服務。
- 已驗證 token 重用／到期更新、事件分頁合併、技能名稱及欄位轉換、GraphQL 錯誤拒絕。
- 此文件不記錄憑證、token 或未去識別化的個人戰報。
