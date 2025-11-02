import datetime
from pydantic import BaseModel


class BookingCreate(BaseModel):
    telegram_id: str
    telegram: str
    fullname: str
    date: str
    start_time: str 
    duration_hours: float
    activity: str | None = ""
    equipment: str | None = None 
    

class BookingCancel(BaseModel):
    telegram_id: str
    booking_number: str