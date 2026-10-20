# 練習 01：HTTP 成功，是否代表分析正確？

目的：練習先預測、再核對證據。預估 30–45 分鐘，不需要 API key 或新服務。
目前狀態：教材與離線測試已備妥；使用者能力尚未驗收。

## 先看這條流程

```text
前端要求範例報告
  GET /api/demo/report
  → 讀 sample_report.json → 組成報告（只提供 fight 1）

前端選擇戰鬥並提交分析
  POST /api/demo/fights/1/analysis
  → 再讀報告與 sample_events.json（本機檔案 I/O）
  → normalize_events（轉換事件）
  → CombatAnalyzer.analyze（分析與示範規則運算）
  → _build_fallback_report（確定性摘要，沒有 Gemini 呼叫）
  → FullAnalysisResponse → 前端呈現
```

來源：[demo 路由](../../../apps/api/app/routers/demo.py)、[API 契約](../../../apps/api/app/models/schemas.py)。
這些 demo handler 使用普通 `def`；不要只因框架支援 async 就認定裡面所有工作都是非同步 I/O。
真實 WCL 路徑的外部網路與示範規則使用方式不同，demo 成功不代表真實串接成功。

| API | 輸入 | 要看的結果 | 能證明／不能證明 |
| --- | --- | --- | --- |
| GET /api/demo/report | 無 | fights 只有 id 1 | 可讀範例報告；不能證明 WCL 可用 |
| POST /api/demo/fights/1/analysis | path fight_id=1，無 body | demo=true、total_deaths=4、source=deterministic、死亡明細 | 固定 fixture 的預期結果；不能證明所有事件資料正確 |
| POST /api/demo/fights/2/analysis | path fight_id=2 | HTTP 404 | 沒有範例資料時不捏造分析 |

## A. 執行前先回答

1. 這個 demo 哪裡讀檔、哪裡做運算、哪裡呼叫外部服務？
2. 把 fight ID 從 1 改成 2，你預期 HTTP 狀態與結果如何變化？為什麼？
3. 如果拿到 HTTP 200，但 total_deaths 變成 0，你會怎麼判斷測試是否成功？

把預測寫在文末，或直接回答聊天。不要先把測試輸出複製成自己的預測。

## B. 重跑現有離線驗證

在 repo 根目錄執行：

```sh
.venv/bin/python -m pytest -c apps/api/pyproject.toml apps/api/tests/test_pipeline.py::test_demo_pipeline_without_external_services -q
```

讀 [這個測試](../../../apps/api/tests/test_pipeline.py)，找出它如何檢查：
HTTP 狀態、死亡數、摘要來源、死亡明細與不支援的 fight。
它用 mock 讓意外的 WCL／AI 呼叫失敗。TestClient 在程序內呼叫 app，不走真實 TCP，不能拿其執行時間作網路容量測量。

把「我的預測」「實際輸出」「差異原因」各寫一行。通過測試只代表所寫 assertion 成立。

## C. 反例題（不改產品程式）

假設有人把分析邏輯改成永遠回傳 4 個死亡，現有測試仍可能通過。

- 提出第二份輸入資料，讓這種錯誤實作一定被抓到。
- 說明預期結果如何由輸入推導，不能再從待測函式取得答案。
- 想出另一種造成死亡數錯誤的原因，以及怎麼和「寫死 4」區分。

完成後再與 AI 討論要如何實作最小反例。不要先增加 Redis 或 worker。

## D. 能力驗收

- L1：用自己的話說明流程與 demo 的證據邊界。
- L2：親自重跑測試，說明每個檢查保護什麼、沒保護什麼。
- L3：提出能抓到錯誤實作的獨立反例，並區分至少兩個原因。

本輪不要求全部達 L3。完成這題後，才把同樣業務檢查搬到 k6 smoke test。

## 我的紀錄（由學習者填寫）

- 預測：待填
- 我做的部分／AI 協助的部分：待填
- 實際輸出：待填
- 反例與預期結果：待填
- 被推翻的假設：待填
- 下一步：待填
