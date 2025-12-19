"""
Валидаторы для проекта
"""
from typing import Dict, List, Optional
from exceptions import ConfigurationError, CheckRolesError


def validate_profile_data(profile_data: Dict) -> None:
    """
    Валидация данных профиля
    
    Args:
        profile_data: Данные профиля
    
    Raises:
        CheckRolesError: Если данные невалидны
    """
    required_fields = ['serial_number', 'email', 'password']
    missing_fields = []
    
    for field in required_fields:
        value = profile_data.get(field)
        if not value or (isinstance(value, str) and not value.strip()):
            missing_fields.append(field)
    
    if missing_fields:
        raise CheckRolesError(f"Отсутствуют обязательные поля профиля: {', '.join(missing_fields)}")


def validate_username(username: str) -> str:
    """
    Валидация и нормализация username
    
    Args:
        username: Username для валидации
    
    Returns:
        Нормализованный username
    
    Raises:
        CheckRolesError: Если username невалиден
    """
    if not username or not username.strip():
        raise CheckRolesError("Username не может быть пустым")
    
    normalized = username.strip()
    # Проверка на минимальную длину (Discord username должен быть не менее 2 символов)
    if len(normalized) < 2:
        raise CheckRolesError("Username слишком короткий (минимум 2 символа)")
    
    return normalized


def validate_server_url(url: str) -> str:
    """
    Валидация URL сервера Discord
    
    Args:
        url: URL для валидации
    
    Returns:
        Валидированный URL
    
    Raises:
        CheckRolesError: Если URL невалиден
    """
    if not url or not url.strip():
        raise CheckRolesError("URL сервера не может быть пустым")
    
    url = url.strip()
    if not url.startswith('http://') and not url.startswith('https://'):
        raise CheckRolesError(f"Некорректный формат URL: {url}")
    
    if 'discord.com' not in url and 'discordapp.com' not in url:
        raise CheckRolesError(f"URL должен быть Discord сервера: {url}")
    
    return url


def validate_config() -> None:
    """
    Валидация конфигурации
    
    Raises:
        ConfigurationError: Если конфигурация невалидна
    """
    import config
    from pathlib import Path
    
    if not config.GOOGLE_SHEETS_ID:
        raise ConfigurationError("GOOGLE_SHEETS_ID не установлен в конфигурации")
    
    if not config.GOOGLE_CREDENTIALS_FILE:
        raise ConfigurationError("GOOGLE_CREDENTIALS_FILE не установлен в конфигурации")
    
    # Проверяем существование файла credentials
    credentials_path = Path(config.GOOGLE_CREDENTIALS_FILE)
    if not credentials_path.exists():
        raise ConfigurationError(f"Файл credentials не найден: {config.GOOGLE_CREDENTIALS_FILE}")
    
    # Проверяем ADSpower API URL
    if not config.ADSPOWER_API_URL:
        raise ConfigurationError("ADSPOWER_API_URL не установлен в конфигурации")
    
    # Проверяем таймауты
    if config.DISCORD_TIMEOUT <= 0:
        raise ConfigurationError(f"DISCORD_TIMEOUT должен быть больше 0, получено: {config.DISCORD_TIMEOUT}")
    
    if config.DISCORD_WAIT_TIME < 0:
        raise ConfigurationError(f"DISCORD_WAIT_TIME не может быть отрицательным, получено: {config.DISCORD_WAIT_TIME}")

