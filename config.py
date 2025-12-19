"""
Конфигурационный файл для чекера ролей Discord
Читает настройки из config.yaml с поддержкой переменных окружения
"""
import os
import yaml
from pathlib import Path
from typing import Optional

# Путь к конфигурационному файлу
CONFIG_FILE = Path(__file__).parent / 'config.yaml'

# Кэш конфигурации (загружается один раз)
_config_cache: Optional[dict] = None


def load_config():
    """Загрузка конфигурации из YAML файла (с кэшированием)"""
    global _config_cache
    
    # Возвращаем кэшированную конфигурацию, если она уже загружена
    if _config_cache is not None:
        return _config_cache
    
    config = {}
    
    # Пытаемся загрузить из YAML файла
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f) or {}
        except Exception as e:
            import sys
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Ошибка загрузки config.yaml: {e}. Используются значения по умолчанию.")
            print(f"Предупреждение: Ошибка загрузки config.yaml: {e}. Используются значения по умолчанию.", file=sys.stderr)
    else:
        import sys
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Файл config.yaml не найден. Создайте его на основе config.example.yaml")
        print(f"Файл config.yaml не найден. Создайте его на основе config.example.yaml", file=sys.stderr)
    
    # Кэшируем результат
    _config_cache = config
    return config


def get_config_value(section: str, key: str, default, env_var: str = None):
    """
    Получение значения конфигурации с приоритетом:
    1. Переменная окружения (если указана)
    2. Значение из YAML файла
    3. Значение по умолчанию
    
    Args:
        section: Секция в YAML (например, 'google_sheets')
        key: Ключ в секции (например, 'sheets_id')
        default: Значение по умолчанию
        env_var: Имя переменной окружения (опционально)
    """
    # Сначала проверяем переменную окружения
    if env_var:
        env_value = os.getenv(env_var)
        if env_value:
            return env_value
    
    # Затем проверяем YAML файл (используем кэш)
    config = load_config()
    if section in config and isinstance(config[section], dict) and key in config[section]:
        return config[section][key]
    
    # Возвращаем значение по умолчанию
    return default


# Загружаем конфигурацию при импорте модуля
_config = load_config()

# Google Sheets настройки
GOOGLE_SHEETS_ID: Optional[str] = get_config_value(
    'google_sheets', 'sheets_id', '', 'GOOGLE_SHEETS_ID'
)
GOOGLE_CREDENTIALS_FILE: str = get_config_value(
    'google_sheets', 'credentials_file', 'credentials.json', 'GOOGLE_CREDENTIALS_FILE'
)
GOOGLE_SHEET_DS_DATA: str = get_config_value(
    'google_sheets', 'sheet_ds_data', 'ds_data', 'GOOGLE_SHEET_DS_DATA'
)
GOOGLE_SHEET_DS_LINK: str = get_config_value(
    'google_sheets', 'sheet_ds_link', 'ds_link', 'GOOGLE_SHEET_DS_LINK'
)
GOOGLE_SHEET_CHECK: str = get_config_value(
    'google_sheets', 'sheet_check', 'чек-отработка', 'GOOGLE_SHEET_CHECK'
)

# ADSpower API настройки
ADSPOWER_API_URL: str = get_config_value(
    'adspower', 'api_url', 'http://local.adspower.net:50325', 'ADSPOWER_API_URL'
)
ADSPOWER_API_KEY: Optional[str] = get_config_value(
    'adspower', 'api_key', '', 'ADSPOWER_API_KEY'
)

# Discord настройки
def _safe_int(value, default: int) -> int:
    """Безопасное преобразование в int с fallback на значение по умолчанию"""
    try:
        if isinstance(value, int):
            return value
        if isinstance(value, str):
            return int(value)
        return default
    except (ValueError, TypeError):
        return default

DISCORD_TIMEOUT: int = _safe_int(get_config_value(
    'discord', 'timeout', 30, None
), 30)
DISCORD_WAIT_TIME: int = _safe_int(get_config_value(
    'discord', 'wait_time', 3, None
), 3)

# Многопоточность
_threading_enabled = get_config_value('threading', 'enabled', False, 'THREADING_ENABLED')
if isinstance(_threading_enabled, bool):
    THREADING_ENABLED: bool = _threading_enabled
else:
    THREADING_ENABLED: bool = str(_threading_enabled).lower() in ('true', '1', 'yes', 'on')

THREADING_MAX_WORKERS: int = _safe_int(get_config_value(
    'threading', 'max_workers', 2, 'THREADING_MAX_WORKERS'
), 2)

# Логирование
LOG_LEVEL: str = get_config_value(
    'logging', 'level', 'INFO', 'LOG_LEVEL'
)
LOG_FILE: str = get_config_value(
    'logging', 'file', 'checker.log', None
)
