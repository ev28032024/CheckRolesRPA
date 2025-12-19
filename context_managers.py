"""
Контекстные менеджеры для управления ресурсами
"""
import logging
from typing import Optional
from contextlib import contextmanager
from discord_bot import DiscordBot
from adspower import ADSpowerClient
from exceptions import BrowserError, ADSpowerError

logger = logging.getLogger(__name__)


@contextmanager
def browser_context(adspower_client: ADSpowerClient, serial_number: str):
    """
    Контекстный менеджер для управления браузером
    
    Args:
        adspower_client: Клиент ADSpower
        serial_number: Серийный номер профиля
    
    Yields:
        DiscordBot: Экземпляр Discord бота
    
    Raises:
        BrowserError: При ошибке работы с браузером
        ADSpowerError: При ошибке ADSpower
    """
    if not serial_number or not serial_number.strip():
        raise BrowserError("serial_number не может быть пустым")
    
    serial_number = serial_number.strip()
    discord_bot: Optional[DiscordBot] = None
    try:
        # Открываем браузер через ADSpower
        webdriver_url = adspower_client.open_browser(serial_number)
        if not webdriver_url:
            raise BrowserError(f"Не удалось получить WebSocket URL для профиля {serial_number}")
        
        # Инициализируем Discord бота
        discord_bot = DiscordBot(webdriver_url=webdriver_url)
        discord_bot.start_browser()
        
        yield discord_bot
        
    except (BrowserError, ADSpowerError):
        raise
    except Exception as e:
        logger.error(f"Неожиданная ошибка в browser_context: {e}")
        raise BrowserError(f"Ошибка работы с браузером: {e}") from e
    finally:
        # Очистка ресурсов
        if discord_bot:
            try:
                discord_bot.stop_browser()
            except Exception as e:
                logger.warning(f"Ошибка при закрытии браузера Discord: {e}")
        
        # Закрываем браузер в ADSpower
        if serial_number:
            try:
                adspower_client.close_browser(serial_number)
            except Exception as e:
                logger.warning(f"Ошибка при закрытии браузера ADSpower: {e}")

