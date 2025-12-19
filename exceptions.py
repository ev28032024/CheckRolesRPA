"""
Кастомные исключения для проекта
"""


class CheckRolesError(Exception):
    """Базовое исключение для проекта"""
    pass


class BrowserError(CheckRolesError):
    """Ошибка работы с браузером"""
    pass


class AuthorizationError(CheckRolesError):
    """Ошибка авторизации"""
    pass


class GoogleSheetsError(CheckRolesError):
    """Ошибка работы с Google Sheets"""
    pass


class ADSpowerError(CheckRolesError):
    """Ошибка работы с ADSpower API"""
    pass


class ConfigurationError(CheckRolesError):
    """Ошибка конфигурации"""
    pass

