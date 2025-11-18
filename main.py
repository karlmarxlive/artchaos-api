import datetime
from fastapi import FastAPI, Query, HTTPException
from starlette.responses import Response
from datetime import timedelta 

import nocodb_client
import booking_logic
import schemas

app = FastAPI(
    title="ArtChaos API",
    description="API для управления бронированиями в творческой мастерской.",
    version="1.0.0"
)

USER_BOOKING_CACHE = {}
CACHE_LIFETIME_MINUTES = 30

def parse_date_from_str(date_str: str) -> datetime.date:
    """Парсит дату из строки формата 'dd.mm.yyyy'."""
    try:
        return datetime.datetime.strptime(date_str, "%d.%m.%Y").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Неверный формат даты. Ожидается dd.mm.yyyy")


@app.get("/api/v1/available_start_times")
async def get_start_times(
    date_str: str = Query(..., alias="date"), 
    telegram_id: str = Query(..., alias="telegram_id"),
    equipment: str | None = Query(None)
):
    """
    Эндпоинт для получения доступных времен начала записи.
    Проверяет, действует ли абонемент пользователя на запрашиваемую дату.
    Возвращает JSON вида {"result": "10:00,10:30,14:00"}
    """
    requested_date = parse_date_from_str(date_str)
    
    abonement_data = await nocodb_client.get_abonement_by_telegram_id(telegram_id)
    
    if not abonement_data:
        return {"result": "❌ У тебя не найден действующий абонемент :( Пожалуйста, напиши об этой ошибке @egor_savenko"}
        
    days_left = int(abonement_data.get("Осталось дней", 0))
    
    today = datetime.date.today()
    delta_days = (requested_date - today).days
    
    if delta_days < 0:
        return {"result": "❌ Нельзя записаться на прошедшую дату. Пожалуйста, напиши об этой ошибке @egor_savenko"}

    if delta_days > days_left:
        return {"result": f"❌ Твой абонемент истекает раньше, чем {date_str}. Ты можешь записаться на даты в пределах оставшихся {days_left} дней."}

    
    bookings = await nocodb_client.get_bookings_by_date(date_str)
    events = await nocodb_client.get_events_by_date(date_str)
    timeline = booking_logic.calculate_timeline_load(bookings, events)
    
    available_times = booking_logic.get_available_start_times(timeline, requested_date, equipment_required=equipment)
    
    if not available_times:
        return {"result": f"❌ На {date_str} нет свободных мест. Попробуй выбрать другую дату."}

    result_string = ",".join(available_times)
    return {"result": result_string}


@app.get("/api/v1/check_duration")
async def check_duration(
    date_str: str = Query(..., alias="date"), 
    start_time: str = Query(...),
    equipment: str | None = Query(None)
):
    """
    Эндпоинт для проверки максимально возможной длительности записи.
    Возвращает JSON вида {"result": "2.5"}
    """
    parse_date_from_str(date_str)
    
    bookings = await nocodb_client.get_bookings_by_date(date_str)
    events = await nocodb_client.get_events_by_date(date_str)
    
    timeline = booking_logic.calculate_timeline_load(bookings, events)
    
    max_duration = booking_logic.get_max_duration(start_time, timeline, equipment_required=equipment)

    return {"result": max_duration}


@app.post("/api/v1/bookings", status_code=201) # status_code=201 означает "Created"
async def create_booking(booking_data: schemas.BookingCreate):
    """
    Эндпоинт для создания новой брони с финальной проверкой.
    """
    
    parse_date_from_str(booking_data.date)
    
    latest_bookings = await nocodb_client.get_bookings_by_date(booking_data.date)
    latest_events = await nocodb_client.get_events_by_date(booking_data.date)
    
    timeline = booking_logic.calculate_timeline_load(latest_bookings, latest_events)
    
    current_max_duration = booking_logic.get_max_duration(
        start_time_str=booking_data.start_time,
        timeline=timeline,
        equipment_required=booking_data.equipment
    )
    
    if booking_data.duration_hours > current_max_duration:
        raise HTTPException(
            status_code=409, # 409 Conflict - подходящий код для этой ситуации
            detail="Извините, это время или его часть только что заняли. Пожалуйста, попробуйте выбрать время заново."
        )
    
    start_dt = datetime.datetime.strptime(booking_data.start_time, "%H:%M")
    duration = timedelta(hours=booking_data.duration_hours)
    end_dt = start_dt + duration
    
    telegram_field_value = booking_data.telegram
    if booking_data.telegram == "—" or booking_data.telegram == "":
        telegram_field_value = booking_data.fullname
    
    data_for_nocodb = {
        "Telegram": telegram_field_value,
        "Дата посещения": booking_data.date,
        "Время начала": start_dt.strftime("%H:%M:%S"),
        "Время конца": end_dt.strftime("%H:%M:%S"),
        "Оборудование": booking_data.equipment,
        "Что будет делать": booking_data.activity,
        "Telegram ID": booking_data.telegram_id
    }
    
    new_booking = await nocodb_client.create_booking(data_for_nocodb)
    
    if not new_booking:
        raise HTTPException(
            status_code=500,
            detail="Не удалось создать запись в базе данных. Пожалуйста, свяжиcь с @egor_savenko"
        )
        
    
    return {"status": "success", 
            "booking_details": new_booking,
            "end_time": end_dt.strftime("%H:%M")
            }
    
    
@app.get("/api/v1/my_bookings")
async def get_my_bookings(telegram_id: str):
    """
    Находит будущие брони пользователя по Telegram ID, форматирует их в красивую строку
    и кэширует ID броней для последующей отмены.
    """
    all_bookings = await nocodb_client.get_all_bookings_by_telegram_id(telegram_id)
    
    # --- Фильтрация и сортировка ---
    future_bookings = []
    now_aware = datetime.datetime.now(booking_logic.WORKSHOP_TIMEZONE)

    for booking in all_bookings:
        try:
            booking_date = datetime.datetime.strptime(booking["Дата посещения"], "%d.%m.%Y").date()
            booking_time = datetime.datetime.strptime(booking["Время начала"], "%H:%M:%S").time()
            booking_datetime = datetime.datetime.combine(booking_date, booking_time)
            
            booking_datetime_aware = booking_datetime.replace(tzinfo=booking_logic.WORKSHOP_TIMEZONE)

            if booking_datetime_aware > now_aware:
                future_bookings.append(booking)
        except (ValueError, KeyError):
            continue

    # Сортируем от ближайшей к самой дальней
    future_bookings.sort(key=lambda b: (
        datetime.datetime.strptime(b["Дата посещения"], "%d.%m.%Y"),
        datetime.datetime.strptime(b["Время начала"], "%H:%M:%S")
    ))

    if not future_bookings:
        no_bookings_text = "У тебя пока нет записей.\nХочешь записаться? 👇"
        return {"result": no_bookings_text}

    formatted_lines = ["Твои записи: \n"]
    booking_map = {} 

    for i, booking in enumerate(future_bookings, 1):
        start_time_short = booking['Время начала'][:5]
        line = f"{i}. 📆 {booking['Дата посещения']} в {start_time_short}"
        
        if booking.get("Оборудование"):
            line += f" (📍 {booking['Оборудование']})"
            
        activity_description = booking.get("Что будет делать")
        if activity_description:
            line += f"\n  📝 {activity_description}"
            
        formatted_lines.append(line)
        booking_map[str(i)] = booking['Id']

    USER_BOOKING_CACHE[telegram_id] = {
        "map": booking_map,
        "timestamp": datetime.datetime.now()
    }

    final_text = "\n\n".join(formatted_lines)
    return {"result": final_text}


@app.post("/api/v1/cancel_booking")
async def cancel_booking(cancel_data: schemas.BookingCancel):
    """
    Отменяет бронь пользователя, используя номер из кэшированного списка.
    """
    telegram_id = cancel_data.telegram_id
    booking_number = cancel_data.booking_number
    
    # --- Сценарий: Кэш не найден или устарел ---
    cached_user_data = USER_BOOKING_CACHE.get(telegram_id)
    
    if not cached_user_data:
        return {
            "status": "error",
            "message": "Список записей устарел. Пожалуйста, открой 'Мои записи' и попробуй снова."
        }
    
    cache_age = datetime.datetime.now() - cached_user_data["timestamp"]
    if cache_age > timedelta(minutes=CACHE_LIFETIME_MINUTES):
        del USER_BOOKING_CACHE[telegram_id] # Чистим устаревший кэш
        return {
            "status": "error",
            "message": "Список записей устарел (прошло более 30 минут). Пожалуйста, открой 'Мои записи' и попробуй снова."
        }

    # --- Сценарий: Номер записи не найден в кэше ---
    booking_id_to_delete = cached_user_data["map"].get(booking_number)
    
    if not booking_id_to_delete:
        return {
            "status": "error",
            "message": f"Записи с номером {booking_number} не найдено в твоём списке. Пожалуйста, проверь номер и попробуй снова."
        }
        
    # --- Сценарий: Успешное удаление ---
    success = await nocodb_client.delete_booking_by_id(booking_id_to_delete)
    
    if success:
        del USER_BOOKING_CACHE[telegram_id]
        return {
            "status": "success",
            "message": "✅ Запись успешно отменена!"
        }
    else:
        return {
            "status": "error",
            "message": "Возникла проблема при отмене брони. Пожалуйста, свяжись с @egor_savenko"
        }