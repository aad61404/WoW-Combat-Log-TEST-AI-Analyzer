"""Repository for imported WCL report metadata."""

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.database import ActorRecord, DemoSnapshotRecord, FightRecord, ReportRecord
from app.models.schemas import Actor, DemoSnapshot, FightSummary, ReportSummary, StoredDemoSnapshot


class ReportRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, code: str) -> ReportSummary | None:
        query = (
            select(ReportRecord)
            .where(ReportRecord.code == code)
            .options(selectinload(ReportRecord.fights), selectinload(ReportRecord.actors))
            .execution_options(populate_existing=True)
        )
        record = (await self.session.execute(query)).scalar_one_or_none()
        return self._to_schema(record) if record else None

    async def upsert(self, report: ReportSummary) -> ReportSummary:
        try:
            await self._write_report(report)
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise
        return report

    async def save_demo(self, snapshot: DemoSnapshot) -> None:
        # Revalidate even model_copy/model_construct callers before any writes.
        snapshot = DemoSnapshot.model_validate(snapshot.model_dump(mode="json"))
        try:
            record = await self._write_report(snapshot.analysis.report)
            self.session.add(
                DemoSnapshotRecord(report_id=record.id, payload=snapshot.model_dump(mode="json"))
            )
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise

    async def get_demo(self) -> StoredDemoSnapshot | None:
        query = (
            select(DemoSnapshotRecord.payload)
            .join(ReportRecord, DemoSnapshotRecord.report_id == ReportRecord.id)
            .where(ReportRecord.code == "demo")
        )
        payload = (await self.session.execute(query)).scalar_one_or_none()
        if payload is None:
            return None
        return StoredDemoSnapshot.model_validate(
            {**payload, "database_engine": self.session.get_bind().dialect.name}
        )

    async def _write_report(self, report: ReportSummary) -> ReportRecord:
        record = (
            await self.session.execute(
                select(ReportRecord).where(ReportRecord.code == report.code).with_for_update()
            )
        ).scalar_one_or_none()
        if record is None:
            record = ReportRecord(
                code=report.code,
                title=report.title,
                owner=report.owner,
                start_time=report.start_time,
                end_time=report.end_time,
            )
            self.session.add(record)
            await self.session.flush()
        else:
            # Refreshes invalidate the old detailed snapshot in the same transaction.
            await self.session.execute(
                delete(DemoSnapshotRecord).where(DemoSnapshotRecord.report_id == record.id)
            )
            await self.session.execute(
                delete(FightRecord).where(FightRecord.report_id == record.id)
            )
            await self.session.execute(
                delete(ActorRecord).where(ActorRecord.report_id == record.id)
            )

        record.title = report.title
        record.owner = report.owner
        record.start_time = report.start_time
        record.end_time = report.end_time
        self.session.add_all(
            [
                FightRecord(
                    report_id=record.id,
                    wcl_fight_id=f.id,
                    name=f.name,
                    start_time=f.start_time,
                    end_time=f.end_time,
                    kill=f.kill,
                    difficulty=f.difficulty,
                    encounter_id=f.encounter_id,
                    fight_percentage=f.fight_percentage,
                    boss_percentage=f.boss_percentage,
                )
                for f in report.fights
            ]
        )
        self.session.add_all(
            [
                ActorRecord(
                    report_id=record.id,
                    wcl_actor_id=a.id,
                    name=a.name,
                    type=a.type,
                    sub_type=a.sub_type,
                    server=a.server,
                )
                for a in report.actors
            ]
        )
        return record

    @staticmethod
    def _to_schema(record: ReportRecord) -> ReportSummary:
        return ReportSummary(
            code=record.code,
            title=record.title,
            owner=record.owner,
            start_time=record.start_time,
            end_time=record.end_time,
            fights=[
                FightSummary(
                    id=f.wcl_fight_id,
                    name=f.name,
                    start_time=f.start_time,
                    end_time=f.end_time,
                    kill=f.kill,
                    difficulty=f.difficulty,
                    encounter_id=f.encounter_id,
                    fight_percentage=f.fight_percentage,
                    boss_percentage=f.boss_percentage,
                )
                for f in record.fights
            ],
            actors=[
                Actor(
                    id=a.wcl_actor_id,
                    name=a.name,
                    type=a.type,
                    sub_type=a.sub_type,
                    server=a.server,
                )
                for a in record.actors
            ],
        )
