import uuid
import enum
from datetime import datetime, date
from typing import Optional

import sqlalchemy as sa

from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass

class PipelineType(enum.Enum):
    MICROLOANS = "microloans"
    REVIEWS = "reviews"

class PipelineStatus(enum.Enum):
    RUNNING = "running"
    OK = "ok"
    ERROR = "error"


class PipelineSnapshot(Base):
    __tablename__ = "pipeline_snapshot"

    run_id: Mapped[uuid.uuid4] = mapped_column(postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pipeline: Mapped[str] = mapped_column(sa.Enum(PipelineType, name='pipeline_type'), nullable=False)
    started_at: Mapped[datetime] = mapped_column(sa.DateTime, server_default=sa.func.now(), nullable=False)
    finished_at: Mapped[Optional[datetime]] = mapped_column(sa.DateTime)
    status: Mapped[Optional[str]] = mapped_column(sa.Enum(PipelineStatus, name="pipeline_status"), nullable=False)
    rows_count: Mapped[Optional[int]] = mapped_column(sa.Integer)

class MicroloanSnapshot(Base):
    __tablename__ = "microloan_snapshot"

    id: Mapped[int] = mapped_column(postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.uuid4] = mapped_column(postgresql.UUID(as_uuid=True), nullable=False)

    card_index: Mapped[Optional[int]] = mapped_column(sa.Integer)
    offer_name: Mapped[str] = mapped_column(sa.String(length=255), nullable=False)

    avail_amount_min: Mapped[Optional[int]] = mapped_column(sa.Integer)
    avail_amount_max: Mapped[Optional[int]] = mapped_column(sa.Integer)
    repayment_period_min: Mapped[Optional[int]] = mapped_column(sa.Integer)
    repayment_period_max: Mapped[Optional[int]] = mapped_column(sa.Integer)
    total_cost_min: Mapped[Optional[float]] = mapped_column(sa.Numeric)
    total_cost_max: Mapped[Optional[float]] = mapped_column(sa.Numeric)


class ReviewSnapshot(Base):
    __tablename__ = "review_snapshot"

    id: Mapped[int] = mapped_column(postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.uuid4] = mapped_column(postgresql.UUID(as_uuid=True), nullable=False)

    title: Mapped[Optional[str]] = mapped_column(sa.String)
    body: Mapped[Optional[str]] = mapped_column(sa.String)
    rating: Mapped[Optional[int]] = mapped_column(sa.SmallInteger)
    published_at: Mapped[Optional[date]] = mapped_column(sa.Date)
