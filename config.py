from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Указываем, что переменные нужно искать в файле .env
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Перечисляем переменные, которые должны быть в .env
    NOCODB_URL: str
    NOCODB_API_TOKEN: str

# Создаем единый экземпляр настроек для всего приложения
settings = Settings()