"""
Модуль для работы с Discord через браузер (patchright)
"""
import logging
import random
from typing import Dict, List, Optional
from patchright import sync_playwright
from patchright.sync_api import Page, Browser, BrowserContext
import config
from antidetect import AntiDetect
from discord_scripts import ROLES_COLLECTION_SCRIPT, AUTH_CHECK_SCRIPT, CHANNEL_ACCESS_SCRIPT
from discord_selectors import (
    AUTH_SELECTORS, LOGIN_FORM_SELECTORS, EMAIL_INPUT_SELECTORS,
    PASSWORD_INPUT_SELECTORS, LOGIN_BUTTON_SELECTORS, SEARCH_INPUT_SELECTORS,
    SEARCH_RESULT_SELECTORS, USERNAME_SELECTORS
)
from constants import (
    DEFAULT_PAGE_LOAD_TIMEOUT, AUTH_CHECK_TIMEOUT, ELEMENT_WAIT_TIMEOUT,
    MIN_DELAY_BEFORE_ACTION, MAX_DELAY_BEFORE_ACTION,
    MIN_DELAY_AFTER_ACTION, MAX_DELAY_AFTER_ACTION,
    MIN_DELAY_BEFORE_NAVIGATION, MAX_DELAY_BEFORE_NAVIGATION,
    MIN_DELAY_AFTER_NAVIGATION, MAX_DELAY_AFTER_NAVIGATION,
    PAUSE_DURING_TYPING_PROBABILITY, RANDOM_ACTIVITY_PROBABILITY,
    DISCORD_LOGIN_URL
)
from utils import parse_roles_string, normalize_username
from exceptions import BrowserError, AuthorizationError

logger = logging.getLogger(__name__)


class DiscordBot:
    """Бот для работы с Discord через браузер"""
    
    def __init__(self, webdriver_url: Optional[str] = None, headless: bool = False):
        """
        Инициализация Discord бота
        
        Args:
            webdriver_url: WebSocket URL для подключения к браузеру ADSpower (CDP endpoint).
                          Если None, запускается локальный браузер.
            headless: Запуск в headless режиме (не используется при подключении к ADSpower)
        """
        self.webdriver_url: Optional[str] = webdriver_url
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.headless: bool = headless
        logger.info("Discord бот инициализирован")
    
    def _convert_ws_to_cdp_endpoint(self, ws_url: str) -> str:
        """
        Преобразование WebSocket URL в CDP endpoint
        
        Args:
            ws_url: WebSocket URL
        
        Returns:
            CDP endpoint URL
        
        Raises:
            BrowserError: Если URL невалиден
        """
        if not ws_url or not ws_url.strip():
            raise BrowserError("WebSocket URL не может быть пустым")
        
        cdp_endpoint = ws_url.strip()
        
        # Преобразуем WebSocket в HTTP для CDP
        if cdp_endpoint.startswith('ws://'):
            cdp_endpoint = cdp_endpoint.replace('ws://', 'http://', 1)
        elif cdp_endpoint.startswith('wss://'):
            cdp_endpoint = cdp_endpoint.replace('wss://', 'https://', 1)
        elif not (cdp_endpoint.startswith('http://') or cdp_endpoint.startswith('https://')):
            # Если URL не в формате HTTP/HTTPS и не содержит протокол, добавляем http://
            if '://' not in cdp_endpoint:
                cdp_endpoint = f"http://{cdp_endpoint}"
        
        # Убираем путь если есть, оставляем только host:port
        if '://' in cdp_endpoint:
            parts = cdp_endpoint.split('://', 1)
            if len(parts) == 2:
                protocol, rest = parts
                # Извлекаем только host:port, убираем путь
                host_port = rest.split('/')[0]
                cdp_endpoint = f"{protocol}://{host_port}"
        
        return cdp_endpoint
    
    def _connect_to_adspower_browser(self, cdp_endpoint: str):
        """
        Подключение к браузеру ADSpower через CDP
        
        Args:
            cdp_endpoint: CDP endpoint URL
        """
        self.browser = self.playwright.chromium.connect_over_cdp(cdp_endpoint)
        logger.info("Успешно подключено к браузеру через CDP")
        
        # Получаем существующий контекст или создаем новый
        contexts = self.browser.contexts
        if contexts:
            self.context = contexts[0]
            logger.info("Используется существующий контекст браузера")
        else:
            self.context = self.browser.new_context()
            logger.info("Создан новый контекст браузера")
        
        # Получаем существующую страницу или создаем новую
        pages = self.context.pages
        if pages:
            self.page = pages[0]
            logger.info("Используется существующая страница")
        else:
            self.page = self.context.new_page()
            logger.info("Создана новая страница")
    
    def _create_local_browser(self):
        """
        Создание локального браузера с антидетект настройками
        """
        viewport = AntiDetect.get_random_viewport()
        user_agent = AntiDetect.get_realistic_user_agent()
        
        self.browser = self.playwright.chromium.launch(headless=self.headless)
        self.context = self.browser.new_context(
            viewport=viewport,
            user_agent=user_agent,
            locale='en-US',
            timezone_id='America/New_York',
            permissions=['geolocation', 'notifications'],
            extra_http_headers={
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
        )
        self.page = self.context.new_page()
        logger.info(f"Локальный браузер запущен (viewport: {viewport['width']}x{viewport['height']})")
    
    def start_browser(self):
        """Запуск браузера"""
        try:
            self.playwright = sync_playwright().start()
            
            if self.webdriver_url:
                logger.info(f"Подключение к браузеру ADSpower: {self.webdriver_url}")
                cdp_endpoint = self._convert_ws_to_cdp_endpoint(self.webdriver_url)
                logger.info(f"Подключение к CDP endpoint: {cdp_endpoint}")
                
                try:
                    self._connect_to_adspower_browser(cdp_endpoint)
                except Exception as e:
                    logger.error(f"Ошибка подключения через CDP: {e}")
                    raise
            else:
                self._create_local_browser()
            
            # Внедряем stealth скрипты для антидетекта
            AntiDetect.inject_stealth_scripts(self.page)
            
            # Устанавливаем таймауты
            self.page.set_default_timeout(config.DISCORD_TIMEOUT * 1000)
            logger.info("Браузер запущен и готов к работе")
        except Exception as e:
            logger.error(f"Ошибка запуска браузера: {e}")
            raise BrowserError(f"Не удалось запустить браузер: {e}") from e
    
    def stop_browser(self):
        """Остановка браузера"""
        try:
            if self.page:
                try:
                    self.page.close()
                except Exception as e:
                    logger.debug(f"Ошибка при закрытии страницы: {e}")
                finally:
                    self.page = None
            if self.context and not self.webdriver_url:
                # Закрываем контекст только если это локальный браузер
                try:
                    self.context.close()
                except Exception as e:
                    logger.debug(f"Ошибка при закрытии контекста: {e}")
                finally:
                    self.context = None
            if self.browser and not self.webdriver_url:
                # Закрываем браузер только если это локальный браузер
                # Для ADSpower не закрываем, так как он управляется ADSpower
                try:
                    self.browser.close()
                except Exception as e:
                    logger.debug(f"Ошибка при закрытии браузера: {e}")
                finally:
                    self.browser = None
            if self.playwright:
                try:
                    self.playwright.stop()
                except Exception as e:
                    logger.debug(f"Ошибка при остановке playwright: {e}")
                finally:
                    self.playwright = None
            logger.info("Браузер остановлен")
        except Exception as e:
            logger.warning(f"Ошибка остановки браузера: {e}")
            # Не поднимаем исключение, так как это cleanup операция
    
    def wait_for_page_load(self, timeout: int = None):
        """
        Ожидание полной загрузки страницы с имитацией человеческого поведения
        
        Args:
            timeout: Таймаут в секундах (по умолчанию из config)
        """
        if not self.page:
            logger.warning("Страница не инициализирована")
            return
        
        if timeout is None:
            timeout = config.DISCORD_TIMEOUT
        
        if timeout <= 0:
            logger.warning(f"Некорректный таймаут: {timeout}, используется значение по умолчанию")
            timeout = config.DISCORD_TIMEOUT
        
        timeout_ms = timeout * 1000
        
        # Проверяем готовность DOM через JavaScript
        try:
            dom_ready = self.page.evaluate("""() => document.readyState === 'complete'""")
            if not dom_ready:
                self.page.wait_for_load_state('domcontentloaded', timeout=timeout_ms)
        except Exception as e:
            logger.debug(f"Ошибка проверки DOM готовности: {e}")
            # Продолжаем, так как это не критично
        
        # Ждем полной загрузки страницы
        try:
            self.page.wait_for_load_state('load', timeout=timeout_ms)
        except Exception as e:
            logger.debug(f"Таймаут ожидания состояния 'load': {e}")
            # Продолжаем, так как страница может быть уже загружена
        
        # Ждем завершения сетевых запросов (опционально)
        try:
            self.page.wait_for_load_state('networkidle', timeout=timeout_ms)
        except Exception:
            # Если networkidle не достигнут, продолжаем (это нормально для динамических страниц)
            pass
        
        # Имитация человеческого поведения после загрузки
        try:
            AntiDetect.random_delay(MIN_DELAY_BEFORE_ACTION, MAX_DELAY_BEFORE_ACTION)
            AntiDetect.random_activity(self.page)
        except Exception as e:
            logger.debug(f"Ошибка при имитации активности: {e}")
            # Не критично, продолжаем
        
        logger.debug("Страница полностью загружена")
    
    def navigate_to_discord(self, url: str = DISCORD_LOGIN_URL):
        """
        Переход на страницу Discord с ожиданием полной загрузки и антидетект
        
        Args:
            url: URL для перехода
        """
        if not self.page:
            raise BrowserError("Страница не инициализирована")
        
        try:
            logger.info(f"Переход на {url}")
            AntiDetect.random_delay(MIN_DELAY_BEFORE_NAVIGATION, MAX_DELAY_BEFORE_NAVIGATION)
            
            self.page.goto(url, wait_until='domcontentloaded')
            self.wait_for_page_load()
            
            AntiDetect.random_activity(self.page)
            AntiDetect.random_delay(MIN_DELAY_AFTER_NAVIGATION, MAX_DELAY_AFTER_NAVIGATION)
            
            logger.info(f"Страница {url} загружена")
        except Exception as e:
            logger.error(f"Ошибка перехода на Discord: {e}")
            raise BrowserError(f"Не удалось перейти на Discord: {e}") from e
    
    def check_authorization(self) -> bool:
        """
        Проверка авторизации в Discord (улучшенная версия)
        
        Returns:
            True если авторизован, False иначе
        """
        if not self.page:
            logger.warning("Страница не инициализирована")
            return False
        
        try:
            self.wait_for_page_load(timeout=AUTH_CHECK_TIMEOUT)
            
            # Используем JavaScript для более надежной проверки
            try:
                auth_check = self.page.evaluate(AUTH_CHECK_SCRIPT)
                if auth_check:
                    logger.info("Пользователь авторизован")
                    return True
            except Exception as e:
                logger.debug(f"Ошибка выполнения скрипта проверки авторизации: {e}")
                # Продолжаем проверку другими способами
            
            # Дополнительная проверка через селекторы
            if self._check_elements_visible(AUTH_SELECTORS, timeout=ELEMENT_WAIT_TIMEOUT):
                logger.info("Пользователь авторизован (найден элемент)")
                return True
            
            # Проверяем наличие формы логина (значит не авторизован)
            if self._check_elements_visible(LOGIN_FORM_SELECTORS, timeout=2):
                logger.warning("Пользователь не авторизован (найдена форма логина)")
                return False
            
            logger.warning("Не удалось определить статус авторизации")
            return False
        except Exception as e:
            logger.error(f"Ошибка проверки авторизации: {e}")
            # Не поднимаем исключение, возвращаем False для возможности повторной попытки
            return False
    
    def _check_elements_visible(self, selectors: List[str], timeout: int = ELEMENT_WAIT_TIMEOUT) -> bool:
        """
        Проверка видимости элементов по списку селекторов
        
        Args:
            selectors: Список селекторов для проверки
            timeout: Таймаут в секундах
        
        Returns:
            True если хотя бы один элемент виден
        """
        if not self.page:
            return False
        
        if timeout is None:
            timeout = ELEMENT_WAIT_TIMEOUT
        
        for selector in selectors:
            try:
                element = self.page.locator(selector).first
                if element.is_visible(timeout=timeout * 1000):
                    return True
            except Exception:
                # Элемент не найден или не виден, пробуем следующий селектор
                continue
        return False
    
    def check_channel_access(self) -> Optional[str]:
        """
        Проверка доступа к каналу и получение текста канала (улучшенная версия)
        
        Returns:
            Текст канала или None если недоступен
        """
        if not self.page:
            logger.warning("Страница не инициализирована")
            return None
            
        try:
            # Используем JavaScript для проверки доступа к каналу
            try:
                channel_text = self.page.evaluate(CHANNEL_ACCESS_SCRIPT)
                
                if channel_text:
                    logger.debug(f"Доступ к каналу подтвержден: {channel_text}")
                    return channel_text
                else:
                    logger.warning("Не удалось определить доступ к каналу")
                    return None
            except Exception as e:
                logger.debug(f"Ошибка выполнения скрипта проверки доступа к каналу: {e}")
                return None
        except Exception as e:
            logger.error(f"Ошибка проверки доступа к каналу: {e}")
            return None
    
    def get_current_username(self) -> Optional[str]:
        """
        Получение текущего username из Discord
        
        Returns:
            Username или None
        """
        try:
            self.wait_for_page_load(timeout=DEFAULT_PAGE_LOAD_TIMEOUT)
            
            # Пытаемся найти username в различных местах интерфейса
            for selector in USERNAME_SELECTORS:
                try:
                    elements = self.page.locator(selector).all()
                    for element in elements:
                        text = element.text_content()
                        if text and ('@' in text or '#' in text):
                            username = text.strip()
                            logger.info(f"Найден username: {username}")
                            return username
                except Exception:
                    # Ошибка при обработке селектора, пробуем следующий
                    continue
            
            logger.warning("Username не найден")
            return None
        except Exception as e:
            logger.error(f"Ошибка получения username: {e}")
            return None
    
    def login(self, email: str, password: str) -> bool:
        """
        Авторизация в Discord с имитацией человеческого ввода
        
        Args:
            email: Email для входа
            password: Пароль
        
        Returns:
            True если успешно, False иначе
        """
        try:
            self.wait_for_page_load()
            
            AntiDetect.random_delay(MIN_DELAY_AFTER_NAVIGATION, MAX_DELAY_AFTER_NAVIGATION)
            
            # Находим и заполняем поле email
            email_input = self._find_visible_element(EMAIL_INPUT_SELECTORS, timeout=ELEMENT_WAIT_TIMEOUT)
            if not email_input:
                raise AuthorizationError("Поле email не найдено")
            
            self._fill_input_humanlike(email_input, email, pause_probability=PAUSE_DURING_TYPING_PROBABILITY)
            logger.debug("Email введен")
            AntiDetect.random_delay(0.3, 0.6)
            
            # Находим и заполняем поле password
            password_input = self._find_visible_element(PASSWORD_INPUT_SELECTORS, timeout=ELEMENT_WAIT_TIMEOUT)
            if not password_input:
                raise AuthorizationError("Поле password не найдено")
            
            self._fill_input_humanlike(password_input, password, faster=True)
            logger.debug("Пароль введен")
            AntiDetect.random_delay(MIN_DELAY_AFTER_ACTION, MAX_DELAY_AFTER_ACTION)
            
            # Находим и нажимаем кнопку входа
            login_button = self._find_visible_element(LOGIN_BUTTON_SELECTORS, timeout=ELEMENT_WAIT_TIMEOUT)
            if not login_button:
                raise AuthorizationError("Кнопка входа не найдена")
            
            self._move_mouse_to_element(login_button)
            login_button.click()
            logger.debug("Кнопка входа нажата")
            
            # Ждем авторизации
            try:
                # Проверяем, что элемент все еще доступен и видим
                # Locator.is_visible() может выбросить исключение, если элемент не найден
                if email_input.is_visible(timeout=1000):
                    email_input.wait_for(state='hidden', timeout=config.DISCORD_TIMEOUT * 1000)
            except Exception:
                # Элемент не найден, уже скрыт или таймаут ожидания - это нормально
                # Используем фиксированную задержку вместо ожидания скрытия элемента
                wait_time = config.DISCORD_WAIT_TIME
                AntiDetect.random_delay(wait_time, wait_time + 2)
            
            # Проверяем успешность авторизации
            if self.check_authorization():
                logger.info("Авторизация успешна")
                AntiDetect.random_delay(MIN_DELAY_AFTER_ACTION, MAX_DELAY_AFTER_ACTION)
                return True
            else:
                logger.warning("Авторизация не удалась")
                return False
        except AuthorizationError:
            raise
        except Exception as e:
            logger.error(f"Ошибка авторизации: {e}")
            raise AuthorizationError(f"Не удалось авторизоваться: {e}") from e
    
    def navigate_to_server(self, server_url: str):
        """
        Переход на сервер Discord по ссылке с ожиданием загрузки и антидетект
        
        Args:
            server_url: Ссылка на сервер (например, https://discord.com/channels/XXXXXXX)
        
        Raises:
            BrowserError: Если страница не инициализирована или произошла ошибка
        """
        if not self.page:
            raise BrowserError("Страница не инициализирована")
        
        if not server_url or not server_url.strip():
            raise BrowserError("URL сервера не может быть пустым")
        
        try:
            server_url = server_url.strip()
            logger.info(f"Переход на сервер: {server_url}")
            AntiDetect.random_delay(MIN_DELAY_BEFORE_NAVIGATION, MAX_DELAY_BEFORE_NAVIGATION)
            
            self.page.goto(server_url, wait_until='domcontentloaded')
            self.wait_for_page_load()
            
            AntiDetect.random_activity(self.page)
            AntiDetect.random_delay(MIN_DELAY_AFTER_NAVIGATION, MAX_DELAY_AFTER_NAVIGATION)
            
            logger.info(f"Сервер {server_url} загружен")
        except Exception as e:
            logger.error(f"Ошибка перехода на сервер: {e}")
            raise BrowserError(f"Не удалось перейти на сервер: {e}") from e
    
    def _find_visible_element(self, selectors: List[str], timeout: int = ELEMENT_WAIT_TIMEOUT):
        """
        Поиск видимого элемента по списку селекторов
        
        Args:
            selectors: Список селекторов для поиска
            timeout: Таймаут в секундах
        
        Returns:
            Locator элемента или None если не найден
        """
        if not self.page:
            logger.warning("Страница не инициализирована")
            return None
        
        if timeout is None:
            timeout = ELEMENT_WAIT_TIMEOUT
            
        for selector in selectors:
            try:
                element = self.page.locator(selector).first
                if element.is_visible(timeout=timeout * 1000):
                    return element
            except Exception as e:
                logger.debug(f"Элемент с селектором {selector} не найден: {e}")
                continue
        return None
    
    def _fill_input_humanlike(self, input_element, text: str, faster: bool = False, pause_probability: float = 0.0):
        """
        Заполнение поля ввода с имитацией человеческого набора
        
        Args:
            input_element: Элемент для ввода
            text: Текст для ввода
            faster: Ускорить ввод (для паролей)
            pause_probability: Вероятность паузы во время ввода
        """
        input_element.click()
        AntiDetect.random_delay(0.2, 0.4)
        
        # Очищаем поле более надежным способом
        try:
            input_element.clear()
        except Exception:
            # Если clear() не поддерживается, используем fill с пустой строкой
            input_element.fill('')
        
        delay_multiplier = 0.7 if faster else 1.0
        for char in text:
            input_element.type(char, delay=AntiDetect.human_type_delay() * 1000 * delay_multiplier)
            if pause_probability > 0 and random.random() < pause_probability:
                AntiDetect.random_delay(0.2, 0.4)
    
    def _move_mouse_to_element(self, element) -> None:
        """
        Движение мыши к элементу перед кликом (имитация человеческого поведения)
        
        Args:
            element: Элемент для движения мыши (Locator)
        """
        if not element or not self.page:
            return
            
        try:
            box = element.bounding_box()
            if box:
                self.page.mouse.move(
                    box['x'] + box['width'] / 2,
                    box['y'] + box['height'] / 2
                )
                AntiDetect.random_delay(0.1, 0.3)
        except Exception as e:
            logger.debug(f"Не удалось переместить мышь к элементу: {e}")
            # Не критичная ошибка, продолжаем
    
    def search_user(self, username: str) -> bool:
        """
        Поиск пользователя на сервере с антидетект
        
        Args:
            username: Username для поиска
        
        Returns:
            True если пользователь найден, False иначе
        """
        if not self.page:
            logger.warning("Страница не инициализирована")
            return False
        
        if not username or not username.strip():
            logger.warning("Username не может быть пустым")
            return False
        
        try:
            username = username.strip()
            self.wait_for_page_load(timeout=DEFAULT_PAGE_LOAD_TIMEOUT)
            AntiDetect.random_delay(MIN_DELAY_BEFORE_ACTION, MAX_DELAY_BEFORE_ACTION)
            
            # Открываем поиск участников через Ctrl+K
            self.page.keyboard.press('Control+k')
            AntiDetect.random_delay(MIN_DELAY_AFTER_ACTION, MAX_DELAY_AFTER_ACTION)
            
            # Находим поле поиска
            search_input = self._find_visible_element(SEARCH_INPUT_SELECTORS, timeout=ELEMENT_WAIT_TIMEOUT)
            if not search_input:
                logger.warning("Поле поиска не найдено")
                self._close_search()
                return False
            
            # Вводим username
            self._fill_input_humanlike(search_input, username)
            AntiDetect.random_delay(1.0, 2.0)
            
            # Проверяем результаты поиска
            username_normalized = normalize_username(username)
            user_element = self._find_user_in_search_results(username_normalized)
            if user_element:
                logger.info(f"Пользователь {username} найден, открываем профиль")
                # Кликаем на результат поиска, чтобы открыть профиль пользователя
                try:
                    user_element.click()
                    AntiDetect.random_delay(1.0, 2.0)
                    self._close_search()
                    return True
                except Exception as e:
                    logger.warning(f"Не удалось открыть профиль пользователя {username}: {e}")
                    self._close_search()
                    return False
            
            logger.warning(f"Пользователь {username} не найден")
            self._close_search()
            return False
        except Exception as e:
            logger.error(f"Ошибка поиска пользователя {username}: {e}")
            self._close_search()
            # Не поднимаем исключение, возвращаем False
            return False
    
    def _find_user_in_search_results(self, username_normalized: str):
        """
        Поиск пользователя в результатах поиска и возврат элемента
        
        Args:
            username_normalized: Нормализованный username
        
        Returns:
            Locator элемента пользователя или None если не найден
        """
        if not self.page:
            return None
        
        if not username_normalized:
            return None
        
        for selector in SEARCH_RESULT_SELECTORS:
            try:
                results = self.page.locator(selector).all()
                for result in results:
                    text = result.text_content()
                    if text:
                        text_lower = text.lower()
                        if username_normalized in text_lower or f"@{username_normalized}" in text_lower:
                            return result
            except Exception:
                # Ошибка при обработке элемента, пробуем следующий
                continue
        return None
    
    def _close_search(self):
        """Закрытие поиска (нажатие Escape)"""
        if not self.page:
            return
        try:
            self.page.keyboard.press('Escape')
        except Exception:
            # Игнорируем ошибки при закрытии поиска
            pass
    
    def get_user_roles(self, username: str) -> List[str]:
        """
        Получение ролей пользователя
        
        Args:
            username: Username пользователя (может быть в формате username#1234 или просто username)
        
        Returns:
            Список ролей
        
        Note:
            ВАЖНО: Скрипт ROLES_COLLECTION_SCRIPT получает данные из nameTag текущей страницы.
            Это означает, что скрипт работает только если на странице уже открыт профиль нужного пользователя.
            
            Если на странице открыт сервер (а не профиль пользователя), nameTag может отсутствовать,
            и скрипт вернет пустой результат. Поэтому сначала находим пользователя через поиск
            и открываем его профиль, затем вызываем скрипт.
            
            Текущая реализация скрипта:
            1. Получает displayName и accountName из nameTag текущей страницы
            2. Открывает список участников
            3. Ищет пользователя в списке по displayName/accountName
            4. Открывает профиль пользователя
            5. Собирает роли
        """
        if not self.page:
            logger.error("Страница не инициализирована")
            return []
        
        if not username or not username.strip():
            logger.warning("Username не может быть пустым")
            return []
        
        try:
            username = username.strip()
            self.wait_for_page_load(timeout=DEFAULT_PAGE_LOAD_TIMEOUT)
            
            # Сначала ищем пользователя через поиск и открываем его профиль
            # Это необходимо, так как скрипт получает данные из nameTag текущей страницы
            if not self.search_user(username):
                logger.warning(f"Пользователь {username} не найден на сервере")
                return []
            
            # Ждем загрузки профиля пользователя
            AntiDetect.random_delay(1.0, 2.0)
            self.wait_for_page_load(timeout=DEFAULT_PAGE_LOAD_TIMEOUT)
            
            # Используем JavaScript для сбора ролей
            # Скрипт получает данные из nameTag текущей страницы (профиль пользователя)
            # и ищет этого пользователя в списке участников для сбора ролей
            try:
                roles_text = self.page.evaluate(ROLES_COLLECTION_SCRIPT)
            except Exception as e:
                logger.error(f"Ошибка выполнения скрипта сбора ролей для {username}: {e}")
                # Поиск уже закрыт в search_user, но на всякий случай закрываем еще раз
                self._close_search()
                return []
            
            # Парсим результат
            roles = parse_roles_string(roles_text) if roles_text else []
            
            if roles:
                logger.info(f"Найдено {len(roles)} ролей для пользователя {username}: {', '.join(roles)}")
            else:
                logger.warning(f"Роли не найдены для пользователя {username}")
            
            return roles
                
        except BrowserError as e:
            logger.error(f"Ошибка браузера при получении ролей для {username}: {e}")
            # Закрываем поиск на случай, если он был открыт
            self._close_search()
            return []
        except Exception as e:
            logger.error(f"Ошибка получения ролей для {username}: {e}")
            # Закрываем поиск на случай, если он был открыт
            self._close_search()
            return []
