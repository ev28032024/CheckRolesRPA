"""
Рабочий класс для многопоточного выполнения
"""
import logging
import threading
from typing import Dict, List, Optional, Any
from google_sheets import GoogleSheetsClient
from adspower import ADSpowerClient
from discord_bot import DiscordBot
from antidetect import AntiDetect
from utils import create_result_data, format_roles_for_save
from constants import MIN_DELAY_BETWEEN_CHECKS, MAX_DELAY_BETWEEN_CHECKS
from exceptions import BrowserError, AuthorizationError, GoogleSheetsError, ADSpowerError
from validators import validate_profile_data, validate_server_url
from context_managers import browser_context
import config

logger = logging.getLogger(__name__)


class CheckWorker:
    """
    Рабочий класс для проверки ролей в отдельном потоке
    
    Каждый экземпляр работает со своим профилем ADSpower и браузером
    """
    
    def __init__(
        self,
        profile_data: Dict,
        sheets_client: GoogleSheetsClient,
        adspower_client: ADSpowerClient
    ):
        """
        Инициализация рабочего
        
        Args:
            profile_data: Данные профиля для работы
            sheets_client: Клиент Google Sheets (потокобезопасный)
            adspower_client: Клиент ADSpower
        """
        self.profile_data = profile_data
        self.sheets_client = sheets_client
        self.adspower_client = adspower_client
        self.discord_bot: Optional[DiscordBot] = None
        
        # Валидация данных профиля
        validate_profile_data(profile_data)
        
        logger.info(f"Worker инициализирован для профиля {profile_data.get('serial_number', 'N/A')}")
    
    def process_server(
        self,
        server_url: str,
        usernames: List[str],
        check_profiles: List[Dict]
    ) -> Dict[str, Any]:
        """
        Обработка одного сервера
        
        Args:
            server_url: URL сервера для проверки
            usernames: Список username для проверки
            check_profiles: Список профилей для сохранения результатов
        
        Returns:
            Словарь с результатами обработки
        """
        thread_name = threading.current_thread().name
        
        try:
            # Валидация URL
            validated_url = validate_server_url(server_url)
            logger.info(f"[{thread_name}] Проверка ролей на сервере: {validated_url}")
            
            # Получаем serial_number
            serial_number = self.profile_data.get('serial_number', '').strip()
            if not serial_number:
                raise BrowserError("serial_number не указан в данных профиля")
            
            # Используем контекстный менеджер для управления браузером
            with browser_context(self.adspower_client, serial_number) as discord_bot:
                self.discord_bot = discord_bot
                
                # Авторизуемся
                if not self._authorize_discord():
                    raise AuthorizationError("Не удалось авторизоваться")
                
                # Проверяем роли
                results = self._check_roles_for_users(validated_url, usernames)
                
                # Сохраняем результаты
                self._save_results_to_sheet(results, check_profiles)
                
                return {
                    'server_url': validated_url,
                    'success': True,
                    'results_count': len(results),
                    'thread': thread_name
                }
        
        except (AuthorizationError, BrowserError, GoogleSheetsError, ADSpowerError) as e:
            logger.error(f"[{thread_name}] Ошибка при обработке сервера {server_url}: {e}")
            return {
                'server_url': server_url,
                'success': False,
                'error': str(e),
                'error_type': type(e).__name__,
                'thread': thread_name
            }
        except Exception as e:
            logger.error(f"[{thread_name}] Неожиданная ошибка при обработке сервера {server_url}: {e}")
            return {
                'server_url': server_url,
                'success': False,
                'error': str(e),
                'error_type': type(e).__name__,
                'thread': thread_name
            }
    
    def _authorize_discord(self) -> bool:
        """
        Авторизация в Discord
        
        Returns:
            True если успешно, False иначе
        
        Raises:
            BrowserError: Если discord_bot не инициализирован
            AuthorizationError: При ошибке авторизации
        """
        if not self.discord_bot:
            raise BrowserError("Discord бот не инициализирован")
        
        try:
            # Переходим на Discord
            self.discord_bot.navigate_to_discord()
            
            # Проверяем авторизацию
            if not self.discord_bot.check_authorization():
                logger.info("Требуется авторизация")
                email = self.profile_data.get('email', '')
                password = self.profile_data.get('password', '')
                
                if not self.discord_bot.login(email, password):
                    raise AuthorizationError("Не удалось авторизоваться")
            else:
                logger.info("Уже авторизован")
            
            # Проверяем username для консистентности с main.py
            expected_username = self.profile_data.get('username', '').strip()
            if expected_username:
                from utils import normalize_username
                current_username = self.discord_bot.get_current_username()
                if current_username:
                    if normalize_username(current_username) != normalize_username(expected_username):
                        logger.warning(f"Username не совпадает: ожидается {expected_username}, получено {current_username}")
                    else:
                        logger.info(f"Username совпадает: {expected_username}")
                else:
                    logger.warning("Не удалось получить текущий username для проверки")
            
            return True
        except (AuthorizationError, BrowserError):
            raise
        except Exception as e:
            logger.error(f"Ошибка авторизации в Discord: {e}")
            raise AuthorizationError(f"Ошибка авторизации: {e}") from e
    
    def _check_roles_for_users(self, server_url: str, usernames: List[str]) -> Dict[str, List[str]]:
        """
        Проверка ролей для списка пользователей
        
        Args:
            server_url: Ссылка на Discord сервер
            usernames: Список username для проверки
        
        Returns:
            Словарь {username: [список ролей]}
        """
        if not self.discord_bot:
            raise BrowserError("Discord бот не инициализирован")
        
        if not server_url or not server_url.strip():
            raise BrowserError("URL сервера не может быть пустым")
        
        if not usernames:
            logger.warning("Список пользователей для проверки пуст")
            return {}
        
        results = {}
        
        try:
            # Переходим на сервер
            self.discord_bot.navigate_to_server(server_url)
            AntiDetect.random_delay(MIN_DELAY_BETWEEN_CHECKS, MAX_DELAY_BETWEEN_CHECKS)
            
            # Проверяем каждого пользователя
            for username in usernames:
                if not username or not username.strip():
                    continue
                
                username = username.strip()
                logger.info(f"Проверка ролей для пользователя: {username}")
                
                try:
                    roles = self.discord_bot.get_user_roles(username)
                    results[username] = roles
                    logger.info(f"Найдено {len(roles)} ролей для {username}: {format_roles_for_save(roles)}")
                except BrowserError as e:
                    logger.error(f"Ошибка браузера при проверке ролей для {username}: {e}")
                    results[username] = []
                    # При критической ошибке браузера прекращаем проверку остальных пользователей
                    error_str = str(e).lower()
                    if any(keyword in error_str for keyword in ["не инициализирован", "закрыт", "disconnected", "connection"]):
                        logger.error("Критическая ошибка браузера, прекращаем проверку")
                        break
                except Exception as e:
                    logger.error(f"Ошибка проверки ролей для {username}: {e}")
                    results[username] = []
                
                # Задержка между проверками
                AntiDetect.random_delay(MIN_DELAY_BETWEEN_CHECKS, MAX_DELAY_BETWEEN_CHECKS)
        
        except BrowserError as e:
            logger.error(f"Критическая ошибка браузера при проверке ролей: {e}")
            # Не поднимаем исключение, возвращаем частичные результаты
        except Exception as e:
            logger.error(f"Ошибка проверки ролей: {e}")
        
        return results
    
    def _save_results_to_sheet(self, results: Dict[str, List[str]], check_profiles: List[Dict]) -> None:
        """
        Сохранение результатов проверки в таблицу (потокобезопасно)
        
        Args:
            results: Словарь {username: [список ролей]}
            check_profiles: Список профилей для сохранения
        """
        if not results or not isinstance(results, dict):
            logger.debug("Нет результатов для сохранения")
            return
        
        if not check_profiles:
            logger.warning("Список профилей для сохранения пуст")
            return
        
        # Получаем serial_number профиля, который выполнял проверку
        checker_serial_number = self.profile_data.get('serial_number', '').strip()
        
        saved_count = 0
        failed_count = 0
        skipped_count = 0
        
        for username, roles in results.items():
            if not username or not username.strip():
                skipped_count += 1
                continue
            
            username = username.strip()
            result_data = create_result_data(roles)
            
            # Находим соответствующий профиль для сохранения
            profile_to_save = next(
                (p for p in check_profiles if p.get('username', '').strip() == username),
                {'username': username}
            )
            
            # Используем serial_number профиля, который выполнял проверку
            profile_to_save['serial_number'] = checker_serial_number
            
            try:
                self.sheets_client.save_check_result(profile_to_save, result_data)
                saved_count += 1
                logger.debug(f"Результат сохранен для {username}: {len(roles)} ролей")
            except GoogleSheetsError as e:
                logger.error(f"Ошибка сохранения результата для {username}: {e}")
                failed_count += 1
                continue
            except Exception as e:
                logger.error(f"Неожиданная ошибка сохранения результата для {username}: {e}")
                failed_count += 1
                continue
        
        if saved_count > 0 or failed_count > 0 or skipped_count > 0:
            logger.info(f"Сохранено результатов: {saved_count}, ошибок: {failed_count}, пропущено: {skipped_count}")

