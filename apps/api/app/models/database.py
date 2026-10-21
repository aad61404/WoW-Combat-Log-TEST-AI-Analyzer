"""SQLAlchemy persistence models for imported WCL report metadata."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class ReportRecord(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(500))
    owner: Mapped[str] = mapped_column(String(255))
    start_time: Mapped[int] = mapped_column(BigInteger)
    end_time: Mapped[int] = mapped_column(BigInteger)
    imported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    fights: Mapped[list[FightRecord]] = relationship(
        back_populates="report", cascade="all, delete-orphan", order_by="FightRecord.wcl_fight_id"
    )
    actors: Mapped[list[ActorRecord]] = relationship(
        back_populates="report", cascade="all, delete-orphan", order_by="ActorRecord.wcl_actor_id"
    )


class FightRecord(Base):
    __tablename__ = "fights"
    __table_args__ = (UniqueConstraint("report_id", "wcl_fight_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    report_id: Mapped[int] = mapped_column(ForeignKey("reports.id", ondelete="CASCADE"))
    wcl_fight_id: Mapped[int] = mapped_column(Integer)
    name: Mapped[str] = mapped_column(String(255))
    start_time: Mapped[int] = mapped_column(BigInteger)
    end_time: Mapped[int] = mapped_column(BigInteger)
    kill: Mapped[bool] = mapped_column(Boolean)
    difficulty: Mapped[int | None] = mapped_column(Integer, nullable=True)
    encounter_id: Mapped[int] = mapped_column(Integer, index=True)
    fight_percentage: Mapped[float | None] = mapped_column(Float, nullable=True)
    boss_percentage: Mapped[float | None] = mapped_column(Float, nullable=True)
    report: Mapped[ReportRecord] = relationship(back_populates="fights")


class ActorRecord(Base):
    __tablename__ = "actors"
    __table_args__ = (UniqueConstraint("report_id", "wcl_actor_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    report_id: Mapped[int] = mapped_column(ForeignKey("reports.id", ondelete="CASCADE"))
    wcl_actor_id: Mapped[int] = mapped_column(Integer)
    name: Mapped[str] = mapped_column(String(255))
    type: Mapped[str] = mapped_column(String(50))
    sub_type: Mapped[str] = mapped_column(String(100), default="")
    server: Mapped[str | None] = mapped_column(String(255), nullable=True)
    report: Mapped[ReportRecord] = relationship(back_populates="actors")


class DemoSnapshotRecord(Base):
    """Versioned fixture snapshot; never a source of live WCL data.

    JSON preserves nested ability/evidence details while the core report tables
    remain queryable. This additive table does not alter existing report rows.
    """

    __tablename__ = "demo_snapshots"

    report_id: Mapped[int] = mapped_column(
        ForeignKey("reports.id", ondelete="CASCADE"), primary_key=True
    )
    payload: Mapped[dict] = mapped_column(JSON)
