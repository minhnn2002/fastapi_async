from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text, func, case, and_, or_
from app.db import get_session
from app.models import SMS_Data
from app.schemas import *
from app.utils import *
from app.config import settings
from datetime import datetime
from pydantic import BeforeValidator
import csv
from collections import defaultdict
import io

router = APIRouter(
    prefix="/frequency",
    tags=['Frequency']
)


@router.get("/")
async def get_spam_base_on_content(
    session: Annotated[AsyncSession, Depends(get_session)],
    from_datetime: Annotated[
        datetime | None, 
        Query(description="Start time (epoch or ISO with timezone)"),
        # BeforeValidator(parse_datetime)
    ] = None,
    to_datetime: Annotated[
        datetime | None, 
        Query(description="End time (epoch or ISO with timezone)"),
        # BeforeValidator(parse_datetime)
    ] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(description="The number of record in one page", enum=[10, 20, 50, 100])] = 10,
    text_keyword: Annotated[str, Query(description="Filter messages that contain this keyword (case insensitive)")] = None
) -> BasePaginatedResponseFrequency:

    # time validation
    from_datetime, to_datetime = await validate_time_range(session, from_datetime, to_datetime)

    # base filter  
    filters = [SMS_Data.ts.between(from_datetime, to_datetime)]
    if text_keyword:
        filters.append(SMS_Data.text_sms.ilike(f"%{text_keyword}%"))

    # cte for pre-calculate
    cte = (
        select(
            SMS_Data.group_id,
            func.min(SMS_Data.ts).label("first_ts"),
            func.count().label("frequency"),
            func.min_by(SMS_Data.text_sms, SMS_Data.ts).label("agg_message"),
            func.sum(case((SMS_Data.predicted_label == 'spam', 1), else_=0)).label("spam_count"),
            func.sum(case((SMS_Data.predicted_label == 'not_spam', 1), else_=0)).label("not_spam_count"),
        )
        .where(and_(*filters))
        .group_by(SMS_Data.group_id)
        .cte("cte")
    )

    # spam and not_spam condition
    spam_condition = and_(cte.c.frequency >= 20, cte.c.spam_count > cte.c.not_spam_count)
    not_spam_condition = and_(cte.c.frequency >= 30, cte.c.spam_count <= cte.c.not_spam_count)

    # main query
    main_stmt = (
        select(
            cte.c.group_id,
            cte.c.first_ts,
            cte.c.frequency,
            cte.c.agg_message,
            case((cte.c.spam_count >= cte.c.not_spam_count, 'spam'), else_='not_spam').label("label"),
            func.count().over().label("total_records"),
        )
        .where(or_(spam_condition, not_spam_condition))
        .order_by(cte.c.first_ts, cte.c.group_id)
        .offset((page - 1) * page_size) 
        .limit(page_size)
    )
    result = await session.execute(main_stmt)
    grouped_records = result.all()
    total_records = grouped_records[0].total_records if grouped_records else 0

    if total_records == 0:
        return BasePaginatedResponseContent(
            status_code=200,
            message="No data found",
            data=[],
            error=False,
            error_message="",
            page=page,
            limit=page_size,
            total=0
        )

    # get all the message for each group
    group_ids = [r.group_id for r in grouped_records]

    msg_stmt = (
        select(
            SMS_Data.group_id,
            SMS_Data.text_sms,
            func.count().label("count")
        )
        .where(
            SMS_Data.group_id.in_(group_ids),
            *filters
        )
        .group_by(SMS_Data.group_id, SMS_Data.text_sms)
    )
    result = await session.execute(msg_stmt)
    all_messages = result.all()

    # --- Build message dictionary ---
    messages_dict = defaultdict(list)
    for m in all_messages:
        messages_dict[m.group_id].append(
            MessageCount(text_sms=m.text_sms, count=m.count)
        )

    # --- Build result ---
    start_index = (page-1) * page_size + 1
    result = [
        SMSGroupedFrequency(
            stt=i,
            group_id=r.group_id,
            frequency=r.frequency,
            ts=r.first_ts,
            agg_message=r.agg_message,
            label=r.label,
            messages=messages_dict.get(r.group_id, [])
        )
        for i, r in enumerate(grouped_records, start=start_index)
    ]

    return BasePaginatedResponseFrequency(
        status_code=200,
        message="Success",
        data=result,
        error=False,
        error_message="",
        page=page,
        limit=page_size,
        total=total_records
    )


@router.get("/export")
async def export_frequency_data(
    session: AsyncSession = Depends(get_session),
    from_datetime: Annotated[
        datetime | None, 
        Query(description="Start time (epoch)"),
        BeforeValidator(parse_datetime)
    ] = None,
    to_datetime: Annotated[
        datetime | None, 
        Query(description="End time (epoch)"),
        BeforeValidator(parse_datetime)
    ] = None,
    text_keyword: str = Query(None, description="Filter messages that contain this keyword (case insensitive)")
):

    # --- Time validation ---
    from_datetime, to_datetime = await validate_time_range(session, from_datetime, to_datetime)

    # --- Build filters ---
    filters = [SMS_Data.ts.between(from_datetime, to_datetime)]
    if text_keyword:
        filters.append(SMS_Data.text_sms.ilike(f"%{text_keyword}%"))

    cte = (
        select(
            SMS_Data.group_id,
            func.min(SMS_Data.ts).label("first_ts"),
            func.count().label("frequency"),
            func.min_by(SMS_Data.text_sms, SMS_Data.ts).label("agg_message"),
            func.sum(case((SMS_Data.predicted_label == 'spam', 1), else_=0)).label("spam_count"),
            func.sum(case((SMS_Data.predicted_label == 'not_spam', 1), else_=0)).label("not_spam_count"),
        )
        .where(and_(*filters))
        .group_by(SMS_Data.group_id)
        .cte("cte")
    )

    # spam and not_spam condition
    spam_condition = and_(cte.c.frequency >= 20, cte.c.spam_count > cte.c.not_spam_count)
    not_spam_condition = and_(cte.c.frequency >= 30, cte.c.spam_count <= cte.c.not_spam_count)

    # main query
    main_stmt = (
        select(
            cte.c.group_id,
            cte.c.first_ts,
            cte.c.frequency,
            cte.c.agg_message,
            case((cte.c.spam_count >= cte.c.not_spam_count, 'spam'), else_='not_spam').label("label"),
        )
        .where(or_(spam_condition, not_spam_condition))
    )
    result = await session.execute(main_stmt)
    grouped_records = result.all()

    output = [
        SMSExportFrequency(
            group_id=r.group_id,
            frequency=r.frequency,
            ts=r.first_ts,
            agg_message=r.agg_message,
            label=r.label
        )
        for r in grouped_records
    ]

    return output


@router.put("/")
async def feedback_base_on_frequency(
    user_feedback: list[FrequencyFeedback],
    session: AsyncSession = Depends(get_session),
):
    if not user_feedback:
        raise HTTPException(status_code=400, detail="No feedback data provided")

    cases = []
    where_clauses = []
    params = {}

    for idx, item in enumerate(user_feedback):
        gid_key = f"gid_{idx}"
        fb_key = f"fb_{idx}"

        cases.append(f"WHEN group_id = :{gid_key} THEN :{fb_key}")
        where_clauses.append(f":{gid_key}")

        params[gid_key] = item.group_id
        params[fb_key] = item.feedback

    case_sql = " ".join(cases)
    where_sql = ", ".join(where_clauses)

    sql = text(f"""
        UPDATE {settings.TABLE_NAME}
        SET feedback = CASE {case_sql} END
        WHERE group_id IN ({where_sql})
    """)

    result = await session.execute(sql, params)
    await session.commit()

    total_updated = result.rowcount or 0
    if total_updated == 0:
        raise HTTPException(status_code=404, detail="No records matched your condition")

    return BaseResponse(
        status_code=200,
        message=f"Updated {total_updated} records",
        error=False,
        error_message=None,
    )
