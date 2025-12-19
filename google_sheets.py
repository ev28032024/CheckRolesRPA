"""
Модуль для работы с Google Sheets API
"""
import logging
import threading
from typing import List, Dict, Optional
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import config
from exceptions import GoogleSheetsError

logger = logging.getLogger(__name__)


class GoogleSheetsClient:
    """Клиент для работы с Google Sheets"""
    
    def __init__(self, spreadsheet_id: str, credentials_file: str = None):
        """
        Инициализация клиента Google Sheets
        
        Args:
            spreadsheet_id: ID Google таблицы
            credentials_file: Путь к файлу с credentials для Google API
        """
        self.spreadsheet_id = spreadsheet_id
        self.credentials_file = credentials_file or config.GOOGLE_CREDENTIALS_FILE
        self._write_lock = threading.Lock()  # Блокировка для потокобезопасной записи
        
        try:
            # Загрузка credentials
            scopes = ['https://www.googleapis.com/auth/spreadsheets']
            creds = Credentials.from_service_account_file(
                self.credentials_file, 
                scopes=scopes
            )
            self.service = build('sheets', 'v4', credentials=creds)
            logger.info("Google Sheets клиент успешно инициализирован")
        except Exception as e:
            logger.error(f"Ошибка инициализации Google Sheets: {e}")
            raise GoogleSheetsError(f"Не удалось инициализировать Google Sheets клиент: {e}") from e
    
    def read_range(self, sheet_name: str, range_name: Optional[str] = None) -> List[List]:
        """
        Чтение данных из указанного диапазона листа
        
        Args:
            sheet_name: Название листа
            range_name: Диапазон (например, 'A1:D10'). Если None, читает весь лист
        
        Returns:
            Список строк с данными
        """
        try:
            range_str = f"{sheet_name}!{range_name}" if range_name else sheet_name
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=range_str
            ).execute()
            
            values = result.get('values', [])
            logger.debug(f"Прочитано {len(values)} строк из листа {sheet_name}")
            return values
        except HttpError as e:
            logger.error(f"Ошибка чтения из Google Sheets ({sheet_name}): {e}")
            raise GoogleSheetsError(f"Ошибка чтения из листа {sheet_name}: {e}") from e
    
    def write_range(self, sheet_name: str, range_name: str, values: List[List]):
        """
        Запись данных в указанный диапазон листа (потокобезопасно)
        
        Args:
            sheet_name: Название листа
            range_name: Диапазон (например, 'A1')
            values: Данные для записи (список списков)
        """
        with self._write_lock:  # Потокобезопасная запись
            try:
                range_str = f"{sheet_name}!{range_name}"
                body = {'values': values}
                
                self.service.spreadsheets().values().update(
                    spreadsheetId=self.spreadsheet_id,
                    range=range_str,
                    valueInputOption='RAW',
                    body=body
                ).execute()
                
                logger.debug(f"Данные записаны в лист {sheet_name}, диапазон {range_name}")
            except HttpError as e:
                logger.error(f"Ошибка записи в Google Sheets ({sheet_name}): {e}")
                raise GoogleSheetsError(f"Ошибка записи в лист {sheet_name}: {e}") from e
    
    def append_row(self, sheet_name: str, values: List):
        """
        Добавление строки в конец листа (потокобезопасно)
        
        Args:
            sheet_name: Название листа
            values: Данные для добавления
        """
        with self._write_lock:  # Потокобезопасная запись
            try:
                body = {'values': [values]}
                
                self.service.spreadsheets().values().append(
                    spreadsheetId=self.spreadsheet_id,
                    range=sheet_name,
                    valueInputOption='RAW',
                    body=body
                ).execute()
                
                logger.debug(f"Строка добавлена в лист {sheet_name}")
            except HttpError as e:
                logger.error(f"Ошибка добавления строки в Google Sheets ({sheet_name}): {e}")
                raise GoogleSheetsError(f"Ошибка добавления строки в лист {sheet_name}: {e}") from e
    
    def get_profile_data(self) -> Dict:
        """
        Получение данных профиля из листа ds_data
        
        Returns:
            Словарь с данными профиля
        
        Raises:
            GoogleSheetsError: При ошибке чтения из Google Sheets
        """
        try:
            data = self.read_range(config.GOOGLE_SHEET_DS_DATA)
            if not data or len(data) < 2:
                logger.warning(f"Лист {config.GOOGLE_SHEET_DS_DATA} пуст или содержит только заголовки")
                return {}
            
            # Первая строка - заголовки
            # data гарантированно имеет минимум 2 элемента из-за проверки выше
            headers = data[0]
            profile_row = data[1]
            
            profile_data = self.parse_row_to_dict(headers, profile_row)
            logger.debug(f"Получены данные профиля: {list(profile_data.keys())}")
            return profile_data
        except GoogleSheetsError:
            # Пробрасываем GoogleSheetsError как есть
            raise
        except Exception as e:
            logger.error(f"Ошибка получения данных профиля: {e}")
            raise GoogleSheetsError(f"Не удалось получить данные профиля: {e}") from e
    
    def parse_row_to_dict(self, headers: List[str], row: List) -> Dict:
        """
        Парсинг строки в словарь по заголовкам
        
        Args:
            headers: Список заголовков
            row: Список значений
        
        Returns:
            Словарь с данными
        """
        result = {}
        for i, header in enumerate(headers):
            if i < len(row):
                value = row[i]
                # Преобразуем значение в строку, если это не строка
                if value is None:
                    result[header.strip().lower()] = ''
                elif isinstance(value, str):
                    result[header.strip().lower()] = value
                else:
                    result[header.strip().lower()] = str(value)
        return result
    
    def get_discord_links(self) -> List[str]:
        """
        Получение ссылок на Discord каналы из листа ds_link
        
        Returns:
            Список ссылок
        
        Raises:
            GoogleSheetsError: При ошибке чтения из Google Sheets
        """
        try:
            data = self.read_range(config.GOOGLE_SHEET_DS_LINK)
            links = []
            
            # Ссылки в первом столбце (пропускаем заголовок)
            for row in data[1:] if len(data) > 1 else []:
                if row and len(row) > 0 and row[0]:
                    link = str(row[0]).strip()
                    if link and link.startswith('http'):
                        links.append(link)
            
            logger.debug(f"Получено {len(links)} ссылок на Discord каналы")
            return links
        except GoogleSheetsError:
            # Пробрасываем GoogleSheetsError как есть
            raise
        except Exception as e:
            logger.error(f"Ошибка получения ссылок: {e}")
            raise GoogleSheetsError(f"Не удалось получить ссылки на Discord каналы: {e}") from e
    
    def get_check_profiles(self) -> List[Dict]:
        """
        Получение списка профилей для проверки из листа чек-отработка
        
        Returns:
            Список словарей с данными профилей для проверки
        
        Raises:
            GoogleSheetsError: При ошибке чтения из Google Sheets
        """
        try:
            data = self.read_range(config.GOOGLE_SHEET_CHECK)
            if not data or len(data) < 2:
                logger.warning(f"Лист {config.GOOGLE_SHEET_CHECK} пуст или содержит только заголовки")
                return []
            
            headers = data[0]
            profiles = []
            
            for row in data[1:]:
                if not row or not any(row):  # Пропускаем пустые строки
                    continue
                
                profile = self.parse_row_to_dict(headers, row)
                if profile:
                    profiles.append(profile)
            
            logger.debug(f"Получено {len(profiles)} профилей для проверки")
            return profiles
        except GoogleSheetsError:
            # Пробрасываем GoogleSheetsError как есть
            raise
        except Exception as e:
            logger.error(f"Ошибка получения профилей для проверки: {e}")
            raise GoogleSheetsError(f"Не удалось получить профили для проверки: {e}") from e
    
    def save_check_result(self, profile_data: Dict, result: Dict):
        """
        Сохранение результата проверки в лист чек-отработка
        
        Args:
            profile_data: Данные профиля, который проверялся
            result: Результат проверки (username, роли и т.д.)
        
        Raises:
            GoogleSheetsError: При ошибке сохранения
        """
        if not profile_data or not isinstance(profile_data, dict):
            raise GoogleSheetsError("profile_data не может быть пустым и должен быть словарем")
        
        if not result or not isinstance(result, dict):
            raise GoogleSheetsError("result не может быть пустым и должен быть словарем")
        
        try:
            # Валидация и формирование строки результата
            username = str(profile_data.get('username', '')).strip()
            serial_number = str(profile_data.get('serial_number', '')).strip()
            found = bool(result.get('found', False))
            roles = str(result.get('roles', '')).strip()
            timestamp = str(result.get('timestamp', '')).strip()
            error = str(result.get('error', '')).strip()
            
            # Формируем строку результата
            result_row = [
                username,
                serial_number,
                found,
                roles,
                timestamp,
                error
            ]
            
            self.append_row(config.GOOGLE_SHEET_CHECK, result_row)
            logger.debug(f"Результат проверки сохранен для {username}")
        except GoogleSheetsError:
            raise
        except Exception as e:
            logger.error(f"Ошибка сохранения результата проверки: {e}")
            raise GoogleSheetsError(f"Не удалось сохранить результат проверки: {e}") from e

