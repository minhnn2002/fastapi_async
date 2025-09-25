from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, text, func
from app.db import get_session
from app.models import SMS_Data
from app.schemas import *
from app.utils import *
from app.config import settings
from datetime import datetime
import csv
from collections import defaultdict
import io

router = APIRouter(
    prefix="/frequency",
    tags=['Frequency']
)


@router.get("/")
async def get_spam_base_on_frequency(
    session: Annotated[AsyncSession, Depends(get_session)],
    from_datetime: Annotated[str, Query(description="Time Start: (ISO format)")] = None,
    to_datetime: Annotated[str, Query(description="Time End: (ISO format)")] = None,
    page: Annotated[int, Query(ge=0)] = 0,
    page_size: Annotated[int, Query(description="The number of record in one page", enum=[10, 50, 100])] = 10,
    text_keyword: Annotated[str, Query(description="Filter messages that contain this keyword (case insensitive)")] = None
) -> BasePaginatedResponseFrequency:
    
    # --- Parse time string ---
    from_datetime = parse_datetime(from_datetime)
    to_datetime = parse_datetime(to_datetime)
    
    # --- Time validation ---
    from_datetime, to_datetime = await validate_time_range(session, from_datetime, to_datetime)

    # --- Base filters ---
    filters = [SMS_Data.ts.between(from_datetime, to_datetime)]
    if text_keyword:
        filters.append(SMS_Data.text_sms.ilike(f"%{text_keyword}%"))

    # --- Aggregation query ---
    agg_query = (
        select(
            SMS_Data.group_id,
            func.min(SMS_Data.ts).label("first_ts"),
            func.count().label("frequency"),
            func.min_by(SMS_Data.text_sms, SMS_Data.ts).label("agg_message")
        )
        .where(*filters)
        .group_by(SMS_Data.group_id)
        .having(func.count() >= 20)
        .subquery()
    )

    # --- Pagination query ---
    main_stmt = (
        select(
            agg_query.c.group_id,
            agg_query.c.first_ts,
            agg_query.c.frequency,
            agg_query.c.agg_message,
            func.count().over().label("total_records")
        )
        .order_by(agg_query.c.first_ts, agg_query.c.group_id)
        .offset(page * page_size)
        .limit(page_size)
    )
    result_record = await session.execute(main_stmt)
    grouped_records = result_record.all()
    total_records = grouped_records[0].total_records if grouped_records else 0

    # --- Second query: all messages ---
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
    result_message = await session.execute(msg_stmt)
    all_messages = result_message.all()

    # --- Build message dictionary ---
    messages_dict = defaultdict(list)
    for m in all_messages:
        messages_dict[m.group_id].append(
            MessageCount(text_sms=m.text_sms, count=m.count)
        )

    # --- Build result ---
    start_index = page * page_size + 1
    result = [
        SMSGroupedFrequency(
            stt=i,
            group_id=r.group_id,
            frequency=r.frequency,
            ts=r.first_ts,
            agg_message=r.agg_message,
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
    from_datetime: str = Query(None, description="Time Start: (ISO format)"),
    to_datetime: str = Query(None, description="Time End: (ISO format)"),
    text_keyword: str = Query(None, description="Filter messages that contain this keyword (case insensitive)")
):

    # --- Parse and validate datetime ---
    from_datetime = parse_datetime(from_datetime)
    to_datetime = parse_datetime(to_datetime)
    from_datetime, to_datetime = await validate_time_range(session, from_datetime, to_datetime)

    # --- Build filters ---
    filters = [SMS_Data.ts.between(from_datetime, to_datetime)]
    if text_keyword:
        filters.append(SMS_Data.text_sms.ilike(f"%{text_keyword}%"))

    # --- Aggregation query ---
    agg_query = (
        select(
            SMS_Data.group_id,
            func.count().label("frequency"),
            func.min(SMS_Data.ts).label("first_ts"),
            func.min_by(SMS_Data.text_sms, SMS_Data.ts).label("agg_message")
        )
        .where(*filters)
        .group_by(SMS_Data.group_id)
        .having(func.count() >= 20)
        .execution_options(stream_results=True)
    )

    # --- Async CSV streaming generator ---
    async def stream():
        buffer = io.StringIO()
        writer = csv.writer(buffer, quoting=csv.QUOTE_ALL)

        # Write header
        writer.writerow(["group_id", "frequency", "first_ts", "agg_message"])
        yield buffer.getvalue()
        buffer.seek(0)
        buffer.truncate(0)

        # Stream rows from DB within a transaction
        row_count = 0
        async with session.begin():  # Ensure session remains open during streaming
            result = await session.stream(agg_query)  # Await to get AsyncResult
            async for row in result:  # Iterate directly over AsyncResult
                row_count += 1
                writer.writerow([row.group_id, row.frequency, row.first_ts, row.agg_message])
                yield buffer.getvalue()
                buffer.seek(0)
                buffer.truncate(0)
            if row_count == 0:
                writer.writerow(["No data found"])
                yield buffer.getvalue()

    # --- Return StreamingResponse ---
    return StreamingResponse(
        stream(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=frequency_export.csv"}
    )


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
