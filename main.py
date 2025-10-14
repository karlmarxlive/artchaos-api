from fastapi import FastAPI
from config import settings  # Импортируем наши настройки

# Создаем экземпляр FastAPI
app = FastAPI()

# Создаем корневой эндпоинт для проверки
@app.get("/")
def read_root():
    # Эта строка нужна просто для проверки в терминале, что настройки подгрузились
    print("NocoDB URL из конфига:", settings.NOCODB_URL) 
    return {"message": "Привет! Сервер для бота запущен."}

# Здесь в будущем появятся другие эндпоинты
# GET /api/v1/available_start_times
# GET /api/v1/check_duration
# POST /api/v1/bookings