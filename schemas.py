import datetime
from pydantic import BaseModel
from typing import List


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


# Модель урока для отправки на фронтенд
class LessonResponse(BaseModel):
    slug: str
    title: str
    status: str  # "completed", "active", "locked"
    is_new_block: bool 


# Ответ для Timeline (список уроков)
class CourseTimelineResponse(BaseModel):
    lessons: List[LessonResponse]
    last_visit: str | None


class LessonCompleteRequest(BaseModel):
    telegram_id: str
    lesson_slug: str