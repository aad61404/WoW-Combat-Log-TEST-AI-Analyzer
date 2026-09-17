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
        if self._token and time.time() < self._token_expires_at - 60:
            return self._token

        resp = await self._http.post(
            self.TOKEN_URL,
            data={"grant_type": "client_credentials"},
            auth=(settings.wcl_client_id, settings.wcl_client_secret),
        )
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

        if "errors" in result:
            error_messages = "; ".join(e.get("message", str(e)) for e in result["errors"])
            raise WCLAPIError(f"GraphQL errors: {error_messages}")

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

    async def get_report(self, code: str) -> ReportSummary:
        """Fetch report summary including fights and player actors."""
        data = await self._graphql(self.REPORT_QUERY, {"code": code})
        report = data["reportData"]["report"]

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
                sub_type=a.get("subType", ""),
                server=a.get("server"),
            )
            for a in report["masterData"]["actors"]
        ]

        return ReportSummary(
            code=code,
            title=report["title"],
            owner=report["owner"]["name"],
            start_time=report["startTime"],
            end_time=report["endTime"],
            fights=fights,
            actors=actors,
        )

    # -------------------------------------------------------------------------
    # Fight Events Query (with pagination)
    # -------------------------------------------------------------------------

    EVENTS_QUERY = """
    query GetFightEvents($code: String!, $fightID: Int!, $startTime: Float!, $endTime: Float!, $nextPage: Float) {
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
    ) -> tuple[list[dict], list[Actor]]:
        """
        Fetch all events for a specific fight, handling pagination.

        Returns:
            Tuple of (raw_events, actors)
        """
        all_events: list[dict] = []
        next_page: float | None = None
        actors: list[Actor] = []

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
            report = data["reportData"]["report"]
            events_data = report["events"]

            all_events.extend(events_data["data"])

            # Parse actors on first page
            if not actors:
                actors = [
                    Actor(
                        id=a["id"],
                        name=a["name"],
                        type=a["type"],
                        sub_type=a.get("subType", ""),
                        server=a.get("server"),
                    )
                    for a in report["masterData"]["actors"]
                ]

            next_page = events_data.get("nextPageTimestamp")
            if next_page is None:
                break

        return all_events, actors

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

    async def get_fight_table(
        self, code: str, fight: FightSummary, data_type: str
    ) -> dict:
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
    """Raised when the WCL API returns an error."""
