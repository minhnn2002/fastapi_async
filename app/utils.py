from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, status
from sqlalchemy import func, select
from app.models import *

def validate_time_range(
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
        to_datetime = datetime.now()
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
        from_datetime = to_datetime - timedelta(hours=1)

    return from_datetime, to_datetime




def parse_datetime(v: str | int | float):
    if v is None:
        return None
    
    if isinstance(v, (int, float)) or (isinstance(v, str) and v.isdigit()):
        v = int(v)
        if abs(v) > 2e10:  
            dt = datetime.fromtimestamp(v / 1000, tz=timezone.utc)
        else:  
            dt = datetime.fromtimestamp(v, tz=timezone.utc)
        return dt
    
    if isinstance(v, str):
        if v.endswith("Z"):
            v = v[:-1] + "+00:00"
        v = v.replace(' ', '+')
        dt = datetime.fromisoformat(v)

        if dt.tzinfo is None:
            raise ValueError("Datetime string must include timezone (Z or ±HH:MM)")

        return dt

    raise ValueError("Invalid datetime format")


def validate_page_size(page_size):
    try:
        page_size = int(page_size)
    except:
        return 10
    if page_size in (10, 20, 50, 100):
        return page_size
    else:
        return 10

def validate_page(page): 
    try:
        page = int(page)
    except (TypeError, ValueError):
        return 1

    if page >= 1:
        return page
    else:
        return 1

