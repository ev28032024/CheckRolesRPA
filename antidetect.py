"""
Модуль для антидетекта автоматизации Discord
"""
import logging
import random
import time
from typing import Optional

logger = logging.getLogger(__name__)


class AntiDetect:
    """Класс для антидетекта автоматизации"""
    
    @staticmethod
    def human_delay(base: float = 1.0, variance: float = 0.5) -> float:
        """
        Генерация случайной задержки, имитирующей человеческое поведение
        
        Args:
            base: Базовая задержка в секундах
            variance: Разброс (0.5 = ±50%)
        
        Returns:
            Случайная задержка в секундах
        """
        min_delay = base * (1 - variance)
        max_delay = base * (1 + variance)
        delay = random.uniform(min_delay, max_delay)
        return delay
    
    @staticmethod
    def random_delay(min_seconds: float = 0.5, max_seconds: float = 2.0):
        """
        Случайная задержка между действиями
        
        Args:
            min_seconds: Минимальная задержка
            max_seconds: Максимальная задержка
        """
        delay = random.uniform(min_seconds, max_seconds)
        time.sleep(delay)
    
    @staticmethod
    def human_type_delay() -> float:
        """
        Задержка между нажатиями клавиш при вводе текста (имитация человеческого набора)
        
        Returns:
            Задержка в секундах
        """
        # Человек печатает со скоростью 40-200 символов в минуту
        # Это примерно 0.3-1.5 секунды между символами
        return random.uniform(0.05, 0.15)  # Быстрый набор с небольшими паузами
    
    @staticmethod
    def human_typing_speed() -> float:
        """
        Скорость ввода текста (символов в секунду)
        
        Returns:
            Скорость ввода
        """
        # 40-200 символов в минуту = 0.67-3.33 символов в секунду
        return random.uniform(0.7, 2.5)
    
    @staticmethod
    def human_type_text(page, selector: str, text: str, delay_between_chars: bool = True):
        """
        Ввод текста с имитацией человеческого набора (синхронная версия)
        
        Args:
            page: Страница Playwright
            selector: Селектор элемента
            text: Текст для ввода
            delay_between_chars: Добавлять ли задержки между символами
        """
        element = page.locator(selector).first
        element.click()
        time.sleep(AntiDetect.human_delay(0.2, 0.3))
        
        if delay_between_chars:
            # Вводим по одному символу с задержками
            for char in text:
                element.type(char, delay=AntiDetect.human_type_delay() * 1000)  # в миллисекундах
                # Иногда делаем небольшие паузы (как будто думаем)
                if random.random() < 0.1:  # 10% вероятность паузы
                    time.sleep(AntiDetect.human_delay(0.3, 0.5))
        else:
            # Быстрый ввод, но с небольшой задержкой
            element.fill(text)
            time.sleep(AntiDetect.human_delay(0.1, 0.2))
    
    @staticmethod
    def get_random_viewport() -> dict:
        """
        Получение случайного разрешения экрана (имитация разных устройств)
        
        Returns:
            Словарь с width и height
        """
        # Популярные разрешения экранов
        viewports = [
            {'width': 1920, 'height': 1080},
            {'width': 1366, 'height': 768},
            {'width': 1536, 'height': 864},
            {'width': 1440, 'height': 900},
            {'width': 1280, 'height': 720},
            {'width': 1600, 'height': 900},
        ]
        return random.choice(viewports)
    
    @staticmethod
    def get_realistic_user_agent() -> str:
        """
        Получение реалистичного User-Agent
        
        Returns:
            User-Agent строка
        """
        # Актуальные User-Agent для Chrome
        chrome_versions = ['120.0.0.0', '121.0.0.0', '122.0.0.0', '123.0.0.0']
        chrome_version = random.choice(chrome_versions)
        
        user_agents = [
            f'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_version} Safari/537.36',
            f'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_version} Safari/537.36 Edg/{chrome_version}',
            f'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_version} Safari/537.36',
        ]
        return random.choice(user_agents)
    
    @staticmethod
    def inject_stealth_scripts(page) -> None:
        """
        Внедрение JavaScript скриптов для скрытия признаков автоматизации
        
        Args:
            page: Страница Playwright
        """
        stealth_script = """
        (function() {
            // Скрываем webdriver флаг
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            
            // Переопределяем plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            
            // Переопределяем languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en']
            });
            
            // Добавляем chrome объект
            window.chrome = {
                runtime: {}
            };
            
            // Переопределяем permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
            
            // Скрываем автоматизацию в WebDriver
            Object.defineProperty(navigator, 'webdriver', {
                get: () => false
            });
            
            // Переопределяем getProperty для webdriver
            try {
                delete navigator.__proto__.webdriver;
            } catch (e) {}
            
            // Добавляем реалистичные свойства
            Object.defineProperty(navigator, 'hardwareConcurrency', {
                get: () => 8
            });
            
            Object.defineProperty(navigator, 'deviceMemory', {
                get: () => 8
            });
            
            // Переопределяем toString для функций
            const getParameter = WebGLRenderingContext.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(parameter) {
                if (parameter === 37445) {
                    return 'Intel Inc.';
                }
                if (parameter === 37446) {
                    return 'Intel Iris OpenGL Engine';
                }
                return getParameter(parameter);
            };
        })();
        """
        
        try:
            page.add_init_script(stealth_script)
            logger.debug("Stealth скрипты внедрены")
        except Exception as e:
            logger.warning(f"Не удалось внедрить stealth скрипты: {e}")
    
    @staticmethod
    def random_mouse_movement(page, duration: float = 0.5):
        """
        Случайное движение мыши (имитация человеческого поведения)
        
        Args:
            page: Страница Playwright
            duration: Длительность движения в секундах
        """
        try:
            viewport = page.viewport_size
            if not viewport:
                return
            
            # Генерируем случайную начальную точку (в центре экрана с небольшим смещением)
            start_x = random.randint(viewport['width'] // 4, viewport['width'] * 3 // 4)
            start_y = random.randint(viewport['height'] // 4, viewport['height'] * 3 // 4)
            
            # Генерируем случайную целевую точку на экране
            end_x = random.randint(100, viewport['width'] - 100)
            end_y = random.randint(100, viewport['height'] - 100)
            
            # Плавное движение мыши от начальной к целевой позиции
            steps = random.randint(10, 20)
            for i in range(steps + 1):
                t = i / steps if steps > 0 else 1.0
                # Линейная интерполяция от начальной к конечной позиции
                current_x = int(start_x + (end_x - start_x) * t)
                current_y = int(start_y + (end_y - start_y) * t)
                
                page.mouse.move(current_x, current_y)
                if i < steps:  # Не ждем после последнего шага
                    time.sleep(duration / steps)
        except Exception as e:
            logger.debug(f"Ошибка движения мыши: {e}")
    
    @staticmethod
    def human_scroll(page, direction: str = 'down', distance: Optional[int] = None):
        """
        Человеческий скроллинг (не мгновенный, с паузами)
        
        Args:
            page: Страница Playwright
            direction: Направление ('up' или 'down')
            distance: Расстояние прокрутки (None = случайное)
        """
        try:
            if distance is None:
                distance = random.randint(200, 800)
            
            # Скроллим небольшими шагами
            steps = random.randint(3, 8)
            step_size = distance // steps
            
            for _ in range(steps):
                if direction == 'down':
                    page.mouse.wheel(0, step_size)
                else:
                    page.mouse.wheel(0, -step_size)
                
                # Случайная пауза между шагами
                time.sleep(random.uniform(0.1, 0.3))
        except Exception as e:
            logger.debug(f"Ошибка скроллинга: {e}")
    
    @staticmethod
    def random_activity(page):
        """
        Случайная активность для имитации человеческого поведения
        
        Args:
            page: Страница Playwright
        """
        activities = [
            lambda: AntiDetect.human_scroll(page, 'down', random.randint(100, 300)),
            lambda: AntiDetect.human_scroll(page, 'up', random.randint(50, 150)),
            lambda: AntiDetect.random_mouse_movement(page, random.uniform(0.3, 0.8)),
        ]
        
        # С вероятностью 30% выполняем случайную активность
        if random.random() < 0.3:
            try:
                activity = random.choice(activities)
                activity()
            except Exception as e:
                logger.debug(f"Ошибка случайной активности: {e}")

