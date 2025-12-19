"""
Модуль для управления многопоточностью
"""
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Callable, Any, Optional
from queue import Queue, Empty
import config
from exceptions import CheckRolesError

logger = logging.getLogger(__name__)


class ThreadSafeQueue:
    """Потокобезопасная очередь для распределения задач"""
    
    def __init__(self, items: List[Any]):
        """
        Инициализация очереди
        
        Args:
            items: Список элементов для очереди
        """
        self.queue = Queue()
        for item in items:
            self.queue.put(item)
    
    def get(self, timeout: Optional[float] = None) -> Any:
        """
        Получение элемента из очереди
        
        Args:
            timeout: Таймаут в секундах
        
        Returns:
            Элемент или None если очередь пуста или таймаут
        """
        try:
            return self.queue.get(timeout=timeout)
        except Empty:
            # Таймаут или очередь пуста
            return None
    
    def empty(self) -> bool:
        """Проверка, пуста ли очередь"""
        return self.queue.empty()
    
    def size(self) -> int:
        """Размер очереди"""
        return self.queue.qsize()


class ThreadManager:
    """Менеджер для управления многопоточным выполнением"""
    
    def __init__(self, max_workers: int = None):
        """
        Инициализация менеджера потоков
        
        Args:
            max_workers: Максимальное количество потоков (по умолчанию из config)
        """
        self.max_workers = max_workers or config.THREADING_MAX_WORKERS
        if self.max_workers < 1:
            self.max_workers = 1
            logger.warning("Количество потоков должно быть >= 1, установлено 1")
        
        logger.info(f"ThreadManager инициализирован с {self.max_workers} потоками")
    
    def execute_parallel(
        self,
        tasks: List[Dict[str, Any]],
        worker_func: Callable[[Dict[str, Any]], Any],
        task_name: str = "задача"
    ) -> List[Any]:
        """
        Параллельное выполнение задач
        
        Args:
            tasks: Список задач (словарей с параметрами)
            worker_func: Функция-обработчик задачи
            task_name: Название задачи для логирования
        
        Returns:
            Список результатов выполнения задач
        """
        if not tasks:
            logger.warning(f"Нет задач для выполнения: {task_name}")
            return []
        
        results = []
        errors = []
        
        logger.info(f"Запуск параллельного выполнения {len(tasks)} {task_name} в {self.max_workers} потоках")
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Отправляем все задачи
            future_to_task = {
                executor.submit(worker_func, task): task
                for task in tasks
            }
            
            # Собираем результаты
            for future in as_completed(future_to_task):
                task = future_to_task[future]
                try:
                    result = future.result()
                    results.append(result)
                    logger.debug(f"Задача {task_name} выполнена успешно")
                except Exception as e:
                    error_info = {
                        'task': task,
                        'error': str(e),
                        'error_type': type(e).__name__
                    }
                    errors.append(error_info)
                    logger.error(f"Ошибка выполнения задачи {task_name}: {e}")
        
        logger.info(f"Выполнение завершено: успешно {len(results)}, ошибок {len(errors)}")
        
        if errors:
            logger.warning(f"Обнаружено {len(errors)} ошибок при выполнении задач")
            # Логируем детали первых нескольких ошибок для отладки
            for i, error_info in enumerate(errors[:5], 1):
                logger.debug(f"Ошибка {i}: {error_info.get('error_type', 'Unknown')} - {error_info.get('error', 'No details')}")
        
        return results
    
    def execute_with_queue(
        self,
        items: List[Any],
        worker_func: Callable[[Any], Any],
        task_name: str = "задача"
    ) -> List[Any]:
        """
        Параллельное выполнение задач из очереди
        
        Args:
            items: Список элементов для обработки
            worker_func: Функция-обработчик элемента
            task_name: Название задачи для логирования
        
        Returns:
            Список результатов выполнения задач
        
        Note:
            Этот метод в настоящее время не используется в проекте.
            Рекомендуется использовать execute_parallel вместо него.
        """
        if not items:
            logger.warning(f"Нет элементов для обработки: {task_name}")
            return []
        
        queue = ThreadSafeQueue(items)
        results = []
        errors = []
        
        logger.info(f"Запуск параллельной обработки {len(items)} {task_name} в {self.max_workers} потоках")
        
        def worker():
            """Рабочая функция потока"""
            thread_results = []
            thread_errors = []
            
            while True:
                # ThreadSafeQueue.get() возвращает None при таймауте, не выбрасывает Empty
                item = queue.get(timeout=1.0)
                if item is None:
                    # Таймаут - проверяем, пуста ли очередь
                    # Примечание: между get() и size() возможна race condition, но это приемлемо,
                    # так как если очередь не пуста, мы просто продолжим попытку получить элемент
                    queue_size = queue.size()
                    if queue_size == 0:
                        # Очередь пуста, выходим
                        break
                    # Очередь не пуста (элемент мог быть добавлен во время таймаута), продолжаем
                    continue
                
                # Обрабатываем полученный элемент
                
                try:
                    result = worker_func(item)
                    thread_results.append(result)
                    logger.debug(f"Элемент {task_name} обработан успешно в потоке {threading.current_thread().name}")
                except Exception as e:
                    error_info = {
                        'item': item,
                        'error': str(e),
                        'error_type': type(e).__name__
                    }
                    thread_errors.append(error_info)
                    logger.error(f"Ошибка обработки элемента {task_name} в потоке {threading.current_thread().name}: {e}")
            
            return thread_results, thread_errors
        
        # Запускаем потоки
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [executor.submit(worker) for _ in range(self.max_workers)]
            
            for future in as_completed(futures):
                try:
                    thread_results, thread_errors = future.result()
                    results.extend(thread_results)
                    errors.extend(thread_errors)
                except Exception as e:
                    logger.error(f"Ошибка в потоке: {e}")
        
        logger.info(f"Обработка завершена: успешно {len(results)}, ошибок {len(errors)}")
        
        if errors:
            logger.warning(f"Обнаружено {len(errors)} ошибок при обработке")
        
        return results

