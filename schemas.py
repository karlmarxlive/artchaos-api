import datetime
from pydantic import BaseModel


class BookingCreate(BaseModel):
    telegram: str
    date: str
    start_time: str 
    duration_hours: float
    activity: str | None = ""
    equipment: str | None = None 