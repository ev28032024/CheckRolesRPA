"""
Модели данных для проекта
Используются для типизации и валидации данных
"""
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime


@dataclass
class ProfileData:
    """Данные профиля для работы"""
    serial_number: str
    email: str
    password: str
    username: str
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ProfileData':
        """Создание объекта из словаря"""
        return cls(
            serial_number=data.get('serial_number', ''),
            email=data.get('email', ''),
            password=data.get('password', ''),
            username=data.get('username', '')
        )
    
    def validate(self) -> bool:
        """Валидация данных профиля"""
        return bool(self.serial_number and self.email and self.password)


@dataclass
class CheckResult:
    """Результат проверки ролей"""
    username: str
    found: bool
    roles: str
    timestamp: str
    error: str = ''
    
    @classmethod
    def create(cls, username: str, roles: List[str], error: str = '') -> 'CheckResult':
        """Создание результата проверки"""
        from utils import format_roles_for_save
        
        return cls(
            username=username,
            found=len(roles) > 0,
            roles=format_roles_for_save(roles),
            timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            error=error
        )


@dataclass
class CheckProfile:
    """Профиль для проверки"""
    username: str
    serial_number: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: dict) -> 'CheckProfile':
        """Создание объекта из словаря"""
        return cls(
            username=data.get('username', '').strip(),
            serial_number=data.get('serial_number', '').strip() or None
        )
    
    def validate(self) -> bool:
        """Валидация данных профиля для проверки"""
        return bool(self.username)

