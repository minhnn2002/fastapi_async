from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean, create_engine
from sqlalchemy.orm import declarative_base
from app.config import settings

Base = declarative_base()


class SMS_Data(Base):
    __tablename__ = settings.TABLE_NAME

    id = Column(String(100), primary_key=True)
    ts = Column(DateTime, primary_key=True)
    sdt_in = Column(String(100))
    group_id = Column(String(100))

    sdt_out = Column(String(100), nullable=True)
    text_sms = Column(String(500), nullable=True)
    predicted_label = Column(String(100), nullable=True)
    llm_label = Column(String(100), nullable=True)
    confidence = Column(String(100), nullable=True)
    feedback = Column(Boolean, nullable=True)

