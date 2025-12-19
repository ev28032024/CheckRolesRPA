"""
Вспомогательные утилиты для проекта
"""
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


def parse_roles_string(roles_text: str) -> List[str]:
    """
    Парсинг строки ролей, разделенных символом |
    
    Args:
        roles_text: Строка с ролями, разделенными |
    
    Returns:
        Список ролей
    """
    if not roles_text or not roles_text.strip():
        return []
    
    roles = [role.strip() for role in roles_text.split('|') if role.strip()]
    return roles


def format_roles_for_save(roles: List[str]) -> str:
    """
    Форматирование списка ролей для сохранения в таблицу
    
    Args:
        roles: Список ролей
    
    Returns:
        Строка с ролями через запятую
    """
    if not roles:
        return 'Нет ролей'
    return ', '.join(roles)


def create_result_data(roles: List[str], error: str = '') -> Dict[str, Any]:
    """
    Создание структуры данных результата для сохранения
    
    Args:
        roles: Список ролей
        error: Текст ошибки (если была)
    
    Returns:
        Словарь с данными результата
    """
    return {
        'found': len(roles) > 0,
        'roles': format_roles_for_save(roles),
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'error': error
    }


def normalize_username(username: str) -> str:
    """
    Нормализация username (удаление @, приведение к нижнему регистру)
    
    Args:
        username: Исходный username
    
    Returns:
        Нормализованный username
    """
    if not username:
        return ''
    return username.lower().replace('@', '').strip()

