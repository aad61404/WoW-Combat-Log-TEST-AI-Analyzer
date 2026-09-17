"""
AI Coach — Gemini LLM integration for generating coaching reports.

The LLM receives ONLY structured evidence from the deterministic analyzer.
It does NOT analyze raw combat logs or guess what happened.
Its job is to explain the evidence in human-readable coaching language.
"""

from __future__ import annotations

import json
import logging

from google import genai
from google.genai import types

from app.config import settings
from app.models.schemas import (
    AnalysisResult,
    CoachReport,
    FightSummary,
    PlayerAdvice,
)

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """你是一位資深的 World of Warcraft 團隊教練。

你會收到一場戰鬥的「確定性分析結果」，包含：
- 戰鬥基本資訊（Boss 名稱、時長、是否通過）
- 死亡時間線（每位死亡玩家的死亡時間和死前 5 秒受到的傷害）
- 分析證據（機制失誤、漏打斷、Debuff 層數過高等）

這些證據已經由 Python 分析引擎確認，是事實，不需要你重新判斷。

你的任務是把這些分析結果轉成清晰、具體、可執行的中文教練報告。

要求：
1. 語氣專業但友善，像資深 RL 在做 after-action review
2. 聚焦在可改進的具體行動，不要說廢話
3. 優先排列最影響 wipe 的原因
4. 每個建議都要具體到「誰、什麼時間、做什麼」

你必須以下面的 JSON 格式回覆，不要加任何 markdown 或其他文字：

{
  "wipe_summary": "一到兩句話總結這場為什麼滅團",
  "primary_causes": ["主因1", "主因2", "主因3"],
  "player_advice": [
    {
      "player": "玩家名",
      "issues": ["問題1", "問題2"],
      "suggestions": ["建議1", "建議2"]
    }
  ],
  "priority_fixes": ["下一場最優先修正的事項"]
}"""


class AICoach:
    """Generates coaching reports from deterministic analysis evidence."""

    def __init__(self) -> None:
        self._client = genai.Client(api_key=settings.gemini_api_key)

    async def generate_report(
        self,
        fight: FightSummary,
        analysis: AnalysisResult,
    ) -> CoachReport:
        """
        Generate a coaching report from analysis evidence.

        The LLM receives structured data, not raw combat logs.
        """
        # Build the user message with fight context and evidence
        user_message = self._build_user_message(fight, analysis)

        try:
            response = self._client.models.generate_content(
                model="gemini-2.0-flash",
                contents=user_message,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    temperature=0.3,  # Low temperature for consistent analysis
                    response_mime_type="application/json",
                ),
            )

            # Parse the JSON response
            return self._parse_response(response.text)

        except Exception as e:
            logger.error(f"AI Coach generation failed: {e}")
            # Return a fallback report based on evidence
            return self._build_fallback_report(fight, analysis)

    def _build_user_message(
        self, fight: FightSummary, analysis: AnalysisResult
    ) -> str:
        """Build the structured user message for the LLM."""
        data = {
            "fight": {
                "name": fight.name,
                "duration_seconds": fight.duration_seconds,
                "duration_display": fight.duration_display,
                "kill": fight.kill,
                "fight_percentage": fight.fight_percentage,
            },
            "total_deaths": analysis.total_deaths,
            "deaths": [
                {
                    "player": d.player,
                    "timestamp_seconds": d.timestamp / 1000,
                    "timestamp_display": d.timestamp_display,
                    "killing_blow": d.killing_blow,
                    "damage_taken_last_5s": [
                        {
                            "source": dm.source,
                            "ability": dm.ability,
                            "amount": dm.amount,
                        }
                        for dm in d.damage_taken_last_5s
                    ],
                }
                for d in analysis.deaths
            ],
            "evidence": [
                {
                    "type": e.type.value,
                    "severity": e.severity.value,
                    "player": e.player,
                    "description": e.description,
                    "timestamp_seconds": e.timestamp / 1000,
                    "timestamp_display": e.timestamp_display,
                }
                for e in analysis.evidence
                if e.type != "death"  # Deaths are already in the deaths section
            ],
        }
        return json.dumps(data, ensure_ascii=False, indent=2)

    def _parse_response(self, text: str | None) -> CoachReport:
        """Parse LLM JSON response into CoachReport."""
        if not text:
            raise ValueError("Empty LLM response")

        # Clean potential markdown wrapping
        clean = text.strip()
        if clean.startswith("```"):
            lines = clean.split("\n")
            clean = "\n".join(lines[1:-1])

        data = json.loads(clean)
        return CoachReport(
            wipe_summary=data.get("wipe_summary", "分析未完成"),
            primary_causes=data.get("primary_causes", []),
            player_advice=[
                PlayerAdvice(
                    player=pa["player"],
                    issues=pa.get("issues", []),
                    suggestions=pa.get("suggestions", []),
                )
                for pa in data.get("player_advice", [])
            ],
            priority_fixes=data.get("priority_fixes", []),
        )

    def _build_fallback_report(
        self, fight: FightSummary, analysis: AnalysisResult
    ) -> CoachReport:
        """Build a basic report from evidence when LLM fails."""
        causes = []
        player_issues: dict[str, list[str]] = {}

        for e in analysis.evidence:
            if e.severity.value == "critical":
                causes.append(e.description)
            if e.player:
                player_issues.setdefault(e.player, []).append(e.description)

        return CoachReport(
            wipe_summary=(
                f"{fight.name} 在 {fight.duration_display} 滅團，"
                f"共 {analysis.total_deaths} 人死亡。"
                f"（AI 分析暫時不可用，以下為自動摘要）"
            ),
            primary_causes=causes[:5] if causes else ["需要更多資料分析"],
            player_advice=[
                PlayerAdvice(
                    player=player,
                    issues=issues,
                    suggestions=["請參考上述問題改進"],
                )
                for player, issues in player_issues.items()
            ],
            priority_fixes=[causes[0]] if causes else ["檢查 AI 服務狀態"],
        )
