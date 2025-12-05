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
    
class FiringCalculationRequest(BaseModel):
    telegram_id: str
    quantity: int
    size: str        # "микро", "маленькое", "среднее", "большое"
    firing_type: str # "утель", "глазурь до 1120", "глазурь до 1220"
    glaze_type: str  # "без глазури", "своя", "из мастерской"