"""
Warcraft Logs API v2 GraphQL Client.

Handles OAuth2 Client Credentials flow and provides typed methods
for fetching report data, fight events, and table summaries.
"""

from __future__ import annotations

import time

import httpx

from app.config import settings
from app.models.schemas import Actor, FightSummary, ReportSummary


class WCLClient:
    """Warcraft Logs API v2 GraphQL client with automatic OAuth token management."""

    TOKEN_URL = "https://www.warcraftlogs.com/oauth/token"
    API_URL = "https://www.warcraftlogs.com/api/v2/client"

    def __init__(self) -> None:
        self._token: str | None = None
        self._token_expires_at: float = 0.0
        self._http = httpx.AsyncClient(timeout=30.0)

    # -------------------------------------------------------------------------
    # OAuth2 Token Management
    # -------------------------------------------------------------------------

    async def _ensure_token(self) -> str:
        """Get a valid access token, refreshing if expired."""
        if not settings.wcl_client_id or not settings.wcl_client_secret:
            raise WCLAPIError(
                "請在根目錄 .env 設定 WCL_CLIENT_ID 和 WCL_CLIENT_SECRET，並重新啟動後端。", 503
            )
        if self._token and time.time() < self._token_expires_at - 60:
            return self._token

        resp = await self._http.post(
            self.TOKEN_URL,
            data={"grant_type": "client_credentials"},
            auth=(settings.wcl_client_id, settings.wcl_client_secret),
        )
        if resp.status_code in (400, 401, 403):
            raise WCLAPIError("WCL 憑證驗證失敗，請檢查 Client ID 與 Client Secret。", 503)
        resp.raise_for_status()
        data = resp.json()

        self._token = data["access_token"]
        self._token_expires_at = time.time() + data.get("expires_in", 3600)
        return self._token  # type: ignore[return-value]

    # -------------------------------------------------------------------------
    # GraphQL Execution
    # -------------------------------------------------------------------------

    async def _graphql(self, query: str, variables: dict | None = None) -> dict:
        """Execute a GraphQL query against the WCL API."""
        token = await self._ensure_token()
        resp = await self._http.post(
            self.API_URL,
            json={"query": query, "variables": variables or {}},
            headers={"Authorization": f"Bearer {token}"},
        )
        resp.raise_for_status()
        result = resp.json()

        if result.get("errors"):
            raise WCLAPIError(
                "WCL 無法處理此查詢，請確認戰報可公開存取；若持續失敗需檢查 API 查詢。"
            )

        return result["data"]

    # -------------------------------------------------------------------------
    # Report Queries
    # -------------------------------------------------------------------------

    REPORT_QUERY = """
    query GetReport($code: String!) {
      reportData {
        report(code: $code) {
          title
          owner { name }
          startTime
          endTime
          fights(killType: Encounters) {
            id
            name
            startTime
            endTime
            kill
            difficulty
            encounterID
            fightPercentage
          }
          masterData {
            actors(type: "Player") {
              id
              name
              type
              subType
              server
            }
          }
        }
      }
    }
    """

    @staticmethod
    def _require_report(data: dict) -> dict:
        report = (data.get("reportData") or {}).get("report")
        if report is None:
            raise WCLAPIError("找不到戰報，或此戰報未公開；請確認網址與存取權限。", 404)
        return report

    async def get_report(self, code: str) -> ReportSummary:
        """Fetch report summary including fights and player actors."""
        data = await self._graphql(self.REPORT_QUERY, {"code": code})
        report = self._require_report(data)

        fights = [
            FightSummary(
                id=f["id"],
                name=f["name"],
                start_time=f["startTime"],
                end_time=f["endTime"],
                kill=f["kill"],
                difficulty=f.get("difficulty"),
                encounter_id=f["encounterID"],
                fight_percentage=f.get("fightPercentage"),
            )
            for f in report["fights"]
        ]

        actors = [
            Actor(
                id=a["id"],
                name=a["name"],
                type=a["type"],
                sub_type=a.get("subType") or "",
                server=a.get("server"),
            )
            for a in report["masterData"]["actors"]
        ]

        return ReportSummary(
            code=code,
            title=report["title"],
            owner=(report.get("owner") or {}).get("name") or "Unknown",
            start_time=report["startTime"],
            end_time=report["endTime"],
            fights=fights,
            actors=actors,
        )

    # -------------------------------------------------------------------------
    # Fight Events Query (with pagination)
    # -------------------------------------------------------------------------

    EVENTS_QUERY = """
    query GetFightEvents($code: String!, $fightID: Int!, $startTime: Float!, $endTime: Float!) {
      reportData {
        report(code: $code) {
          events(
            fightIDs: [$fightID]
            startTime: $startTime
            endTime: $endTime
            filterExpression: "type in ('begincast','cast','interrupt','death','damage','heal','applydebuff','refreshdebuff','removedebuff','applydebuffstack','removedebuffstack','applybuff','removebuff')"
          ) {
            data
            nextPageTimestamp
          }
          masterData {
            abilities { gameID name }
            actors {
              id
              name
              type
              subType
              server
            }
          }
        }
      }
    }
    """

    async def get_fight_events(
        self, code: str, fight: FightSummary
    ) -> tuple[list[dict], list[Actor], dict[int, str]]:
        """
        Fetch all events for a specific fight, handling pagination.

        Returns:
            Tuple of (raw_events, actors, ability_names)
        """
        all_events: list[dict] = []
        next_page: float | None = None
        actors: list[Actor] = []
        ability_names: dict[int, str] = {}

        while True:
            variables: dict = {
                "code": code,
                "fightID": fight.id,
                "startTime": float(fight.start_time),
                "endTime": float(fight.end_time),
            }
            if next_page is not None:
                variables["startTime"] = next_page

            data = await self._graphql(self.EVENTS_QUERY, variables)
            report = self._require_report(data)
            events_data = report["events"]
            ability_names.update(
                {a["gameID"]: a["name"] for a in report["masterData"].get("abilities", [])}
            )

            all_events.extend(events_data["data"])

            # Parse actors on first page
            if not actors:
                actors = [
                    Actor(
                        id=a["id"],
                        name=a["name"],
                        type=a["type"],
                        sub_type=a.get("subType") or "",
                        server=a.get("server"),
                    )
                    for a in report["masterData"]["actors"]
                ]

            previous_start = variables["startTime"]
            next_page = events_data.get("nextPageTimestamp")
            if next_page is not None and next_page <= previous_start:
                raise WCLAPIError("WCL pagination did not advance")
            if next_page is None:
                break

        return all_events, actors, ability_names

    # -------------------------------------------------------------------------
    # Table Query
    # -------------------------------------------------------------------------

    TABLE_QUERY = """
    query GetFightTable($code: String!, $fightID: Int!, $startTime: Float!, $endTime: Float!, $dataType: TableDataType!) {
      reportData {
        report(code: $code) {
          table(
            fightIDs: [$fightID]
            startTime: $startTime
            endTime: $endTime
            dataType: $dataType
          )
        }
      }
    }
    """

    async def get_fight_table(self, code: str, fight: FightSummary, data_type: str) -> dict:
        """
        Fetch table data for a fight (DamageDone, DamageTaken, Healing, Deaths, Interrupts).
        """
        data = await self._graphql(
            self.TABLE_QUERY,
            {
                "code": code,
                "fightID": fight.id,
                "startTime": float(fight.start_time),
                "endTime": float(fight.end_time),
                "dataType": data_type,
            },
        )
        return data["reportData"]["report"]["table"]

    # -------------------------------------------------------------------------
    # Cleanup
    # -------------------------------------------------------------------------

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._http.aclose()


class WCLAPIError(Exception):
    """Safe public error text with an appropriate HTTP status."""

    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.status_code = status_code
