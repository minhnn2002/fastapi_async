from pydantic import BaseModel, Field
from datetime import datetime

class MessageCount(BaseModel):
    text_sms: str|None
    count: int


class BaseDataFrequency(BaseModel):
    stt: int
    group_id: str
    frequency: int
    ts: datetime
    agg_message: str|None

class BaseDataContent(BaseDataFrequency):
    sdt_in: str

class SMSGroupedFrequency(BaseDataFrequency):
    messages: list[MessageCount]

class SMSGroupedContent(BaseDataContent):
    messages: list[MessageCount]


class BaseResponse(BaseModel):
    status_code: int
    message: str|None = None
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




class BaseFeedback(BaseModel):
    feedback: bool
    group_id: str


class FrequencyFeedback(BaseFeedback):
    pass

class ContentFeedback(FrequencyFeedback):
    sdt_in: str
    


