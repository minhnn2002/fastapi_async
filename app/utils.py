from datetime import datetime, timedelta
from fastapi import HTTPException, status
from sqlalchemy import func, select
from app.models import *


def parse_datetime(dt_str: str) -> datetime:
    """
    Convert datetime string to datetime with timezone.
    """

    if dt_str is None:
        return None

    try:
        dt = dt_str.replace(' ', '+')
        dt = datetime.fromisoformat(dt)
        if dt.tzinfo is None: 
            raise ValueError("Missing timezone info")
        return dt
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail={
                "message": f"Invalid datetime format: {dt_str}. Use ISO 8601, e.g., 2025-09-10T15:15:00+07:00"
            }
        )



async def validate_time_range(
    session,
    from_datetime: datetime | None,
    to_datetime: datetime | None,
):
    """
    Validate and normalize a time range:
    - Default: last `max_hours` if both None.
    - Not exceed `max_hours`.
    - `to_datetime` <= now.
    - `from_datetime` >= min(ts) in DB.
    """

    if from_datetime is None and to_datetime is None: 
        result = await session.execute(select(func.max(SMS_Data.ts)))
        to_datetime = result.scalar()
        from_datetime = to_datetime - timedelta(hours=1)
    else:
        if from_datetime is None:
            from_datetime = to_datetime - timedelta(hours=1)
        if to_datetime is None:
            to_datetime = from_datetime + timedelta(hours=1)

    if to_datetime < from_datetime:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="'to_datetime' cannot be earlier than 'from_datetime'."
        )
    if to_datetime - from_datetime > timedelta(hours=1):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Time range cannot exceed 1 hour."
        )

    return from_datetime, to_datetime
