import httpx
import datetime
from urllib.parse import quote

from config import settings

# --- КОНСТАНТЫ: ID ТАБЛИЦ В NOCODB ---
BOOKINGS_TABLE_ID = "mgaqhk43i310jv7"
EVENTS_TABLE_ID = "m3itfdcts4vcet8" 

# --- Константы и базовые настройки ---
BASE_URL = f"{settings.NOCODB_URL}/api/v2/tables"
HEADERS = {
    "xc-token": settings.NOCODB_API_TOKEN
}

# --- Функции для получения данных из NocoDB ---

async def get_bookings_by_date(date: datetime.date) -> list:
    """Получает все бронирования (Bookings) на указанную дату."""
    
    date_field_name = "Дата посещения"
    date_str = date.strftime("%Y-%m-%d")
    filter_query = quote(f"({date_field_name},eq,{date_str})")
    
    # Используем константу с ID таблицы
    request_url = f"{BASE_URL}/{BOOKINGS_TABLE_ID}/records?where={filter_query}"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(request_url, headers=HEADERS)
            response.raise_for_status() 
            return response.json().get("list", [])
        except httpx.HTTPStatusError as e:
            print(f"Ошибка при запросе к NocoDB (Bookings): {e}")
            return []

async def get_events_by_date(date: datetime.date) -> list:
    """Получает все мероприятия (Events), которые блокируют мастерскую на указанную дату."""
    
    date_field_name = "Дата"
    blocking_field_name = "Занять мастерскую?"
    date_str = date.strftime("%Y-%m-%d")
    filter_query = quote(f"({date_field_name},eq,{date_str})and({blocking_field_name},is,true)")
    
    # Используем константу с ID таблицы
    request_url = f"{BASE_URL}/{EVENTS_TABLE_ID}/records?where={filter_query}"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(request_url, headers=HEADERS)
            response.raise_for_status()
            return response.json().get("list", [])
        except httpx.HTTPStatusError as e:
            print(f"Ошибка при запросе к NocoDB (Events): {e}")
            return []

async def create_booking(booking_data: dict) -> dict | None:
    """Создает новую запись в таблице Bookings."""
    
    # Используем константу с ID таблицы
    request_url = f"{BASE_URL}/{BOOKINGS_TABLE_ID}/records"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(request_url, headers=HEADERS, json=booking_data)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            print(f"Ошибка при создании записи в NocoDB: {e}")
            print(f"Тело ответа: {e.response.text}")
            return None