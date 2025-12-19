"""
Декораторы для проекта
"""
import logging
import time
import functools
from typing import Callable, Any
from exceptions import CheckRolesError

logger = logging.getLogger(__name__)


def handle_errors(error_class: type = CheckRolesError, log_error: bool = True):
    """
    Декоратор для обработки ошибок
    
    Args:
        error_class: Класс исключения для обертки
        log_error: Логировать ли ошибку
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            except error_class:
                raise
            except Exception as e:
                if log_error:
                    logger.error(f"Ошибка в {func.__name__}: {e}")
                raise error_class(f"Ошибка в {func.__name__}: {e}") from e
        return wrapper
    return decorator


def retry_on_error(max_attempts: int = 3, delay: float = 1.0):
    """
    Декоратор для повторных попыток при ошибке
    
    Args:
        max_attempts: Максимальное количество попыток
        delay: Задержка между попытками в секундах
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_attempts:
                        logger.warning(f"Попытка {attempt}/{max_attempts} не удалась в {func.__name__}: {e}")
                        time.sleep(delay * attempt)  # Экспоненциальная задержка
                    else:
                        logger.error(f"Все попытки исчерпаны в {func.__name__}: {e}")
            if last_exception is not None:
                raise last_exception
            # Если мы дошли сюда, значит не было ни одной попытки (max_attempts <= 0)
            raise RuntimeError(f"Не удалось выполнить {func.__name__}: все попытки исчерпаны")
        return wrapper
    return decorator

