import os
import sqlalchemy as sa
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from extractor_microloans import extract_microloans
from extractor_finrating import extract_reviews
from models import Base, MicroloanSnapshot, PipelineSnapshot, ReviewSnapshot, PipelineType, PipelineStatus


def get_engine():
    return create_engine(os.environ.get("DATABASE_URL"))

def create_tables():
    engine = get_engine()
    Base.metadata.create_all(engine)

def insert_microloans(rows, pipeline_name=PipelineType.MICROLOANS):
    engine = get_engine()
    with sessionmaker(engine).begin() as session:
        run = PipelineSnapshot(pipeline=pipeline_name, status=PipelineStatus.RUNNING)
        session.add(run)
        session.flush()
        run_id = run.run_id

        objs = [
            MicroloanSnapshot(
                run_id=run_id,
                card_index=row.get("card_index"),
                offer_name=row.get("offer_name", ""),
                avail_amount_min=row.get("avail_amount_min"),
                avail_amount_max=row.get("avail_amount_max"),
                repayment_period_min=row.get("repayment_period_min"),
                repayment_period_max=row.get("repayment_period_max"),
                total_cost_min=row.get("total_cost_min"),
                total_cost_max=row.get("total_cost_max"),
            )
            for row in rows
        ]
        session.add_all(objs)
        run.status = PipelineStatus.OK
        run.rows_count = len(objs)
        run.finished_at = sa.func.now()
        session.commit()
        return run_id


def insert_reviews(rows, pipeline_name=PipelineType.REVIEWS):
    engine = get_engine()
    with sessionmaker(engine).begin() as session:
        run = PipelineSnapshot(pipeline=pipeline_name, status=PipelineStatus.RUNNING)
        session.add(run)
        session.flush()
        run_id = run.run_id

        objs = [
            ReviewSnapshot(
                run_id=run_id,
                title=r.get("title"),
                body=r.get("body"),
                rating=r.get("rating"),
                published_at=r.get("date"),
            )
            for r in rows
        ]
        session.add_all(objs)
        run.status = PipelineStatus.OK
        run.rows_count = len(objs)
        run.finished_at = sa.func.now()
        session.commit()
        return run_id


if __name__ == "__main__":
    create_tables()
    insert_microloans(extract_microloans())
    insert_reviews(extract_reviews())
