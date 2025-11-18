import httpx
import datetime
from urllib.parse import quote

from config import settings

# --- КОНСТАНТЫ: ID ТАБЛИЦ В NOCODB ---
BOOKINGS_TABLE_ID = "mgaqhk43i310jv7"
EVENTS_TABLE_ID = "m3itfdcts4vcet8" 
ABONEMENTS_TABLE_ID = "moy99x4xmd1oaxd"


# --- Константы и базовые настройки ---
BASE_URL = f"{settings.NOCODB_URL}/api/v2/tables"
HEADERS = {
    "xc-token": settings.NOCODB_API_TOKEN
}

# --- Функции для получения данных из NocoDB ---

async def get_all_bookings_by_username(username: str) -> list:
    """Получает ВСЕ бронирования для указанного username."""
    
    username_field_name = "Telegram"
    
    filter_query = quote(f"({username_field_name},eq,{username})")
    
    request_url = f"{BASE_URL}/{BOOKINGS_TABLE_ID}/records?where={filter_query}"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(request_url, headers=HEADERS)
            response.raise_for_status() 
            return response.json().get("list", [])
        except httpx.HTTPStatusError as e:
            print(f"Ошибка при запросе к NocoDB (all bookings by username): {e}")
            return []
        
async def get_all_bookings_by_telegram_id(telegram_id: str) -> list:
    """Получает ВСЕ бронирования для указанного Telegram ID."""
    
    id_field_name = "Telegram ID"
    
    filter_query = quote(f"({id_field_name},eq,{telegram_id})")
    
    request_url = f"{BASE_URL}/{BOOKINGS_TABLE_ID}/records?where={filter_query}"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(request_url, headers=HEADERS)
            response.raise_for_status() 
            return response.json().get("list", [])
        except httpx.HTTPStatusError as e:
            print(f"Ошибка при запросе к NocoDB (all bookings by telegram_id): {e}")
            return []

async def get_bookings_by_date(date_str: str) -> list:
    """Получает все бронирования (Bookings) на указанную дату (поле — строка)."""
    
    date_field_name = "Дата посещения"
    # date_str = date.strftime("%Y-%m-%d")
    filter_query = quote(f"({date_field_name},eq,{date_str})")
    
    request_url = f"{BASE_URL}/{BOOKINGS_TABLE_ID}/records?where={filter_query}"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(request_url, headers=HEADERS)
            response.raise_for_status() 
            return response.json().get("list", [])
        except httpx.HTTPStatusError as e:
            print(f"Ошибка при запросе к NocoDB (Bookings): {e}")
            return []

async def get_events_by_date(date_str: str) -> list:
    """Получает все мероприятия (Events), которые блокируют мастерскую на указанную дату."""
    
    date_field_name = "Дата"
    blocking_field_name = "Занять мастерскую?"
    # date_str = date.strftime("%Y-%m-%d")
    
    filter_query = quote(f"({date_field_name},eq,{date_str})~and({blocking_field_name},is,true)")
    
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
        
        
async def delete_booking_by_id(booking_id: str) -> bool:
    """Удаляет запись из Bookings по ее уникальному ID."""
    
    request_url = f"{BASE_URL}/{BOOKINGS_TABLE_ID}/records"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.request("DELETE", request_url, headers=HEADERS, json={"Id": booking_id})
            
            response.raise_for_status()
            
            return True
        except httpx.HTTPStatusError as e:
            print(f"Ошибка при удалении записи {booking_id} из NocoDB: {e}")
            print(f"Тело ответа: {e.response.text}")
            return False
        except Exception as e:
            print(f"Неизвестная ошибка при удалении: {e}")
            return False
        

async def get_abonement_by_telegram_id(telegram_id: str) -> dict | None:
    """
    Находит абонемент пользователя по его Telegram ID.
    Если найдено несколько - возвращает первый.
    """
    id_field_name = "Telegram ID"
    filter_query = quote(f"({id_field_name},eq,{telegram_id})")
    
    request_url = f"{BASE_URL}/{ABONEMENTS_TABLE_ID}/records?where={filter_query}"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(request_url, headers=HEADERS)
            response.raise_for_status()
            
            results = response.json().get("list", [])
            if results:
                return results[0]
            return None
        except httpx.HTTPStatusError as e:
            print(f"Ошибка при запросе к NocoDB (Abonements): {e}")
            return None