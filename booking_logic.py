import datetime
from zoneinfo import ZoneInfo

# --- КОНСТАНТЫ И НАСТРОЙКИ МАСТЕРСКОЙ ---

WORKSHOP_OPEN_HOUR = 10   # Час открытия
WORKSHOP_CLOSE_HOUR = 22  # Час закрытия
TIME_STEP_MINUTES = 30    # Шаг для проверки слотов (30 минут)
TOTAL_SPOTS = 8           # Всего мест в мастерской
EVENT_BUFFER_MINUTES = 30 # Буфер по времени до и после мероприятий

TOTAL_POTTERY_WHEELS = 2
POTTERY_WHEEL_NAME = "Гончарный круг"

WORKSHOP_TIMEZONE = ZoneInfo("Asia/Novosibirsk")


# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---

def str_to_time(time_str: str) -> datetime.time:
    """Преобразует строку 'HH:MM:SS' в объект datetime.time."""
    return datetime.datetime.strptime(time_str, "%H:%M:%S").time()

def generate_timeline() -> dict:
    """
    Создает пустой "таймлайн" рабочего дня с шагом в 30 минут.
    Ключ - время, значение - информация о нагрузке.
    """
    timeline = {}
    current_time = datetime.datetime.combine(datetime.date.today(), datetime.time(WORKSHOP_OPEN_HOUR))
    end_time = datetime.datetime.combine(datetime.date.today(), datetime.time(WORKSHOP_CLOSE_HOUR))

    while current_time < end_time:
        timeline[current_time.time()] = {
            "people_count": 0,
            "is_blocked_by_event": False,
            "pottery_wheels_used": 0
        }
        current_time += datetime.timedelta(minutes=TIME_STEP_MINUTES)
    
    return timeline

# --- ОСНОВНЫЕ ЛОГИЧЕСКИЕ ФУНКЦИИ ---

def calculate_timeline_load(bookings: list, events: list) -> dict:
    """
    Рассчитывает нагрузку на каждый временной слот в течение дня.
    
    Args:
        bookings: Список словарей с данными о бронированиях из NocoDB.
        events: Список словарей с данными о мероприятиях из NocoDB.
        
    Returns:
        Словарь (таймлайн) с рассчитанной нагрузкой на каждый слот.
    """
    timeline = generate_timeline()

    for event in events:
        start_time_obj = str_to_time(event["Начало"])
        end_time_obj = str_to_time(event["Конец"])
        
        today = datetime.date.today()
        start_dt = datetime.datetime.combine(today, start_time_obj)
        end_dt = datetime.datetime.combine(today, end_time_obj)
        
        buffer = datetime.timedelta(minutes=EVENT_BUFFER_MINUTES)
        
        buffered_start_time = (start_dt - buffer).time()
        buffered_end_time = (end_dt + buffer).time()
        
        for slot_time in timeline:
            if buffered_start_time <= slot_time < buffered_end_time:
                timeline[slot_time]["is_blocked_by_event"] = True

    for booking in bookings:
        start_time = str_to_time(booking["Время начала"])
        end_time = str_to_time(booking["Время конца"])

        for slot_time in timeline:
            if start_time <= slot_time < end_time:
                timeline[slot_time]["people_count"] += 1
                
                if booking.get("Оборудование") == POTTERY_WHEEL_NAME:
                    timeline[slot_time]["pottery_wheels_used"] += 1
    
    return timeline


def get_available_start_times(timeline: dict, request_date: datetime.date, equipment_required: str | None = None) -> list[str]:
    """
    Находит доступные времена для НАЧАЛА записи.
    Если указано equipment_required, проверяет и его доступность.
    Фильтрует прошедшие слоты для текущего дня.
    """
    available_times = []
    
    today = datetime.date.today()
    current_time = datetime.datetime.now(WORKSHOP_TIMEZONE).time()

    
    for slot_time, load_info in timeline.items():
        is_available = not load_info["is_blocked_by_event"] and load_info["people_count"] < TOTAL_SPOTS
        
        if equipment_required == POTTERY_WHEEL_NAME:
            is_available = is_available and (load_info["pottery_wheels_used"] < TOTAL_POTTERY_WHEELS)
            
        if request_date == today and slot_time <= current_time:
            is_available = False
        
        if is_available:
            available_times.append(slot_time.strftime("%H:%M"))
            
    return available_times



def get_max_duration(start_time_str: str, timeline: dict, equipment_required: str | None = None) -> float:
    """
    Рассчитывает максимально возможную длительность записи с учетом оборудования.
    """
    start_time = datetime.datetime.strptime(start_time_str, "%H:%M").time()
    
    if start_time not in timeline:
        return 0.0

    max_duration_minutes = 0
    sorted_slots = sorted(timeline.keys())
    
    try:
        start_index = sorted_slots.index(start_time)
    except ValueError:
        return 0.0
    
    for i in range(start_index, len(sorted_slots)):
        slot_time = sorted_slots[i]
        load_info = timeline[slot_time]

        is_slot_ok = not load_info["is_blocked_by_event"] and load_info["people_count"] < TOTAL_SPOTS
        
        if equipment_required == POTTERY_WHEEL_NAME:
            is_slot_ok = is_slot_ok and (load_info["pottery_wheels_used"] < TOTAL_POTTERY_WHEELS)
        
        if is_slot_ok:
            max_duration_minutes += TIME_STEP_MINUTES
        else:
            break
            
    return max_duration_minutes / 60.0