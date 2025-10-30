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
    bookings = await nocodb_client.get_bookings_by_date(date_str)
    events = await nocodb_client.get_events_by_date(date_str)
    
    # 2. Рассчитываем таймлайн
    timeline = booking_logic.calculate_timeline_load(bookings, events)
    
    # 3. Получаем доступные слоты с учетом запрошенного оборудования
    available_times = booking_logic.get_available_start_times(timeline, date, equipment_required=equipment)
    
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
    parse_date_from_str(date_str)
    
    # 1. Получаем данные из NocoDB
    bookings = await nocodb_client.get_bookings_by_date(date_str)
    events = await nocodb_client.get_events_by_date(date_str)
    
    # 2. Рассчитываем таймлайн
    timeline = booking_logic.calculate_timeline_load(bookings, events)
    
    # 3. Рассчитываем максимальную длительность
    max_duration = booking_logic.get_max_duration(start_time, timeline, equipment_required=equipment)

    # 4. Возвращаем результат в виде json
    return {"result": max_duration}


@app.post("/api/v1/bookings", status_code=201) # status_code=201 означает "Created"
async def create_booking(booking_data: schemas.BookingCreate):
    """
    Эндпоинт для создания новой брони с финальной проверкой.
    """
    
    parse_date_from_str(booking_data.date)
    # --- Шаг 1: Повторная проверка доступности (защита от "гонки") ---
    
    # Получаем самые свежие данные из NocoDB
    latest_bookings = await nocodb_client.get_bookings_by_date(booking_data.date)
    latest_events = await nocodb_client.get_events_by_date(booking_data.date)
    
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
        "Дата посещения": booking_data.date,
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
    
    return {"status": "success", 
            "booking_details": new_booking,
            "end_time": end_dt.strftime("%H:%M")
            }
    
    
@app.get("/api/v1/my_bookings")
async def get_my_bookings(username: str):
    """
    Находит будущие брони пользователя, форматирует их в красивую строку
    и кэширует ID броней для последующей отмены.
    """
    all_bookings = await nocodb_client.get_all_bookings_by_username(username)
    
    # --- Фильтрация и сортировка ---
    future_bookings = []
    now_aware = datetime.datetime.now(booking_logic.WORKSHOP_TIMEZONE)

    for booking in all_bookings:
        try:
            # Собираем дату и время брони в один объект для сравнения
            booking_date = datetime.datetime.strptime(booking["Дата посещения"], "%d.%m.%Y").date()
            booking_time = datetime.datetime.strptime(booking["Время начала"], "%H:%M:%S").time()
            booking_datetime = datetime.datetime.combine(booking_date, booking_time)
            
            # Делаем объект "осведомленным" о часовом поясе для корректного сравнения
            booking_datetime_aware = booking_datetime.replace(tzinfo=booking_logic.WORKSHOP_TIMEZONE)

            if booking_datetime_aware > now_aware:
                future_bookings.append(booking)
        except (ValueError, KeyError):
            # Пропускаем записи с некорректным форматом даты/времени, если такие есть
            continue

    # Сортируем от ближайшей к самой дальней
    future_bookings.sort(key=lambda b: (
        datetime.datetime.strptime(b["Дата посещения"], "%d.%m.%Y"),
        datetime.datetime.strptime(b["Время начала"], "%H:%M:%S")
    ))

    # --- Форматирование ответа и создание кэша ---
    if not future_bookings:
        no_bookings_text = "У тебя пока нет записей.\nХочешь записаться? 👇"
        return {"result": no_bookings_text}

    formatted_lines = ["Твои записи: \n"]
    booking_map = {} # Карта для кэша: "1" -> "recAbc123"

    for i, booking in enumerate(future_bookings, 1):
        # Форматируем время начала, убирая секунды
        start_time_short = booking['Время начала'][:5]
        line = f"{i}. 📆 {booking['Дата посещения']} в {start_time_short}"
        
        # Добавляем информацию об оборудовании, если она есть
        if booking.get("Оборудование"):
            line += f" (📍 {booking['Оборудование']})"
            
        activity_description = booking.get("Что будет делать")
        if activity_description:
            # Добавляем описание с новой строки с отступом и в курсиве
            line += f"\n  📝 {activity_description}"
            
        formatted_lines.append(line)
        booking_map[str(i)] = booking['Id']

    # Сохраняем карту в кэш
    USER_BOOKING_CACHE[username] = {
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
    username = cancel_data.username
    booking_number = cancel_data.booking_number
    
    # --- Сценарий: Кэш не найден или устарел ---
    cached_user_data = USER_BOOKING_CACHE.get(username)
    
    if not cached_user_data:
        return {
            "status": "error",
            "message": "Список записей устарел. Пожалуйста, открой 'Мои записи' и попробуй снова."
        }
    
    cache_age = datetime.datetime.now() - cached_user_data["timestamp"]
    if cache_age > timedelta(minutes=CACHE_LIFETIME_MINUTES):
        del USER_BOOKING_CACHE[username] # Чистим устаревший кэш
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
        del USER_BOOKING_CACHE[username]
        return {
            "status": "success",
            "message": "✅ Запись успешно отменена!"
        }
    else:
        return {
            "status": "error",
            "message": "Возникла проблема при отмене брони. Пожалуйста, свяжись с @egor_savenko"
        }