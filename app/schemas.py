from pydantic import BaseModel, ConfigDict, field_validator
from datetime import datetime, timezone, timedelta

# Model for GET API
class MessageCount(BaseModel):
    text_sms: str|None
    count: int

class BaseData(BaseModel):
    stt: int
    group_id: str
    frequency: int
    ts: datetime
    agg_message: str
    label: str

class SMSGroupedFrequency(BaseData):
    messages: list[MessageCount]

class SMSGroupedContent(BaseData):
    sdt_in: str
    messages: list[MessageCount]

class BaseResponse(BaseModel):
    status_code: int
    message: str
    error: bool = False
    error_message: str|None = None

class BasePaginatedResponseContent(BaseResponse):
    data: list[SMSGroupedContent]|None = None
    page: int
    limit: int
    total: int

class BasePaginatedResponseFrequency(BaseResponse):
    data: list[SMSGroupedFrequency]|None = None
    page: int
    limit: int
    total: int



# Model for Feedback
class BaseFeedback(BaseModel):
    feedback: bool
    group_id: str


class FrequencyFeedback(BaseFeedback):
    pass

class ContentFeedback(FrequencyFeedback):
    sdt_in: str
    

# Model for export
class SMSExportFrequency(BaseModel):
    group_id: str
    frequency: int
    ts: datetime
    agg_message: str
    label: str

class SMSExportContent(BaseModel):
    group_id: str
    sdt_in: str
    frequency: int
    ts: datetime
    agg_message: str
    label: str





# UTC_PLUS_7 = timezone(timedelta(hours=7))

# class DateTimeModel(BaseModel):
#     model_config = ConfigDict(strict=True)
#     t: datetime

#     @field_validator("t", mode="before")
#     def parse_datetime(cls, v):
#         # --- Epoch dạng số ---
#         if isinstance(v, (int, float)):
#             if abs(v) > 2e10:  # mili-giây
#                 dt = datetime.fromtimestamp(v / 1000, tz=timezone.utc)
#             else:  # giây
#                 dt = datetime.fromtimestamp(v, tz=timezone.utc)
#             return dt.astimezone(UTC_PLUS_7)

#         # # --- Epoch dạng string số ---
#         # if isinstance(v, str) and v.isdigit():
#         #     v = int(v)
#         #     if abs(v) > 2e10:
#         #         dt = datetime.fromtimestamp(v / 1000, tz=timezone.utc)
#         #     else:
#         #         dt = datetime.fromtimestamp(v, tz=timezone.utc)
#         #     return dt.astimezone(UTC_PLUS_7)

#         # --- ISO format ---
#         if isinstance(v, str):
#             # Hỗ trợ ISO có "Z"
#             if v.endswith("Z"):
#                 v = v[:-1] + "+00:00"
#             dt = datetime.fromisoformat(v)

#             # Strict: bắt buộc phải có tzinfo
#             if dt.tzinfo is None:
#                 raise ValueError("Datetime string must include timezone (Z or ±HH:MM)")

#             return dt.astimezone(UTC_PLUS_7)

#         # --- Datetime object ---
#         if isinstance(v, datetime):
#             if v.tzinfo is None:
#                 raise ValueError("Datetime object must be timezone-aware")
#             return v.astimezone(UTC_PLUS_7)

#         raise ValueError(f"Unsupported datetime format: {v}")
