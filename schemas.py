import datetime
from pydantic import BaseModel


class BookingCreate(BaseModel):
    telegram: str
    date: datetime.date
    start_time: str 
    duration_hours: float
    equipment: str | None = None 