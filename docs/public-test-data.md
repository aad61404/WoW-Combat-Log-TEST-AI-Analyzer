# 公開真實戰報資料集

候選清單位於 `data/public-report-candidates.json`。來源均為玩家或公會在公開論壇、
社群中自行分享的 Warcraft Logs report code；清單只保存 code、分類、日期、來源與用途，
不保存角色、公會、伺服器或原始事件。

## 驗證候選資料

先在根目錄 `.env` 設定 WCL Client Credentials，完成 `make setup` 後執行：

```sh
.venv/bin/python scripts/validate_public_reports.py
```

Windows PowerShell 使用：

```powershell
.venv\Scripts\python.exe scripts\validate_public_reports.py
```

輸出僅包含 fight 數、kill／wipe 數和 encounter ID。候選報告可能改為 private、被刪除或封存；
因此 API 驗證成功以前不可當作穩定 fixture。

## 建立回歸 fixture 的準則

1. 優先選同一 encounter 的 progression wipe、一般 kill、高排名 kill 各一份。
2. 在 WCL 頁面人工核對 fight ID、難度、結果、死亡數與 Boss 剩餘血量。
3. 只擷取能重現欄位轉換或分析規則的最小事件集合。
4. 將角色、公會、伺服器名稱替換成固定假名；保留 actor ID 的相對關係。
5. fixture 內記錄取得日期、encounter ID、difficulty 和原始 report code；不要保存 OAuth token。
6. Boss 規則必須分版本與難度核對。單一 report 不足以證明某技能必然可迴避或可打斷。

`ranked_reference` 適合作為成功執行的對照；`raid_review`、`guild_raid`、
`player_review` 適合尋找 wipe；`raid_edge_case` 用來驗證系統遇到異常戰鬥時不應過度推論。
`mythic_plus` 目前不在本專案 raid MVP 範圍內，保留用來測試清楚拒絕或未支援提示。
