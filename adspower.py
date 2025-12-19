"""
Модуль для работы с ADSpower API
"""
import logging
import requests
from typing import Dict, Optional, List
import config
from exceptions import ADSpowerError

logger = logging.getLogger(__name__)


class ADSpowerClient:
    """Клиент для работы с ADSpower API"""
    
    # Коды успешного ответа ADSpower API
    SUCCESS_CODE = 0
    
    def __init__(self, api_url: str = None, api_key: str = None):
        """
        Инициализация клиента ADSpower
        
        Args:
            api_url: URL API ADSpower
            api_key: API ключ (опционально, для локального API обычно не требуется)
        """
        self.api_url = api_url or config.ADSPOWER_API_URL
        self.api_key = api_key or config.ADSPOWER_API_KEY
        self.session = requests.Session()
        
        # API ключ опционален для локального API
        # Добавляем только если указан
        if self.api_key:
            self.session.headers.update({'Authorization': f'Bearer {self.api_key}'})
            logger.info(f"ADSpower клиент инициализирован с API ключом: {self.api_url}")
        else:
            logger.info(f"ADSpower клиент инициализирован без API ключа: {self.api_url}")
    
    def _make_request(self, endpoint: str, method: str = 'GET', data: Dict = None) -> Dict:
        """
        Выполнение запроса к API
        
        Args:
            endpoint: Конечная точка API
            method: HTTP метод
            data: Данные для отправки
        
        Returns:
            Ответ от API
        
        Raises:
            ADSpowerError: При ошибке запроса или парсинга JSON
        """
        url = f"{self.api_url}/{endpoint.lstrip('/')}"
        
        try:
            if method == 'GET':
                response = self.session.get(url, params=data, timeout=30)
            elif method == 'POST':
                response = self.session.post(url, json=data, timeout=30)
            else:
                raise ValueError(f"Неподдерживаемый метод: {method}")
            
            response.raise_for_status()
            
            # Проверяем, что ответ является JSON
            try:
                return response.json()
            except ValueError as e:
                logger.error(f"Ответ не является валидным JSON: {response.text[:200]}")
                raise ADSpowerError(f"Не удалось распарсить JSON ответ от ADSpower API: {e}") from e
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка запроса к ADSpower API: {e}")
            raise ADSpowerError(f"Ошибка запроса к ADSpower API ({endpoint}): {e}") from e
    
    def get_profile_by_serial(self, serial_number: str) -> Optional[Dict]:
        """
        Получение информации о профиле по serial_number
        
        Args:
            serial_number: Серийный номер профиля
        
        Returns:
            Информация о профиле или None
        """
        try:
            data = self._make_request('api/v1/browser/active', method='POST', data={
                'serial_number': serial_number
            })
            
            if data.get('code') == self.SUCCESS_CODE:
                profile_info = data.get('data', {})
                logger.info(f"Профиль {serial_number} найден")
                return profile_info
            else:
                logger.warning(f"Профиль {serial_number} не найден: {data.get('msg', 'Unknown error')}")
                return None
        except Exception as e:
            logger.error(f"Ошибка получения профиля {serial_number}: {e}")
            return None
    
    def open_browser(self, serial_number: str) -> Optional[str]:
        """
        Открытие браузера профиля
        
        Args:
            serial_number: Серийный номер профиля
        
        Returns:
            WebSocket URL для подключения к браузеру (для Playwright/patchright) или None
        
        Raises:
            ADSpowerError: При ошибке открытия браузера или невалидном serial_number
        """
        if not serial_number or not serial_number.strip():
            raise ADSpowerError("serial_number не может быть пустым")
        
        serial_number = serial_number.strip()
        try:
            data = self._make_request('api/v1/browser/active', method='POST', data={
                'serial_number': serial_number
            })
            
            if data.get('code') == self.SUCCESS_CODE:
                data_obj = data.get('data', {})
                ws_url = self._extract_websocket_url(data_obj)
                
                if ws_url:
                    logger.info(f"Браузер профиля {serial_number} открыт, WebSocket URL: {ws_url}")
                    return ws_url
                else:
                    error_msg = f"WebSocket URL не найден в ответе ADSpower: {data_obj}"
                    logger.error(error_msg)
                    raise ADSpowerError(error_msg)
            else:
                error_msg = data.get('msg', 'Unknown error')
                logger.error(f"Не удалось открыть браузер: {error_msg}")
                raise ADSpowerError(f"Не удалось открыть браузер: {error_msg}")
        except ADSpowerError:
            raise
        except Exception as e:
            logger.error(f"Ошибка открытия браузера: {e}")
            raise ADSpowerError(f"Ошибка открытия браузера: {e}") from e
    
    def _extract_websocket_url(self, data: Dict) -> Optional[str]:
        """
        Извлечение WebSocket URL из ответа ADSpower API
        
        Args:
            data: Объект данных из ответа API
        
        Returns:
            WebSocket URL или None если не найден
        """
        if not data or not isinstance(data, dict):
            logger.debug("Данные для извлечения WebSocket URL пусты или не являются словарем")
            return None
        
        # ADSpower API может возвращать WebSocket URL в разных полях
        # Проверяем наиболее вероятные поля в порядке приоритета
        possible_fields = ['ws', 'ws_url', 'webdriver_url', 'wsUrl', 'webdriverUrl', 'ws_endpoint', 'puppeteer']
        
        def _check_url_value(value: any, field_path: str) -> Optional[str]:
            """Вспомогательная функция для проверки и извлечения URL из значения"""
            if not value:
                return None
            try:
                url = str(value).strip()
                if url and (url.startswith('ws://') or url.startswith('wss://') or 
                           url.startswith('http://') or url.startswith('https://')):
                    logger.debug(f"WebSocket URL найден в '{field_path}': {url[:50]}...")
                    return url
            except Exception as e:
                logger.debug(f"Ошибка обработки значения '{field_path}': {e}")
            return None
        
        # Сначала проверяем прямые поля
        for field in possible_fields:
            url = _check_url_value(data.get(field), field)
            if url:
                return url
        
        # Если не найдено в стандартных полях, ищем вложенные объекты
        ws_obj = data.get('ws')
        if isinstance(ws_obj, dict):
            for field in possible_fields:
                url = _check_url_value(ws_obj.get(field), f'ws.{field}')
                if url:
                    return url
        
        # Проверяем другие возможные вложенные структуры
        for key in ['data', 'result', 'browser']:
            nested_obj = data.get(key)
            if isinstance(nested_obj, dict):
                for field in possible_fields:
                    url = _check_url_value(nested_obj.get(field), f'{key}.{field}')
                    if url:
                        return url
        
        logger.warning(f"WebSocket URL не найден в ответе ADSpower. Доступные ключи: {list(data.keys())}")
        return None
    
    def close_browser(self, serial_number: str) -> bool:
        """
        Закрытие браузера профиля
        
        Args:
            serial_number: Серийный номер профиля
        
        Returns:
            True если успешно, False иначе
        """
        if not serial_number or not serial_number.strip():
            logger.warning("serial_number пуст, пропускаем закрытие браузера")
            return False
        
        serial_number = serial_number.strip()
        try:
            data = self._make_request('api/v1/browser/close', method='POST', data={
                'serial_number': serial_number
            })
            
            if data.get('code') == self.SUCCESS_CODE:
                logger.info(f"Браузер профиля {serial_number} закрыт")
                return True
            else:
                logger.warning(f"Не удалось закрыть браузер: {data.get('msg', 'Unknown error')}")
                return False
        except Exception as e:
            logger.error(f"Ошибка закрытия браузера: {e}")
            return False
    
    def get_browser_list(self) -> List[Dict]:
        """
        Получение списка всех профилей
        
        Returns:
            Список профилей
        """
        try:
            data = self._make_request('api/v1/user/list', method='GET')
            
            if data.get('code') == self.SUCCESS_CODE:
                data_obj = data.get('data', {})
                if isinstance(data_obj, dict):
                    profiles = data_obj.get('list', [])
                else:
                    profiles = []
                logger.info(f"Получено {len(profiles)} профилей")
                return profiles
            else:
                logger.warning(f"Не удалось получить список профилей: {data.get('msg', 'Unknown error')}")
                return []
        except Exception as e:
            logger.error(f"Ошибка получения списка профилей: {e}")
            return []

