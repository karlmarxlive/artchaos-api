import sys
import datetime
import logging
from fastapi import FastAPI, Query, HTTPException
from starlette.responses import Response
from datetime import timedelta 

import nocodb_client
import booking_logic
import schemas
import firing_logic

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

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
    Эндпоинт для создания новой брони.
    """
    
    logger.info(f"🚀 НАЧАЛО СОЗДАНИЯ БРОНИ. Telegram ID: {booking_data.telegram_id}. Данные: {booking_data.model_dump()}")

    try:
        parsed_date = parse_date_from_str(booking_data.date)
    except Exception as e:
        err_msg = f"Ошибка формата даты: {booking_data.date}"
        logger.error(f"⚠️ Ошибка парсинга даты: {e} | {err_msg}")
        return {"status": "error", "result": "Неверный формат даты. Попробуй ещё раз или напиши @egor_savenko."}
    
    # Проверка на дубли
    existing_bookings = await nocodb_client.get_all_bookings_by_telegram_id(booking_data.telegram_id)
    start_dt_check = datetime.datetime.strptime(booking_data.start_time, "%H:%M").time()
    
    for b in existing_bookings:
        if (b["Дата посещения"] == booking_data.date and 
            b["Время начала"][:5] == booking_data.start_time):
            
            logger.warning(f"⚠️ ДУБЛЬ ЗАПРОСА. Бронь на {booking_data.date} {booking_data.start_time} уже существует для этого юзера.")
            return {"status": "error", "result": "Ты уже записан на это время! Возможно, это произошло случайно. Лучше проверь свои записи."}
    
    logger.info("🔍 Проверяем доступность слотов...")
    
    latest_bookings = await nocodb_client.get_bookings_by_date(booking_data.date)
    latest_events = await nocodb_client.get_events_by_date(booking_data.date)
    
    timeline = booking_logic.calculate_timeline_load(latest_bookings, latest_events)
    
    current_max_duration = booking_logic.get_max_duration(
        start_time_str=booking_data.start_time,
        timeline=timeline,
        equipment_required=booking_data.equipment
    )
    
    logger.info(f"⏱ Доступная длительность: {current_max_duration} ч. Запрошено: {booking_data.duration_hours} ч.")
    
    if booking_data.duration_hours > current_max_duration:
        logger.warning(f"⛔️ ОТКАЗ: Нет места. Доступно {current_max_duration}, надо {booking_data.duration_hours}")
        return {"status": "error", "result": "Это время или его часть только что заняли 😕."}
    
    start_dt = datetime.datetime.strptime(booking_data.start_time, "%H:%M")
    duration = timedelta(hours=booking_data.duration_hours)
    end_dt = start_dt + duration
    end_time_str = end_dt.strftime("%H:%M")
    
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
    
    logger.info(f"📤 Отправляем запрос в NocoDB: {data_for_nocodb}")
    
    new_booking = await nocodb_client.create_booking(data_for_nocodb)
    
    if not new_booking:
        logger.error("❌ NocoDB вернула пустой ответ или ошибку.")
        return {"status": "error", "result": "Техническая ошибка сервера. Попробуй позже или напиши @egor_savenko."}
    
    logger.info(f"✅ Бронь успешно создана! ID: {new_booking.get('Id')}")    
    
    return {
            "status": "success", 
            "result": end_time_str,
            "booking_id": new_booking.get('Id')
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

    future_bookings.sort(key=lambda b: (
        datetime.datetime.strptime(b["Дата посещения"], "%d.%m.%Y"),
        datetime.datetime.strptime(b["Время начала"], "%H:%M:%S")
    ))

    if not future_bookings:
        return {"result": "У тебя пока нет записей.\nХочешь записаться? 👇"}

    # --- Получаем мероприятия, проверим пересечения ниже ---
    unique_dates = {b["Дата посещения"] for b in future_bookings}
    events_map = {} 
    
    for date_str in unique_dates:
        events = await nocodb_client.get_events_by_date(date_str)
        if events:
            events_map[date_str] = events
    
    # --- Форматирование списка ---
    formatted_lines = ["Твои записи:"]
    booking_map = {} 

    for i, booking in enumerate(future_bookings, 1):
        start_time_short = booking['Время начала'][:5]
        end_time_short = booking["Время конца"][:5]
        line = f"{i}. {booking['Дата посещения']}: {start_time_short} — {end_time_short}"
        
        if booking.get("Оборудование"):
            line += f" (📍 {booking['Оборудование']})"
            
        activity_description = booking.get("Что будет делать")
        if activity_description:
            line += f"\n► {activity_description}"
            
        # --- Проверка пересечений ---
        date_key = booking["Дата посещения"]
        if date_key in events_map:
            b_start = datetime.datetime.strptime(booking["Время начала"], "%H:%M:%S").time()
            b_end = datetime.datetime.strptime(booking["Время конца"], "%H:%M:%S").time()
            
            for event in events_map[date_key]:
                e_start = datetime.datetime.strptime(event["Начало"], "%H:%M:%S").time()
                e_end = datetime.datetime.strptime(event["Конец"], "%H:%M:%S").time()
                                
                if b_start < e_end and b_end > e_start:
                    event_name = event.get("Название", "Мероприятие")
                    line += f"\n⚠️ Пересекается с: {event_name}"
                    break 
            
        formatted_lines.append(line)
        booking_map[str(i)] = booking['Id']

    USER_BOOKING_CACHE[telegram_id] = {
        "map": booking_map,
        "timestamp": datetime.datetime.now()
    }

    final_text = "\n\n".join(formatted_lines)
    return {"result": final_text}


@app.get("/api/v1/daily_bookings")
async def get_daily_bookings(date_str: str = Query(..., alias="date")):
    """
    Возвращает список всех броней на конкретную дату.
    """
    try:
        parse_date_from_str(date_str)
    except Exception:
         return {"result": "Неверный формат даты. Пожалуйста, попробуй ещё раз или напиши @egor_savenko"}

    bookings = await nocodb_client.get_bookings_by_date(date_str)

    if not bookings:
        return {"result": f"Ой, кажется, ты будешь первым :)"}

    bookings.sort(key=lambda b: b["Время начала"])
    
    formatted_lines = []

    for i, booking in enumerate(bookings, 1):
        name = booking.get("Telegram", "Гость")
        
        start_time = booking["Время начала"][:5]
        end_time = booking["Время конца"][:5]

        line = f"{i}. @{name}: {start_time} — {end_time}"

        if booking.get("Оборудование"):
            line += f" (📍 {booking['Оборудование']})"

        activity_description = booking.get("Что будет делать")
        if activity_description:
            line += f"\n► {activity_description}"

        formatted_lines.append(line)

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
        
        
@app.post("/api/v1/calculate_firing_cost", status_code=200)
async def calculate_firing_cost(data: schemas.FiringCalculationRequest):
    """
    Рассчитывает стоимость обжига с учетом клубной карты и конкурсов.
    """
    logger.info(f"🔥 РАСЧЕТ ОБЖИГА. ID: {data.telegram_id}. {data.quantity} шт, {data.size}, {data.firing_type}")

    item_base_cost = firing_logic.calculate_base_item_cost(
        data.size, data.firing_type, data.glaze_type
    )

    if item_base_cost == -1:
        logger.error(f"❌ Неверные параметры обжига: {data.size}, {data.firing_type}")
        return {"result": "Ошибка: Неверно указан размер или тип обжига."}

    total_cost = item_base_cost * data.quantity
    logger.info(f"💰 Базовая стоимость: {total_cost} руб.")

    is_client = await nocodb_client.check_client_exists(data.telegram_id)
    
    if not is_client:
        logger.info("👤 Пользователь не найден в Clients. Наценка +25%.")
        total_cost = total_cost * 1.25
    else:
        logger.info("👤 Пользователь найден в Clients. Цена стандартная.")

    is_contestant = await nocodb_client.check_contest_participant(data.telegram_id)
    
    if is_contestant:
        logger.info("🏆 Участник конкурса! Скидка -15%.")
        total_cost = total_cost * 0.85

    final_price = round(total_cost)

    logger.info(f"✅ Итоговая цена: {final_price}")

    return {"result": final_price}