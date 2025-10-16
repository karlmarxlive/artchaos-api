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


def parse_date_from_str(date_str: str) -> datetime.date:
    """Парсит дату из строки формата 'dd.mm.yyyy'."""
    try:
        return datetime.datetime.strptime(date_str, "%d.%m.%Y").date()
    except ValueError:
        # Если формат неверный, возвращаем ошибку 400 Bad Request
        raise HTTPException(status_code=400, detail="Неверный формат даты. Ожидается dd.mm.yyyy")


@app.get("/api/v1/available_start_times")
async def get_start_times(
    date_str: str = Query(..., alias="date"), 
    equipment: str | None = Query(None)
):
    """
    Эндпоинт для получения доступных времен начала записи.
    Возвращает JSON вида {"result": "10:00,10:30,14:00"}
    """
    date = parse_date_from_str(date_str)
    
    # 1. Получаем данные из NocoDB
    bookings = await nocodb_client.get_bookings_by_date(date)
    events = await nocodb_client.get_events_by_date(date)
    
    # 2. Рассчитываем таймлайн
    timeline = booking_logic.calculate_timeline_load(bookings, events)
    
    # 3. Получаем доступные слоты с учетом запрошенного оборудования
    available_times = booking_logic.get_available_start_times(timeline, equipment_required=equipment)
    
    # 4. Формируем и возвращаем ответ в виде json
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
    date = parse_date_from_str(date_str)
    
    # 1. Получаем данные из NocoDB
    bookings = await nocodb_client.get_bookings_by_date(date)
    events = await nocodb_client.get_events_by_date(date)
    
    # 2. Рассчитываем таймлайн
    timeline = booking_logic.calculate_timeline_load(bookings, events)
    
    # 3. Рассчитываем максимальную длительность
    max_duration = booking_logic.get_max_duration(start_time, timeline, equipment_required=equipment)

    # 4. Возвращаем результат в виде json
    return {"result": str(max_duration)}


@app.post("/api/v1/bookings", status_code=201) # status_code=201 означает "Created"
async def create_booking(booking_data: schemas.BookingCreate):
    """
    Эндпоинт для создания новой брони с финальной проверкой.
    """
    
    parsed_date = parse_date_from_str(booking_data.date)
    # --- Шаг 1: Повторная проверка доступности (защита от "гонки") ---
    
    # Получаем самые свежие данные из NocoDB
    latest_bookings = await nocodb_client.get_bookings_by_date(parsed_date)
    latest_events = await nocodb_client.get_events_by_date(parsed_date)
    
    # Рассчитываем актуальную загрузку
    timeline = booking_logic.calculate_timeline_load(latest_bookings, latest_events)
    
    # Рассчитываем, какая максимальная длительность доступна ПРЯМО СЕЙЧАС
    current_max_duration = booking_logic.get_max_duration(
        start_time_str=booking_data.start_time,
        timeline=timeline,
        equipment_required=booking_data.equipment
    )
    
    # Если пользователь хочет забронировать больше времени, чем сейчас доступно,
    # значит, слот уже заняли.
    if booking_data.duration_hours > current_max_duration:
        raise HTTPException(
            status_code=409, # 409 Conflict - подходящий код для этой ситуации
            detail="Извините, это время или его часть только что заняли. Пожалуйста, попробуйте выбрать время заново."
        )

    # --- Шаг 2: Подготовка данных для NocoDB ---
    
    # Рассчитываем время окончания
    start_dt = datetime.datetime.strptime(booking_data.start_time, "%H:%M")
    duration = timedelta(hours=booking_data.duration_hours)
    end_dt = start_dt + duration
    
    # Форматируем всё в строки, которые ожидает NocoDB
    data_for_nocodb = {
        "Telegram": booking_data.telegram,
        "Дата посещения": parsed_date.strftime("%Y-%m-%d"),
        "Время начала": start_dt.strftime("%H:%M:%S"),
        "Время конца": end_dt.strftime("%H:%M:%S"),
        "Оборудование": booking_data.equipment,
        "Что будет делать": booking_data.activity
    }

    # --- Шаг 3: Создание записи ---
    
    new_booking = await nocodb_client.create_booking(data_for_nocodb)
    
    if not new_booking:
        # Если по какой-то причине запись не создалась, возвращаем ошибку сервера
        raise HTTPException(
            status_code=500,
            detail="Не удалось создать запись в базе данных. Пожалуйста, свяжитесь с администратором."
        )
        
    # --- Шаг 4: Успешный ответ ---
    
    return {"status": "success", "booking_details": new_booking}