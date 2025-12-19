"""
Основной модуль чекера ролей Discord
"""
import logging
import sys
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import config
from google_sheets import GoogleSheetsClient
from adspower import ADSpowerClient
from discord_bot import DiscordBot
from antidetect import AntiDetect
from utils import create_result_data, format_roles_for_save, normalize_username
from constants import MIN_DELAY_BETWEEN_CHECKS, MAX_DELAY_BETWEEN_CHECKS
from exceptions import (
    CheckRolesError, BrowserError, AuthorizationError, 
    GoogleSheetsError, ADSpowerError, ConfigurationError
)
from validators import validate_profile_data, validate_config, validate_server_url
from context_managers import browser_context
from thread_manager import ThreadManager
from worker import CheckWorker

# Настройка логирования
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(config.LOG_FILE, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


class RolesChecker:
    """
    Основной класс для проверки ролей в Discord
    
    Управляет процессом проверки ролей пользователей на Discord серверах:
    - Инициализирует подключения к Google Sheets и ADSpower
    - Загружает данные профилей и списки для проверки
    - Выполняет авторизацию в Discord
    - Собирает роли пользователей
    - Сохраняет результаты в Google Sheets
    """
    
    def __init__(self):
        """
        Инициализация чекера
        
        Атрибуты инициализируются как None и заполняются при вызове initialize()
        """
        self.sheets_client: Optional[GoogleSheetsClient] = None
        self.adspower_client: Optional[ADSpowerClient] = None
        self.discord_bot: Optional[DiscordBot] = None
        self.thread_manager: Optional[ThreadManager] = None
        
        logger.info("Инициализация чекера ролей")
    
    def initialize(self):
        """
        Инициализация всех компонентов
        
        Raises:
            ConfigurationError: Если конфигурация невалидна
            GoogleSheetsError: При ошибке инициализации Google Sheets
            ADSpowerError: При ошибке инициализации ADSpower
            CheckRolesError: При других ошибках инициализации
        """
        try:
            # Валидация конфигурации
            validate_config()
            
            # Инициализация Google Sheets
            self.sheets_client = GoogleSheetsClient(config.GOOGLE_SHEETS_ID)
            logger.info("Google Sheets клиент инициализирован")
            
            # Инициализация ADSpower
            self.adspower_client = ADSpowerClient()
            logger.info("ADSpower клиент инициализирован")
            
            # Инициализация менеджера потоков (если включен многопоточный режим)
            if config.THREADING_ENABLED:
                self.thread_manager = ThreadManager(max_workers=config.THREADING_MAX_WORKERS)
                logger.info(f"Многопоточный режим включен: {config.THREADING_MAX_WORKERS} потоков")
            else:
                logger.info("Многопоточный режим отключен")
            
        except (GoogleSheetsError, ADSpowerError, ConfigurationError) as e:
            logger.error(f"Ошибка инициализации: {e}")
            raise
        except Exception as e:
            logger.error(f"Неожиданная ошибка инициализации: {e}")
            raise CheckRolesError(f"Ошибка инициализации: {e}") from e
    
    def get_profile_for_work(self) -> Dict:
        """
        Получение профиля для работы из таблицы ds_data
        
        Returns:
            Данные профиля
        """
        try:
            profile_data = self.sheets_client.get_profile_data()
            if not profile_data:
                raise CheckRolesError("Профиль для работы не найден в таблице ds_data")
            
            # Валидация данных профиля
            validate_profile_data(profile_data)
            
            logger.info(f"Профиль для работы: {profile_data.get('serial_number', 'N/A')}")
            return profile_data
        except GoogleSheetsError:
            raise
        except Exception as e:
            logger.error(f"Ошибка получения профиля для работы: {e}")
            raise CheckRolesError(f"Не удалось получить профиль для работы: {e}") from e
    
    def verify_and_authorize(self, profile_data: Dict) -> bool:
        """
        Проверка и авторизация в Discord
        
        Args:
            profile_data: Данные профиля
        
        Returns:
            True если успешно, False иначе
        """
        try:
            # Валидация данных профиля
            validate_profile_data(profile_data)
            
            serial_number = profile_data.get('serial_number', '').strip()
            if not serial_number:
                raise BrowserError("serial_number не указан в данных профиля")
            
            # Открываем браузер через ADSpower
            webdriver_url = self.adspower_client.open_browser(serial_number)
            if not webdriver_url:
                raise BrowserError(f"Не удалось получить WebSocket URL для профиля {serial_number}")
            
            # Инициализируем Discord бота
            self.discord_bot = DiscordBot(webdriver_url=webdriver_url)
            self.discord_bot.start_browser()
            
            # Переходим на Discord
            self.discord_bot.navigate_to_discord()
            
            # Проверяем авторизацию
            if not self.discord_bot.check_authorization():
                logger.info("Требуется авторизация")
                # Получаем данные для авторизации из профиля
                email = profile_data.get('email', '')
                password = profile_data.get('password', '')
                
                if not self.discord_bot.login(email, password):
                    raise AuthorizationError("Не удалось авторизоваться")
            else:
                logger.info("Уже авторизован")
            
            # Проверяем username
            expected_username = profile_data.get('username', '').strip()
            if expected_username:
                current_username = self.discord_bot.get_current_username()
                if current_username:
                    if normalize_username(current_username) != normalize_username(expected_username):
                        logger.warning(f"Username не совпадает: ожидается {expected_username}, получено {current_username}")
                    else:
                        logger.info(f"Username совпадает: {expected_username}")
                else:
                    logger.warning("Не удалось получить текущий username для проверки")
            
            return True
        except Exception as e:
            logger.error(f"Ошибка проверки и авторизации: {e}")
            return False
    
    def check_roles_for_users(self, server_url: str, usernames: List[str]) -> Dict[str, List[str]]:
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
            # Не поднимаем исключение, возвращаем частичные результаты (если есть)
            # Это позволяет сохранить результаты для уже проверенных пользователей
        except Exception as e:
            logger.error(f"Ошибка проверки ролей: {e}")
        
        return results
    
    def process_check_list(self):
        """
        Обработка списка проверки из таблицы
        
        Поддерживает как однопоточный, так и многопоточный режимы
        """
        try:
            # Получаем данные для проверки
            server_urls, usernames, check_profiles = self._load_check_data()
            if not server_urls or not usernames:
                logger.warning("Нет данных для проверки")
                return
            
            logger.info(f"Найдено {len(usernames)} пользователей для проверки на {len(server_urls)} серверах")
            
            # Выбираем режим работы
            if config.THREADING_ENABLED and self.thread_manager:
                logger.info("Используется многопоточный режим")
                self._process_check_list_multithreaded(server_urls, usernames, check_profiles)
            else:
                logger.info("Используется однопоточный режим")
                self._process_check_list_singlethreaded(server_urls, usernames, check_profiles)
        except (AuthorizationError, BrowserError, GoogleSheetsError) as e:
            logger.error(f"Ошибка обработки списка проверки: {e}")
            raise
        except Exception as e:
            logger.error(f"Неожиданная ошибка обработки списка проверки: {e}")
            raise CheckRolesError(f"Ошибка обработки списка проверки: {e}") from e
    
    def _load_check_data(self) -> Tuple[List[str], List[str], List[Dict]]:
        """
        Загрузка данных для проверки из Google Sheets
        
        Никнеймы для проверки берутся из листа ds_data.
        Лист чек-отработка используется только для записи результатов.
        
        Returns:
            Кортеж (server_urls, usernames, check_profiles)
        
        Raises:
            GoogleSheetsError: При ошибке работы с Google Sheets
        """
        try:
            # Получаем ссылки на серверы
            server_urls = self.sheets_client.get_discord_links()
            if not server_urls:
                logger.warning("Ссылки на серверы не найдены")
                return [], [], []
            
            # Получаем список никнеймов для проверки из ds_data
            try:
                usernames = self.sheets_client.get_usernames_from_ds_data()
            except GoogleSheetsError as e:
                logger.error(f"Ошибка получения никнеймов из ds_data: {e}")
                raise
            
            if not usernames:
                logger.warning("Никнеймы для проверки не найдены в ds_data")
                return server_urls, [], []
            
            # Получаем профили из ds_data для сохранения результатов
            # (содержат username и serial_number для записи в чек-отработка)
            try:
                check_profiles = self.sheets_client.get_check_profiles_from_ds_data()
            except GoogleSheetsError as e:
                logger.error(f"Ошибка получения профилей из ds_data для сохранения: {e}")
                # Продолжаем работу даже если не удалось получить профили для сохранения
                # Создаем минимальные профили только с username
                check_profiles = [{'username': username} for username in usernames]
            
            logger.info(f"Найдено {len(usernames)} никнеймов для проверки из ds_data")
            return server_urls, usernames, check_profiles
        
        except GoogleSheetsError:
            # Пробрасываем GoogleSheetsError как есть
            raise
        except Exception as e:
            logger.error(f"Неожиданная ошибка загрузки данных для проверки: {e}")
            raise CheckRolesError(f"Ошибка загрузки данных для проверки: {e}") from e
    
    def _process_check_list_singlethreaded(
        self,
        server_urls: List[str],
        usernames: List[str],
        check_profiles: List[Dict]
    ):
        """
        Однопоточная обработка списка проверки
        
        Args:
            server_urls: Список URL серверов
            usernames: Список username
            check_profiles: Список профилей для сохранения
        """
        profile_data = None
        try:
            # Получаем профиль для работы
            profile_data = self.get_profile_for_work()
            
            # Проверяем и авторизуемся
            if not self.verify_and_authorize(profile_data):
                raise AuthorizationError("Не удалось авторизоваться")
            
            # Проверяем роли на каждом сервере
            self._process_servers(server_urls, usernames, check_profiles, profile_data)
        
        finally:
            self._cleanup_resources(profile_data)
    
    def _process_check_list_multithreaded(
        self,
        server_urls: List[str],
        usernames: List[str],
        check_profiles: List[Dict]
    ):
        """
        Многопоточная обработка списка проверки
        
        Args:
            server_urls: Список URL серверов
            usernames: Список username
            check_profiles: Список профилей для сохранения
        
        Raises:
            CheckRolesError: Если thread_manager не инициализирован или нет профилей
        """
        if not self.thread_manager:
            raise CheckRolesError("ThreadManager не инициализирован для многопоточного режима")
        
        # Получаем профили для работы (нужно несколько профилей для потоков)
        try:
            profiles_data = self._get_profiles_for_workers()
        except (CheckRolesError, GoogleSheetsError) as e:
            logger.error(f"Ошибка получения профилей для многопоточного режима: {e}")
            logger.warning("Переключаемся на однопоточный режим")
            self._process_check_list_singlethreaded(server_urls, usernames, check_profiles)
            return
        
        if not profiles_data:
            logger.warning("Профили для работы не найдены, переключаемся на однопоточный режим")
            self._process_check_list_singlethreaded(server_urls, usernames, check_profiles)
            return
        
        # Ограничиваем количество потоков количеством доступных профилей
        original_max_workers = self.thread_manager.max_workers
        actual_workers = min(len(profiles_data), self.thread_manager.max_workers)
        max_workers_modified = False
        
        if actual_workers < self.thread_manager.max_workers:
            logger.warning(
                f"Найдено только {len(profiles_data)} профилей, "
                f"но запрошено {self.thread_manager.max_workers} потоков. "
                f"Будет использовано {actual_workers} потоков"
            )
            # Временно обновляем max_workers для ThreadPoolExecutor
            self.thread_manager.max_workers = actual_workers
            max_workers_modified = True
        
        try:
            # Распределяем серверы между потоками
            tasks = []
            task_index = 0  # Отдельный счетчик для задач (не зависит от индекса в server_urls)
            
            for i, server_url in enumerate(server_urls):
                if not server_url or not server_url.strip():
                    logger.warning(f"Пропущен пустой URL сервера на позиции {i}")
                    continue
                
                # Используем профиль по кругу для равномерного распределения нагрузки
                profile_data = profiles_data[task_index % len(profiles_data)]
                tasks.append({
                    'server_url': server_url.strip(),
                    'profile_data': profile_data,
                    'usernames': usernames,
                    'check_profiles': check_profiles
                })
                task_index += 1
            
            if not tasks:
                logger.warning("Нет валидных задач для многопоточного выполнения")
                return
            
            # Создаем функцию-обработчик для потоков
            def worker_func(task: Dict) -> Dict:
                """Функция-обработчик для потока"""
                worker = CheckWorker(
                    profile_data=task['profile_data'],
                    sheets_client=self.sheets_client,
                    adspower_client=self.adspower_client
                )
                return worker.process_server(
                    server_url=task['server_url'],
                    usernames=task['usernames'],
                    check_profiles=task['check_profiles']
                )
            
            # Запускаем параллельное выполнение
            results = self.thread_manager.execute_parallel(
                tasks=tasks,
                worker_func=worker_func,
                task_name="серверов"
            )
            
            # Анализируем результаты
            successful = sum(1 for r in results if isinstance(r, dict) and r.get('success', False))
            failed = len(results) - successful
            
            logger.info(f"Многопоточная обработка завершена: успешно {successful}, ошибок {failed}")
        finally:
            # Восстанавливаем оригинальное значение max_workers, если оно было изменено
            if max_workers_modified:
                self.thread_manager.max_workers = original_max_workers
    
    def _get_profiles_for_workers(self) -> List[Dict]:
        """
        Получение профилей для работы в многопоточном режиме
        
        Returns:
            Список профилей (каждый поток использует свой профиль)
        
        Raises:
            GoogleSheetsError: При ошибке чтения из Google Sheets
        """
        try:
            # Читаем все строки из листа ds_data (кроме заголовка)
            data = self.sheets_client.read_range(config.GOOGLE_SHEET_DS_DATA)
            if not data or len(data) < 2:
                logger.warning(f"Лист {config.GOOGLE_SHEET_DS_DATA} пуст или содержит только заголовки")
                return []
            
            headers = data[0]
            profiles = []
            
            # Парсим все строки с профилями
            for row_index, row in enumerate(data[1:], start=2):  # start=2 потому что первая строка - заголовок
                if not row or not any(row):
                    continue
                
                try:
                    profile = self.sheets_client.parse_row_to_dict(headers, row)
                    
                    # Валидируем профиль
                    try:
                        validate_profile_data(profile)
                        profiles.append(profile)
                    except CheckRolesError as e:
                        logger.warning(f"Профиль в строке {row_index} пропущен из-за ошибки валидации: {e}")
                        continue
                except Exception as e:
                    logger.warning(f"Ошибка парсинга профиля в строке {row_index}: {e}")
                    continue
            
            if not profiles:
                logger.warning("Не найдено ни одного валидного профиля для многопоточного режима")
            else:
                logger.info(f"Найдено {len(profiles)} валидных профилей для многопоточного режима")
            
            return profiles
        
        except GoogleSheetsError:
            raise
        except Exception as e:
            logger.error(f"Ошибка получения профилей для потоков: {e}")
            raise CheckRolesError(f"Не удалось получить профили для потоков: {e}") from e
    
    def _cleanup_resources(self, profile_data: Optional[Dict] = None) -> None:
        """
        Очистка ресурсов (браузер, ADSpower)
        
        Args:
            profile_data: Данные профиля для закрытия браузера ADSpower
        
        Note:
            Этот метод используется только для обратной совместимости.
            Рекомендуется использовать browser_context для автоматической очистки.
        """
        # Закрываем браузер Discord
        if self.discord_bot:
            try:
                self.discord_bot.stop_browser()
            except Exception as e:
                logger.warning(f"Ошибка при закрытии браузера Discord: {e}")
        
        # Закрываем браузер в ADSpower
        if self.adspower_client and profile_data:
            serial_number = profile_data.get('serial_number', '').strip()
            if serial_number:
                try:
                    self.adspower_client.close_browser(serial_number)
                except Exception as e:
                    logger.warning(f"Ошибка при закрытии браузера ADSpower: {e}")
    
    def _extract_usernames(self, check_profiles: List[Dict]) -> List[str]:
        """
        Извлечение username из списка профилей
        
        Args:
            check_profiles: Список профилей для проверки
        
        Returns:
            Список username
        """
        usernames = []
        for profile in check_profiles:
            username = profile.get('username', '').strip()
            if username:
                usernames.append(username)
        return usernames
    
    def _process_servers(self, server_urls: List[str], usernames: List[str], check_profiles: List[Dict], profile_data: Dict):
        """
        Обработка проверки ролей на всех серверах
        
        Args:
            server_urls: Список URL серверов для проверки
            usernames: Список username для проверки
            check_profiles: Список профилей для сохранения результатов
            profile_data: Данные профиля, который выполняет проверку (для serial_number)
        
        Raises:
            BrowserError: При критической ошибке браузера
        """
        if not self.discord_bot:
            raise BrowserError("Discord бот не инициализирован")
        
        if not server_urls:
            logger.warning("Список URL серверов пуст")
            return
        
        if not usernames:
            logger.warning("Список пользователей для проверки пуст")
            return
        
        processed_count = 0
        failed_count = 0
        
        for server_url in server_urls:
            if not server_url or not server_url.strip():
                logger.warning("Пропущен пустой URL сервера")
                continue
                
            try:
                # Валидация URL
                validated_url = validate_server_url(server_url)
                logger.info(f"Проверка ролей на сервере: {validated_url}")
                
                results = self.check_roles_for_users(validated_url, usernames)
                
                # Сохраняем результаты, даже если они пустые (для логирования)
                # check_roles_for_users всегда возвращает dict, никогда None
                self._save_results_to_sheet(results, check_profiles, profile_data)
                processed_count += 1
                    
            except BrowserError as e:
                logger.error(f"Критическая ошибка браузера при проверке сервера {server_url}: {e}")
                # При критической ошибке браузера прекращаем работу
                raise
            except CheckRolesError as e:
                logger.error(f"Ошибка валидации URL сервера {server_url}: {e}")
                failed_count += 1
                # Продолжаем работу с другими серверами
                continue
            except Exception as e:
                logger.error(f"Неожиданная ошибка при проверке сервера {server_url}: {e}")
                failed_count += 1
                # Продолжаем работу с другими серверами
                continue
        
        logger.info(f"Обработка серверов завершена: обработано {processed_count}, ошибок {failed_count}")
    
    def _save_results_to_sheet(self, results: Dict[str, List[str]], check_profiles: List[Dict], profile_data: Dict):
        """
        Сохранение результатов проверки в таблицу
        
        Args:
            results: Словарь {username: [список ролей]}
            check_profiles: Список профилей для сохранения
            profile_data: Данные профиля, который выполнял проверку (для serial_number)
        """
        if not results or not isinstance(results, dict):
            logger.debug("Нет результатов для сохранения")
            return
        
        if not check_profiles:
            logger.warning("Список профилей для сохранения пуст")
            return
        
        # Получаем serial_number профиля, который выполнял проверку
        checker_serial_number = profile_data.get('serial_number', '').strip() if profile_data else ''
        
        saved_count = 0
        failed_count = 0
        skipped_count = 0
        
        for username, roles in results.items():
            if not username or not username.strip():
                skipped_count += 1
                continue
            
            username = username.strip()
            
            # Создаем данные результата
            result_data = create_result_data(roles)
            
            # Находим соответствующий профиль для сохранения
            profile_to_save = self._find_profile_for_username(check_profiles, username)
            
            # Используем serial_number профиля, который выполнял проверку
            profile_to_save['serial_number'] = checker_serial_number
            
            try:
                self.sheets_client.save_check_result(profile_to_save, result_data)
                saved_count += 1
                logger.debug(f"Результат сохранен для {username}: {len(roles)} ролей")
            except GoogleSheetsError as e:
                logger.error(f"Ошибка сохранения результата для {username}: {e}")
                failed_count += 1
                # Продолжаем сохранение других результатов
                continue
            except Exception as e:
                logger.error(f"Неожиданная ошибка сохранения результата для {username}: {e}")
                failed_count += 1
                continue
        
        if saved_count > 0 or failed_count > 0 or skipped_count > 0:
            logger.info(f"Сохранено результатов: {saved_count}, ошибок: {failed_count}, пропущено: {skipped_count}")
    
    def _find_profile_for_username(self, check_profiles: List[Dict], username: str) -> Dict:
        """
        Поиск профиля по username
        
        Args:
            check_profiles: Список профилей
            username: Username для поиска
        
        Returns:
            Профиль или словарь с username
        """
        return next(
            (p for p in check_profiles if p.get('username', '').strip() == username),
            {'username': username}
        )
    
    def run(self):
        """Запуск чекера"""
        try:
            logger.info("Запуск чекера ролей Discord")
            self.initialize()
            self.process_check_list()
            logger.info("Чекер завершил работу")
        except CheckRolesError:
            raise
        except Exception as e:
            logger.error(f"Критическая ошибка: {e}")
            raise CheckRolesError(f"Критическая ошибка выполнения: {e}") from e


def main():
    """Главная функция"""
    checker = RolesChecker()
    try:
        checker.run()
    except KeyboardInterrupt:
        logger.info("Работа прервана пользователем")
    except Exception as e:
        logger.error(f"Ошибка выполнения: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

